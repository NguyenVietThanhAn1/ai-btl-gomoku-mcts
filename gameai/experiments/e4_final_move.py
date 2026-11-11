"""E4: chọn nước cuối của MCTS — N lớn nhất vs W/N lớn nhất (đề ý 4) — D-19.

Phần 1 (`roots`): thống kê gốc (W, N, W/N) ở các thế cờ; so nước max_n / max_wn / max_lcb
(tính offline từ cây, không đổi agent) với giá trị trò chơi (3×3) hoặc tham chiếu
20 000 iter (15×15).
Phần 2 (`match`): `final_move=max_n` vs `max_wn` cùng iteration, đổi lượt — chỉ 3×3 (ở 15×15 hai
tiêu chí không chọn khác nhau ở c chuẩn, xem D-19).

    python -m gameai.experiments.e4_final_move all --quick
    python -m gameai.experiments.e4_final_move roots | match | plot
"""

from __future__ import annotations

import argparse
import csv
import math
import statistics
import sys
import time
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from gameai.agents.mcts import MCTSAgent, Node
from gameai.agents.registry import AgentSpec, GameSpec, make_agent, make_game
from gameai.core.game import Game, Move
from gameai.experiments.common import (
    SUMMARY_COLUMNS,
    add_runner_args,
    moves_path_for,
    read_rows,
    run_match,
    summarize,
    wilson,
)
from gameai.experiments.e1_nodes import build_game, make_position
from gameai.experiments.e2_never_lose import solve
from gameai.experiments.e3_c_sweep import SERIES_COLORS, fit_cost

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "results" / "raw"
TABLE_DIR = ROOT / "results" / "tables"
FIG_DIR = ROOT / "results" / "figures"

C = 1.4
C_SENS = 0.5  # biến thể độ nhạy 15×15 — không phải c chuẩn (D-19)
GAME3 = GameSpec("kinrow", {"n": 3, "k": 3})
GAME15 = GameSpec("kinrow", {"n": 15, "k": 5})
SPEEDUP_4_WORKERS = 3.5  # như E3

# Phần 1 — 3×3
ROOT_ITERS_3 = (10, 20, 50, 100, 250, 1000)
QUICK_ROOT_ITERS_3 = (10, 100)
QUICK_STRIDE_3 = 15  # quick: mỗi thế thứ 15 theo thứ tự chuẩn (0, 15, 30, …)
SEED_3 = 0
EXAMPLE_ITER_3 = 100
N_EXAMPLES = 3
# Phần 1 — 15×15
C_15 = (C, C_SENS)
PLIES_15 = (6, 8, 10, 12, 14, 16, 18, 20, 22, 24)
SEEDS_15 = (0, 1, 2, 3, 4)
ROOT_ITERS_15 = (50, 250, 1000)
REF_ITER_15 = 20000
QUICK_PLIES_15 = PLIES_15[:3]
QUICK_SEEDS_15 = (0,)
QUICK_ROOT_ITERS_15 = (50, 250)
QUICK_REF_ITER_15 = 5000
TOP_K_15 = 5
# Phần 2 — đối đầu: board → (game, iters, n_pairs, quick_pairs). 15×15 bỏ (D-19).
MATCH = {
    "3x3": (GAME3, (10, 20, 50, 100, 250), 100, 2),
}

ROOT_COLUMNS = ["board", "kind", "c", "pos_id", "plies", "n_moves", "moves", "iterations", "seed",
                "tactic", "time", "child_order", "move", "W", "N", "wn", "wn_lo", "wn_hi",
                "is_max_n", "is_max_wn", "is_max_lcb", "value", "optimal"]  # fmt: skip
SUMMARY_ROOT_COLUMNS = ["board", "c", "set", "iterations", "n_positions", "n_skipped_tactic",
                        "n_differ", "differ_rate", "opt_max_n", "opt_max_wn", "opt_max_lcb",
                        "differ_opt_max_n", "differ_opt_max_wn", "differ_opt_max_lcb",
                        "lcb_eq_max_n", "max_n_child_N_median", "max_wn_child_N_median",
                        "max_wn_child_N_max", "children_median", "max_n_wn_is_1",
                        "max_n_tied_median"]  # fmt: skip
EXAMPLE_COLUMNS = ["board", "example", *ROOT_COLUMNS[2:], "ref_iterations", "ref_W", "ref_N",
                   "ref_wn"]  # fmt: skip
MATCH_COLUMNS = ["board", "iterations", *SUMMARY_COLUMNS, "score_lo", "score_hi"]
ESTIMATE_COLUMNS = ["part", "searches_or_games", "fit_a", "fit_b", "seq_minutes",
                    "est_minutes"]  # fmt: skip


def prefix(quick: bool) -> str:
    return "e4quick_" if quick else "e4_"


def _fmt(v: Any) -> Any:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return ""
    if isinstance(v, bool):
        return int(v)
    return v


def write_csv(rows: Iterable[dict[str, Any]], columns: list[str], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, columns, extrasaction="ignore")
        w.writeheader()
        w.writerows({k: _fmt(r.get(k)) for k in columns} for r in rows)


# ---------------------------------------------------------------- spec MCTS


def mcts_params(board: int, iterations: int, final_move: str = "max_n",
                c: float = C) -> dict[str, Any]:  # fmt: skip
    """3×3: rollout random, tactics tắt (D-16). 15×15: h300 + tactics (D-14). c = 1.4 (D-19)."""
    p: dict[str, Any] = {"iterations": iterations, "c": c, "final_move": final_move}
    if board == 3:
        p["check_tactics"] = False
    else:
        p.update({"rollout": "heavy_kinrow", "temperature": 300, "check_tactics": True})
    return p


def mcts_spec(board: int, iterations: int, final_move: str) -> AgentSpec:
    tag = {"max_n": "maxn", "max_wn": "maxwn"}[final_move]
    return AgentSpec("mcts", mcts_params(board, iterations, final_move),
                     label=f"{tag}_i{iterations}")  # fmt: skip


# ---------------------------------------------------------------- tiêu chí chọn ở gốc


def _argmax(children: list[Node], key) -> int:
    """Chỉ số con có key lớn nhất; bằng → con mở rộng trước (như `max` của Python)."""
    best = 0
    for i in range(1, len(children)):
        if key(children[i]) > key(children[best]):
            best = i
    return best


def lcb(ch: Node) -> float:
    """Cận dưới Wilson 95 % của W/N (xấp xỉ: hòa = 0,5 nên không nhị thức; D-19)."""
    return wilson(ch.W, ch.N)[0]  # type: ignore[arg-type]


def choose_indices(children: list[Node]) -> tuple[int, int, int]:
    """(max_n, max_wn, max_lcb) — tie-break đúng như `MCTSAgent._final_child` (D-19)."""
    return (
        _argmax(children, lambda ch: (ch.N, ch.W)),
        _argmax(children, lambda ch: (ch.W / ch.N, ch.N)),
        _argmax(children, lambda ch: (lcb(ch), ch.N)),
    )


def search_root(game_spec: GameSpec, moves: list[Move], iterations: int, seed: int,
                c: float = C) -> tuple[MCTSAgent, float]:  # fmt: skip
    """MCTS (max_n) trên thế `moves`; trả (agent, giây). `agent.root` None nếu tactic đi tắt."""
    board = int(game_spec.params["n"])
    agent = make_agent(AgentSpec("mcts", mcts_params(board, iterations, c=c)), seed)
    assert isinstance(agent, MCTSAgent)
    g = build_game(game_spec, moves)
    t0 = time.perf_counter()
    agent.select_move(g)
    return agent, time.perf_counter() - t0


def root_rows(agent: MCTSAgent, base: dict[str, Any],
              values: dict[Move, int] | None = None) -> list[dict[str, Any]]:  # fmt: skip
    """Một dòng/con của gốc theo thứ tự mở rộng. `values`: giá trị trò chơi (1/0/−1) của nước theo
    góc nhìn người đi ở gốc → cột `value`, `optimal` (= bằng giá trị tốt nhất)."""
    assert agent.root is not None
    children = agent.root.children
    i_n, i_wn, i_lcb = choose_indices(children)
    best = max(values.values()) if values else None
    out = []
    for i, ch in enumerate(children):
        lo, hi = wilson(ch.W, ch.N)  # type: ignore[arg-type]
        v = values[ch.move] if values else None
        out.append({**base, "child_order": i, "move": ch.move, "W": ch.W, "N": ch.N,
                    "wn": ch.W / ch.N, "wn_lo": lo, "wn_hi": hi, "is_max_n": i == i_n,
                    "is_max_wn": i == i_wn, "is_max_lcb": i == i_lcb, "value": v,
                    "optimal": None if v is None else v == best})  # fmt: skip
    return out


# ---------------------------------------------------------------- thế 3×3


def enumerate_3x3(min_moves: int = 2) -> list[list[Move]]:
    """Mọi thế chưa kết thúc đạt được từ bàn trống, mỗi key một lần (chuỗi nước tìm thấy đầu tiên),
    có ≥ `min_moves` nước hợp lệ; sắp theo (số quân, key) — thứ tự chuẩn của D-19."""
    g = make_game(GAME3)
    seen: dict[Any, list[Move]] = {}

    def walk(path: list[Move]) -> None:
        k = g.key()
        if k in seen or g.is_terminal():
            return
        seen[k] = list(path)
        for m in g.legal_moves():
            g.play(m)
            path.append(m)
            walk(path)
            path.pop()
            g.undo()

    walk([])
    items = [(len(p), k, p) for k, p in seen.items()
             if 9 - len(p) >= min_moves]  # 3×3: số nước hợp lệ = số ô trống  # fmt: skip
    items.sort(key=lambda t: (t[0], t[1]))
    return [p for _, _, p in items]


def move_values(g: Game, cache: dict[object, int]) -> dict[Move, int]:
    """Giá trị trò chơi (1/0/−1) của từng nước theo góc nhìn người đi ở `g` (memo theo key)."""
    out = {}
    for m in g.legal_moves():
        g.play(m)
        out[m] = -solve(g, cache)
        g.undo()
    return out


def roots_3x3(quick: bool) -> list[dict[str, Any]]:
    positions = enumerate_3x3()
    if quick:
        positions = positions[::QUICK_STRIDE_3]
    iters = QUICK_ROOT_ITERS_3 if quick else ROOT_ITERS_3
    cache: dict[object, int] = {}
    rows: list[dict[str, Any]] = []
    for pid, moves in enumerate(positions):
        g = build_game(GAME3, moves)
        values = move_values(g, cache)
        for it in iters:
            agent, sec = search_root(GAME3, moves, it, SEED_3)
            base = {"board": "3x3", "kind": "search", "c": C, "pos_id": pid, "plies": len(moves),
                    "n_moves": len(values), "moves": ";".join(map(str, moves)),
                    "iterations": it, "seed": SEED_3, "tactic": agent.stats.get("tactic", 0),
                    "time": sec}  # fmt: skip
            rows += root_rows(agent, base, values)
    return rows


# ---------------------------------------------------------------- thế 15×15


def roots_15x15(quick: bool) -> list[dict[str, Any]]:
    """Mỗi (c, thế, seed, iter): dòng các con; tactic đi tắt → 1 dòng không có `move` (đếm bỏ
    qua). Rồi tham chiếu (kind = "ref") cho các thế ví dụ của mỗi c."""
    plies = QUICK_PLIES_15 if quick else PLIES_15
    seeds = QUICK_SEEDS_15 if quick else SEEDS_15
    iters = QUICK_ROOT_ITERS_15 if quick else ROOT_ITERS_15
    rows: list[dict[str, Any]] = []
    for c in C_15:
        for pid, n in enumerate(plies):
            moves, _ = make_position(GAME15, n)
            n_moves = len(build_game(GAME15, moves).candidate_moves())
            for seed in seeds:
                for it in iters:
                    agent, sec = search_root(GAME15, moves, it, seed, c)
                    base = {"board": "15x15", "kind": "search", "c": c, "pos_id": pid,
                            "plies": len(moves), "n_moves": n_moves,
                            "moves": ";".join(map(str, moves)), "iterations": it, "seed": seed,
                            "tactic": agent.stats.get("tactic", 0), "time": sec}  # fmt: skip
                    rows += root_rows(agent, base) if agent.root is not None else [base]
        print(f"[roots 15x15] c={c}: xong {len(plies)} thế")
    ref_iter = QUICK_REF_ITER_15 if quick else REF_ITER_15
    done: set[tuple[float, int]] = set()
    for c, pid, _, _ in example_searches_15(rows):
        if (c, pid) in done:
            continue
        done.add((c, pid))
        r0 = next(r for r in rows if r["pos_id"] == pid)
        moves = [int(x) for x in r0["moves"].split(";")]
        agent, sec = search_root(GAME15, moves, ref_iter, 0, c)
        base = {**{k: r0[k] for k in ("board", "pos_id", "plies", "n_moves", "moves")},
                "kind": "ref", "c": c, "iterations": ref_iter, "seed": 0,
                "tactic": agent.stats.get("tactic", 0), "time": sec}  # fmt: skip
        rows += root_rows(agent, base) if agent.root is not None else [base]
        print(f"[roots 15x15] tham chiếu c={c} thế {pid}: {ref_iter} iter, {sec:.1f} s")
    return rows


# ---------------------------------------------------------------- tổng hợp


def _b(v: Any) -> bool:
    return str(v) in ("1", "True")


def _has_tree(v: list[dict[str, Any]]) -> bool:
    return v[0].get("move") not in (None, "")


def group_searches(rows: list[dict[str, Any]]) -> dict[tuple, list[dict[str, Any]]]:
    """(board, c, pos_id, seed, iter) → các dòng con của một lần search (kind = search)."""
    out: dict[tuple, list[dict[str, Any]]] = {}
    for r in rows:
        if r.get("kind", "search") != "search":
            continue
        key = (r["board"], float(r["c"]), int(r["pos_id"]), int(r["seed"]), int(r["iterations"]))
        out.setdefault(key, []).append(r)
    return out


def _pick(children: list[dict[str, Any]], col: str) -> dict[str, Any]:
    return next(r for r in children if _b(r[col]))


def _rate(k: int, n: int) -> float:
    return k / n if n else math.nan


def _median(xs: list[float]) -> float:
    return statistics.median(xs) if xs else math.nan


def _summary_row(board: str, c: float, name: str, it: int, sel: list[list[dict[str, Any]]],
                 skipped: int) -> dict[str, Any]:  # fmt: skip
    picks = [(_pick(v, "is_max_n"), _pick(v, "is_max_wn"), _pick(v, "is_max_lcb")) for v in sel]
    differ = [p for p in picks if p[0]["move"] != p[1]["move"]]
    has_val = board == "3x3"

    def opt(ps: list, i: int) -> float:
        if not has_val:
            return math.nan
        return _rate(sum(_b(p[i]["optimal"]) for p in ps), len(ps))

    n_wn = [int(p[1]["N"]) for p in picks]
    # chẩn đoán (D-19): con max_n có W/N = 1? bao nhiêu con hòa (N, W) với nó?
    wn1 = [float(p[0]["W"]) == float(p[0]["N"]) for p in picks]
    tied = [sum((float(r["N"]), float(r["W"])) == (float(p[0]["N"]), float(p[0]["W"])) for r in v)
            for p, v in zip(picks, sel, strict=True)]  # fmt: skip
    return {
        "board": board, "c": c, "set": name, "iterations": it, "n_positions": len(sel),
        "n_skipped_tactic": skipped, "n_differ": len(differ),
        "differ_rate": _rate(len(differ), len(sel)),
        "opt_max_n": opt(picks, 0), "opt_max_wn": opt(picks, 1), "opt_max_lcb": opt(picks, 2),
        "differ_opt_max_n": opt(differ, 0), "differ_opt_max_wn": opt(differ, 1),
        "differ_opt_max_lcb": opt(differ, 2),
        "lcb_eq_max_n": _rate(sum(p[0]["move"] == p[2]["move"] for p in picks), len(picks)),
        "max_n_child_N_median": _median([int(p[0]["N"]) for p in picks]),
        "max_wn_child_N_median": _median(n_wn), "max_wn_child_N_max": max(n_wn, default=math.nan),
        "children_median": _median([len(v) for v in sel]),
        "max_n_wn_is_1": _rate(sum(wn1), len(wn1)), "max_n_tied_median": _median(tied),
    }  # fmt: skip


def summarize_roots(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Bảng tổng theo (board, c, tập, iter). 3×3: tập "all" (≥ 2 nước) và "has_bad" (có ≥ 1 nước
    không tối ưu). 15×15: tập "all" (bỏ thế tactic đi tắt, đếm ở `n_skipped_tactic`)."""
    groups = group_searches(rows)
    out = []
    keys = sorted({(k[0], k[1], k[4]) for k in groups}, key=lambda t: (t[0], -t[1], t[2]))
    for board, c, it in keys:
        gs = [v for k, v in groups.items() if (k[0], k[1], k[4]) == (board, c, it)]
        skipped = sum(1 for v in gs if not _has_tree(v))
        gs = [v for v in gs if _has_tree(v)]
        out.append(_summary_row(board, c, "all", it, gs, skipped))
        if board == "3x3":
            bad = [v for v in gs if any(not _b(r["optimal"]) for r in v)]
            out.append(_summary_row(board, c, "has_bad", it, bad, 0))
    return out


def example_positions_3x3(rows: list[dict[str, Any]], iterations: int = EXAMPLE_ITER_3,
                          n: int = N_EXAMPLES) -> list[tuple[str, int]]:  # fmt: skip
    """Luật D-19: thế (iter `iterations`) có max_n ≠ max_wn **và** max_wn không tối ưu; `n` thế đầu
    theo thứ tự chuẩn (pos_id) + 1 thế ít ô trống nhất (nhiều quân nhất; bằng → pos_id nhỏ)."""
    ok = []
    for (board, _, pid, _, it), v in sorted(group_searches(rows).items()):
        if board != "3x3" or it != iterations:
            continue
        a, b = _pick(v, "is_max_n"), _pick(v, "is_max_wn")
        if a["move"] != b["move"] and not _b(b["optimal"]):
            ok.append((int(v[0]["plies"]), pid))
    out = [("rule", pid) for _, pid in ok[:n]]
    if ok:
        most = max(ok, key=lambda t: (t[0], -t[1]))
        out.append(("trace", most[1]))
    return out


def example_searches_15(rows: list[dict[str, Any]],
                        n: int = N_EXAMPLES) -> list[tuple[float, int, int, int]]:  # fmt: skip
    """Luật D-19: với mỗi c, các search max_n ≠ max_wn theo thứ tự (pos_id, seed, iter), mỗi thế
    một lần; `n` search đầu. Trả [(c, pos_id, seed, iter)] (có thể rỗng)."""
    groups = group_searches(rows)
    out: list[tuple[float, int, int, int]] = []
    for c in sorted({k[1] for k in groups if k[0] == "15x15"}, reverse=True):
        found: list[tuple[float, int, int, int]] = []
        for (board, cc, pid, seed, it), v in sorted(groups.items()):
            if board != "15x15" or cc != c or not _has_tree(v) or any(f[1] == pid for f in found):
                continue
            if _pick(v, "is_max_n")["move"] != _pick(v, "is_max_wn")["move"]:
                found.append((c, pid, seed, it))
        out += found[:n]
    return out


def example_rows(rows3: list[dict[str, Any]],
                 rows15: list[dict[str, Any]]) -> list[dict[str, Any]]:  # fmt: skip
    """Bảng ví dụ: 3×3 mọi con; 15×15 top-K theo N + con max_wn/max_lcb, kèm W, N, W/N tham
    chiếu."""
    out = []
    g3 = group_searches(rows3)
    for tag, pid in example_positions_3x3(rows3):
        out += [{**r, "example": tag} for r in g3[("3x3", C, pid, SEED_3, EXAMPLE_ITER_3)]]
    g15 = group_searches(rows15)
    for c, pid, seed, it in example_searches_15(rows15):
        v = g15[("15x15", c, pid, seed, it)]
        top = sorted(v, key=lambda r: (-int(r["N"]), int(r["child_order"])))[:TOP_K_15]
        top += [r for r in v if (_b(r["is_max_wn"]) or _b(r["is_max_lcb"])) and r not in top]
        ref = {str(r["move"]): r for r in rows15 if r.get("kind") == "ref"
               and float(r["c"]) == c and int(r["pos_id"]) == pid
               and r.get("move") not in (None, "")}  # fmt: skip
        for r in top:
            x = ref.get(str(r["move"]))
            out.append({**r, "example": "rule" if c == C else "sensitivity",
                        "ref_iterations": x and x["iterations"], "ref_W": x and x["W"],
                        "ref_N": x and x["N"], "ref_wn": x and x["wn"]})  # fmt: skip
    return out


def run_roots(quick: bool) -> None:
    p = prefix(quick)
    t0 = time.perf_counter()
    rows3 = roots_3x3(quick)
    write_csv(rows3, ROOT_COLUMNS, RAW_DIR / f"{p}roots_3x3.csv")
    t3 = time.perf_counter() - t0
    print(f"[roots 3x3] {len({r['pos_id'] for r in rows3})} thế, {t3:.1f} s")
    rows15 = roots_15x15(quick)
    write_csv(rows15, ROOT_COLUMNS, RAW_DIR / f"{p}roots_15x15.csv")
    print(f"[roots 15x15] {time.perf_counter() - t0 - t3:.1f} s")
    rows3, rows15 = (read_rows(RAW_DIR / f"{p}roots_{b}.csv") for b in ("3x3", "15x15"))
    summ = summarize_roots(rows3 + rows15)
    write_csv(summ, SUMMARY_ROOT_COLUMNS, TABLE_DIR / f"{p}roots_summary.csv")
    ex = example_rows(rows3, rows15)
    write_csv(ex, EXAMPLE_COLUMNS, TABLE_DIR / f"{p}roots_examples.csv")
    for s in summ:
        print(f"[roots] {s['board']} c={s['c']} {s['set']} iter {s['iterations']}: "
              f"n={s['n_positions']} khác={s['n_differ']} tối ưu khi khác: "
              f"max_n={_fmt(s['differ_opt_max_n'])} max_wn={_fmt(s['differ_opt_max_wn'])}; "
              f"max_n có W/N=1: {s['max_n_wn_is_1']:.2f}")  # fmt: skip
    print(f"[roots] ví dụ: {len({(r['board'], r['c'], r['pos_id']) for r in ex})} thế")


# ---------------------------------------------------------------- đối đầu


def match_raw_path(board: str, iterations: int, quick: bool) -> Path:
    return RAW_DIR / f"{prefix(quick)}match_{board}_i{iterations}.csv"


def score_ci(rows: list[dict[str, str]], split: str, z: float = 1.96) -> tuple[float, float]:
    """Khoảng xấp xỉ chuẩn cho score trung bình của A (điểm/ván ∈ {0; 0,5; 1}):
    mean ± z·sd/√n (score không nhị thức → không dùng Wilson; D-19). Cắt vào [0, 1]."""
    sel = [r for r in rows if split == "all" or (split == "A=X") == (r["a_is_x"] == "1")]
    xs = [float(r["result_a"]) for r in sel]
    if len(xs) < 2:
        return math.nan, math.nan
    m, sd = statistics.fmean(xs), statistics.stdev(xs)
    h = z * sd / math.sqrt(len(xs))
    return max(0.0, m - h), min(1.0, m + h)


def run_matches(quick: bool, workers: int, allow: bool) -> list[dict[str, Any]]:
    table: list[dict[str, Any]] = []
    for board, (game, iters, pairs, qpairs) in MATCH.items():
        n = int(game.params["n"])
        for it in iters:
            t1 = time.perf_counter()
            raw = match_raw_path(board, it, quick)
            rows = run_match(raw, game, mcts_spec(n, it, "max_n"), mcts_spec(n, it, "max_wn"),
                             qpairs if quick else pairs, workers=workers,
                             allow_code_change=allow)  # fmt: skip
            summ = summarize(rows, read_rows(moves_path_for(raw)))
            for s in summ:
                s["score_lo"], s["score_hi"] = score_ci(rows, s["split"])
            table += [{"board": board, "iterations": it, **s} for s in summ]
            a = next(s for s in summ if s["split"] == "all")
            print(f"[match {board}] iter {it}: max_n W/D/L {a['wins']}/{a['draws']}/{a['losses']} "
                  f"score {a['score']:.3f} (n={a['n']}, distinct={a['distinct_games']}), "
                  f"{time.perf_counter() - t1:.1f} s")  # fmt: skip
    write_csv(table, MATCH_COLUMNS, TABLE_DIR / f"{prefix(quick)}match.csv")
    return table


# ---------------------------------------------------------------- ước tính từ quick


def estimate_full() -> list[dict[str, Any]]:
    """Fit giây = a + b·iter từ quick (mỗi search gốc / mỗi ván), ngoại suy cho full.
    Phần roots chạy tuần tự (1 tiến trình); đối đầu chia cho 3,5 (4 worker, như E3)."""
    out = []
    for board, n_searches, iters, ref in (
        ("3x3", len(enumerate_3x3()), ROOT_ITERS_3, None),
        ("15x15", len(PLIES_15) * len(SEEDS_15) * len(C_15), ROOT_ITERS_15, REF_ITER_15),
    ):
        seen = {}
        for r in read_rows(RAW_DIR / f"e4quick_roots_{board}.csv"):  # mỗi search một thời gian
            key = (r["kind"], r["c"], r["pos_id"], r["seed"], r["iterations"])
            seen[key] = (int(r["iterations"]), float(r["time"]))
        a, b = fit_cost(list(seen.values()))
        seq = sum(n_searches * (a + b * it) for it in iters)
        count = n_searches * len(iters)
        if ref:  # cận trên: mỗi c tối đa N_EXAMPLES thế tham chiếu
            seq += N_EXAMPLES * len(C_15) * (a + b * ref)
            count += N_EXAMPLES * len(C_15)
        out.append({"part": f"roots_{board}", "searches_or_games": count, "fit_a": round(a, 4),
                    "fit_b": round(b, 7), "seq_minutes": round(seq / 60, 1),
                    "est_minutes": round(seq / 60, 1)})  # fmt: skip
    for board, (_, iters, pairs, _) in MATCH.items():
        data = []
        for it in iters:
            f = match_raw_path(board, it, True)
            if f.exists():
                data += [(it, sum(float(r[k]) for k in ("a_time_sum", "b_time_sum") if r[k]))
                         for r in read_rows(f)]  # fmt: skip
        a, b = fit_cost(data)
        seq = sum(2 * pairs * (a + b * it) for it in iters)
        out.append({"part": f"match_{board}", "searches_or_games": 2 * pairs * len(iters),
                    "fit_a": round(a, 4), "fit_b": round(b, 7), "seq_minutes": round(seq / 60, 1),
                    "est_minutes": round(seq / 60 / SPEEDUP_4_WORKERS, 1)})  # fmt: skip
    write_csv(out, ESTIMATE_COLUMNS, TABLE_DIR / "e4quick_estimate.csv")
    for r in out:
        print(
            f"[estimate] {r['part']}: {r['searches_or_games']} search/ván, "
            f"~{r['seq_minutes']} phút tuần tự, ~{r['est_minutes']} phút thực"
        )
    return out


# ---------------------------------------------------------------- hình

INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"


def plot_match(table: list[dict[str, Any]], path: Path) -> Path:
    """3×3: score của max_n (chính, khoảng xấp xỉ chuẩn) + tỉ lệ thắng của max_n và của max_wn
    (Wilson 95 %) theo iter; trục x log."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rows = sorted((r for r in table if r["board"] == "3x3" and r["split"] == "all"),
                  key=lambda r: int(r["iterations"]))  # fmt: skip
    its = [int(r["iterations"]) for r in rows]
    fig, ax = plt.subplots(figsize=(6.6, 4.6), facecolor=SURFACE)

    def band(key: str) -> tuple[list[float], list[list[float]]]:
        ys, lo, hi = [], [], []
        for r in rows:
            if key == "score":
                p, lw, hw = float(r["score"]), float(r["score_lo"]), float(r["score_hi"])
            else:
                k, n = int(r[key]), int(r["n"])
                p = k / n
                lw, hw = wilson(k, n)
            ys.append(p)
            lo.append(max(0.0, p - lw))
            hi.append(max(0.0, hw - p))
        return ys, [lo, hi]

    series = (("score", "score của max_n", 0, "o"), ("wins", "max_n thắng", 1, "s"),
              ("losses", "max_wn thắng", 2, "^"))  # fmt: skip
    for j, (key, lab, ci, mk) in enumerate(series):
        ys, err = band(key)
        xs = [x * 10 ** (0.02 * (j - 1)) for x in its]
        ax.errorbar(xs, ys, yerr=err, color=SERIES_COLORS[ci], marker=mk, markersize=6,
                    linewidth=2.4 if key == "score" else 1.6, elinewidth=1.2, capsize=0,
                    markeredgecolor=SURFACE, markeredgewidth=1, label=lab)  # fmt: skip
    ax.axhline(0.5, color=INK2, linewidth=0.8, linestyle=(0, (3, 3)))
    ax.set_xscale("log")
    ax.set_xticks(its, [str(x) for x in its])
    ax.minorticks_off()
    ax.set_ylim(0.0, 1.03)
    ax.set_facecolor(SURFACE)
    ax.grid(True, axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(INK2)
    ax.tick_params(colors=INK2)
    ax.set_xlabel("iteration / nước (cả hai bên)", color=INK2)
    ax.set_ylabel("tỉ lệ / score", color=INK2)
    handles, labels = ax.get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper left", bbox_to_anchor=(0.005, 0.94),
               ncol=len(labels), frameon=False, labelcolor=INK, fontsize=9)  # fmt: skip
    fig.suptitle("E4 — 3×3, max N vs max W/N, cùng iteration, đổi lượt", color=INK, fontsize=12,
                 x=0.01, y=0.99, ha="left")  # fmt: skip
    fig.text(0.01, 0.005, "Score: mean ± 1,96·sd/√n (xấp xỉ). Thắng: Wilson 95 %. "
             "Phần còn lại là hòa.", color=INK2, fontsize=8, ha="left", va="bottom")  # fmt: skip
    fig.tight_layout(rect=(0, 0.03, 1, 0.88))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150, facecolor=SURFACE)
    plt.close(fig)
    return path


def make_figures(quick: bool) -> None:
    f = TABLE_DIR / f"{prefix(quick)}match.csv"
    if f.exists():
        print(f"[plot] {plot_match(read_rows(f), FIG_DIR / f'{prefix(quick)}match.png')}")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("step", choices=("roots", "match", "plot", "all"))
    add_runner_args(ap)
    args = ap.parse_args()
    t0 = time.perf_counter()
    if args.step in ("roots", "all"):
        run_roots(args.quick)
    if args.step in ("match", "all"):
        run_matches(args.quick, args.workers, args.allow_code_change)
    make_figures(args.quick)
    if args.quick and args.step == "all":
        estimate_full()
    print(f"tổng {time.perf_counter() - t0:.1f} s")


if __name__ == "__main__":
    main()
