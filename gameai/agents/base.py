"""Agent base class: chọn nước đi cho một `Game` và ghi thống kê vào `stats`."""

from __future__ import annotations

from abc import ABC, abstractmethod

from gameai.core.game import Game, Move


class Agent(ABC):
    """Giao diện chung của mọi agent (Random, Greedy, Minimax, Alpha-Beta, MCTS).

    Template method (D-7): agent con override `_select_move`, không override `select_move`.
    """

    def __init__(self) -> None:
        self.stats: dict[str, float] = {}

    @property
    def name(self) -> str:
        return type(self).__name__

    def reset_stats(self) -> None:
        """Xóa thống kê; `select_move` gọi ở đầu mỗi lượt."""
        self.stats = {}

    def select_move(self, game: Game) -> Move:
        """Reset `stats` rồi chọn nước cho `game.current_player()`."""
        self.reset_stats()
        return self._select_move(game)

    @abstractmethod
    def _select_move(self, game: Game) -> Move:
        """Trả về một nước hợp lệ; ghi thống kê vào `self.stats`.

        Không được làm thay đổi `game` khi trả về (tự `undo`/`clone` nếu cần).
        Precondition: `game.is_terminal()` là False.
        """
