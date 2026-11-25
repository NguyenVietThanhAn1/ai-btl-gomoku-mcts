"""P8.2: đo nhanh AB cờ tướng (nút/s, ordering, `depth_reached` theo `time_limit`) + trận thử.

Chạy: `python -m gameai.experiments.p82_ab_check [--out results/tables/p82_ab_speed.csv]
[--skip-match]`
Số đo trên **một máy**, minh họa cỡ độ lớn — không phải số liệu thí nghiệm (E7 ở P8.4).
Trận thử (`run_match`): khai cuộc ngẫu nhiên có seed 2–4 nước, mỗi khai cuộc 2 ván đổi bên (như B5).
"""

from __future__ import annotations

import argparse
import csv
import random
import sys
import time
from pathlib import Path
from typing import Any

from gameai.agents.registry import AgentSpec, GameSpec, make_agent, make_game
from gameai.arena import derive_seed, play_game, random_opening_moves
from gameai.core.game import P1, P2, Move, result_for
from gameai.games.xiangqi import START_FEN, Xiangqi

OPENING_LEN = (2, 4)
FIELDS = ["metric", "config", "value", "unit", "n_samples", "note"]


def ab_spec(
    depth: int,
    order: str | None = "xq_mvv_lva",
    use_tt: bool = False,
    time_limit: float | None = None,
    label: str | None = None,
) -> AgentSpec:
    """AB cờ tướng tất định (`seeded: false`), eval + delta; TT "exact", không `top_k` (D-23)."""
    params: dict[str, Any] = {
        "depth": depth,
        "eval": "xq_evaluate",
        "delta": "xq_delta",
        "order": order,
        "use_tt": use_tt,
        "seeded": False,
    }
    if time_limit is not None:
        params["time_limit"] = time_limit
    return AgentSpec("alphabeta", params, label=label)


RANDOM = AgentSpec("random", label="random")
GREEDY = AgentSpec("greedy", {"score": "xq_delta"}, label="greedy_xq")


# ---------------------------------------------------------------- thế thử
def midgame_fens(n: int, seed: int = 0, plies: tuple[int, int] = (14, 36)) -> list[str]:
    """`n` FEN giữa ván: đi nước ngẫu nhiên có seed từ thế đầu, ván chưa kết thúc."""
    rng = random.Random(seed)
    out: list[str] = []
    while len(out) < n:
        g = Xiangqi()
        for _ in range(rng.randint(*plies)):
            if g.is_terminal():
                break
            g.play(rng.choice(g.legal_moves()))
        if not g.is_terminal():
            out.append(g.to_fen())
    return out


# ---------------------------------------------------------------- đo tốc độ
def measure_ordering(fens: list[str], depth: int) -> list[dict[str, Any]]:
    """Cùng `fens`, độ sâu cố định: nút / thời gian theo ordering; kiểm giá trị gốc giống nhau."""
    configs = {
        "none": ab_spec(depth, order=None),
        "mvv_lva": ab_spec(depth),
        "mvv_lva+tt": ab_spec(depth, use_tt=True),
        "mvv_lva_check": ab_spec(depth, order="xq_mvv_lva_check"),
    }
    rows: list[dict[str, Any]] = []
    ref: list[float] | None = None
    for name, spec in configs.items():
        nodes, secs, values = 0, 0.0, []
        for fen in fens:
            agent = make_agent(spec, None)
            _, v = agent.search(Xiangqi(fen))
            nodes += agent.stats["nodes"]
            secs += agent.stats["time"]
            values.append(v)
        same = ref is None or values == ref
        ref = values if ref is None else ref
        note = (
            f"depth {depth}, {len(fens)} thế (đầu + giữa ván); "
            f"giá trị gốc {'giống' if same else 'KHÁC'} 'none'"
        )
        rows.append(
            {
                "metric": "ab_nodes",
                "config": name,
                "value": nodes,
                "unit": "nodes",
                "n_samples": len(fens),
                "note": note,
            }
        )
        rows.append(
            {
                "metric": "ab_seconds",
                "config": name,
                "value": round(secs, 3),
                "unit": "s",
                "n_samples": len(fens),
                "note": note,
            }
        )
        rows.append(
            {
                "metric": "ab_nodes_per_sec",
                "config": name,
                "value": round(nodes / secs),
                "unit": "nodes/s",
                "n_samples": len(fens),
                "note": note,
            }
        )
    return rows


def measure_time_limits(
    fens: list[str], limits: tuple[float, ...], max_depth: int = 8
) -> list[dict[str, Any]]:
    """`depth_reached` (iterative deepening, TT exact) theo `time_limit`, trên `fens`."""
    rows: list[dict[str, Any]] = []
    for tl in limits:
        reached, used, nodes = [], [], []
        for fen in fens:
            agent = make_agent(ab_spec(max_depth, use_tt=True, time_limit=tl), None)
            agent.select_move(Xiangqi(fen))
            reached.append(agent.stats["depth_reached"])
            used.append(agent.stats["time"])
            nodes.append(agent.stats["nodes"])
        n = len(fens)
        note = (
            f"{n} thế, depth tối đa {max_depth}, TT exact; "
            f"depth_reached min–max {min(reached)}–{max(reached)}"
        )
        cfg = f"time_limit={tl}"
        rows += [
            {
                "metric": "depth_reached_mean",
                "config": cfg,
                "value": round(sum(reached) / n, 2),
                "unit": "ply",
                "n_samples": n,
                "note": note,
            },
            {
                "metric": "time_used_max",
                "config": cfg,
                "value": round(max(used), 3),
                "unit": "s",
                "n_samples": n,
                "note": "quá hạn = time_used_max − time_limit",
            },
            {
                "metric": "nodes_mean",
                "config": cfg,
                "value": round(sum(nodes) / n),
                "unit": "nodes",
                "n_samples": n,
                "note": note,
            },
        ]
    return rows


# ---------------------------------------------------------------- trận thử
def make_openings(n_pairs: int, base_seed: int = 0, spec: GameSpec | None = None):
    """[(pair_seed, khai cuộc)] — 2–4 nước ngẫu nhiên theo seed, các khai cuộc đôi một khác nhau."""
    spec = spec or GameSpec("xiangqi")
    taken: set[tuple[Move, ...]] = set()
    out = []
    for i in range(n_pairs):
        pair_seed = base_seed + i
        for attempt in range(200):
            rng = random.Random(derive_seed(pair_seed, f"p82-opening-{attempt}"))
            op = tuple(random_opening_moves(make_game(spec), rng.randint(*OPENING_LEN), rng))
            if op not in taken:
                taken.add(op)
                out.append((pair_seed, op))
                break
        else:
            raise RuntimeError(f"không dựng được khai cuộc cho seed {pair_seed}")
    return out


def play_one(
    spec: GameSpec, spec_a: AgentSpec, spec_b: AgentSpec, pair_seed: int, opening, a_is_red: bool
) -> dict[str, Any]:
    """Một ván A vs B từ `opening`; A cầm Đỏ nếu `a_is_red`. Agent mới, seed suy từ `pair_seed`."""
    game = make_game(spec)
    for m in opening:
        game.play(m)
    agent_a = make_agent(spec_a, derive_seed(pair_seed, "A"))
    agent_b = make_agent(spec_b, derive_seed(pair_seed, "B"))
    red, black = (agent_a, agent_b) if a_is_red else (agent_b, agent_a)
    t0 = time.perf_counter()
    rec = play_game(game, red, black, opening=tuple(opening))
    a_player = P1 if a_is_red else P2
    return {
        "pair_seed": pair_seed,
        "a_is_red": a_is_red,
        "result_a": result_for(rec.winner, a_player),
        "winner": rec.winner,
        "termination": rec.termination,
        "n_moves": rec.n_moves,
        "ply": game.ply,
        "seconds": time.perf_counter() - t0,
        "seq": (tuple(opening), tuple(m.move for m in rec.moves)),
    }


def run_match(
    spec_a: AgentSpec, spec_b: AgentSpec, n_pairs: int, base_seed: int = 0, max_plies: int = 200
) -> dict[str, Any]:
    """`2 × n_pairs` ván (mỗi khai cuộc 2 ván đổi bên), tuần tự. W/D/L theo góc nhìn A."""
    spec = GameSpec("xiangqi", {"max_plies": max_plies})
    openings = make_openings(n_pairs, base_seed, spec)
    games = [
        play_one(spec, spec_a, spec_b, ps, op, a_is_red)
        for ps, op in openings
        for a_is_red in (True, False)
    ]
    w = sum(g["result_a"] == 1.0 for g in games)
    d = sum(g["result_a"] == 0.5 for g in games)
    losses = sum(g["result_a"] == 0.0 for g in games)
    seqs = [g["seq"] for g in games]
    return {
        "games": games,
        "W": w,
        "D": d,
        "L": losses,
        "score": (w + 0.5 * d) / len(games),
        "distinct_openings": len({op for _, op in openings}),
        "duplicate_games": len(seqs) - len(set(seqs)),
        "seconds": sum(g["seconds"] for g in games),
        "errors": sum(g["termination"] != "normal" for g in games),
    }


# ---------------------------------------------------------------- main
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=Path("results/tables/p82_ab_speed.csv"))
    ap.add_argument("--skip-match", action="store_true", help="chỉ đo tốc độ, không chạy trận thử")
    ap.add_argument("--pairs", type=int, default=5)
    ap.add_argument("--max-plies", type=int, default=200)
    ap.add_argument("--base-seed", type=int, default=0)
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    fens = [START_FEN] + midgame_fens(8, seed=82)
    rows = measure_ordering(fens, depth=3) + measure_time_limits(fens, (0.5, 1.0, 2.0))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    for r in rows:
        print(f"{r['metric']:<20} {r['config']:<18} {r['value']:>10} {r['unit']:<8} {r['note']}")
    print(f"-> {args.out}")

    if not args.skip_match:
        for name, opp in (("random", RANDOM), ("greedy_xq", GREEDY)):
            res = run_match(ab_spec(2), opp, args.pairs, args.base_seed, args.max_plies)
            print(
                f"ab2 vs {name}: W/D/L = {res['W']}/{res['D']}/{res['L']} "
                f"(score {res['score']:.2f}), {res['distinct_openings']} khai cuộc phân biệt, "
                f"ván trùng chuỗi nước {res['duplicate_games']}, lỗi {res['errors']}, "
                f"{res['seconds']:.0f} s"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
