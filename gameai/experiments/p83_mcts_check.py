"""P8.3: MCTS cờ tướng (rollout cắt L ply + `sigmoid_value(xq_evaluate)`): cấu hình mẫu + đo.

Lệnh con (`python -m gameai.experiments.p83_mcts_check <lệnh> [--quick]`):
  speed   iter/s theo L          -> results/tables/p83_speed.csv (metric `iter_per_s`, ...)
  labels  sinh nhãn hiệu chỉnh `scale` (AB depth 1 tự đấu, khai cuộc ngẫu nhiên) -> local_out/p83/,
          IN tỉ lệ ván phân thắng thua (D-24: < 30 % → AB depth 2). Chưa fit.
  fit     hồi quy logistic scale trên lưới -> results/tables/p83_scale_fit.csv
  lmatch  L=0 vs L=10 đấu trực tiếp (tiêu chí chốt trước, D-24) -> thêm dòng vào p83_speed.csv
  tactics ms/nước + % đi thẳng của `check_tactics` -> results/tables/p83_tactics_cost.csv
Số đo trên **một máy**, minh họa — không phải số liệu thí nghiệm (E7 ở P8.4).
"""

from __future__ import annotations

import argparse
import csv
import math
import random
import sys
import time
from pathlib import Path
from typing import Any

from gameai.agents.registry import AgentSpec, GameSpec, make_agent, make_game
from gameai.arena import derive_seed, random_opening_moves
from gameai.core.game import P1, result_for
from gameai.experiments.p82_ab_check import ab_spec, midgame_fens, run_match
from gameai.games.xiangqi import START_FEN, Xiangqi
from gameai.heuristics.xiangqi_eval import MATERIAL

TABLES = Path("results/tables")
LOCAL = Path("local_out/p83")
FIELDS = ["metric", "config", "value", "unit", "n_samples", "note"]

# ---- cấu hình mẫu (D-24)
XQ_MCTS_C = math.sqrt(2)  # mặc định UCB1, không tinh chỉnh
XQ_MCTS_L = 10  # số ply rollout trước khi chấm eval (chốt ở D-24 theo `lmatch`)
XQ_MCTS_SCALE = 2000.0  # fit main, AB depth 2 (p83_scale_fit.csv, D-24)
XQ_MCTS_TIME_LIMIT = 1.0
SCALES = (100, 200, 300, 500, 1000, 2000, 5000)
CALIB_SEEDS = range(50_000, 50_200)  # tách biệt seed ván 0–9 (D-12)
OPENING_RANGE = (2, 8)
LABEL_MAX_PLIES = 300


def xq_mcts_spec(
    time_limit: float | None = XQ_MCTS_TIME_LIMIT,
    iterations: int | None = None,
    rollout_limit: int = XQ_MCTS_L,
    scale: float = XQ_MCTS_SCALE,
    tactics: bool = False,
    c: float = XQ_MCTS_C,
    label: str | None = None,
) -> AgentSpec:
    """MCTS cờ tướng qua registry: rollout cắt `rollout_limit` ply rồi σ(xq_evaluate/scale)."""
    params: dict[str, Any] = {
        "iterations": iterations,
        "c": c,
        "rollout_limit": rollout_limit,
        "value_eval": "xq_evaluate",
        "value_scale": scale,
        "check_tactics": tactics,
    }
    if time_limit is not None:
        params["time_limit"] = time_limit
    return AgentSpec("mcts", params, label=label)


def wilson_score(score: float, n: int, z: float = 1.96) -> tuple[float, float]:
    """Khoảng Wilson 95 % cho điểm (W + 0,5·D)/n (coi như tỉ lệ)."""
    if n == 0:
        return math.nan, math.nan
    d = 1 + z * z / n
    centre = (score + z * z / (2 * n)) / d
    half = z * math.sqrt(score * (1 - score) / n + z * z / (4 * n * n)) / d
    return centre - half, centre + half


def _write(
    path: Path, rows: list[dict[str, Any]], keep_prefix: tuple[str, ...] = (), keep: bool = False
) -> None:
    """Ghi CSV; `keep_prefix` cho trước → giữ dòng cũ có (keep) / không có (not keep) tiền tố đó."""
    old: list[dict[str, Any]] = []
    if keep_prefix and path.exists():
        with path.open(encoding="utf-8", newline="") as fh:
            old = [r for r in csv.DictReader(fh) if r["metric"].startswith(keep_prefix) == keep]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(old + rows)


def _row(metric: str, config: str, value: Any, unit: str, n: int, note: str) -> dict[str, Any]:
    return {
        "metric": metric,
        "config": config,
        "value": value,
        "unit": unit,
        "n_samples": n,
        "note": note,
    }


# ---------------------------------------------------------------- speed
def cmd_speed(args: argparse.Namespace) -> int:
    fens = [START_FEN] + midgame_fens(8, seed=82)
    tl = args.time_limit
    rows = []
    for L in (0, 10, 20, 40):
        its, depth, nodes, plies = [], [], [], []
        for fen in fens:
            a = make_agent(xq_mcts_spec(time_limit=tl, rollout_limit=L), 1)
            a.select_move(Xiangqi(fen))
            its.append(a.stats["iterations"] / a.stats["time"])
            depth.append(a.stats["max_depth"])
            nodes.append(a.stats["nodes"])
            plies.append(a.stats["rollout_plies"] / max(1, a.stats["iterations"]))
        n = len(fens)
        note = (
            f"{n} thế (đầu + giữa ván), time_limit {tl} s, scale {XQ_MCTS_SCALE:g} "
            f"seed 1, tactics tắt"
        )
        cfg = f"L={L}"
        rows += [
            _row(
                "iter_per_s", cfg, round(sum(its) / n), "iter/s", n, note + f"; min {min(its):.0f}"
            ),
            _row("max_depth_mean", cfg, round(sum(depth) / n, 2), "ply", n, note),
            _row("nodes_mean", cfg, round(sum(nodes) / n), "nodes", n, note),
            _row("rollout_plies_per_iter", cfg, round(sum(plies) / n, 2), "ply", n, note),
        ]
        print(f"L={L:>2}: {rows[-4]['value']} iter/s, depth {rows[-3]['value']}")
    t0 = time.perf_counter()
    g = Xiangqi(fens[3])
    for _ in range(20000):
        from gameai.heuristics.xiangqi_eval import evaluate

        evaluate(g, P1)
    us = (time.perf_counter() - t0) / 20000 * 1e6
    rows.append(_row("evaluate", "xq_evaluate", round(us, 2), "us/call", 20000, "1 thế giữa ván"))
    _write(args.out or TABLES / "p83_speed.csv", rows, keep_prefix=("lmatch",), keep=True)
    print(f"evaluate {us:.2f} us/call")
    return 0


# ---------------------------------------------------------------- labels / fit
def _label_game(seed: int, depth: int) -> list[dict[str, Any]]:
    from gameai.heuristics.xiangqi_eval import evaluate

    rng = random.Random(derive_seed(seed, "p83-calib"))
    game = make_game(GameSpec("xiangqi", {"max_plies": LABEL_MAX_PLIES}))
    n_open = rng.randint(*OPENING_RANGE)
    random_opening_moves(game, n_open, rng)
    spec = ab_spec(depth)
    a, b = make_agent(spec, None), make_agent(spec, None)
    samples: list[dict[str, Any]] = []
    # play_game ghi nước nhưng không cho móc từng thế → tự chạy vòng ngắn
    while not game.is_terminal():
        samples.append({"seed": seed, "ply": game.ply, "eval_p1": evaluate(game, P1)})
        game.play((a if game.current_player() == P1 else b).select_move(game))
    z = result_for(game.winner(), P1)
    if z != 0.5:
        term = "win"
    elif game.ply >= game.max_plies:
        term = "max_plies"
    else:
        term = "repetition"
    mat = sum(MATERIAL[abs(p)] * (1 if p > 0 else -1) for p in game.board if p)
    for s in samples:
        s["z"] = z
        s["n_open"] = n_open
        s["total_ply"] = game.ply
        s["term"] = term
        s["end_material"] = mat
    return samples


def cmd_labels(args: argparse.Namespace) -> int:
    seeds = list(CALIB_SEEDS)[: args.games or (20 if args.quick else len(CALIB_SEEDS))]
    out = LOCAL / f"labels_d{args.depth}{'_quick' if args.quick else ''}.csv"
    rows: list[dict[str, Any]] = []
    zs: list[float] = []
    t0 = time.perf_counter()
    for s in seeds:
        g = _label_game(s, args.depth)
        rows += g
        zs.append(g[0]["z"] if g else 0.5)
    secs = time.perf_counter() - t0
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(
            fh,
            fieldnames=[
                "seed",
                "n_open",
                "ply",
                "total_ply",
                "eval_p1",
                "z",
                "term",
                "end_material",
            ],
        )
        w.writeheader()
        w.writerows(rows)
    n = len(zs)
    red, blk, draw = zs.count(1.0), zs.count(0.0), zs.count(0.5)
    first = [r for r in rows if r["ply"] == r["n_open"]]
    for term in ("win", "repetition", "max_plies"):
        g = [r for r in first if r["term"] == term]
        if g:
            m = sum(r["end_material"] for r in g) / len(g)
            am = sum(abs(r["end_material"]) for r in g) / len(g)
            print(f"  {term:<10} {len(g):>3} ván: vật chất Đỏ−Đen TB {m:+.0f}, |.| TB {am:.0f}")
    lens = [r["total_ply"] for r in rows if r["ply"] == r["n_open"]] or [0]
    print(f"nhãn AB depth {args.depth}: {n} ván, {secs:.0f} s, {len(rows)} thế -> {out}")
    print(f"  Đỏ thắng {red}, Đen thắng {blk}, hòa {draw}; phân thắng thua {(red + blk) / n:.1%}")
    print(f"  độ dài ván trung bình {sum(lens) / len(lens):.0f} ply (max_plies {LABEL_MAX_PLIES})")
    return 0


def _log_sigmoid(x: float) -> float:
    return -math.log1p(math.exp(-x)) if x >= 0 else x - math.log1p(math.exp(x))


def mean_loglik(samples: list[tuple[float, float]], scale: float) -> float:
    t = 0.0
    for e, z in samples:
        x = e / scale
        t += z * _log_sigmoid(x) + (1 - z) * _log_sigmoid(-x)
    return t / len(samples)


def fit_scale(samples: list[tuple[float, float]], max_ext: int = 4) -> dict[float, float]:
    """LL trung bình trên lưới SCALES; tốt nhất ở biên → mở rộng (÷2 / ×2), tối đa `max_ext` lần."""
    lls = {float(s): mean_loglik(samples, s) for s in SCALES}
    for _ in range(max_ext):
        grid = sorted(lls)
        best = max(grid, key=lls.get)
        if best == grid[0]:
            new = grid[0] / 2
        elif best == grid[-1]:
            new = grid[-1] * 2
        else:
            break
        lls[new] = mean_loglik(samples, new)
    return lls


def cmd_fit(args: argparse.Namespace) -> int:
    """Hai bản: `main` (hòa = 0,5) và `no_draw` (bỏ ván hòa). Lệch scale > 2× → báo người dùng."""
    src = LOCAL / f"labels_d{args.depth}{'_quick' if args.quick else ''}.csv"
    with src.open(encoding="utf-8") as fh:
        data = list(csv.DictReader(fh))
    firsts = {r["seed"]: r for r in data if r["ply"] == r["n_open"]}
    zs = [float(r["z"]) for r in firsts.values()]
    note0 = (
        f"AB depth {args.depth} tự đấu: {len(zs)} ván, Đỏ thắng {zs.count(1.0)}, "
        f"Đen thắng {zs.count(0.0)}, hòa {zs.count(0.5)}"
    )
    variants = {
        "main": [(float(r["eval_p1"]), float(r["z"])) for r in data],
        "no_draw": [(float(r["eval_p1"]), float(r["z"])) for r in data if float(r["z"]) != 0.5],
    }
    base = {float(s) for s in SCALES}
    rows, best_of = [], {}
    fields = [
        "label_depth",
        "variant",
        "scale",
        "mean_loglik",
        "n_positions",
        "n_games",
        "chosen",
        "extended",
        "at_edge",
        "note",
    ]
    for name, smp in variants.items():
        n_games = len(zs) if name == "main" else sum(z != 0.5 for z in zs)
        lls = fit_scale(smp)
        best = max(lls, key=lls.get)
        best_of[name] = best
        grid = sorted(lls)
        for s in grid:
            rows.append(
                {
                    "label_depth": args.depth,
                    "variant": name,
                    "scale": int(s) if float(s).is_integer() else s,
                    "mean_loglik": round(lls[s], 6),
                    "n_positions": len(smp),
                    "n_games": n_games,
                    "chosen": int(s == best),
                    "extended": int(s not in base),
                    "at_edge": int(s == best and s in (grid[0], grid[-1])),
                    "note": note0,
                }
            )
        print(
            f"[{name}] scale tốt nhất {best:g} (LL {lls[best]:.4f}); {len(smp)} thế, {n_games} ván"
        )
        for s in grid:
            print(f"    scale {s:>7g}: LL {lls[s]:.5f}{'  <-' if s == best else ''}")
    out = args.out or TABLES / "p83_scale_fit.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    old: list[dict[str, Any]] = []
    if out.exists():  # giữ dòng của các depth nhãn khác (file cũ chưa có cột label_depth = depth 1)
        with out.open(encoding="utf-8", newline="") as fh:
            for r in csv.DictReader(fh):
                r.setdefault("label_depth", 1)
                if int(r["label_depth"] or 1) != args.depth:
                    old.append(r)
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(sorted(old + rows, key=lambda r: int(r["label_depth"])))
    ratio = max(best_of.values()) / min(best_of.values())
    print(
        f"tỉ số scale hai bản = {ratio:.2f}× "
        f"({'LỆCH > 2× → no_draw' if ratio > 2 else 'ổn → main'})"
    )
    return 0


# ---------------------------------------------------------------- lmatch
def cmd_lmatch(args: argparse.Namespace) -> int:
    """Tiêu chí (chốt TRƯỚC khi đo, D-24): chọn L điểm cao hơn; ngang (CI Wilson chồng lấn VÀ
    chênh điểm < 0,1) → L=10."""
    pairs = args.pairs or (3 if args.quick else 25)
    a = xq_mcts_spec(time_limit=args.time_limit, rollout_limit=0, scale=args.scale, label="L0")
    b = xq_mcts_spec(time_limit=args.time_limit, rollout_limit=10, scale=args.scale, label="L10")
    t0 = time.perf_counter()
    res = run_match(a, b, n_pairs=pairs, base_seed=args.base_seed, max_plies=args.max_plies)
    secs = time.perf_counter() - t0
    n = len(res["games"])
    lo, hi = wilson_score(res["score"], n)
    lo2, hi2 = 1 - hi, 1 - lo  # điểm của L=10
    overlap = lo <= hi2 and lo2 <= hi
    diff = abs(res["score"] - (1 - res["score"]))  # |điểm L0 − điểm L10|
    if overlap and diff < 0.1:
        pick = 10
    else:
        pick = 0 if res["score"] > 0.5 else 10
    note = (
        f"L=0 vs L=10, time_limit {args.time_limit} s, scale {args.scale:g}, "
        f"{pairs} khai cuộc × 2 bên, "
        f"max_plies {args.max_plies}, W/D/L (L=0) = {res['W']}/{res['D']}/{res['L']}, "
        f"Wilson95 [{lo:.2f}, {hi:.2f}], lỗi {res['errors']}, {secs:.0f} s"
    )
    rows = [
        _row("lmatch_score_L0", "L0_vs_L10", round(res["score"], 3), "score", n, note),
        _row("lmatch_pick", "L0_vs_L10", pick, "L", n, "tiêu chí: điểm cao hơn; ngang → L=10"),
    ]
    print(note)
    print(f"-> chọn L={pick}")
    if not args.quick:
        _write(args.out or TABLES / "p83_speed.csv", rows, keep_prefix=("lmatch",))
    return 0


# ---------------------------------------------------------------- tactics
def cmd_tactics(args: argparse.Namespace) -> int:
    fens = [START_FEN] + midgame_fens(args.n - 1, seed=83)
    rows = []
    for tactics in (False, True):
        ms, direct = [], 0
        for fen in fens:
            a = make_agent(
                xq_mcts_spec(time_limit=None, iterations=args.iterations, tactics=tactics), 1
            )
            t0 = time.perf_counter()
            a.select_move(Xiangqi(fen))
            ms.append((time.perf_counter() - t0) * 1000)
            direct += a.stats["tactic"] in (1, 2)
        n = len(fens)
        state = "bật" if tactics else "tắt"
        note = f"{n} thế, {args.iterations} iteration cố định, L={XQ_MCTS_L}, tactics {state}"
        cfg = f"tactics={'on' if tactics else 'off'}"
        rows += [
            _row("ms_per_move", cfg, round(sum(ms) / n, 1), "ms", n, note + f"; max {max(ms):.0f}"),
            _row("direct_move_pct", cfg, round(100 * direct / n, 1), "%", n, note),
        ]
        print(f"{cfg}: {rows[-2]['value']} ms/nước, đi thẳng {rows[-1]['value']} %")
    _write(args.out or TABLES / "p83_tactics_cost.csv", rows)
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn in (("speed", cmd_speed), ("labels", cmd_labels), ("fit", cmd_fit),
                     ("lmatch", cmd_lmatch), ("tactics", cmd_tactics)):  # fmt: skip
        p = sub.add_parser(name)
        p.set_defaults(fn=fn)
        p.add_argument("--quick", action="store_true")
        p.add_argument("--out", type=Path)
        p.add_argument("--depth", type=int, default=1, help="độ sâu AB sinh nhãn")
        p.add_argument("--games", type=int, default=0)
        p.add_argument("--time-limit", type=float, default=XQ_MCTS_TIME_LIMIT)
        p.add_argument("--scale", type=float, default=XQ_MCTS_SCALE)
        p.add_argument("--pairs", type=int, default=0)
        p.add_argument("--base-seed", type=int, default=0)
        p.add_argument("--max-plies", type=int, default=200)
        p.add_argument("--n", type=int, default=12)
        p.add_argument("--iterations", type=int, default=300)
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
