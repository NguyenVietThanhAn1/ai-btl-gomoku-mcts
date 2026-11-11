"""E5: rollout random vs rollout heuristic h300 (đề ý 5) — D-20.

15×15, MCTS c = 1.4 + tactics, hai cấu hình chỉ khác rollout: `rand` / `h300`.
- Cùng iteration (4 worker): đối đầu trực tiếp và vs `mref` ở {250, 1000, 5000}; vs Greedy
  {100 … 5000} (h300 vs Greedy tái dùng E3 nếu spec + code khớp); vs AB2 chỉ 5000 iter, pilot rand
  có cổng ≥ 2/20.
- Cùng thời gian {0,5; 2} s/nước (2 worker, máy rảnh): đối đầu, vs Greedy, vs mref — kết luận chính.

    python -m gameai.experiments.e5_rollout all --quick
    python -m gameai.experiments.e5_rollout all      # iter → ab2-pilot → ab2 (qua cổng) → time
    python -m gameai.experiments.e5_rollout <step>   # bench | h2h-iter | greedy-iter | mref-iter
                                                     # | ab2-pilot | ab2 | h2h-time | greedy-time
                                                     # | mref-time | tables
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import platform
import statistics
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from gameai.agents.mcts import MCTSAgent
from gameai.agents.registry import AgentSpec, GameSpec, make_agent, make_game
from gameai.arena import derive_seed
from gameai.experiments.common import (
    SUMMARY_COLUMNS,
    add_runner_args,
    git_info,
    moves_path_for,
    read_rows,
    run_match,
    summarize,
)
from gameai.experiments.e1_nodes import make_position
from gameai.experiments.e3_c_sweep import AB2, GREEDY, fit_cost, gate_passes

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "results" / "raw"
TABLE_DIR = ROOT / "results" / "tables"
FIG_DIR = ROOT / "results" / "figures"

C = 1.4
GAME15 = GameSpec("kinrow", {"n": 15, "k": 5})
ROLLOUTS = ("rand", "h300")
ITER_GREEDY = (100, 250, 500, 1000, 2500, 5000)
ITER_MAIN = (250, 1000, 5000)
TIMES = (0.5, 2.0)
AB2_ITER = 5000
MREF_ITER = 1000
N_PAIRS = 25  # 50 ván/điểm
PILOT_PAIRS = 10  # 20 ván
QUICK_PAIRS = 1
QUICK_ITER_GREEDY = (100, 1000, 5000)
QUICK_ITER_H2H = (250, 5000)
QUICK_ITER_MREF = (250, 1000, 5000)  # cần 1000 cho kiểm tra hợp lệ rand_i1000 vs mref
WORKERS_TIME = 2  # D-20: phần time chạy 2 worker
SPEEDUP = {1: 1.0, 2: 1.9, 4: 3.5}  # ước tính thô số worker → tăng tốc thời gian thực
POOL_OVERHEAD_S = 2.0  # khởi động pool mỗi điểm
FLAG_THRESHOLD = 0.20  # D-20: lệch tốc độ > 20 % → đánh dấu
BENCH_PLIES = (4, 8, 12, 16, 20, 24, 28)  # ≥ 2 thế cho mỗi nhóm giai đoạn ván
# Nhóm giai đoạn ván theo số quân trên bàn trước nước đi (= ply của *_moves.csv, D-20).
PHASES = (("0-9", 0, 9), ("10-19", 10, 19), (">=20", 20, None))
BENCH_SEEDS = (0, 1, 2)
BENCH_SECONDS = 1.0
# Code ảnh hưởng tới kết quả ván: tái dùng E3 chỉ khi các đường dẫn này không đổi (D-20).
CODE_PATHS = (
    "gameai/agents",
    "gameai/games",
    "gameai/heuristics",
    "gameai/core",
    "gameai/arena.py",
)

ITER_STEPS = ("h2h-iter", "greedy-iter", "mref-iter")
TIME_STEPS = ("h2h-time", "greedy-time", "mref-time")
STEPS = ("bench", *ITER_STEPS, "ab2-pilot", "ab2", *TIME_STEPS, "tables", "all")
PART_OF_STEP = {
    "h2h-iter": "h2h",
    "greedy-iter": "greedy",
    "mref-iter": "mref",
    "h2h-time": "h2h",
    "greedy-time": "greedy",
    "mref-time": "mref",
    "ab2-pilot": "ab2",
    "ab2": "ab2",
}


# ---------------------------------------------------------------- agent / spec


class MRefAgent(MCTSAgent):
    """Đối thủ tham chiếu `mref` (D-20): MCTS rollout random, 1000 iter, c = 1.4, tactics bật.

    Dãy seed tách riêng: seed MCTS = `derive_seed(seed, "mref")` (seed do arena cấp cho bên B) →
    không trùng dãy seed A/B của các agent MCTS khác. Dùng qua registry:
    `AgentSpec("gameai.experiments.e5_rollout:MRefAgent", {...}, label="mref")`.
    """

    def __init__(
        self,
        seed: int | None = None,
        iterations: int = MREF_ITER,
        c: float = C,
        check_tactics: bool = True,
    ) -> None:
        inner = None if seed is None else derive_seed(seed, "mref")
        super().__init__(
            iterations=iterations,
            c=c,
            rollout_policy="random",
            check_tactics=check_tactics,
            seed=inner,
        )


MREF = AgentSpec(
    "gameai.experiments.e5_rollout:MRefAgent",
    {"iterations": MREF_ITER, "c": C, "check_tactics": True},
    label="mref",
)


def budget_tag(iterations: int | None = None, time_limit: float | None = None) -> str:
    if (iterations is None) == (time_limit is None):
        raise ValueError("cần đúng một trong iterations / time_limit")
    return f"i{iterations}" if iterations is not None else f"t{time_limit}"


def mcts_spec(
    rollout: str, iterations: int | None = None, time_limit: float | None = None
) -> AgentSpec:
    """`rand` / `h300` (D-20): c = 1.4, tactics bật; chỉ khác rollout.
    Ngân sách iteration hoặc thời gian."""
    tag = budget_tag(iterations, time_limit)
    params: dict[str, Any] = {"c": C, "check_tactics": True}
    if rollout == "h300":
        params.update({"rollout": "heavy_kinrow", "temperature": 300})
    elif rollout == "rand":
        params["rollout"] = "random"
    else:
        raise ValueError(f"rollout không hợp lệ: {rollout!r}")
    if iterations is not None:
        params["iterations"] = iterations
    else:
        params.update({"iterations": None, "time_limit": time_limit})
    return AgentSpec("mcts", params, label=f"{rollout}_{tag}")


@dataclass(frozen=True)
class Point:
    part: str  # h2h | greedy | mref | ab2
    budget_type: str  # iter | time
    budget: float
    rollout: str  # rollout của A (h2h: A = h300, B = rand)
    spec_a: AgentSpec
    spec_b: AgentSpec
    n_pairs: int
    workers: int | None  # None → dùng --workers
    e3_path: str | None = None  # file E3 có thể tái dùng

    @property
    def key(self) -> tuple[str, str, float, str]:
        return (self.part, self.budget_type, float(self.budget), self.rollout)


def _budget_kw(btype: str, b: float) -> dict[str, Any]:
    return {"iterations": int(b)} if btype == "iter" else {"time_limit": float(b)}


def points(step: str, quick: bool) -> list[Point]:
    """Các điểm của một bước (ngân sách thấp trước)."""
    pairs = QUICK_PAIRS if quick else N_PAIRS
    out: list[Point] = []
    if step in ("h2h-iter", "h2h-time"):
        btype = "iter" if step.endswith("iter") else "time"
        bs = (QUICK_ITER_H2H if quick else ITER_MAIN) if btype == "iter" else TIMES
        w = None if btype == "iter" else WORKERS_TIME
        for b in bs:
            kw = _budget_kw(btype, b)
            out.append(
                Point(
                    "h2h",
                    btype,
                    b,
                    "h300",
                    mcts_spec("h300", **kw),
                    mcts_spec("rand", **kw),
                    pairs,
                    w,
                )
            )
    elif step in ("greedy-iter", "greedy-time", "mref-iter", "mref-time"):
        part, btype = step.split("-")
        if btype == "iter":
            bs = {
                ("greedy", False): ITER_GREEDY,
                ("greedy", True): QUICK_ITER_GREEDY,
                ("mref", False): ITER_MAIN,
                ("mref", True): QUICK_ITER_MREF,
            }[(part, quick)]
        else:
            bs = TIMES
        opp = GREEDY if part == "greedy" else MREF
        w = None if btype == "iter" else WORKERS_TIME
        for b in bs:
            for r in ROLLOUTS:
                e3 = None
                if part == "greedy" and btype == "iter" and r == "h300":
                    e3 = str(RAW_DIR / f"e3_greedy_c{C}_i{int(b)}.csv")
                out.append(
                    Point(
                        part, btype, b, r, mcts_spec(r, **_budget_kw(btype, b)), opp, pairs, w, e3
                    )
                )
    elif step in ("ab2-pilot", "ab2"):
        n = QUICK_PAIRS if quick else (PILOT_PAIRS if step == "ab2-pilot" else N_PAIRS)
        out.append(
            Point(
                "ab2",
                "iter",
                AB2_ITER,
                "rand",
                mcts_spec("rand", iterations=AB2_ITER),
                AB2,
                n,
                None,
            )
        )
        out.append(
            Point(
                "ab2",
                "iter",
                AB2_ITER,
                "h300",
                mcts_spec("h300", iterations=AB2_ITER),
                AB2,
                N_PAIRS,
                None,
                str(RAW_DIR / f"e3_ab2_c{C}_i{AB2_ITER}.csv"),
            )
        )
    else:
        raise ValueError(f"bước không có điểm: {step!r}")
    return out


def prefix(quick: bool) -> str:
    return "e5quick_" if quick else "e5_"


def raw_path(pt: Point, quick: bool, raw_dir: Path = RAW_DIR) -> Path:
    return raw_dir / f"{prefix(quick)}{pt.part}_{pt.spec_a.name}.csv"


# ---------------------------------------------------------------- tái dùng E3


def git_diff_empty(commit: str, paths: tuple[str, ...] = CODE_PATHS) -> bool:
    """`git diff --quiet <commit> HEAD -- paths` (True = không đổi)."""
    r = subprocess.run(
        ["git", "diff", "--quiet", commit, "HEAD", "--", *paths], cwd=ROOT, capture_output=True
    )
    return r.returncode == 0


def _same_spec(js: str, spec: AgentSpec) -> bool:
    d = json.loads(js)
    return d.get("kind") == spec.kind and d.get("params") == spec.params


def e3_reusable(
    path: str | Path,
    spec_a: AgentSpec,
    spec_b: AgentSpec,
    n_pairs: int,
    game: GameSpec = GAME15,
    base_seed: int = 0,
    diff_empty: Callable[[str], bool] = git_diff_empty,
) -> tuple[bool, str]:
    """Điều kiện D-20 để dùng file raw E3 thay cho chạy lại: spec A/B (bỏ label), game, base_seed
    khớp,
    `git_dirty = 0`, đủ `2·n_pairs` ván, và code agent/game không đổi từ commit ghi trong file."""
    p = Path(path)
    if not p.exists():
        return False, f"không có {p.name}"
    rows = read_rows(p)
    if len(rows) < 2 * n_pairs:
        return False, f"{p.name} có {len(rows)} ván < {2 * n_pairs}"
    for r in rows:
        if not _same_spec(r["spec_a"], spec_a):
            return False, f"spec A khác ({r['spec_a']})"
        if not _same_spec(r["spec_b"], spec_b):
            return False, f"spec B khác ({r['spec_b']})"
        if json.loads(r["game_spec"]) != game.to_dict():
            return False, "game khác"
        if int(r["base_seed"]) != base_seed:
            return False, f"base_seed {r['base_seed']} ≠ {base_seed}"
        if r["git_dirty"] not in ("0", "False"):
            return False, "git_dirty"
    for commit in sorted({r["git_commit"] for r in rows}):
        if not diff_empty(commit):
            return False, f"code đổi từ {commit[:7]}"
    return True, f"ok ({p.name})"


def _keep_pairs(
    rows: list[dict[str, str]], n_pairs: int, base_seed: int = 0
) -> list[dict[str, str]]:
    return [r for r in rows if int(r["pair_seed"]) < base_seed + n_pairs]


# ---------------------------------------------------------------- chạy

RUNINFO_COLUMNS = [
    "step",
    "part",
    "label_a",
    "label_b",
    "budget_type",
    "budget",
    "source",
    "workers",
    "n_pairs",
    "cpu",
    "logical_cpus",
    "started",
    "finished",
    "wall_s",
    "git_commit",
    "git_dirty",
    "note",
]


def cpu_name() -> str:
    """Tên CPU (Windows: registry; nơi khác: platform.processor())."""
    try:
        import winreg

        k = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
        )
        return str(winreg.QueryValueEx(k, "ProcessorNameString")[0]).strip()
    except Exception:  # noqa: BLE001 — không có registry → fallback
        return platform.processor() or "unknown"


def _append_csv(path: Path, columns: list[str], row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, columns, extrasaction="ignore")
        if new:
            w.writeheader()
        w.writerow(row)


def run_point(
    pt: Point, step: str, quick: bool, workers: int, allow: bool, raw_dir: Path = RAW_DIR
) -> str:
    """Chạy một điểm (hoặc xác nhận tái dùng E3). Trả `source` ('e3' / 'e5'). Ghi runinfo."""
    started = datetime.now().isoformat(timespec="seconds")
    t0 = time.perf_counter()
    w = pt.workers if pt.workers is not None else workers
    source, note = "e5", ""
    if pt.e3_path is not None:
        ok, reason = e3_reusable(
            pt.e3_path, pt.spec_a, pt.spec_b, pt.n_pairs if not quick else N_PAIRS
        )
        note = reason
        if ok:
            source = "e3"
    if source == "e5":
        rows = run_match(
            raw_path(pt, quick, raw_dir),
            GAME15,
            pt.spec_a,
            pt.spec_b,
            pt.n_pairs,
            workers=w,
            allow_code_change=allow,
        )
        s = next(x for x in summarize(rows) if x["split"] == "all")
        wdl = f"{s['wins']}/{s['draws']}/{s['losses']}"
        msg = f"W/D/L {wdl} (n={s['n']}, distinct={s['distinct_games']})"
    else:
        msg = f"tái dùng E3: {note}"
    commit, dirty = git_info()
    _append_csv(
        raw_dir / f"{prefix(quick)}runinfo.csv",
        RUNINFO_COLUMNS,
        {
            "step": step,
            "part": pt.part,
            "label_a": pt.spec_a.name,
            "label_b": pt.spec_b.name,
            "budget_type": pt.budget_type,
            "budget": pt.budget,
            "source": source,
            "workers": w,
            "n_pairs": pt.n_pairs,
            "cpu": cpu_name(),
            "logical_cpus": os.cpu_count(),
            "started": started,
            "finished": datetime.now().isoformat(timespec="seconds"),
            "wall_s": round(time.perf_counter() - t0, 1),
            "git_commit": commit,
            "git_dirty": int(dirty),
            "note": note,
        },
    )
    print(f"[{step}] {pt.spec_a.name} vs {pt.spec_b.name}: {msg}, {time.perf_counter() - t0:.1f} s")
    return source


def run_step(step: str, quick: bool, workers: int, allow: bool) -> None:
    for pt in points(step, quick):
        run_point(pt, step, quick, workers, allow)


def pilot_wins(quick: bool, table_dir: Path = TABLE_DIR) -> tuple[int, int]:
    rows = read_rows(table_dir / f"{prefix(quick)}ab2.csv")
    r = next(x for x in rows if x["rollout"] == "rand" and x["split"] == "all")
    return int(r["wins"]), int(r["n"])


def run_pilot(quick: bool, workers: int, allow: bool) -> bool:
    run_step("ab2-pilot", quick, workers, allow)
    build_tables(quick)
    wins, n = pilot_wins(quick)
    passed = gate_passes(wins)
    verdict = (
        "(quick: không áp cổng)"
        if quick
        else ("QUA cổng → chạy đủ 50 ván" if passed else "KHÔNG qua → floor, dừng AB2")
    )
    print(f"[ab2-pilot] rand_i{AB2_ITER} thắng {wins}/{n} — {verdict}")
    return passed and not quick


def run_ab2(quick: bool, workers: int, allow: bool, force: bool = False) -> None:
    wins, n = pilot_wins(quick)
    if not quick and n < 2 * PILOT_PAIRS:
        sys.exit(f"pilot có {n} ván, cần {2 * PILOT_PAIRS}")
    if not quick and not gate_passes(wins) and not force:
        sys.exit(f"pilot thắng {wins}/{n} < 2 → không chạy AB2 (D-20); --force để ép")
    run_step("ab2", quick, workers, allow)


# ---------------------------------------------------------------- benchmark đơn luồng

BENCH_COLUMNS = ["rollout", "plies", "seed", "iterations", "agent_time", "iter_per_s"]


def bench(
    seconds: float = BENCH_SECONDS,
    plies: tuple[int, ...] = BENCH_PLIES,
    seeds: tuple[int, ...] = BENCH_SEEDS,
    path: Path | None = TABLE_DIR / "e5_bench.csv",
) -> list[dict[str, Any]]:
    """Đo iteration/giây đơn luồng (trong tiến trình, tuần tự) của rand và h300 trên thế cố định
    (`e1_nodes.make_position`). `check_tactics=False` để mọi thế đều search (tactic đi tắt
    → 0 iter)."""
    rows: list[dict[str, Any]] = []
    for r in ROLLOUTS:
        spec = mcts_spec(r, time_limit=seconds)
        params = {**spec.params, "check_tactics": False}
        for n in plies:
            moves, _ = make_position(GAME15, n)
            for s in seeds:
                g = make_game(GAME15)
                for m in moves:
                    g.play(m)
                agent = make_agent(AgentSpec("mcts", params), s)
                agent.select_move(g)
                it, t = int(agent.stats["iterations"]), float(agent.stats["time"])
                rows.append(
                    {
                        "rollout": r,
                        "plies": n,
                        "seed": s,
                        "iterations": it,
                        "agent_time": round(t, 4),
                        "iter_per_s": round(it / t, 1),
                    }
                )
    if path is not None:
        _write(path, BENCH_COLUMNS, rows)
        print(f"[bench] {path}")
    for r in ROLLOUTS:
        print(f"[bench] {r}: trung vị {bench_rates(rows)[r]:.0f} iter/s")
    rr = bench_rates(rows)
    print(f"[bench] rand/h300 = {rr['rand'] / rr['h300']:.2f}")
    return rows


def bench_rates(rows: list[dict[str, Any]]) -> dict[str, float]:
    """Trung vị iter/s theo rollout."""
    return {
        r: statistics.median(float(x["iter_per_s"]) for x in rows if x["rollout"] == r)
        for r in ROLLOUTS
        if any(x["rollout"] == r for x in rows)
    }


# ---------------------------------------------------------------- bảng

TABLE_COLUMNS = ["part", "budget_type", "budget", "rollout", "source", "raw", *SUMMARY_COLUMNS]
PAIRED_COLUMNS = [
    "part",
    "budget_type",
    "budget",
    "n",
    "mean_h300",
    "mean_rand",
    "diff",
    "paired_lo",
    "paired_hi",
    "indep_lo",
    "indep_hi",
    "sd_diff",
]
VALIDITY_COLUMNS = [
    "label_a",
    "label_b",
    "n",
    "wins",
    "win_rate",
    "win_lo",
    "win_hi",
    "contains_half",
    "distinct_games",
    "valid",
]
RATE_COLUMNS = [
    "part",
    "budget",
    "side",
    "rollout",
    "phase",
    "method",
    "n_moves",
    "iterations",
    "agent_time",
    "rate_iter_per_s",
    "bench_iter_per_s",
    "dev_bench",
    "flag",
    "load_indicator",
]


def fnum(v: Any) -> float:
    """float từ ô CSV / số; ô trống hoặc None → nan."""
    if v is None or v == "":
        return math.nan
    return float(v)


def _fmt(v: Any) -> Any:
    return "" if v is None or (isinstance(v, float) and math.isnan(v)) else v


def _write(path: Path, columns: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, columns, extrasaction="ignore")
        w.writeheader()
        w.writerows({k: _fmt(r.get(k)) for k in columns} for r in rows)


def all_points(quick: bool) -> list[Point]:
    pts: dict[tuple, Point] = {}
    for step in (*ITER_STEPS, "ab2", *TIME_STEPS):
        for pt in points(step, quick):
            pts[pt.key] = pt
    return list(pts.values())


def point_rows(
    pt: Point,
    quick: bool,
    raw_dir: Path = RAW_DIR,
    reuse_check: Callable[..., tuple[bool, str]] = e3_reusable,
) -> tuple[str, Path, list[dict[str, str]], list[dict[str, str]]] | None:
    """(source, raw, rows, moves) của một điểm; E3 nếu tái dùng được, không thì file E5;
    chưa có → None."""
    if pt.e3_path is not None:
        ok, _ = reuse_check(pt.e3_path, pt.spec_a, pt.spec_b, N_PAIRS)
        if ok:
            p = Path(pt.e3_path)
            rows = _keep_pairs(read_rows(p), N_PAIRS)
            ids = {r["game_id"] for r in rows}
            moves = [m for m in read_rows(moves_path_for(p)) if m["game_id"] in ids]
            return "e3", p, rows, moves
    p = raw_path(pt, quick, raw_dir)
    if not p.exists():
        return None
    rows = read_rows(p)
    if not rows:
        return None
    return "e5", p, rows, read_rows(moves_path_for(p))


def paired_diff(rows_h: list[dict[str, str]], rows_r: list[dict[str, str]]) -> dict[str, float]:
    """So h300 với rand vs cùng đối thủ theo `game_id` chung (cùng seed đối thủ + lượt).

    Cặp: d = result_h300 − result_rand, mean(d) ± 1,96·sd(d)/√n.
    Độc lập: Δ ± 1,96·√(var_h/n + var_r/n).
    """
    h = {r["game_id"]: float(r["result_a"]) for r in rows_h}
    r_ = {r["game_id"]: float(r["result_a"]) for r in rows_r}
    ids = sorted(set(h) & set(r_))
    n = len(ids)
    nan = math.nan
    if n == 0:
        return {
            "n": 0,
            "mean_h300": nan,
            "mean_rand": nan,
            "diff": nan,
            "paired_lo": nan,
            "paired_hi": nan,
            "indep_lo": nan,
            "indep_hi": nan,
            "sd_diff": nan,
        }
    xh = [h[i] for i in ids]
    xr = [r_[i] for i in ids]
    d = [a - b for a, b in zip(xh, xr, strict=True)]
    mh, mr, md = sum(xh) / n, sum(xr) / n, sum(d) / n
    sd = statistics.stdev(d) if n > 1 else nan
    vh = statistics.variance(xh) if n > 1 else nan
    vr = statistics.variance(xr) if n > 1 else nan
    hw_p = 1.96 * sd / math.sqrt(n)
    hw_i = 1.96 * math.sqrt(vh / n + vr / n)
    return {
        "n": n,
        "mean_h300": mh,
        "mean_rand": mr,
        "diff": md,
        "paired_lo": md - hw_p,
        "paired_hi": md + hw_p,
        "indep_lo": md - hw_i,
        "indep_hi": md + hw_i,
        "sd_diff": sd,
    }


def check_validity(summary_all: dict[str, Any]) -> dict[str, Any]:
    """Kiểm tra hợp lệ D-20: Wilson win rate rand_i1000 vs mref phải chứa 0,5."""
    lo, hi = float(summary_all["win_lo"]), float(summary_all["win_hi"])
    contains = int(lo <= 0.5 <= hi)
    return {
        **{k: summary_all.get(k) for k in VALIDITY_COLUMNS if k in summary_all},
        "contains_half": contains,
        "valid": contains,
    }


def phase_of(stones: int) -> str:
    """Nhóm giai đoạn ván của một thế có `stones` quân (0–9, 10–19, ≥ 20)."""
    for name, lo, hi in PHASES:
        if stones >= lo and (hi is None or stones <= hi):
            return name
    raise ValueError(stones)


def bench_phase_rates(rows: list[dict[str, Any]]) -> dict[tuple[str, str], float]:
    """Trung vị iter/s của benchmark theo (rollout, nhóm giai đoạn) — nhóm theo số quân của thế."""
    groups: dict[tuple[str, str], list[float]] = {}
    for x in rows:
        key = (x["rollout"], phase_of(int(x["plies"])))
        groups.setdefault(key, []).append(float(x["iter_per_s"]))
    return {k: statistics.median(v) for k, v in groups.items()}


def _flag(rate: float, bench: float) -> tuple[float, Any]:
    if not (rate == rate and bench == bench and bench > 0):
        return math.nan, ""
    dev = round(rate / bench - 1, 3)
    return dev, int(abs(dev) > FLAG_THRESHOLD)


def rate_rows(
    time_tables: dict[str, list[dict[str, Any]]],
    bench_rows: list[dict[str, Any]],
    time_moves: dict[tuple[str, float, str], list[dict[str, str]]] | None = None,
) -> list[dict[str, Any]]:
    """Kiểm tra tải phần time (D-20): tốc độ iter/s thực tế của mỗi bên MCTS chạy theo thời gian.

    - Có `*_moves` (iteration + agent_time từng nước) → `method = "phase"`: gom nước có search (bỏ
      tactic 1/2 và nước 0 iteration) theo nhóm giai đoạn ván (ply 0–9, 10–19, ≥ 20), tốc độ =
      Σ iterations / Σ agent_time, so với trung vị benchmark cùng rollout + cùng nhóm.
    - Không có → `method = "mixed"`: `search_iterations_per_move / time_limit` so với trung vị
      benchmark mọi thế (trộn giai đoạn ván — lệch một phần do giai đoạn, không chỉ do tải).
    Lệch > 20 % → `flag = 1`. `load_indicator = 1` cho rand (chỉ báo tải: tốc độ rand ít phụ thuộc
    giai đoạn hơn h300). Cờ chỉ để báo cáo, không loại dữ liệu.
    """
    phase_bench = bench_phase_rates(bench_rows) if bench_rows else {}
    all_bench = bench_rates(bench_rows) if bench_rows else {}
    time_moves = time_moves or {}
    out: list[dict[str, Any]] = []
    for part, rows in time_tables.items():
        for r in rows:
            if r["split"] != "all" or r["budget_type"] != "time":
                continue
            t = float(r["budget"])
            sides = [("A", r["rollout"])] + ([("B", "rand")] if part == "h2h" else [])
            moves = time_moves.get((part, t, r["rollout"]))
            for side, roll in sides:
                base = {"part": part, "budget": t, "side": side, "rollout": roll,
                        "load_indicator": int(roll == "rand")}  # fmt: skip
                if moves:
                    acc: dict[str, list[float]] = {name: [0, 0.0, 0.0] for name, _, _ in PHASES}
                    for m in moves:
                        if m["side"] != side or m["tactic"] in ("1", "2"):
                            continue
                        it, at = fnum(m["iterations"]), fnum(m["agent_time"])
                        if not (it == it and at == at) or it <= 0 or at <= 0:
                            continue
                        a = acc[phase_of(int(m["ply"]))]
                        a[0] += 1
                        a[1] += it
                        a[2] += at
                    for name, _, _ in PHASES:
                        n, it, at = acc[name]
                        if n == 0:
                            continue
                        rate = it / at
                        b = phase_bench.get((roll, name), math.nan)
                        dev, flag = _flag(rate, b)
                        out.append({**base, "phase": name, "method": "phase", "n_moves": int(n),
                                    "iterations": int(it), "agent_time": round(at, 3),
                                    "rate_iter_per_s": round(rate, 1), "bench_iter_per_s": b,
                                    "dev_bench": dev, "flag": flag})  # fmt: skip
                else:
                    it = fnum(r[f"{side.lower()}_search_iterations_per_move"])
                    rate = it / t
                    b = all_bench.get(roll, math.nan)
                    dev, flag = _flag(rate, b)
                    out.append({**base, "phase": "all (trộn giai đoạn)", "method": "mixed",
                                "n_moves": r.get(f"{side.lower()}_search_moves", ""),
                                "rate_iter_per_s": round(rate, 1) if rate == rate else math.nan,
                                "bench_iter_per_s": b, "dev_bench": dev, "flag": flag})  # fmt: skip
    return out


def build_tables(
    quick: bool,
    raw_dir: Path = RAW_DIR,
    table_dir: Path = TABLE_DIR,
    reuse_check: Callable[..., tuple[bool, str]] = e3_reusable,
) -> dict[str, list[dict[str, Any]]]:
    """Dựng mọi bảng E5 từ raw đang có (+ E3 tái dùng). Trả {tên bảng: dòng}."""
    p = prefix(quick)
    tables: dict[str, list[dict[str, Any]]] = {"h2h": [], "greedy": [], "mref": [], "ab2": []}
    rows_by_key: dict[tuple, list[dict[str, str]]] = {}
    time_moves: dict[tuple[str, float, str], list[dict[str, str]]] = {}
    for pt in all_points(quick):
        got = point_rows(pt, quick, raw_dir, reuse_check)
        if got is None:
            continue
        source, path, rows, moves = got
        rows_by_key[pt.key] = rows
        if pt.budget_type == "time":
            time_moves[(pt.part, float(pt.budget), pt.rollout)] = moves
        rel = path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path)
        for s in summarize(rows, moves):
            tables[pt.part].append(
                {
                    "part": pt.part,
                    "budget_type": pt.budget_type,
                    "budget": pt.budget,
                    "rollout": pt.rollout,
                    "source": source,
                    "raw": rel,
                    **s,
                }
            )
    for name, rows in tables.items():
        rows.sort(key=lambda r: (r["budget_type"], float(r["budget"]), r["rollout"]))
        _write(table_dir / f"{p}{name}.csv", TABLE_COLUMNS, rows)
    paired = []
    for part in ("greedy", "mref", "ab2"):
        for (pa, bt, b, roll), rows in sorted(rows_by_key.items()):
            if pa != part or roll != "h300" or (pa, bt, b, "rand") not in rows_by_key:
                continue
            paired.append(
                {
                    "part": part,
                    "budget_type": bt,
                    "budget": b,
                    **paired_diff(rows, rows_by_key[(pa, bt, b, "rand")]),
                }
            )
    _write(table_dir / f"{p}paired.csv", PAIRED_COLUMNS, paired)
    validity = [
        check_validity(r)
        for r in tables["mref"]
        if r["split"] == "all"
        and r["rollout"] == "rand"
        and r["budget_type"] == "iter"
        and int(r["budget"]) == MREF_ITER
    ]
    _write(table_dir / f"{p}validity.csv", VALIDITY_COLUMNS, validity)
    bench_path = table_dir / "e5_bench.csv"
    bench_rows = read_rows(bench_path) if bench_path.exists() else []
    rates = rate_rows({k: tables[k] for k in ("h2h", "greedy", "mref")}, bench_rows, time_moves)
    _write(table_dir / f"{p}rates.csv", RATE_COLUMNS, rates)
    for v in validity:
        print(
            f"[validity] {v['label_a']} vs mref: win {v['wins']}/{v['n']} "
            f"[{float(v['win_lo']):.3f}; {float(v['win_hi']):.3f}], "
            f"distinct {v['distinct_games']}, "
            f"valid={v['valid']}"
        )
    for r in rates:
        if r["flag"] == 1:
            print(
                f"[rates] CỜ: {r['part']} t={r['budget']} {r['side']}={r['rollout']} "
                f"pha {r['phase']}: {r['rate_iter_per_s']} it/s, bench {r['bench_iter_per_s']}, "
                f"lệch {r['dev_bench']} ({r['method']})"
            )
    return {**tables, "paired": paired, "validity": validity, "rates": rates}


# ---------------------------------------------------------------- ước tính từ quick

ESTIMATE_COLUMNS = [
    "step",
    "points_run",
    "points_reused",
    "games",
    "workers",
    "seq_minutes",
    "est_wall_minutes",
    "note",
]


def _game_seconds(r: dict[str, str]) -> float:
    return sum(float(r[k]) for k in ("a_time_sum", "b_time_sum") if r.get(k))


def estimate_full(
    raw_dir: Path = RAW_DIR, table_dir: Path = TABLE_DIR, workers: int = 4
) -> list[dict[str, Any]]:
    """Ngoại suy thời gian full từ raw quick: điểm quick có cùng (part, budget, rollout) →
    trung bình
    giây/ván đo được; điểm iter khác → fit a + b·iter theo (part, rollout). Điểm tái dùng E3 → 0."""
    measured: dict[tuple, float] = {}
    for pt in all_points(True):
        f = raw_path(pt, True, raw_dir)
        if f.exists():
            rows = read_rows(f)
            if rows:
                measured[pt.key] = sum(_game_seconds(r) for r in rows) / len(rows)
    fits: dict[tuple[str, str], tuple[float, float]] = {}
    for part in ("h2h", "greedy", "mref", "ab2"):
        for r in ROLLOUTS:
            data = [
                (int(k[2]), v)
                for k, v in measured.items()
                if k[0] == part and k[1] == "iter" and k[3] == r
            ]
            if data:
                fits[(part, r)] = fit_cost(data)
    out = []
    for step in (*ITER_STEPS, "ab2-pilot", "ab2", *TIME_STEPS):
        w = WORKERS_TIME if step in TIME_STEPS else workers
        seq, games, run, reused, notes = 0.0, 0, 0, 0, []
        for pt in points(step, False):
            if pt.e3_path is not None and e3_reusable(pt.e3_path, pt.spec_a, pt.spec_b, N_PAIRS)[0]:
                reused += 1
                continue
            n_games = 2 * pt.n_pairs
            if step == "ab2":
                n_games = 2 * (N_PAIRS - PILOT_PAIRS)  # resume từ pilot
            if pt.key in measured:
                sec = measured[pt.key]
            elif (pt.part, pt.rollout) in fits:
                a, b = fits[(pt.part, pt.rollout)]
                sec = a + b * pt.budget
                notes.append(f"{pt.spec_a.name} fit")
            else:
                sec = math.nan
                notes.append(f"{pt.spec_a.name} thiếu dữ liệu")
            seq += n_games * sec
            games += n_games
            run += 1
        wall = (seq / SPEEDUP.get(w, w * 0.85) + run * POOL_OVERHEAD_S) / 60
        out.append(
            {
                "step": step,
                "points_run": run,
                "points_reused": reused,
                "games": games,
                "workers": w,
                "seq_minutes": round(seq / 60, 1),
                "est_wall_minutes": round(wall, 1),
                "note": ("chỉ chạy nếu pilot qua cổng; " if step == "ab2" else "")
                + "; ".join(notes),
            }
        )
    tot = sum(r["est_wall_minutes"] for r in out if r["step"] != "ab2")
    out.append(
        {
            "step": "total (không gồm ab2)",
            "games": sum(r["games"] for r in out if r["step"] != "ab2"),
            "seq_minutes": round(sum(r["seq_minutes"] for r in out if r["step"] != "ab2"), 1),
            "est_wall_minutes": round(tot, 1),
        }
    )
    _write(table_dir / "e5quick_estimate.csv", ESTIMATE_COLUMNS, out)
    for r in out:
        workers = f" ({r['workers']} worker)" if r.get("workers") else ""
        print(f"[estimate] {r['step']}: {r['games']} ván, ~{r['est_wall_minutes']} phút{workers}")
    return out


# ---------------------------------------------------------------- hình

COLORS = {"rand": "#2a78d6", "h300": "#eb6834"}  # 2 slot đầu bảng màu đã kiểm ở E3
MARKERS = {"rand": "o", "h300": "s"}
NAMES = {"rand": "rollout random", "h300": "rollout heavy h300"}
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"


def _style(ax: Any) -> None:
    ax.set_facecolor(SURFACE)
    ax.grid(True, axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(INK2)
    ax.tick_params(colors=INK2)


def _series(
    rows: list[dict[str, Any]],
    btype: str,
    roll: str,
    xkey: str = "budget",
) -> list[tuple[float, float, float, float]]:
    pts = []
    for r in rows:
        if r["split"] != "all" or r["budget_type"] != btype or r["rollout"] != roll:
            continue
        x = fnum(r[xkey])
        if not x == x:  # nan
            continue
        pts.append((x, fnum(r["win_rate"]), fnum(r["win_lo"]), fnum(r["win_hi"])))
    return sorted(pts)


def _plot_lines(
    ax: Any, rows: list[dict[str, Any]], btype: str, xkey: str, rolls: tuple[str, ...] = ROLLOUTS
) -> list[float]:
    xs_all: list[float] = []
    for i, roll in enumerate(rolls):
        pts = _series(rows, btype, roll, xkey)
        if not pts:
            continue
        shift = 10 ** (0.02 * (i - 0.5)) if xkey == "budget" else 1.0
        xs = [p[0] * shift for p in pts]
        err = [[max(0.0, p[1] - p[2]) for p in pts], [max(0.0, p[3] - p[1]) for p in pts]]
        ax.errorbar(
            xs,
            [p[1] for p in pts],
            yerr=err,
            color=COLORS[roll],
            marker=MARKERS[roll],
            markersize=6,
            linewidth=2,
            elinewidth=1.2,
            capsize=0,
            markeredgecolor=SURFACE,
            markeredgewidth=1,
            label=NAMES[roll],
        )
        xs_all += [p[0] for p in pts]
    ax.set_xscale("log")
    ax.set_ylim(0.0, 1.03)
    _style(ax)
    return xs_all


def make_figures(quick: bool, table_dir: Path = TABLE_DIR, fig_dir: Path = FIG_DIR) -> list[Path]:
    """`e5_iter.png` (3 panel, x = iteration) và `e5_time.png` (hàng trên x = thời gian/nước,
    hàng dưới
    x = iteration thực tế/nước; panel đối đầu hàng dưới = iteration thực tế của từng bên)."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    p = prefix(quick)

    def table(name: str) -> list[dict[str, str]]:
        f = table_dir / f"{p}{name}.csv"
        return read_rows(f) if f.exists() else []

    t = {k: table(k) for k in ("greedy", "mref", "h2h")}
    # đối đầu: vẽ win rate của h300 (A); trục y là tỉ lệ thắng của bên được ghi trong tiêu đề
    subs = {
        "greedy": "Thắng vs Greedy",
        "mref": "Thắng vs mref (MCTS random 1000 iter)",
        "h2h": "Đối đầu: tỉ lệ thắng của h300 vs rand",
    }
    out: list[Path] = []
    fig, axes = plt.subplots(1, 3, figsize=(15.6, 4.6), facecolor=SURFACE)
    for ax, k in zip(axes, ("greedy", "mref", "h2h"), strict=True):
        rolls = ("h300",) if k == "h2h" else ROLLOUTS
        xs = _plot_lines(ax, t[k], "iter", "budget", rolls)
        ticks = sorted(set(xs))
        if ticks:
            ax.set_xticks(ticks, [str(int(x)) for x in ticks])
        ax.minorticks_off()
        if k == "h2h":
            ax.axhline(0.5, color=INK2, linewidth=0.8, linestyle="--")
        ax.set_xlabel("iteration / nước (cùng cho hai bên)", color=INK2)
        ax.set_ylabel("tỉ lệ thắng", color=INK2)
        ax.set_title(subs[k], color=INK, fontsize=11, loc="left")
    _finish(
        fig,
        axes[0],
        "E5 — cùng số iteration (thiên vị h300: mỗi iteration heavy đắt hơn)",
        fig_dir / f"{p}iter.png",
        out,
    )

    fig, axes = plt.subplots(2, 3, figsize=(15.6, 8.4), facecolor=SURFACE)
    for col, k in enumerate(("greedy", "mref", "h2h")):
        ax = axes[0][col]
        rolls = ("h300",) if k == "h2h" else ROLLOUTS
        xs = _plot_lines(ax, t[k], "time", "budget", rolls)
        ticks = sorted(set(xs))
        if ticks:
            ax.set_xticks(ticks, [f"{x:g} s" for x in ticks])
        ax.minorticks_off()
        if k == "h2h":
            ax.axhline(0.5, color=INK2, linewidth=0.8, linestyle="--")
        ax.set_xlabel("thời gian / nước", color=INK2)
        ax.set_ylabel("tỉ lệ thắng", color=INK2)
        ax.set_title(subs[k], color=INK, fontsize=11, loc="left")
        ax = axes[1][col]
        if k == "h2h":
            _plot_h2h_iters(ax, t[k])
        else:
            _plot_lines(ax, t[k], "time", "a_search_iterations_per_move")
            ax.set_xlabel("iteration thực tế / nước (có search)", color=INK2)
            ax.set_ylabel("tỉ lệ thắng", color=INK2)
            ax.set_title(f"{subs[k]} — theo iteration thực tế", color=INK, fontsize=11, loc="left")
    _finish(
        fig,
        axes[0][0],
        "E5 — cùng thời gian/nước (so sánh công bằng)",
        fig_dir / f"{p}time.png",
        out,
    )
    for f in out:
        print(f"[plot] {f}")
    return out


def _plot_h2h_iters(ax: Any, rows: list[dict[str, Any]]) -> None:
    """Đối đầu theo thời gian: iteration thực tế/nước của từng bên ở mỗi mức thời gian
    (cột, trục log)."""
    rs = sorted(
        (r for r in rows if r["split"] == "all" and r["budget_type"] == "time"),
        key=lambda r: float(r["budget"]),
    )
    for j, r in enumerate(rs):
        for i, (side, roll) in enumerate((("a", "h300"), ("b", "rand"))):
            v = fnum(r[f"{side}_search_iterations_per_move"])
            if v == v:
                ax.bar(
                    j + (i - 0.5) * 0.38,
                    v,
                    width=0.36,
                    color=COLORS[roll],
                    label=NAMES[roll] if j == 0 else None,
                )
                ax.text(
                    j + (i - 0.5) * 0.38,
                    v,
                    f"{v:.0f}",
                    ha="center",
                    va="bottom",
                    fontsize=8,
                    color=INK2,
                )
    ax.set_xticks(range(len(rs)), [f"{float(r['budget']):g} s" for r in rs])
    ax.set_yscale("log")
    _style(ax)
    ax.set_xlabel("thời gian / nước", color=INK2)
    ax.set_ylabel("iteration thực tế / nước", color=INK2)
    ax.set_title("Đối đầu: iteration thực tế mỗi bên", color=INK, fontsize=11, loc="left")


def _finish(fig: Any, legend_ax: Any, title: str, path: Path, out: list[Path]) -> None:
    import matplotlib.pyplot as plt

    handles, labels = legend_ax.get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="upper left",
        bbox_to_anchor=(0.005, 0.95),
        ncol=max(1, len(labels)),
        frameon=False,
        labelcolor=INK,
        fontsize=9,
    )
    fig.suptitle(title, color=INK, fontsize=12, x=0.01, y=0.995, ha="left")
    fig.text(
        0.01,
        0.005,
        "Thanh lỗi: Wilson 95 % của tỉ lệ thắng, tính độc lập từng điểm "
        "(rand và h300 dùng chung seed đối thủ; so sánh cặp: e5_paired.csv).",
        color=INK2,
        fontsize=8,
        ha="left",
        va="bottom",
    )
    fig.tight_layout(rect=(0, 0.03, 1, 0.9))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150, facecolor=SURFACE)
    plt.close(fig)
    out.append(path)


# ---------------------------------------------------------------- main


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]  # console cp1252
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("step", choices=STEPS)
    ap.add_argument("--force", action="store_true", help="ab2: chạy dù pilot không qua cổng")
    add_runner_args(ap)
    args = ap.parse_args()
    q, w, allow = args.quick, args.workers, args.allow_code_change
    t0 = time.perf_counter()
    if args.step in ("bench", "all"):  # full: bench ở đầu, khi máy rảnh
        bench()
    if args.step == "all":
        for s in ITER_STEPS:  # D-20: mọi phần iteration trước
            run_step(s, q, w, allow)
        if run_pilot(q, w, allow):
            run_ab2(q, w, allow)
        for s in TIME_STEPS:  # phần time sau cùng, máy rảnh
            run_step(s, q, w, allow)
    elif args.step == "ab2-pilot":
        run_pilot(q, w, allow)
    elif args.step == "ab2":
        run_ab2(q, w, allow, args.force)
    elif args.step in (*ITER_STEPS, *TIME_STEPS):
        run_step(args.step, q, w, allow)
    if args.step != "bench":
        build_tables(q)
        make_figures(q)
    if q and args.step == "all":
        estimate_full(workers=w)
    print(f"tổng {time.perf_counter() - t0:.1f} s")


if __name__ == "__main__":
    main()
