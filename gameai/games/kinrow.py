"""k-in-a-row trên bàn n×n (3×3 k=3 và 15×15 k=5 dùng chung một class)."""

from __future__ import annotations

from collections.abc import Hashable
from functools import cache

from gameai.core.game import DRAW, P1, P2

X = P1
O = P2  # noqa: E741

_DIRS = ((0, 1), (1, 0), (1, 1), (1, -1))


@cache
def _neighbors(n: int, radius: int) -> tuple[tuple[int, ...], ...]:
    """Với mỗi ô: các ô khác trong bán kính Chebyshev `radius` (cắt ở mép bàn)."""
    out = []
    for r in range(n):
        for c in range(n):
            out.append(
                tuple(
                    rr * n + cc
                    for rr in range(max(0, r - radius), min(n, r + radius + 1))
                    for cc in range(max(0, c - radius), min(n, c + radius + 1))
                    if (rr, cc) != (r, c)
                )
            )
    return tuple(out)


class KInRow:
    """Board 1 chiều, index = r*n + c. Ô: 0 trống, 1 = X (P1), 2 = O (P2)."""

    def __init__(self, n: int = 15, k: int = 5, radius: int = 2) -> None:
        if k > n:
            raise ValueError("k không được lớn hơn n")
        self.n = n
        self.k = k
        self.radius = radius
        self.board = bytearray(n * n)
        self._player = X
        self._winner: int | None = None
        self._history: list[tuple[int, int | None]] = []  # (move, winner trước đó)
        self._nbrs = _neighbors(n, radius)
        self._near = [0] * (n * n)  # số quân trong bán kính quanh mỗi ô
        self._cand: set[int] = set()  # ô trống có _near > 0

    # --- trạng thái -------------------------------------------------------
    def current_player(self) -> int:
        return self._player

    def is_terminal(self) -> bool:
        return self._winner is not None

    def winner(self) -> int | None:
        return self._winner

    def legal_moves(self) -> list[int]:
        if self._winner is not None:
            return []
        board = self.board
        return [i for i in range(self.n * self.n) if not board[i]]

    def candidate_moves(self) -> list[int]:
        """Ô trống trong bán kính `radius` quanh quân đã đặt (sắp tăng dần)."""
        if self._winner is not None:
            return []
        if not self._history:
            if self.n <= 2 * self.radius + 1:  # bàn nhỏ: bán kính phủ cả bàn
                return self.legal_moves()
            return [(self.n // 2) * self.n + self.n // 2]
        return sorted(self._cand)

    # --- đi / hoàn tác ----------------------------------------------------
    def play(self, move: int) -> None:
        board = self.board
        assert not board[move] and self._winner is None
        player = self._player
        stone = 1 if player == X else 2
        board[move] = stone
        self._history.append((move, self._winner))
        near, cand = self._near, self._cand
        cand.discard(move)
        for j in self._nbrs[move]:
            near[j] += 1
            if near[j] == 1 and not board[j]:
                cand.add(j)
        if self._wins_at(move, stone):
            self._winner = player
        elif len(self._history) == self.n * self.n:
            self._winner = DRAW
        self._player = -player

    def undo(self) -> None:
        move, prev_winner = self._history.pop()
        self.board[move] = 0
        near, cand = self._near, self._cand
        for j in self._nbrs[move]:
            near[j] -= 1
            if near[j] == 0:
                cand.discard(j)
        if near[move] > 0:
            cand.add(move)
        self._winner = prev_winner
        self._player = -self._player

    def _wins_at(self, move: int, stone: int) -> bool:
        """Chỉ quét 4 hướng qua `move`: O(k)."""
        n, k, board = self.n, self.k, self.board
        r, c = divmod(move, n)
        for dr, dc in _DIRS:
            count = 1
            rr, cc = r + dr, c + dc
            while 0 <= rr < n and 0 <= cc < n and board[rr * n + cc] == stone:
                count += 1
                rr += dr
                cc += dc
            rr, cc = r - dr, c - dc
            while 0 <= rr < n and 0 <= cc < n and board[rr * n + cc] == stone:
                count += 1
                rr -= dr
                cc -= dc
            if count >= k:
                return True
        return False

    # --- tiện ích ---------------------------------------------------------
    def clone(self) -> KInRow:
        g = KInRow.__new__(KInRow)
        g.n, g.k, g.radius = self.n, self.k, self.radius
        g.board = bytearray(self.board)
        g._player = self._player
        g._winner = self._winner
        g._history = list(self._history)
        g._nbrs = self._nbrs  # bất biến, dùng chung
        g._near = list(self._near)
        g._cand = set(self._cand)
        return g

    def key(self) -> Hashable:
        return (bytes(self.board), self._player)

    def render(self) -> str:
        sym = ".XO"
        return "\n".join(
            " ".join(sym[self.board[r * self.n + c]] for c in range(self.n)) for r in range(self.n)
        )
