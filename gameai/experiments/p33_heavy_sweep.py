"""P3.3: quét sơ bộ tham số heavy rollout (T, rollout_limit, scale) — SƠ BỘ, không phải số liệu E5.

Bước 1 `calibrate`: hiệu chỉnh `scale` của `sigmoid_value(evaluate, scale)` cho từng T bằng hồi quy
logistic một tham số (chọn trên lưới theo log-likelihood) trên các thế cờ của rollout heavy, seed
50 000–50 199 (tách biệt với seed 0–9 của bước quét, D-12).
Bước 2 `sweep`: 7 cấu hình MCTS (random + T ∈ {100, 300, 1000} × {không cắt; cắt 10 +
sigmoid_value}),
cùng 0,5 s/nước, vs Greedy và vs AlphaBeta depth 2, 10 seed × 2 lượt mỗi cặp.

    python -m gameai.experiments.p33_heavy_sweep calibrate
    python -m gameai.experiments.p33_heavy_sweep sweep --quick
    python -m gameai.experiments.p33_heavy_sweep all [--workers 4] [--allow-code-change]
"""

from __future__ import annotations

import argparse
import csv
import math
import random
import time
from collections.abc import Iterable, Sequence
from pathlib import Path

from gameai.agents.registry import AgentSpec, GameSpec
from gameai.arena import derive_seed, random_opening_moves
from gameai.core.game import P1, result_for
from gameai.experiments.common import add_runner_args, run_match, summarize, write_summary
from gameai.games.kinrow import KInRow
from gameai.heuristics.kinrow_eval import evaluate
from gameai.heuristics.kinrow_rollout import KInRowHeavyRollout

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "results" / "raw"
TABLE_DIR = ROOT / "results" / "tables"
CALIB_RAW = RAW_DIR / "p33_calib_positions.csv"
SCALE_TABLE = TABLE_DIR / "p33_scale_prelim.csv"

N, K = 15, 5
GAME = GameSpec("kinrow", {"n": N, "k": K})
TEMPERATURES = (100, 300, 1000)
SCALES = (100, 200, 300, 500, 1000, 2000, 5000)
CALIB_SEEDS = range(50_000, 50_200)
OPENING_RANGE = (4, 20)  # độ dài khai cuộc ngẫu nhiên (gồm cả hai đầu) của dữ liệu hiệu chỉnh
TIME_LIMIT = 0.5
ROLLOUT_LIMIT = 10
BASE_SEED = 0
N_PAIRS = 10  # seed 0–9, mỗi seed 2 ván đổi lượt
QUICK_PAIRS = 1

CALIB_COLUMNS = ["temperature", "seed", "opening_len", "ply", "to_move", "eval_p1", "z"]
SCALE_COLUMNS = ["temperature", "scale", "n_positions", "n_rollouts", "mean_loglik", "chosen",
                 "extended", "at_edge"]  # fmt: skip
MAX_GRID_EXTENSIONS = 4
WORKER_CHECK_PAIRS = 2  # 4 ván: đủ để 4 worker cùng bận
WORKER_DROP_LIMIT = 0.15

OPPONENTS: dict[str, AgentSpec] = {
    "greedy": AgentSpec("greedy", label="greedy"),
    "ab2": AgentSpec(
        "alphabeta",
        {"depth": 2, "eval": "evaluate", "delta": "delta_eval", "order": "move_score"},
        label="ab2",
    ),
}


# ---------------------------------------------------------------- calibrate


def calibration_samples(temperature: float, seed: int) -> list[dict]:
    """Một rollout hiệu chỉnh: khai cuộc ngẫu nhiên rồi heavy(T) tới hết ván.

    Trả về mọi thế **chưa kết thúc** từ sau khai cuộc (trước mỗi nước rollout), kèm `eval_p1` và
    nhãn `z` = kết quả ván theo góc nhìn P1 (1 / 0.5 / 0). Tất định theo (T, seed).
    """
    rng = random.Random(derive_seed(seed, f"calib-T{temperature}"))
    game = KInRow(N, K)
    n_open = rng.randint(*OPENING_RANGE)
    random_opening_moves(game, n_open, rng)
    policy = KInRowHeavyRollout(temperature)
    samples = []
    ply = 0
    while not game.is_terminal():
        samples.append(
            {"temperature": temperature, "seed": seed, "opening_len": n_open, "ply": ply,
             "to_move": game.current_player(), "eval_p1": evaluate(game, P1)}
        )  # fmt: skip
        game.play(policy(game, rng))
        ply += 1
    z = result_for(game.winner(), P1)
    for s in samples:
        s["z"] = z
    return samples


def generate_calibration(
    seeds: Iterable[int] = CALIB_SEEDS, temperatures: Sequence[float] = TEMPERATURES
) -> list[dict]:
    rows = []
    for t in temperatures:
        for s in seeds:
            rows.extend(calibration_samples(t, s))
    return rows


def _log_sigmoid(x: float) -> float:
    """log σ(x), ổn định số với |x| lớn."""
    if x >= 0:
        return -math.log1p(math.exp(-x))
    return x - math.log1p(math.exp(x))


def mean_loglik(samples: Iterable[tuple[float, float]], scale: float) -> float:
    """Trung bình z·log σ(e/scale) + (1−z)·log(1−σ(e/scale)) trên các cặp (e, z); z ∈ [0, 1]."""
    total, n = 0.0, 0
    for e, z in samples:
        x = e / scale
        total += z * _log_sigmoid(x) + (1 - z) * _log_sigmoid(-x)
        n += 1
    return total / n if n else math.nan


def fit_scale_grid(
    samples: Sequence[tuple[float, float]],
    scales: Sequence[float] = SCALES,
    max_extensions: int = MAX_GRID_EXTENSIONS,
) -> tuple[dict[float, float], float]:
    """Log-likelihood trên lưới; nếu tốt nhất nằm ở **biên** thì mở rộng lưới (biên dưới ÷2, biên
    trên ×2) và fit lại, tối đa `max_extensions` lần. Trả ({scale: mean_loglik}, scale tốt nhất).
    """
    lls = {float(s): mean_loglik(samples, s) for s in scales}
    for _ in range(max_extensions + 1):
        grid = sorted(lls)
        best = max(grid, key=lambda s: lls[s])
        if best == grid[0]:
            new = grid[0] / 2
        elif best == grid[-1]:
            new = grid[-1] * 2
        else:
            break
        if len(lls) >= len(scales) + max_extensions:
            break  # vẫn ở biên sau khi đã mở rộng tối đa → `at_edge = 1` trong bảng
        lls[new] = mean_loglik(samples, new)
    return lls, max(lls, key=lambda s: lls[s])


def fit_scales(rows: Iterable[dict], scales: Sequence[float] = SCALES) -> list[dict]:
    """Bảng log-likelihood theo (T, scale); `chosen = 1` ở scale tốt nhất của mỗi T.

    `extended = 1`: scale được thêm khi mở rộng lưới; `at_edge = 1` (ở dòng chosen): vẫn nằm ở biên
    của lưới cuối cùng.
    """
    groups: dict[float, list[tuple[float, float]]] = {}
    rollouts: dict[float, set] = {}
    for r in rows:
        t = float(r["temperature"])
        groups.setdefault(t, []).append((float(r["eval_p1"]), float(r["z"])))
        rollouts.setdefault(t, set()).add(r["seed"])
    base = {float(s) for s in scales}
    out = []
    for t in sorted(groups):
        lls, best = fit_scale_grid(groups[t], scales)
        grid = sorted(lls)
        for s in grid:
            out.append(
                {"temperature": _num(t), "scale": _num(s), "n_positions": len(groups[t]),
                 "n_rollouts": len(rollouts[t]), "mean_loglik": round(lls[s], 6),
                 "chosen": int(s == best), "extended": int(s not in base),
                 "at_edge": int(s == best and s in (grid[0], grid[-1]))}
            )  # fmt: skip
    return out


def chosen_scales(table: Iterable[dict]) -> dict[float, float]:
    """{T: scale} từ các dòng `chosen = 1` của bảng hiệu chỉnh."""
    return {float(r["temperature"]): float(r["scale"]) for r in table if int(r["chosen"]) == 1}


def _num(x: float) -> int | float:
    return int(x) if float(x).is_integer() else x


def _write_csv(path: Path, columns: list[str], rows: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, columns)
        w.writeheader()
        w.writerows(rows)


def _read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def calibrate(raw: Path = CALIB_RAW, table: Path = SCALE_TABLE) -> dict[float, float]:
    """Sinh (hoặc dùng lại) dữ liệu hiệu chỉnh, ghi bảng scale, trả {T: scale đã chọn}."""
    t0 = time.perf_counter()
    if raw.exists():
        rows = _read_csv(raw)
        print(f"calibrate: reuse {raw.name} ({len(rows)} positions)")
    else:
        rows = generate_calibration()
        _write_csv(raw, CALIB_COLUMNS, rows)
        print(f"calibrate: generated {len(rows)} positions in {time.perf_counter() - t0:.1f} s")
    fitted = fit_scales(rows)
    _write_csv(table, SCALE_COLUMNS, fitted)
    for line in describe_fit(fitted):
        print(line)
    return chosen_scales(fitted)


def describe_fit(fitted: Sequence[dict]) -> list[str]:
    """Mỗi T một dòng: scale chọn + mean_loglik của nó và hai scale kề bên (ASCII)."""
    lines = []
    temps = sorted({float(r["temperature"]) for r in fitted})
    for t in temps:
        rs = sorted(
            (r for r in fitted if float(r["temperature"]) == t), key=lambda r: float(r["scale"])
        )
        i = next(j for j, r in enumerate(rs) if int(r["chosen"]))
        parts = [f"{r['scale']}:{float(r['mean_loglik']):.5f}" for r in rs[max(i - 1, 0) : i + 2]]
        ext = " (grid extended)" if any(int(r["extended"]) for r in rs) else ""
        edge = " WARNING still at grid edge" if int(rs[i]["at_edge"]) else ""
        lines.append(f"  T={_num(t)}: scale={rs[i]['scale']} n={rs[i]['n_positions']} "
                     f"[{' | '.join(parts)}]{ext}{edge}")  # fmt: skip
    return lines


# ---------------------------------------------------------------- sweep


def sweep_configs(scales: dict[float, float]) -> list[AgentSpec]:
    """7 cấu hình MCTS cùng `time_limit` 0,5 s/nước, `check_tactics=False` (D-12)."""
    base = {"iterations": None, "time_limit": TIME_LIMIT, "check_tactics": False}
    specs = [AgentSpec("mcts", {**base, "rollout": "random"}, label="rand")]
    for t in TEMPERATURES:
        heavy = {**base, "rollout": "heavy_kinrow", "temperature": t}
        specs.append(AgentSpec("mcts", {**heavy, "rollout_limit": None}, label=f"h{t}"))
    for t in TEMPERATURES:
        if float(t) not in scales:
            raise KeyError(f"thiếu scale cho T={t}: chạy `calibrate` trước")
        heavy = {**base, "rollout": "heavy_kinrow", "temperature": t}
        specs.append(
            AgentSpec(
                "mcts",
                {**heavy, "rollout_limit": ROLLOUT_LIMIT, "value_scale": _num(scales[float(t)])},
                label=f"h{t}c{ROLLOUT_LIMIT}",
            )
        )
    return specs


def _prefix(quick: bool) -> str:
    return "p33quick" if quick else "p33"


def match_path(config: str, opponent: str, quick: bool) -> Path:
    return RAW_DIR / f"{_prefix(quick)}_{config}_vs_{opponent}.csv"


def summary_path(quick: bool) -> Path:
    return TABLE_DIR / f"{_prefix(quick)}_sweep_prelim.csv"


def _game_seconds(rows: Iterable[dict[str, str]]) -> float:
    return sum(float(r["a_time_sum"] or 0) + float(r["b_time_sum"] or 0) for r in rows)


def sweep(quick: bool, workers: int, allow_code_change: bool) -> None:
    if not SCALE_TABLE.exists():
        raise SystemExit(f"missing {SCALE_TABLE}: run `calibrate` first")
    scales = chosen_scales(_read_csv(SCALE_TABLE))
    configs = sweep_configs(scales)
    n_pairs = QUICK_PAIRS if quick else N_PAIRS
    all_rows: list[dict[str, str]] = []
    for opp_label, opp in OPPONENTS.items():
        wall0 = time.perf_counter()
        opp_rows: list[dict[str, str]] = []
        for spec in configs:
            t0 = time.perf_counter()
            rows = run_match(
                match_path(spec.name, opp_label, quick), GAME, spec, opp,
                n_pairs=n_pairs, base_seed=BASE_SEED, workers=workers, random_opening=0,
                allow_code_change=allow_code_change,
            )  # fmt: skip
            opp_rows.extend(rows)
            score = sum(float(r["result_a"]) for r in rows)
            print(f"  {spec.name:9s} vs {opp_label:6s}: {len(rows)} games, score {score:.1f}, "
                  f"wall {time.perf_counter() - t0:.1f} s")  # fmt: skip
        wall = time.perf_counter() - wall0
        game_s = _game_seconds(opp_rows)
        factor = N_PAIRS / n_pairs
        print(f"vs {opp_label}: {len(configs)} configs, {len(opp_rows)} games, wall {wall:.0f} s, "
              f"sum game time {game_s:.0f} s")  # fmt: skip
        if quick:
            print(f"  estimate full ({len(configs) * 2 * N_PAIRS} games): sequential "
                  f"~{game_s * factor / 60:.0f} min, {workers} workers ~"
                  f"{game_s * factor / workers / 60:.0f} min")  # fmt: skip
        all_rows.extend(opp_rows)
    write_summary(summarize(all_rows), summary_path(quick))
    print(f"summary -> {summary_path(quick).relative_to(ROOT)} (PRELIMINARY, not E5)")
    if quick:
        worker_check(configs[0], workers, allow_code_change)


def worker_check_path(workers: int) -> Path:
    return RAW_DIR / f"p33quick_wcheck_rand_vs_greedy_w{workers}.csv"


def iterations_per_move(rows: Sequence[dict[str, str]]) -> float:
    """a_iterations_per_move của dòng "all" (A = MCTS)."""
    return next(s["a_iterations_per_move"] for s in summarize(rows) if s["split"] == "all")


def worker_check(spec: AgentSpec, workers: int, allow_code_change: bool) -> None:
    """Ngân sách thời gian nhạy với tải: so iteration/nước của rand vs greedy khi 1 và `workers`
    tiến trình (cùng 2 seed × 2 lượt). Giảm > 15% → cảnh báo."""
    ipm = {}
    for w in (1, workers):
        rows = run_match(
            worker_check_path(w), GAME, spec, OPPONENTS["greedy"], n_pairs=WORKER_CHECK_PAIRS,
            base_seed=BASE_SEED, workers=w, allow_code_change=allow_code_change,
        )  # fmt: skip
        ipm[w] = iterations_per_move(rows)
        print(f"worker check: {spec.name} vs greedy, workers={w}: {ipm[w]:.0f} iterations/move")
    drop = 1 - ipm[workers] / ipm[1]
    flag = "  >15% DROP -> reduce workers for full" if drop > WORKER_DROP_LIMIT else "  ok"
    print(f"  workers={workers} vs 1: {-drop:+.1%}{flag}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("step", choices=("calibrate", "sweep", "all"))
    ap.add_argument("--quick", action="store_true",
                    help=f"{QUICK_PAIRS} seed x 2 games/match, files p33quick_*")  # fmt: skip
    add_runner_args(ap)
    args = ap.parse_args()
    if args.step in ("calibrate", "all"):
        calibrate()
    if args.step in ("sweep", "all"):
        sweep(args.quick, args.workers, args.allow_code_change)


if __name__ == "__main__":
    main()
