"""Heavy rollout nhanh cho k-in-a-row: cùng phân phối với `HeavyRollout(move_score, T)`.

Thay vì gọi `move_score` cho mọi candidate ở mỗi bước (quét ~20 cửa sổ × k ô mỗi ô), policy giữ
số quân X/O của từng cửa sổ và, với từng ô × từng bên, ba thành phần của `move_score`
(delta, số cửa sổ cho thắng ngay, số cửa sổ cần chặn). Mỗi nước đi chỉ cập nhật các cửa sổ qua ô
vừa đặt. Điểm ra đúng bằng `move_score` → cùng trọng số softmax → cùng chuỗi nước với cùng rng.
"""

from __future__ import annotations

import math
import random
from functools import cache

from gameai.games.kinrow import KInRow, cell_of
from gameai.heuristics.kinrow_eval import (
    _weights,
    block_bonus,
    move_score,
    win_score,
    windows,
    windows_through,
)

Contrib = tuple[int, int, int]  # (delta, cho thắng ngay?, cần chặn?) của một cửa sổ với một ô trống


@cache
def _contrib_table(k: int) -> tuple[tuple[Contrib, ...], ...]:
    """`table[a][b]`: đóng góp của một cửa sổ (a quân mình, b quân đối thủ) vào điểm của một ô trống
    trong nó, cho người sắp đi — đúng nhánh của `kinrow_eval._scan`."""
    w = _weights(k)
    table = []
    for a in range(k + 1):
        row = []
        for b in range(k + 1):
            if b == 0:
                row.append((w[a + 1] - w[a] if a < k else 0, 1 if a + 1 >= k else 0, 0))
            elif a == 0:
                row.append((w[b], 0, 1 if b == k - 1 else 0))
            else:
                row.append((0, 0, 0))
        table.append(tuple(row))
    return tuple(table)


@cache
def _empty_board_scores(n: int, k: int) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """(delta, win) của mỗi ô trên bàn trống (giống nhau cho hai bên; block luôn 0)."""
    d0, w0, _ = _contrib_table(k)[0][0]
    through = windows_through(n, k)
    return tuple(d0 * len(t) for t in through), tuple(w0 * len(t) for t in through)


class KInRowHeavyRollout:
    """Rollout policy cho `KInRow`: softmax((move_score − max) / T) trên candidate, tính tăng dần.

    Tương đương từng bit với `HeavyRollout(kinrow_eval.move_score, T)` (cùng điểm, cùng trọng số,
    cùng lời gọi `rng.choices`). Tự đồng bộ với ván qua `KInRow.move_history`: gỡ các nước không còn
    trong lịch sử, áp các nước mới → dùng chung được cho nhiều ván/clone, undo, gọi lẻ.
    """

    name = "heavy_kinrow"

    def __init__(self, temperature: float = 100.0) -> None:
        if temperature <= 0:
            raise ValueError("temperature phải > 0")
        self.temperature = temperature
        self._nk: tuple[int, int] | None = None
        self._hist: tuple[int, ...] = ()  # các nước đã áp vào trạng thái
        self._stones: list[int] = []  # quân (1 = X, 2 = O) tương ứng với `_hist`

    # --- trạng thái tăng dần --------------------------------------------------
    def _reset(self, n: int, k: int) -> None:
        self._nk = (n, k)
        self._wins = windows(n, k)
        self._through = windows_through(n, k)
        self._table = _contrib_table(k)
        n_win = len(self._wins)
        self._count = ([0] * n_win, [0] * n_win)  # số quân X, số quân O trong mỗi cửa sổ
        d, w = _empty_board_scores(n, k)
        cells = n * n
        # chỉ số 0 = điểm khi X đi, 1 = khi O đi
        self._delta = (list(d), list(d))
        self._win = (list(w), list(w))
        self._block = ([0] * cells, [0] * cells)
        self._hist = ()
        self._stones = []

    def _update(self, move: int, stone: int, sign: int) -> None:
        """Đặt (`sign` = 1) hoặc gỡ (−1) quân `stone` ở `move`; cập nhật mọi cửa sổ qua ô đó."""
        table, wins = self._table, self._wins
        cx, co = self._count
        dx, do = self._delta
        wx, wo = self._win
        bx, bo = self._block
        for wid in self._through[move]:
            x0, o0 = cx[wid], co[wid]
            if stone == 1:
                x1, o1 = x0 + sign, o0
                cx[wid] = x1
            else:
                x1, o1 = x0, o0 + sign
                co[wid] = o1
            # góc nhìn X: mình = x, đối thủ = o
            ad, aw, ab = table[x0][o0]
            nd, nw, nb = table[x1][o1]
            dd, dw, db = nd - ad, nw - aw, nb - ab
            if dd or dw or db:
                for c in wins[wid]:
                    dx[c] += dd
                    wx[c] += dw
                    bx[c] += db
            # góc nhìn O
            ad, aw, ab = table[o0][x0]
            nd, nw, nb = table[o1][x1]
            dd, dw, db = nd - ad, nw - aw, nb - ab
            if dd or dw or db:
                for c in wins[wid]:
                    do[c] += dd
                    wo[c] += dw
                    bo[c] += db

    def _sync(self, game: KInRow) -> None:
        """Đưa trạng thái nội bộ về đúng `game`: gỡ phần lịch sử khác, áp phần mới."""
        if self._nk != (game.n, game.k):
            self._reset(game.n, game.k)
        hist, old = game.move_history, self._hist
        common = len(old)
        if len(hist) < common or hist[:common] != old:
            common = 0
            for a, b in zip(hist, old, strict=False):
                if a != b:
                    break
                common += 1
        stones = self._stones
        for i in range(len(old) - 1, common - 1, -1):  # gỡ từ nước mới nhất
            self._update(old[i], stones[i], -1)
        del stones[common:]
        board = game.board
        for m in hist[common:]:
            s = board[m]
            self._update(m, s, 1)
            stones.append(s)
        self._hist = hist

    # --- API ------------------------------------------------------------------
    def move_scores(self, game: KInRow) -> list[int]:
        """`move_score(game, m)` cho mọi m trong `game.candidate_moves()` (cùng thứ tự)."""
        moves = game.candidate_moves()
        return self._scores(game, moves)

    def _scores(self, game: KInRow, moves: list[int]) -> list[int]:
        self._sync(game)
        if game.n * game.n - len(self._hist) == 1:  # ô trống cuối: move_score cần −evaluate
            return [move_score(game, m) for m in moves]
        p = cell_of(game.current_player()) - 1
        delta, win, block = self._delta[p], self._win[p], self._block[p]
        k = game.k
        top_score, bonus = win_score(k), block_bonus(k)
        return [
            top_score if win[m] else (delta[m] + bonus if block[m] else delta[m]) for m in moves
        ]

    def __call__(self, game: KInRow, rng: random.Random) -> int:
        moves = game.candidate_moves()
        scores = self._scores(game, moves)
        top = max(scores)
        t = self.temperature
        weights = [math.exp((s - top) / t) for s in scores]  # y hệt HeavyRollout
        return rng.choices(moves, weights=weights)[0]
