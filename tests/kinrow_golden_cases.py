"""Golden hồi quy k-in-row (P8.0): chụp chuỗi nước + stats từ code ở tag `kinrow-final`.

Mọi ván dùng ngân sách iteration / depth (tất định theo seed). Sinh lại file golden:
    python tests/kinrow_golden_cases.py
Chỉ sinh lại khi **cố ý** đổi hành vi mặc định (ghi lý do vào DECISIONS.md).
Test: `tests/test_regression_kinrow.py`.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

if __name__ == "__main__":  # chạy như script: thêm gốc repo vào sys.path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gameai.agents.registry import AgentSpec, GameSpec, make_game
from gameai.arena import MatchGame, play_seeded_game

GOLDEN_PATH = Path(__file__).with_name("golden") / "kinrow_golden.json"

G3 = GameSpec("kinrow", {"n": 3, "k": 3})
G15 = GameSpec("kinrow", {"n": 15, "k": 5})
_KINROW_FNS = {"eval": "evaluate", "delta": "delta_eval", "order": "move_score"}

# (tên, game, spec A, spec B, pair_seeds, max_moves, random_opening)
CASES: list[tuple[str, GameSpec, AgentSpec, AgentSpec, tuple[int, ...], int | None, int]] = [
    (
        "3x3_ab_order_tt_vs_mcts1000",
        G3,
        AgentSpec("alphabeta", {"order": "move_score", "use_tt": True}, label="ab_ot"),
        AgentSpec("mcts", {"iterations": 1000}, label="mcts1000"),
        (0, 1),
        None,
        0,
    ),
    (
        "3x3_ab_plain_vs_random",
        G3,
        AgentSpec("alphabeta", {}, label="ab"),
        AgentSpec("random", label="random"),
        (0,),
        None,
        0,
    ),
    (
        "15x15_ab2_vs_h300_tactics",
        G15,
        AgentSpec("alphabeta", {"depth": 2, **_KINROW_FNS}, label="ab2"),
        AgentSpec(
            "mcts",
            {
                "iterations": 300,
                "c": 1.4,
                "check_tactics": True,
                "rollout": "heavy_kinrow",
                "temperature": 300,
            },
            label="h300_i300",
        ),  # fmt: skip
        (0,),
        30,
        0,
    ),
    (
        "15x15_mcts_rand_cut_vs_greedy",
        G15,
        AgentSpec(
            "mcts",
            {
                "iterations": 200,
                "c": 1.4,
                "check_tactics": True,
                "rollout": "random",
                "rollout_limit": 10,
                "value_scale": 500,
            },
            label="rand_cut",
        ),  # fmt: skip
        AgentSpec("greedy", label="greedy"),
        (0,),
        24,
        0,
    ),
    (
        "15x15_ab2_tt_vs_greedy_opening",
        G15,
        AgentSpec("alphabeta", {"depth": 2, "use_tt": True, **_KINROW_FNS}, label="ab2_tt"),
        AgentSpec("greedy", label="greedy"),
        (3,),
        24,
        4,
    ),
]


def _key_digest(key: Any) -> str:
    return hashlib.sha1(repr(key).encode()).hexdigest()[:16]


def _record(case: str, gs: GameSpec, mg: MatchGame) -> dict[str, Any]:
    rec = mg.record
    game = make_game(gs)
    for m in rec.opening:
        game.play(m)
    keys = []
    for mr in rec.moves:
        game.play(mr.move)
        keys.append(_key_digest(game.key()))
    return {
        "case": case,
        "game_id": mg.game_id,
        "winner": rec.winner,
        "termination": rec.termination,
        "opening": list(rec.opening),
        "moves": [mr.move for mr in rec.moves],
        "keys": keys,
        "stats": [{k: v for k, v in sorted(mr.stats.items()) if k != "time"} for mr in rec.moves],
    }


def run_cases() -> list[dict[str, Any]]:
    out = []
    for case, gs, a, b, seeds, max_moves, opening in CASES:
        for s in seeds:
            for a_is_x in (True, False):
                mg = play_seeded_game(gs, a, b, s, a_is_x, max_moves, opening)
                out.append(_record(case, gs, mg))
    return out


def normalize(records: list[dict[str, Any]]) -> list[str]:
    """Một chuỗi JSON/ván (NaN → "NaN" ở cả hai phía nên so sánh chuỗi được)."""
    return [json.dumps(r, sort_keys=True, default=str) for r in records]


if __name__ == "__main__":
    recs = run_cases()
    GOLDEN_PATH.parent.mkdir(exist_ok=True)
    GOLDEN_PATH.write_text(json.dumps(recs, indent=1, default=str), encoding="utf-8")
    n_moves = sum(len(r["moves"]) for r in recs)
    print(f"{len(recs)} games, {n_moves} moves -> {GOLDEN_PATH}")
