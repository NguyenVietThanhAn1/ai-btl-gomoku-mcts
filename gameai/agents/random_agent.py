"""RandomAgent: chọn đều ngẫu nhiên trong các nước hợp lệ (đối thủ cơ sở)."""

from __future__ import annotations

import random

from gameai.agents.base import Agent
from gameai.core.game import Game, Move


class RandomAgent(Agent):
    def __init__(self, seed: int | None = None, use_candidates: bool = False) -> None:
        super().__init__()
        self.rng = random.Random(seed)
        self.use_candidates = use_candidates

    def select_move(self, game: Game) -> Move:
        assert not game.is_terminal(), "select_move gọi trên ván đã kết thúc"
        self.reset_stats()
        moves = game.candidate_moves() if self.use_candidates else game.legal_moves()
        self.stats["nodes"] = 0
        self.stats["iterations"] = 0
        return self.rng.choice(moves)
