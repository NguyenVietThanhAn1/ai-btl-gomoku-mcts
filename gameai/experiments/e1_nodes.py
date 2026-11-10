"""E1: Alpha-Beta tiết kiệm bao nhiêu nút so với Minimax? (đề ý 1)

3×3 (tìm tới kết thúc): bàn trống + 5 thế giữa ván; Minimax / AB / AB+ordering / AB+ordering+TT;
    kiểm giá trị gốc VÀ nước đi giống Minimax.
15×15 (k=5): 5 thế cố định; AB depth 2, 3, có / không ordering; Minimax thuần chỉ depth 2
    (nếu đủ nhanh); thêm `ab_evalonly` (AB không delta, không ordering) ở depth 2 để tách tác dụng
    của cắt tỉa khỏi tác dụng của delta_eval khi so thời gian với Minimax.

    python -m gameai.experiments.e1_nodes --quick
    python -m gameai.experiments.e1_nodes
"""

from __future__ import annotations

import argparse
import csv
import random
import statistics
import sys
import time
from pathlib import Path

from gameai.agents.alphabeta import AlphaBetaAgent
from gameai.agents.minimax import MinimaxAgent
from gameai.agents.registry import AgentSpec, GameSpec, make_agent, make_game
from gameai.core.game import Game

ROOT = Path(__file__).resolve().parents[2]
TABLE_DIR = ROOT / "results" / "tables"

G3 = GameSpec("kinrow", {"n": 3, "k": 3})
G15 = GameSpec("kinrow", {"n": 15, "k": 5})

PLIES_3 = (2, 3, 4, 5, 6)  # + bàn trống (0 nước)
PLIES_15 = (6, 10, 14, 18, 22)
POS_SEED_START = 0  # mỗi thế: seed nhỏ nhất ≥ 0 cho chuỗi playout ngẫu nhiên không kết thúc sớm
REPEATS = 3  # thời gian = trung vị; nodes tất định (kiểm)
QUICK_POSITIONS = 2
SLOW_SECONDS = 5.0  # lần đo đầu lâu hơn → chỉ đo 1 lần
MINIMAX_SKIP_SECONDS = 60.0  # Minimax 15×15 một thế lâu hơn mức này → bỏ các thế còn lại

DELTA = {"eval": "evaluate", "delta": "delta_eval"}
VARIANTS_3 = {
    "minimax": AgentSpec("minimax", {"depth": None, "seeded": False}, label="minimax"),
    "ab": AgentSpec("alphabeta", {"depth": None, "seeded": False}, label="ab"),
    "ab_order": AgentSpec(
        "alphabeta", {"depth": None, "order": "move_score", "seeded": False}, label="ab_order"
    ),
    "ab_order_tt": AgentSpec(
        "alphabeta",
        {"depth": None, "order": "move_score", "use_tt": True, "seeded": False},
        label="ab_order_tt",
    ),
}


def variants_15(depth: int) -> dict[str, AgentSpec]:
    v: dict[str, AgentSpec] = {}
    if depth == 2:
        v["minimax"] = AgentSpec(
            "minimax", {"depth": 2, "eval": "evaluate", "seeded": False}, label="minimax"
        )
        v["ab_evalonly"] = AgentSpec(
            "alphabeta", {"depth": 2, "eval": "evaluate", "seeded": False}, label="ab_evalonly"
        )
    v["ab"] = AgentSpec("alphabeta", {"depth": depth, **DELTA, "seeded": False}, label="ab")
    v["ab_order"] = AgentSpec(
        "alphabeta",
        {"depth": depth, **DELTA, "order": "move_score", "seeded": False},
        label="ab_order",
    )
    return v


NODE_COLUMNS = [
    "board", "pos_id", "plies", "depth", "variant", "nodes", "time", "repeats", "cutoffs",
    "tt_hits", "value", "move", "value_same_as_minimax", "move_same_as_minimax",
    "move_optimal", "nodes_saving_vs_minimax_pct", "time_saving_vs_minimax_pct",
    "value_same_as_ab", "move_same_as_ab", "nodes_saving_vs_ab_pct", "time_saving_vs_ab_pct",
    "note",
]  # fmt: skip
POS_COLUMNS = ["board", "pos_id", "plies", "seed", "side_to_move", "moves"]
SUMMARY_COLUMNS = [
    "board", "depth", "variant", "n_positions", "nodes_sum", "time_sum",
    "nodes_saving_vs_minimax_pooled_pct", "nodes_saving_vs_minimax_mean_pct",
    "time_saving_vs_minimax_pooled_pct", "nodes_saving_vs_ab_pooled_pct",
    "nodes_saving_vs_ab_mean_pct", "time_saving_vs_ab_pooled_pct",
    "values_same_as_minimax", "moves_same_as_minimax", "moves_optimal",
    "values_same_as_ab", "moves_same_as_ab", "n_compared_minimax",
]  # fmt: skip


# ---------------------------------------------------------------- thế cờ cố định


def make_position(game_spec: GameSpec, plies: int) -> tuple[list[int], int]:
    """Playout ngẫu nhiên trên `candidate_moves` (tất định theo seed). Seed nhỏ nhất ≥
    `POS_SEED_START` mà ván chưa kết thúc sau `plies` nước. Trả (chuỗi nước, seed)."""
    seed = POS_SEED_START
    while True:
        rng = random.Random(seed)
        g = make_game(game_spec)
        moves: list[int] = []
        for _ in range(plies):
            m = rng.choice(g.candidate_moves())
            g.play(m)
            moves.append(m)
            if g.is_terminal():
                break
        if not g.is_terminal():
            return moves, seed
        seed += 1


def build_game(game_spec: GameSpec, moves: list[int]) -> Game:
    g = make_game(game_spec)
    for m in moves:
        g.play(m)
    return g


# ---------------------------------------------------------------- đo


def measure(
    spec: AgentSpec, game: Game, repeats: int
) -> tuple[dict[str, object], float, list[tuple[int, float]] | None]:
    """Chạy `repeats` lần (agent dựng mới mỗi lần). nodes phải giống nhau mọi lần (tất định).
    Trả (kết quả, trung vị thời gian, root_values nếu là Minimax).
    Lần đầu > SLOW_SECONDS → chỉ 1 lần."""
    times: list[float] = []
    out: dict[str, object] = {}
    root_vals = None
    r = 0
    while r < repeats:
        agent = make_agent(spec, None)
        key0 = game.key()
        if isinstance(agent, MinimaxAgent):
            root_vals = agent.root_values(game)
            best = max(v for _, v in root_vals)
            move = next(m for m, v in root_vals if v == best)  # đầu tiên, như _select_move
            value = best
        else:
            assert isinstance(agent, AlphaBetaAgent)
            move, value = agent.search(game)
        assert game.key() == key0  # agent không làm đổi ván
        res = {
            "nodes": int(agent.stats["nodes"]),
            "cutoffs": agent.stats.get("cutoffs"),
            "tt_hits": agent.stats.get("tt_hits"),
            "value": value,
            "move": move,
        }
        if r > 0:
            assert res["nodes"] == out["nodes"], "nodes không tất định giữa các lần chạy"
            assert res["value"] == out["value"] and res["move"] == out["move"]
        out = res
        times.append(float(agent.stats["time"]))
        r += 1
        if r == 1 and times[0] > SLOW_SECONDS:
            repeats = 1
    return out, statistics.median(times), root_vals


def _saving(x: float, ref: float) -> float | str:
    return round(100.0 * (1.0 - x / ref), 2) if ref else ""


def run_position(
    board: str,
    pos_id: str,
    game_spec: GameSpec,
    moves: list[int],
    depth: int | None,
    variants: dict[str, AgentSpec],
    repeats: int,
    skip_minimax: bool = False,
) -> list[dict[str, object]]:
    """Mọi biến thể trên một thế; so với Minimax (nếu có) và với `ab` (không ordering/TT)."""
    game = build_game(game_spec, moves)
    res: dict[str, dict[str, object]] = {}
    times: dict[str, float] = {}
    minimax_vals: list[tuple[int, float]] | None = None
    for name, spec in variants.items():
        if name == "minimax" and skip_minimax:
            continue
        r, t, rv = measure(spec, game, repeats)
        res[name], times[name] = r, t
        if name == "minimax":
            minimax_vals = rv
    mm, ab = res.get("minimax"), res["ab"]
    rows = []
    for name, r in res.items():
        row: dict[str, object] = {
            "board": board, "pos_id": pos_id, "plies": len(moves),
            "depth": depth if depth is not None else "full", "variant": name,
            "nodes": r["nodes"], "time": round(times[name], 6), "repeats": repeats,
            "cutoffs": r["cutoffs"] if r["cutoffs"] is not None else "",
            "tt_hits": r["tt_hits"] if r["tt_hits"] is not None else "",
            "value": r["value"], "move": r["move"], "note": "",
        }  # fmt: skip
        if mm is not None:
            row["value_same_as_minimax"] = int(r["value"] == mm["value"])
            row["move_same_as_minimax"] = int(r["move"] == mm["move"])
            if minimax_vals is not None:  # nước đi có giá trị = giá trị gốc (tối ưu) không?
                mv = dict(minimax_vals)
                row["move_optimal"] = int(mv[r["move"]] == mm["value"])
            if name != "minimax":
                row["nodes_saving_vs_minimax_pct"] = _saving(r["nodes"], mm["nodes"])
                row["time_saving_vs_minimax_pct"] = _saving(times[name], times["minimax"])
        if name not in ("minimax", "ab", "ab_evalonly"):
            row["value_same_as_ab"] = int(r["value"] == ab["value"])
            row["move_same_as_ab"] = int(r["move"] == ab["move"])
            row["nodes_saving_vs_ab_pct"] = _saving(r["nodes"], ab["nodes"])
            row["time_saving_vs_ab_pct"] = _saving(times[name], times["ab"])
        rows.append(row)
    return rows


# ---------------------------------------------------------------- tổng hợp


def summarize(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    """Một dòng / (board, depth, variant). Pooled = 1 − Σx/Σref trên các thế có tham chiếu
    (thế bị bỏ Minimax không tính vào phía Minimax)."""
    by_key: dict[tuple, list[dict[str, object]]] = {}
    for r in rows:
        by_key.setdefault((r["board"], r["depth"], r["variant"]), []).append(r)
    # tra nodes/time theo (board, pos, depth, variant)
    idx = {(r["board"], r["pos_id"], r["depth"], r["variant"]): r for r in rows}
    out = []
    for (board, depth, variant), rs in by_key.items():

        def pooled(ref_variant: str, field: str, rs=rs, board=board, depth=depth) -> float | str:
            num = den = 0.0
            for r in rs:
                ref = idx.get((board, r["pos_id"], depth, ref_variant))
                if ref is None:
                    continue
                num += float(r[field])
                den += float(ref[field])
            return _saving(num, den) if den else ""

        def mean(col: str, rs=rs) -> float | str:
            vals = [float(r[col]) for r in rs if r.get(col, "") != ""]
            return round(statistics.mean(vals), 2) if vals else ""

        def count(col: str, rs=rs) -> str:
            vals = [int(r[col]) for r in rs if r.get(col, "") != ""]
            return f"{sum(vals)}/{len(vals)}" if vals else ""

        n_mm = sum(1 for r in rs if r.get("value_same_as_minimax", "") != "")
        s = {
            "board": board, "depth": depth, "variant": variant, "n_positions": len(rs),
            "nodes_sum": sum(int(r["nodes"]) for r in rs),
            "time_sum": round(sum(float(r["time"]) for r in rs), 4),
            "nodes_saving_vs_minimax_pooled_pct": (
                pooled("minimax", "nodes") if variant != "minimax" else ""
            ),
            "nodes_saving_vs_minimax_mean_pct": mean("nodes_saving_vs_minimax_pct"),
            "time_saving_vs_minimax_pooled_pct": (
                pooled("minimax", "time") if variant != "minimax" else ""
            ),
            "nodes_saving_vs_ab_pooled_pct": (
                pooled("ab", "nodes") if variant not in ("minimax", "ab", "ab_evalonly") else ""
            ),
            "nodes_saving_vs_ab_mean_pct": mean("nodes_saving_vs_ab_pct"),
            "time_saving_vs_ab_pooled_pct": (
                pooled("ab", "time") if variant not in ("minimax", "ab", "ab_evalonly") else ""
            ),
            "values_same_as_minimax": count("value_same_as_minimax"),
            "moves_same_as_minimax": count("move_same_as_minimax"),
            "moves_optimal": count("move_optimal"),
            "values_same_as_ab": count("value_same_as_ab"),
            "moves_same_as_ab": count("move_same_as_ab"),
            "n_compared_minimax": n_mm,
        }  # fmt: skip
        out.append(s)
    return out


# ---------------------------------------------------------------- chạy


def _write(path: Path, columns: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def run(quick: bool) -> list[dict[str, object]]:
    repeats = 1 if quick else REPEATS
    n_pos = QUICK_POSITIONS if quick else None
    prefix = "e1quick_" if quick else "e1_"
    t_all = time.perf_counter()
    rows: list[dict[str, object]] = []
    positions: list[dict[str, object]] = []

    def add_positions(board: str, spec: GameSpec, plies_list: tuple[int, ...]) -> list:
        out = []
        for i, plies in enumerate(plies_list[:n_pos]):
            moves, seed = make_position(spec, plies)
            pid = f"{board}-p{i}"
            positions.append({"board": board, "pos_id": pid, "plies": plies, "seed": seed,
                              "side_to_move": "X" if plies % 2 == 0 else "O",
                              "moves": ";".join(map(str, moves))})  # fmt: skip
            out.append((pid, moves))
        return out

    # --- 3×3
    t0 = time.perf_counter()
    pos3 = [("3x3-empty", [])]
    positions.append({"board": "3x3", "pos_id": "3x3-empty", "plies": 0, "seed": "",
                      "side_to_move": "X", "moves": ""})  # fmt: skip
    pos3 += add_positions("3x3", G3, PLIES_3)
    for pid, moves in pos3:
        rows += run_position("3x3", pid, G3, moves, None, VARIANTS_3, repeats)
    print(f"[3x3] {len(pos3)} thế, {time.perf_counter() - t0:.1f} s")

    # --- 15×15
    pos15 = add_positions("15x15", G15, PLIES_15)
    skip_mm = False
    for depth in (2, 3):
        t0 = time.perf_counter()
        for pid, moves in pos15:
            before = len(rows)
            rows += run_position("15x15", pid, G15, moves, depth, variants_15(depth), repeats,
                                 skip_minimax=skip_mm)  # fmt: skip
            mm = [r for r in rows[before:] if r["variant"] == "minimax"]
            if mm and float(mm[0]["time"]) > MINIMAX_SKIP_SECONDS and not skip_mm:
                skip_mm = True
                print(f"[15x15] Minimax depth {depth} {float(mm[0]['time']):.1f} s/thế "
                      f"> {MINIMAX_SKIP_SECONDS:.0f} s → bỏ Minimax ở các thế còn lại")  # fmt: skip
        print(f"[15x15] depth {depth}: {time.perf_counter() - t0:.1f} s")

    summary = summarize(rows)
    _write(TABLE_DIR / f"{prefix}nodes.csv", NODE_COLUMNS, rows)
    _write(TABLE_DIR / f"{prefix}positions.csv", POS_COLUMNS, positions)
    _write(TABLE_DIR / f"{prefix}summary.csv", SUMMARY_COLUMNS, summary)
    print(f"tổng {time.perf_counter() - t_all:.1f} s")
    for s in summary:
        print(f"  {s['board']:>5} d={s['depth']!s:>4} {s['variant']:<12} nodes={s['nodes_sum']:>9} "
              f"time={s['time_sum']:>8}s  tiết kiệm nút vs minimax/ab = "
              f"{s['nodes_saving_vs_minimax_pooled_pct']}/{s['nodes_saving_vs_ab_pooled_pct']} %  "
              f"giá trị=mm {s['values_same_as_minimax']} nước=mm {s['moves_same_as_minimax']} "
              f"tối ưu {s['moves_optimal']}")  # fmt: skip
    return rows


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]  # console cp1252
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--quick", action="store_true", help="2 thế mỗi bàn, 1 lần đo (e1quick_*)")
    args = ap.parse_args()
    run(args.quick)


if __name__ == "__main__":
    main()
