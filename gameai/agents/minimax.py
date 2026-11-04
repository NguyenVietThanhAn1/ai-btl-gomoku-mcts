"""MinimaxAgent: minimax thuần (không cắt tỉa), giới hạn độ sâu tùy chọn, đếm số nút."""

from __future__ import annotations

import random
import time
from collections.abc import Callable

from gameai.agents.base import Agent
from gameai.core.game import DRAW, Game, Move

EvalFn = Callable[[Game, int], float]

# Lớn hơn mọi giá trị heuristic (kinrow_eval: WIN = 10**(k+1)): thắng thật luôn trội hơn eval.
WIN_SCORE = 10**12


def terminal_score(winner: int, player: int, ply: int) -> float:
    """Điểm ván đã kết thúc theo góc nhìn `player`; `ply` = số nước từ gốc.

    Ưu tiên thắng nhanh / thua chậm: thắng = WIN_SCORE − ply, thua = −(WIN_SCORE − ply), hòa = 0.
    """
    if winner == DRAW:
        return 0
    return WIN_SCORE - ply if winner == player else -(WIN_SCORE - ply)


class MinimaxAgent(Agent):
    """Minimax tường minh (tầng MAX = người đi ở gốc, tầng MIN = đối thủ).

    depth=None → tìm đến trạng thái kết thúc. Khi chạm `depth` mà chưa kết thúc: dùng
    `eval_fn(game, root_player)` (None → 0).
    """

    def __init__(
        self,
        depth: int | None = None,
        eval_fn: EvalFn | None = None,
        use_candidates: bool = True,
        seed: int | None = None,
    ) -> None:
        super().__init__()
        if depth is not None and depth < 1:
            raise ValueError("depth phải ≥ 1 hoặc None")
        self.depth = depth
        self.eval_fn = eval_fn
        self.use_candidates = use_candidates
        self.rng = random.Random(seed) if seed is not None else None
        self._nodes = 0

    def _moves(self, game: Game) -> list[Move]:
        return game.candidate_moves() if self.use_candidates else game.legal_moves()

    def root_values(self, game: Game) -> list[tuple[Move, float]]:
        """Giá trị minimax của từng nước ở gốc, theo góc nhìn người đang đi. Cập nhật `stats`."""
        assert not game.is_terminal(), "root_values gọi trên ván đã kết thúc"
        root = game.current_player()
        self._nodes = 1  # nút gốc
        t0 = time.perf_counter()
        values = []
        for move in self._moves(game):
            game.play(move)
            values.append((move, self._minimax(game, 1, root)))
            game.undo()
        self.stats["nodes"] = self._nodes
        self.stats["iterations"] = 0
        self.stats["time"] = time.perf_counter() - t0
        self.stats["value"] = max(v for _, v in values)
        return values

    def value(self, game: Game) -> float:
        """Giá trị minimax của `game` theo góc nhìn người đang đi (dùng để so với Alpha-Beta)."""
        return max(v for _, v in self.root_values(game))

    def _select_move(self, game: Game) -> Move:
        values = self.root_values(game)
        best = max(v for _, v in values)
        best_moves = [m for m, v in values if v == best]
        return self.rng.choice(best_moves) if self.rng else best_moves[0]

    def _minimax(self, game: Game, ply: int, root: int) -> float:
        """Giá trị nút theo góc nhìn `root`; MAX nếu tới lượt `root`, ngược lại MIN."""
        self._nodes += 1
        winner = game.winner()
        if winner is not None:
            return terminal_score(winner, root, ply)
        if self.depth is not None and ply >= self.depth:
            return self.eval_fn(game, root) if self.eval_fn else 0
        maximizing = game.current_player() == root
        best = float("-inf") if maximizing else float("inf")
        for move in self._moves(game):
            game.play(move)
            v = self._minimax(game, ply + 1, root)
            game.undo()
            best = max(best, v) if maximizing else min(best, v)
        return best
