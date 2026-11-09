"""Agent giả lỗi cho test arena (P4.1). Import được bằng `AgentSpec("arena_helpers:<Class>")`.

Đặt ở module riêng (không phải file test) để tiến trình worker (spawn) import được.
"""

from __future__ import annotations

import random

from gameai.agents.base import Agent
from gameai.core.game import Game, Move


class RaisingAgent(Agent):
    """Ném exception ở nước thứ `fail_at` (đếm từ 0) của mình; trước đó đi ngẫu nhiên."""

    def __init__(self, seed: int | None = None, fail_at: int = 0) -> None:
        super().__init__()
        self._rng = random.Random(seed)
        self._fail_at = fail_at
        self._calls = 0

    def _select_move(self, game: Game) -> Move:
        self._calls += 1
        if self._calls > self._fail_at:
            raise RuntimeError("boom\nsecond line")
        return self._rng.choice(game.legal_moves())


class IllegalAgent(Agent):
    """Luôn trả một nước không hợp lệ (ô ngoài bàn)."""

    def __init__(self, seed: int | None = None) -> None:
        super().__init__()

    def _select_move(self, game: Game) -> Move:
        self.stats["nodes"] = 7
        return -1


class MutatingAgent(Agent):
    """Đi một nước lên `game` (không undo) rồi trả một nước khác."""

    def __init__(self, seed: int | None = None) -> None:
        super().__init__()

    def _select_move(self, game: Game) -> Move:
        moves = game.legal_moves()
        game.play(moves[0])
        return moves[-1]


class BrokenInitAgent(Agent):
    """Lỗi ngay khi dựng (mô phỏng sai config)."""

    def __init__(self, seed: int | None = None) -> None:
        raise ValueError("bad config")

    def _select_move(self, game: Game) -> Move:  # pragma: no cover
        raise AssertionError


class SlowAgent(Agent):
    """Ngủ `sleep` giây mỗi nước rồi đi ngẫu nhiên (để test ghi CSV từng ván khi chạy song song)."""

    def __init__(self, seed: int | None = None, sleep: float = 0.2) -> None:
        super().__init__()
        self._rng = random.Random(seed)
        self._sleep = sleep

    def _select_move(self, game: Game) -> Move:
        import time

        time.sleep(self._sleep)
        return self._rng.choice(game.legal_moves())
