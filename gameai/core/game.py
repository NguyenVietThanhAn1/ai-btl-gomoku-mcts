"""Interface `Game` dùng chung cho k-in-a-row và cờ tướng."""

from __future__ import annotations

from collections.abc import Hashable
from typing import Protocol, TypeAlias, runtime_checkable

Move: TypeAlias = Hashable

P1 = 1
P2 = -1
DRAW = 0


@runtime_checkable
class Game(Protocol):
    """Hợp đồng mà mọi agent dựa vào. Chi tiết từng hàm: xem `game.md`."""

    def current_player(self) -> int: ...

    def legal_moves(self) -> list[Move]: ...

    def candidate_moves(self) -> list[Move]: ...

    def play(self, move: Move) -> None: ...

    def undo(self) -> None: ...

    def is_terminal(self) -> bool: ...

    def winner(self) -> int | None: ...

    def clone(self) -> Game: ...

    def key(self) -> Hashable: ...

    def render(self) -> str: ...


def result_for(winner: int | None, player: int) -> float:
    """Điểm của ván đã kết thúc theo góc nhìn `player`: thắng 1.0, hòa 0.5, thua 0.0."""
    if winner is None:
        raise ValueError("ván chưa kết thúc")
    if winner == DRAW:
        return 0.5
    return 1.0 if winner == player else 0.0
