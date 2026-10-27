"""Test interface `Game`, hằng số người chơi và `result_for`."""

from __future__ import annotations

from collections.abc import Hashable

import pytest

from gameai.core.game import DRAW, P1, P2, Game, Move, result_for


class CountGame:
    """Game giả: mỗi người lần lượt chọn 1 trong 2 nước; hết `limit` nước thì hòa."""

    def __init__(self, limit: int = 3) -> None:
        self.limit = limit
        self.history: list[int] = []

    def current_player(self) -> int:
        return P1 if len(self.history) % 2 == 0 else P2

    def is_terminal(self) -> bool:
        return len(self.history) >= self.limit

    def legal_moves(self) -> list[Move]:
        return [] if self.is_terminal() else [0, 1]

    def candidate_moves(self) -> list[Move]:
        return self.legal_moves()

    def play(self, move: Move) -> None:
        assert move in (0, 1)
        self.history.append(move)

    def undo(self) -> None:
        self.history.pop()

    def winner(self) -> int | None:
        return DRAW if self.is_terminal() else None

    def clone(self) -> CountGame:
        other = CountGame(self.limit)
        other.history = list(self.history)
        return other

    def key(self) -> Hashable:
        return (tuple(self.history), self.current_player())

    def render(self) -> str:
        return " ".join(map(str, self.history))


class Incomplete:
    def current_player(self) -> int:
        return P1


def first_move_agent(game: Game) -> Move:
    """Agent giả chỉ dùng các hàm của interface."""
    return game.candidate_moves()[0]


def test_player_constants() -> None:
    assert (P1, P2, DRAW) == (1, -1, 0)
    assert P1 == -P2


def test_runtime_checkable_accepts_complete_game() -> None:
    assert isinstance(CountGame(), Game)


def test_runtime_checkable_rejects_missing_methods() -> None:
    assert not isinstance(Incomplete(), Game)


def test_agent_can_play_through_interface_only() -> None:
    g = CountGame()
    while not g.is_terminal():
        g.play(first_move_agent(g))
    assert g.winner() == DRAW
    assert g.legal_moves() == []


def test_play_undo_and_clone_independent() -> None:
    g = CountGame()
    g.play(1)
    c = g.clone()
    c.play(0)
    assert g.history == [1] and c.history == [1, 0]
    c.undo()
    assert c.key() == g.key()


@pytest.mark.parametrize(
    ("winner", "player", "expected"),
    [
        (P1, P1, 1.0),
        (P2, P2, 1.0),
        (P1, P2, 0.0),
        (P2, P1, 0.0),
        (DRAW, P1, 0.5),
        (DRAW, P2, 0.5),
    ],
)
def test_result_for(winner: int, player: int, expected: float) -> None:
    assert result_for(winner, player) == expected


def test_result_for_rejects_unfinished_game() -> None:
    with pytest.raises(ValueError):
        result_for(None, P1)
