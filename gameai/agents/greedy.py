"""GreedyAgent: tìm 1 nước (1-ply) theo hàm điểm heuristic, tie-break ngẫu nhiên có seed."""

from __future__ import annotations

import random
import time

from gameai.agents.alphabeta import MoveFn
from gameai.agents.base import Agent
from gameai.core.game import Game, Move


class GreedyAgent(Agent):
    """Chọn nước có `score_fn(game, move)` lớn nhất; nhiều nước bằng điểm → chọn ngẫu nhiên.

    K-in-row: `score_fn = kinrow_eval.move_score` (thắng ngay > chặn thua ngay > delta).
    """

    def __init__(
        self, score_fn: MoveFn, seed: int | None = None, use_candidates: bool = True
    ) -> None:
        super().__init__()
        self.score_fn = score_fn
        self.rng = random.Random(seed)
        self.use_candidates = use_candidates

    def _select_move(self, game: Game) -> Move:
        assert not game.is_terminal(), "select_move gọi trên ván đã kết thúc"
        t0 = time.perf_counter()
        moves = game.candidate_moves() if self.use_candidates else game.legal_moves()
        score_fn = self.score_fn
        best = float("-inf")
        best_moves: list[Move] = []
        for move in moves:
            s = score_fn(game, move)
            if s > best:
                best, best_moves = s, [move]
            elif s == best:
                best_moves.append(move)
        self.stats["nodes"] = len(moves)
        self.stats["iterations"] = 0
        self.stats["time"] = time.perf_counter() - t0
        self.stats["value"] = best
        return best_moves[0] if len(best_moves) == 1 else self.rng.choice(best_moves)
