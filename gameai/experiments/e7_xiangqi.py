"""P8.4 — E7 cờ tướng (thiết kế D-25).

    python -m gameai.experiments.e7_xiangqi <phần> [--quick] [--workers 1]

Phần: `bench`, `b` (ordering AB), `c` (= c1..c4 + luật c4), `c1`..`c4`,
`d` (= d1, d2; cần c1 + c4 đủ ván), `d1`, `d2`, `a` (= a1, a2), `a1`, `a2`,
`wcheck` (iter/s c3: 1 worker vs `--workers`), `summary`,
`all` (b → c → luật c4 → d → a → summary; quick thêm wcheck + ước tính).
Mỗi phần chạy tiếp được sau khi ngắt (`common.run_match`; ordering bỏ dòng đã có).
Full chỉ chạy khi cắm sạc (D-21) trừ khi `--allow-battery`.
Log: `results/e7_full.log` / `e7quick.log`.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
import time
from collections.abc import Iterable, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

from gameai.agents.registry import AgentSpec, GameSpec, make_agent, make_game
from gameai.experiments.common import git_info, moves_path_for, read_rows, run_match
from gameai.experiments.p82_ab_check import RANDOM, ab_spec, midgame_fens
from gameai.experiments.p83_mcts_check import wilson_score, xq_mcts_spec
from gameai.games.xiangqi import START_FEN, Xiangqi

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "results" / "raw"
TABLE_DIR = ROOT / "results" / "tables"
FIG_DIR = ROOT / "results" / "figures"
LOG_DIR = ROOT / "results"

MAX_PLIES = 200
GAME = GameSpec("xiangqi", {"max_plies": MAX_PLIES})
BASE_SEED = 7000
RANDOM_OPENING = 4  # 2 nước mỗi bên
N_PAIRS, QUICK_PAIRS = 25, 2  # 50 / 4 ván mỗi điểm
DEFAULT_WORKERS = 1  # full chạy 1 worker (D-25 sau quick: 3 worker giảm iter/s 25 %)
WCHECK_WORKERS = 3
C_TIME = 1.0
D_TIMES = {"d1": 1.0, "d2": 2.5}
AB_MAX_DEPTH = 12
EXTRA_MOVE_STATS = ("depth_reached",)  # AB không ghi max_depth → ghi riêng (D-25)
ORDER_DEPTHS = (2, 3, 4)
ORDER_FEN_SEED = 84  # tách bộ thế 82 (P8.2) / 83 (P8.3)
N_MIDGAME = 10
QUICK_DEPTH4_FENS = 3
WORKER_DROP_LIMIT = 0.15  # iter/s c3 giảm > 15 % khi chạy 3 worker → full dùng 1 worker (D-25)
DIRECT_TACTICS = frozenset({"1", "2"})  # nước đi thẳng nhờ tactics, không search (D-15)
TERMS = ("mate", "stalemate", "repetition", "max_plies", "error")


# ---------------------------------------------------------------- spec
def mcts(rollout: int | None, t: float = C_TIME) -> AgentSpec:
    """MCTS cờ tướng tactics bật; `rollout=None` = rollout ngẫu nhiên tới hết (chặn max_plies)."""
    name = "end" if rollout is None else str(rollout)
    label = f"mcts_L{name}" + ("" if t == C_TIME else f"_t{t:g}")
    return xq_mcts_spec(time_limit=t, rollout_limit=rollout, tactics=True, label=label)  # type: ignore[arg-type]


def ab_time(t: float) -> AgentSpec:
    """AB theo D-23 (không theo GUI): ID depth ≤ 12, TT `exact` ghi rõ, không `top_k`."""
    s = ab_spec(AB_MAX_DEPTH, use_tt=True, time_limit=t, label=f"ab_t{t:g}")
    return AgentSpec(s.kind, {**s.params, "tt_mode": "exact"}, label=s.label)


ROLLOUTS: dict[str, int | None] = {"Lend": None, "L0": 0, "L10": 10}
FIXED_POINTS: dict[str, tuple[AgentSpec, AgentSpec]] = {
    "c1": (mcts(None), mcts(10)),
    "c2": (mcts(None), RANDOM),
    "c3": (mcts(10), RANDOM),
    "c4": (mcts(0), mcts(10)),
    "a1": (ab_spec(1, label="ab_d1"), RANDOM),
    "a2": (ab_spec(2, label="ab_d2"), RANDOM),
}
C_POINTS = ("c1", "c2", "c3", "c4")
A_POINTS = ("a1", "a2")
D_POINTS = tuple(D_TIMES)


def d_specs(best: str) -> dict[str, tuple[AgentSpec, AgentSpec]]:
    """(d): MCTS tốt nhất ở (c) vs AB, cùng s/nước."""
    return {p: (mcts(ROLLOUTS[best], t), ab_time(t)) for p, t in D_TIMES.items()}


# ---------------------------------------------------------------- tiện ích
def prefix(quick: bool) -> str:
    return "e7quick_" if quick else "e7_"


def raw_path(point: str, quick: bool, raw_dir: Path = RAW_DIR) -> Path:
    return raw_dir / f"{prefix(quick)}{point}.csv"


def _f(x: Any, d: int = 3) -> Any:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return ""
    return round(x, d) if isinstance(x, float) else x


def _write(path: Path, columns: Sequence[str], rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, list(columns), extrasaction="ignore")
        w.writeheader()
        w.writerows({c: _f(r.get(c)) for c in columns} for r in rows)


def _append(path: Path, columns: Sequence[str], row: dict[str, Any]) -> None:
    new = not path.exists() or path.stat().st_size == 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, list(columns), extrasaction="ignore")
        if new:
            w.writeheader()
        w.writerow({c: _f(row.get(c)) for c in columns})
        fh.flush()


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


# ---------------------------------------------------------------- lý do kết thúc
def classify_game(row: dict[str, str]) -> tuple[str, int]:
    """(lý do, ply cuối) của một dòng ván: replay khai cuộc + nước trên game của `game_spec`.

    Thắng/thua: bên thua (sắp đi) đang bị chiếu → `mate`, không → `stalemate` (bí nước).
    Hòa: ply < max_plies → `repetition`, ngược lại `max_plies`. `termination ≠ normal` → `error`.
    """
    seq = [int(m) for m in f"{row['opening']};{row['moves']}".split(";") if m != ""]
    if row["termination"] != "normal":
        return "error", len(seq)
    gs = json.loads(row["game_spec"])
    game = make_game(GameSpec(gs["kind"], gs["params"]))
    for m in seq:
        game.play(m)
    w = game.winner()
    if w is None or str(w) != row["winner"]:
        raise ValueError(f"{row['game_id']}: replay winner {w} ≠ CSV {row['winner']}")
    if w != 0:
        return ("mate" if game.in_check() else "stalemate"), game.ply
    return ("max_plies" if game.ply >= game.max_plies else "repetition"), game.ply


# ---------------------------------------------------------------- thống kê mỗi bên
def side_game_stats(moves: list[dict[str, str]], side: str) -> dict[str, float | None]:
    """Một ván, một bên ("A"/"B"): iter/s (chỉ nước có search), độ sâu cây, ply rollout/iter, ..."""
    ms = [m for m in moves if m["side"] == side]
    times = [float(m["time"]) for m in ms if m["time"] != ""]
    search = [
        m for m in ms if m["tactic"] not in DIRECT_TACTICS and m["iterations"] not in ("", "0")
    ]
    its = sum(float(m["iterations"]) for m in search)
    at = sum(float(m["agent_time"]) for m in search)
    rp = [float(m["rollout_plies"]) for m in search if m["rollout_plies"] != ""]
    td = [float(m["max_depth"]) for m in search if m["max_depth"] != ""]
    nodes = [float(m["nodes"]) for m in ms if m["nodes"] != ""]
    dr = [int(m["depth_reached"]) for m in ms if m.get("depth_reached", "") != ""]
    return {
        "time_sum": sum(times),
        "time_n": len(times),
        "time_max": max(times) if times else None,
        "iter_per_s": its / at if search and at > 0 else None,
        "tree_depth": sum(td) / len(td) if td else None,
        "rollout_per_iter": sum(rp) / its if rp and its else None,
        "nodes_mean": sum(nodes) / len(nodes) if nodes else None,
        "depth_reached": dr,
    }


def _cv(xs: list[float]) -> float | None:
    if len(xs) < 2:
        return None
    m = statistics.fmean(xs)
    return statistics.stdev(xs) / m if m else None


SIDE_COLS = (
    "s_per_move_mean",
    "s_per_move_max",
    "iter_per_s_mean",
    "iter_per_s_median",
    "iter_per_s_cv",
    "tree_depth_mean",
    "rollout_plies_per_iter",
    "nodes_per_move",
    "depth_reached_mean",
    "depth_reached_min",
    "depth_reached_max",
)
MATCH_COLUMNS = [
    "point",
    "label_a",
    "label_b",
    "split",
    "n",
    "wins",
    "draws",
    "losses",
    "score",
    "score_lo",
    "score_hi",
    "distinct_games",
    *(f"term_{t}" for t in TERMS),
    "ply_mean",
    "ply_median",
    *(f"{s}_{c}" for s in ("a", "b") for c in SIDE_COLS),
    "workers",
    "git_commits",
    "git_dirty",
]


def summarize_point(
    point: str, rows: list[dict[str, str]], moves: list[dict[str, str]]
) -> list[dict[str, Any]]:
    """3 dòng: `all`, `A=Đỏ`, `A=Đen` (A = agent thứ nhất của điểm)."""
    by_game: dict[str, list[dict[str, str]]] = {}
    for m in moves:
        by_game.setdefault(m["game_id"], []).append(m)
    info = {r["game_id"]: classify_game(r) for r in rows}
    out = []
    for split, sel in (("all", None), ("A=Đỏ", "1"), ("A=Đen", "0")):
        rs = [r for r in rows if sel is None or r["a_is_x"] == sel]
        n = len(rs)
        res = [float(r["result_a"]) for r in rs]
        score = sum(res) / n if n else math.nan
        lo, hi = wilson_score(score, n) if n else (math.nan, math.nan)
        plies = [info[r["game_id"]][1] for r in rs]
        row: dict[str, Any] = {
            "point": point,
            "label_a": rs[0]["label_a"] if rs else "",
            "label_b": rs[0]["label_b"] if rs else "",
            "split": split,
            "n": n,
            "wins": res.count(1.0),
            "draws": res.count(0.5),
            "losses": res.count(0.0),
            "score": score,
            "score_lo": lo,
            "score_hi": hi,
            "distinct_games": len({(r["opening"], r["moves"]) for r in rs}),
            "ply_mean": statistics.fmean(plies) if plies else None,
            "ply_median": statistics.median(plies) if plies else None,
            "workers": ";".join(sorted({r["workers"] for r in rs})),
            "git_commits": ";".join(sorted({r["git_commit"][:7] for r in rs})),
            "git_dirty": ";".join(sorted({r["git_dirty"] for r in rs})),
        }
        for t in TERMS:
            row[f"term_{t}"] = sum(info[r["game_id"]][0] == t for r in rs)
        for side in ("A", "B"):
            st = [side_game_stats(by_game.get(r["game_id"], []), side) for r in rs]
            p = side.lower()
            tn = sum(s["time_n"] for s in st)  # type: ignore[misc]
            ips = [s["iter_per_s"] for s in st if s["iter_per_s"] is not None]
            td = [s["tree_depth"] for s in st if s["tree_depth"] is not None]
            rp = [s["rollout_per_iter"] for s in st if s["rollout_per_iter"] is not None]
            nd = [s["nodes_mean"] for s in st if s["nodes_mean"] is not None]
            dr = [d for s in st for d in s["depth_reached"]]  # type: ignore[union-attr]
            tmax = [s["time_max"] for s in st if s["time_max"] is not None]
            row |= {
                f"{p}_s_per_move_mean": sum(s["time_sum"] for s in st) / tn if tn else None,  # type: ignore[misc]
                f"{p}_s_per_move_max": max(tmax) if tmax else None,
                f"{p}_iter_per_s_mean": statistics.fmean(ips) if ips else None,
                f"{p}_iter_per_s_median": statistics.median(ips) if ips else None,
                f"{p}_iter_per_s_cv": _cv(ips),  # type: ignore[arg-type]
                f"{p}_tree_depth_mean": statistics.fmean(td) if td else None,
                f"{p}_rollout_plies_per_iter": statistics.fmean(rp) if rp else None,
                f"{p}_nodes_per_move": statistics.fmean(nd) if nd else None,
                f"{p}_depth_reached_mean": statistics.fmean(dr) if dr else None,
                f"{p}_depth_reached_min": min(dr) if dr else None,
                f"{p}_depth_reached_max": max(dr) if dr else None,
            }
        out.append(row)
    return out


def load_point(point: str, quick: bool, raw_dir: Path = RAW_DIR):
    p = raw_path(point, quick, raw_dir)
    if not p.exists():
        return [], []
    mp = moves_path_for(p)
    return read_rows(p), (read_rows(mp) if mp.exists() else [])


def point_score(point: str, quick: bool, raw_dir: Path = RAW_DIR) -> tuple[float, int]:
    rows, _ = load_point(point, quick, raw_dir)
    n = len(rows)
    return (sum(float(r["result_a"]) for r in rows) / n if n else math.nan), n


# ---------------------------------------------------------------- luật chốt trước (D-25)
def l_verdict(score: float, n: int) -> str:
    """c4 (A = L0 vs L10): Wilson cận dưới > 0,5 → `L0_stronger`; cận trên < 0,5 → `L10_stronger`;
    chứa 0,5 → `tie` (giữ L = 10)."""
    lo, hi = wilson_score(score, n)
    if lo > 0.5:
        return "L0_stronger"
    if hi < 0.5:
        return "L10_stronger"
    return "tie"


def best_rollout(c1: tuple[float, int], c4: tuple[float, int]) -> str:
    """MCTS tốt nhất ở (c): mặc định `L10`; X ∈ {Lend (c1), L0 (c4)} thay khi X vs L10 có Wilson cận
    dưới > 0,5 (cả hai → điểm cao hơn)."""
    ok = [(s, name) for name, (s, n) in (("Lend", c1), ("L0", c4)) if wilson_score(s, n)[0] > 0.5]
    return max(ok)[1] if ok else "L10"


# ---------------------------------------------------------------- (b) ordering
ORDER_CONFIGS = ("none", "mvv_lva", "mvv_lva+tt")
ORDER_COLUMNS = [
    "pos_id",
    "fen",
    "depth",
    "config",
    "nodes",
    "seconds",
    "value",
    "move",
    "value_match",
    "git_commit",
    "git_dirty",
]


def order_spec(config: str, depth: int) -> AgentSpec:
    if config == "none":
        return ab_spec(depth, order=None)
    return ab_spec(depth, use_tt=config.endswith("+tt"))


def order_fens() -> list[str]:
    return [START_FEN, *midgame_fens(N_MIDGAME, seed=ORDER_FEN_SEED)]


def run_ordering(
    quick: bool,
    raw_dir: Path = RAW_DIR,
    fens: list[str] | None = None,
    depths: Sequence[int] = ORDER_DEPTHS,
) -> list[dict[str, str]]:
    """Mỗi (depth, thế, cấu hình) một dòng; `none` chạy trước làm chuẩn giá trị gốc.

    Chạy tiếp được (bỏ khóa đã có trong file raw)."""
    fens = fens if fens is not None else order_fens()
    path = raw_dir / f"{prefix(quick)}ordering.csv"
    done = {
        (r["pos_id"], r["depth"], r["config"]): r
        for r in (read_rows(path) if path.exists() else [])
    }
    commit, dirty = git_info()
    for depth in depths:
        n_fens = QUICK_DEPTH4_FENS if (quick and depth >= 4) else len(fens)
        for i, fen in enumerate(fens[:n_fens]):
            for cfg in ORDER_CONFIGS:
                key = (str(i), str(depth), cfg)
                if key in done:
                    continue
                agent = make_agent(order_spec(cfg, depth), None)
                move, value = agent.search(Xiangqi(fen, max_plies=MAX_PLIES))
                ref = done.get((str(i), str(depth), "none"))
                match = (
                    1 if cfg == "none" else int(ref is not None and float(ref["value"]) == value)
                )
                row = {
                    "pos_id": i,
                    "fen": fen,
                    "depth": depth,
                    "config": cfg,
                    "nodes": agent.stats["nodes"],
                    "seconds": round(agent.stats["time"], 4),
                    "value": value,
                    "move": move,
                    "value_match": match,
                    "git_commit": commit,
                    "git_dirty": int(dirty),
                }
                _append(path, ORDER_COLUMNS, row)
                done[key] = {k: str(v) for k, v in row.items()}
                print(
                    f"  [b] d{depth} pos {i} {cfg}: {row['nodes']} nút, {row['seconds']} s, "
                    f"v={value}{'' if match else '  ≠ none!'}",
                    flush=True,
                )
    return list(done.values())


ORDER_TABLE_COLUMNS = [
    "depth",
    "config",
    "n_pos",
    "nodes_sum",
    "seconds_sum",
    "nodes_per_s",
    "nodes_vs_none",
    "seconds_vs_none",
    "value_match",
    "value_mismatch",
]


def ordering_table(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Gộp theo (depth, cấu hình) trên các thế có đủ 3 cấu hình; tỉ lệ so với `none`."""
    out = []
    for depth in sorted({int(r["depth"]) for r in rows}):
        rs = [r for r in rows if int(r["depth"]) == depth]
        full = {
            p
            for p in {r["pos_id"] for r in rs}
            if {r["config"] for r in rs if r["pos_id"] == p} == set(ORDER_CONFIGS)
        }
        agg = {}
        for cfg in ORDER_CONFIGS:
            cs = [r for r in rs if r["config"] == cfg and r["pos_id"] in full]
            agg[cfg] = (sum(int(r["nodes"]) for r in cs), sum(float(r["seconds"]) for r in cs), cs)
        for cfg in ORDER_CONFIGS:
            nodes, secs, cs = agg[cfg]
            n0, s0, _ = agg["none"]
            m = sum(int(r["value_match"]) for r in cs)
            out.append(
                {
                    "depth": depth,
                    "config": cfg,
                    "n_pos": len(cs),
                    "nodes_sum": nodes,
                    "seconds_sum": secs,
                    "nodes_per_s": nodes / secs if secs else None,
                    "nodes_vs_none": nodes / n0 if n0 else None,
                    "seconds_vs_none": secs / s0 if s0 else None,
                    "value_match": m,
                    "value_mismatch": len(cs) - m,
                }
            )
    return out


# ---------------------------------------------------------------- bench + runinfo
def power_status() -> tuple[str, int | str]:
    from gameai.experiments.e6_tactics import power_status as ps

    return ps()


def run_bench() -> float:
    """Bench ngắn như E6 (1 s/thế, thế 8/16/24 quân, rand + h300) → trung vị iter/s / `e5_bench`."""
    from gameai.experiments.e5_rollout import bench

    rows = bench(seconds=1.0, plies=(8, 16, 24), seeds=(0,), path=None)
    ref_path = TABLE_DIR / "e5_bench.csv"
    if not ref_path.exists():
        return math.nan
    ref = {
        (r["rollout"], r["plies"], r["seed"]): float(r["iter_per_s"]) for r in read_rows(ref_path)
    }
    ratios = [
        r["iter_per_s"] / e
        for r in rows
        if (e := ref.get((r["rollout"], str(r["plies"]), str(r["seed"]))))
    ]
    return round(statistics.median(ratios), 3) if ratios else math.nan


RUNINFO_COLUMNS = [
    "part",
    "workers",
    "n_pairs",
    "power",
    "battery_pct",
    "bench_vs_e5",
    "started",
    "finished",
    "wall_s",
    "git_commit",
    "git_dirty",
    "note",
]


class Ctx:
    """Trạng thái một lần gọi: quick, workers, cờ, bench (đo một lần đầu khúc)."""

    def __init__(self, args: argparse.Namespace) -> None:
        self.quick: bool = args.quick
        self.workers: int = args.workers
        self.allow_code_change: bool = args.allow_code_change
        self.n_pairs: int = args.pairs or (QUICK_PAIRS if args.quick else N_PAIRS)
        self.raw_dir: Path = args.raw_dir
        self.table_dir: Path = args.table_dir
        self.fig_dir: Path = args.fig_dir
        self.bench: float | None = None
        self.skip_bench: bool = args.skip_bench

    def log_part(
        self, part: str, started: str, t0: float, note: str = "", workers: int | None = None
    ) -> None:
        if self.bench is None and not self.skip_bench:
            self.bench = run_bench()
        commit, dirty = git_info()
        power, pct = power_status()
        _append(
            self.raw_dir / f"{prefix(self.quick)}runinfo.csv",
            RUNINFO_COLUMNS,
            {
                "part": part,
                "workers": workers or self.workers,
                "n_pairs": self.n_pairs,
                "power": power,
                "battery_pct": pct,
                "bench_vs_e5": self.bench,
                "started": started,
                "finished": _now(),
                "wall_s": round(time.perf_counter() - t0, 1),
                "git_commit": commit,
                "git_dirty": int(dirty),
                "note": note,
            },
        )


def run_point(
    ctx: Ctx,
    point: str,
    spec_a: AgentSpec,
    spec_b: AgentSpec,
    workers: int | None = None,
    out: Path | None = None,
) -> list[dict[str, str]]:
    started, t0 = _now(), time.perf_counter()
    w = workers or ctx.workers
    out = out or raw_path(point, ctx.quick, ctx.raw_dir)
    print(
        f"[{point}] {spec_a.name} vs {spec_b.name}: {2 * ctx.n_pairs} ván, {w} worker → {out}",
        flush=True,
    )
    rows = run_match(
        out,
        GAME,
        spec_a,
        spec_b,
        ctx.n_pairs,
        base_seed=BASE_SEED,
        workers=w,
        random_opening=RANDOM_OPENING,
        allow_code_change=ctx.allow_code_change,
        extra_move_stats=EXTRA_MOVE_STATS,
    )
    s, n = sum(float(r["result_a"]) for r in rows) / len(rows), len(rows)
    lo, hi = wilson_score(s, n)
    print(
        f"[{point}] điểm A {s:.3f} [{lo:.2f}; {hi:.2f}] ({n} ván), "
        f"{time.perf_counter() - t0:.0f} s",
        flush=True,
    )
    ctx.log_part(point, started, t0, note=out.name, workers=w)
    return rows


# ---------------------------------------------------------------- phần
def part_b(ctx: Ctx) -> int:
    started, t0 = _now(), time.perf_counter()
    rows = run_ordering(ctx.quick, ctx.raw_dir)
    tab = ordering_table(rows)
    _write(ctx.table_dir / f"{prefix(ctx.quick)}ordering.csv", ORDER_TABLE_COLUMNS, tab)
    bad = sum(int(r["value_mismatch"]) for r in tab)
    print(f"[b] xong, lệch giá trị gốc: {bad}", flush=True)
    ctx.log_part("b", started, t0, note=f"value_mismatch={bad}", workers=1)
    return 0


def decide(ctx: Ctx) -> tuple[str, str] | None:
    """(kết luận c4, MCTS tốt nhất) nếu c1 + c4 đủ ván; ngược lại None."""
    need = 2 * ctx.n_pairs
    c1, c4 = point_score("c1", ctx.quick, ctx.raw_dir), point_score("c4", ctx.quick, ctx.raw_dir)
    if c1[1] < need or c4[1] < need:
        print(f"[luật] chưa đủ ván: c1 {c1[1]}/{need}, c4 {c4[1]}/{need}")
        return None
    v, best = l_verdict(*c4), best_rollout(c1, c4)
    lo, hi = wilson_score(*c4)
    print(
        f"[luật c4] L0 vs L10 điểm {c4[0]:.3f} [{lo:.2f}; {hi:.2f}] → {v}; "
        f"MCTS tốt nhất ở (c): {best}",
        flush=True,
    )
    return v, best


def part_d(ctx: Ctx, points: Sequence[str] = D_POINTS) -> int:
    dec = decide(ctx)
    if dec is None:
        return 2
    verdict, best = dec
    if verdict == "L0_stronger":
        if not ctx.quick:
            print("[luật c4] L0 mạnh hơn rõ → DỪNG trước (d), báo An (D-25).")
            return 3
        print("[luật c4] (quick) L0 mạnh hơn — chỉ minh họa, vẫn chạy (d) với luật best.")
    specs = d_specs(best)
    for p in points:
        run_point(ctx, p, *specs[p])
    return 0


def part_wcheck(ctx: Ctx) -> int:
    """iter/s của MCTS (A) ở c3: 1 worker vs `WCHECK_WORKERS` (file riêng `c3_w1`, `c3_w3`);
    giảm > 15 % → khuyến nghị full 1 worker, ngược lại `WCHECK_WORKERS` (D-25)."""
    a, b = FIXED_POINTS["c3"]
    wn = WCHECK_WORKERS
    paths = {}
    for w in (1, wn):
        paths[f"w{w}"] = raw_path(f"c3_w{w}", ctx.quick, ctx.raw_dir)
        run_point(ctx, f"c3_w{w}", a, b, workers=w, out=paths[f"w{w}"])
    med = {}
    for name, path in paths.items():
        rows, moves = read_rows(path), read_rows(moves_path_for(path))
        by = {}
        for m in moves:
            by.setdefault(m["game_id"], []).append(m)
        ips = [
            x for r in rows if (x := side_game_stats(by.get(r["game_id"], []), "A")["iter_per_s"])
        ]
        med[name] = statistics.median(ips) if ips else math.nan
    drop = 1 - med[f"w{wn}"] / med["w1"]
    rec = 1 if drop > WORKER_DROP_LIMIT else wn
    rows = [{"workers": k, "median_iter_per_s": v} for k, v in med.items()]
    rows.append({"workers": "drop", "median_iter_per_s": drop, "recommend": rec})
    _write(
        ctx.table_dir / f"{prefix(ctx.quick)}workers.csv",
        ["workers", "median_iter_per_s", "recommend"],
        rows,
    )
    print(
        f"[wcheck] iter/s trung vị 1 worker {med['w1']:.0f}, {wn} worker "
        f"{med[f'w{wn}']:.0f} → giảm {drop:.1%} → full dùng {rec} worker",
        flush=True,
    )
    return 0


def part_summary(ctx: Ctx) -> int:
    out = []
    for p in (*C_POINTS, *D_POINTS, *A_POINTS):
        rows, moves = load_point(p, ctx.quick, ctx.raw_dir)
        if rows:
            out += summarize_point(p, rows, moves)
    _write(ctx.table_dir / f"{prefix(ctx.quick)}matches.csv", MATCH_COLUMNS, out)
    order = ctx.raw_dir / f"{prefix(ctx.quick)}ordering.csv"
    if order.exists():
        _write(
            ctx.table_dir / f"{prefix(ctx.quick)}ordering.csv",
            ORDER_TABLE_COLUMNS,
            ordering_table(read_rows(order)),
        )
    if out:
        plot_scores(
            [r for r in out if r["split"] == "all"], ctx.fig_dir / f"{prefix(ctx.quick)}scores.png"
        )
    for r in out:
        if r["split"] == "all":
            print(
                f"[summary] {r['point']}: {r['label_a']} vs {r['label_b']} "
                f"{r['wins']}/{r['draws']}/{r['losses']} điểm {_f(r['score'], 3)} "
                f"[{_f(r['score_lo'], 2)}; {_f(r['score_hi'], 2)}]"
            )
    if ctx.quick:
        write_estimate(ctx)
    return 0


POINT_NAMES = {
    "c1": "c1 Lend vs L10",
    "c2": "c2 Lend vs Random",
    "c3": "c3 L10 vs Random",
    "c4": "c4 L0 vs L10",
    "d1": "d1 MCTS vs AB (1 s)",
    "d2": "d2 MCTS vs AB (2,5 s)",
    "a1": "a1 AB d1 vs Random",
    "a2": "a2 AB d2 vs Random",
}


def plot_scores(rows: list[dict[str, Any]], path: Path) -> None:
    """Điểm A + khoảng Wilson 95 % mỗi điểm (dòng `all`), đường 0,5."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from gameai.experiments.figfmt import vn_figure

    fig, ax = plt.subplots(figsize=(7, 0.45 * len(rows) + 1.2))
    ys = list(range(len(rows)))[::-1]
    for y, r in zip(ys, rows, strict=True):
        ax.errorbar(
            r["score"],
            y,
            xerr=[[r["score"] - r["score_lo"]], [r["score_hi"] - r["score"]]],
            fmt="o",
            color="#1f5fa8",
            capsize=3,
        )
    ax.axvline(0.5, color="#888", lw=1, ls="--")
    ax.set_yticks(ys, [POINT_NAMES.get(r["point"], r["point"]) for r in rows])
    ax.set_xlim(-0.03, 1.03)
    ax.set_xlabel("Điểm của bên A (thắng 1, hòa 0,5) · khoảng Wilson 95 %")
    vn_figure(fig)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)


ESTIMATE_COLUMNS = ["part", "quick_games", "game_s_mean", "full_games", "workers", "full_min"]


def write_estimate(ctx: Ctx) -> None:
    """Ước tính full từ quick: s/ván (Σ thời gian nước hai bên) × 50 / worker; (b) theo giờ đo."""
    w_full = ctx.workers
    wfile = ctx.table_dir / f"{prefix(True)}workers.csv"
    if wfile.exists():
        rec = [r for r in read_rows(wfile) if r["workers"] == "drop"]
        if rec and rec[0]["recommend"]:
            w_full = int(rec[0]["recommend"])
    rows = []
    for p in (*C_POINTS, *D_POINTS, *A_POINTS):
        rs, _ = load_point(p, True, ctx.raw_dir)
        if not rs:
            continue
        gs = [float(r["a_time_sum"] or 0) + float(r["b_time_sum"] or 0) for r in rs]
        m = statistics.fmean(gs)
        rows.append(
            {
                "part": p,
                "quick_games": len(rs),
                "game_s_mean": m,
                "full_games": 2 * N_PAIRS,
                "workers": w_full,
                "full_min": m * 2 * N_PAIRS / w_full / 60,
            }
        )
    order = ctx.raw_dir / f"{prefix(True)}ordering.csv"
    if order.exists():
        orows = read_rows(order)
        n_all = 1 + N_MIDGAME
        t = sum(float(r["seconds"]) for r in orows if int(r["depth"]) < 4)
        t4 = sum(float(r["seconds"]) for r in orows if int(r["depth"]) >= 4)
        rows.append(
            {
                "part": "b",
                "quick_games": "",
                "game_s_mean": "",
                "full_games": "",
                "workers": 1,
                "full_min": (t + t4 * n_all / QUICK_DEPTH4_FENS) / 60,
            }
        )
    rows.append({"part": "TOTAL", "full_min": sum(r["full_min"] for r in rows), "workers": w_full})
    _write(ctx.table_dir / f"{prefix(True)}estimate.csv", ESTIMATE_COLUMNS, rows)
    for r in rows:
        print(f"[estimate] {r['part']:<6} {r['full_min']:.1f} phút")


# ---------------------------------------------------------------- main
class _Tee:
    def __init__(self, stream: Any, path: Path) -> None:
        self.stream = stream
        path.parent.mkdir(parents=True, exist_ok=True)
        self.fh = path.open("a", encoding="utf-8")

    def write(self, s: str) -> int:
        self.stream.write(s)
        self.fh.write(s)
        return len(s)

    def flush(self) -> None:
        self.stream.flush()
        self.fh.flush()


PARTS = ("bench", "b", "c", *C_POINTS, "d", *D_POINTS, "a", *A_POINTS, "wcheck", "summary", "all")


def run_part(ctx: Ctx, part: str) -> int:
    if part == "bench":
        started, t0 = _now(), time.perf_counter()
        ctx.bench = run_bench()
        print(f"[bench] {ctx.bench}× e5_bench")
        ctx.log_part("bench", started, t0)
        return 0
    if part == "b":
        return part_b(ctx)
    if part in FIXED_POINTS:
        run_point(ctx, part, *FIXED_POINTS[part])
        return 0
    if part == "c":
        for p in C_POINTS:
            run_point(ctx, p, *FIXED_POINTS[p])
        decide(ctx)
        return 0
    if part == "d":
        return part_d(ctx)
    if part in D_POINTS:
        return part_d(ctx, (part,))
    if part == "a":
        for p in A_POINTS:
            run_point(ctx, p, *FIXED_POINTS[p])
        return 0
    if part == "wcheck":
        return part_wcheck(ctx)
    if part == "summary":
        return part_summary(ctx)
    # all: b → c → luật c4 → d → a (quick: + wcheck) → summary
    for p in ("b", "c", "d", "a"):
        rc = run_part(ctx, p)
        if rc:
            part_summary(ctx)
            return rc
    if ctx.quick:
        part_wcheck(ctx)
    return part_summary(ctx)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("part", choices=PARTS)
    ap.add_argument(
        "--quick", action="store_true", help=f"{QUICK_PAIRS} khai cuộc/điểm, file e7quick_*"
    )
    ap.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    ap.add_argument("--pairs", type=int, default=0, help=f"số khai cuộc/điểm (mặc định {N_PAIRS})")
    ap.add_argument("--allow-code-change", action="store_true")
    ap.add_argument("--allow-battery", action="store_true", help="cho chạy full khi dùng pin")
    ap.add_argument("--skip-bench", action="store_true")
    ap.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    ap.add_argument("--table-dir", type=Path, default=TABLE_DIR)
    ap.add_argument("--fig-dir", type=Path, default=FIG_DIR)
    ap.add_argument("--log", type=Path, default=None)
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    log = args.log or LOG_DIR / ("e7quick.log" if args.quick else "e7_full.log")
    old = sys.stdout
    sys.stdout = _Tee(old, log)  # type: ignore[assignment]
    try:
        power, pct = power_status()
        print(
            f"\n===== {_now()} e7_xiangqi {' '.join(argv or sys.argv[1:])} "
            f"| power {power} {pct}% | git {'/'.join(map(str, git_info()))}"
        )
        if not args.quick and power == "battery" and not args.allow_battery:
            print("DỪNG: full chỉ chạy khi cắm sạc (D-21); dùng --allow-battery nếu cố ý.")
            return 2
        return run_part(Ctx(args), args.part)
    finally:
        sys.stdout.flush()
        sys.stdout = old


if __name__ == "__main__":
    sys.exit(main())
