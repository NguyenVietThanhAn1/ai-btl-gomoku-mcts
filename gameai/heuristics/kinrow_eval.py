"""Lượng giá k-in-a-row theo cửa sổ k ô liên tiếp (dùng chung cho AB, greedy, rollout)."""

from __future__ import annotations

from functools import cache

from gameai.core.game import DRAW
from gameai.games.kinrow import _DIRS, KInRow, cell_of


def win_score(k: int) -> int:
    """Điểm của ván thắng: lớn hơn mọi tổng điểm cửa sổ."""
    return 10**k * 10


def block_bonus(k: int) -> int:
    """Thưởng khi chặn nước thắng ngay của đối thủ (= WIN/10)."""
    return win_score(k) // 10


@cache
def _weights(k: int) -> tuple[int, ...]:
    """W[c] = 10^(c-1) cho cửa sổ có c quân cùng màu, W[0] = 0."""
    return (0, *(10 ** (c - 1) for c in range(1, k + 1)))


@cache
def windows(n: int, k: int) -> tuple[tuple[int, ...], ...]:
    """Mọi đoạn k ô liên tiếp theo 4 hướng trên bàn n×n (không quấn hàng)."""
    out = []
    for r in range(n):
        for c in range(n):
            for dr, dc in _DIRS:
                er, ec = r + dr * (k - 1), c + dc * (k - 1)
                if 0 <= er < n and 0 <= ec < n:
                    out.append(tuple((r + dr * i) * n + c + dc * i for i in range(k)))
    return tuple(out)


@cache
def windows_through(n: int, k: int) -> tuple[tuple[int, ...], ...]:
    """Với mỗi ô: chỉ số các cửa sổ (trong `windows`) chứa ô đó."""
    through: list[list[int]] = [[] for _ in range(n * n)]
    for wid, cells in enumerate(windows(n, k)):
        for cell in cells:
            through[cell].append(wid)
    return tuple(tuple(t) for t in through)


def evaluate(game: KInRow, player: int) -> int:
    """Điểm vị trí theo góc nhìn `player` (phản đối xứng giữa hai bên).

    Ván đã kết thúc: +WIN nếu `player` thắng, -WIN nếu thua, 0 nếu hòa. Ngược lại là
    tổng W[c] của cửa sổ chỉ có quân của `player` trừ tổng của đối thủ.
    """
    k = game.k
    if game.is_terminal():
        w = game.winner()
        return 0 if w == DRAW else (win_score(k) if w == player else -win_score(k))
    board, weights = game.board, _weights(k)
    own, opp = cell_of(player), cell_of(-player)
    total = 0
    for cells in windows(game.n, k):
        a = b = 0
        for c in cells:
            v = board[c]
            if v == own:
                a += 1
            elif v == opp:
                b += 1
        if b == 0:
            total += weights[a]
        elif a == 0:
            total -= weights[b]
    return total


def _scan(game: KInRow, move: int) -> tuple[bool, int, bool]:
    """Quét cửa sổ qua `move` cho người đang đi: (thắng, delta cục bộ, chặn k-1 của đối thủ)."""
    k, board, weights = game.k, game.board, _weights(game.k)
    player = game.current_player()
    own, opp = cell_of(player), cell_of(-player)
    wins = windows(game.n, k)
    win = block = False
    delta = 0
    for wid in windows_through(game.n, k)[move]:
        a = b = 0
        for c in wins[wid]:
            v = board[c]
            if v == own:
                a += 1
            elif v == opp:
                b += 1
        if b == 0:
            if a + 1 >= k:
                win = True
            delta += weights[a + 1] - weights[a]
        elif a == 0:
            delta += weights[b]  # cửa sổ của đối thủ bị xóa điểm
            if b == k - 1:
                block = True
    return win, delta, block


def delta_eval(game: KInRow, move: int) -> int:
    """`evaluate` sau khi đi `move` trừ `evaluate` trước đó, theo góc nhìn người đang đi.

    Chỉ quét cửa sổ qua `move` (không play/undo, không copy bàn); riêng nước kết thúc ván
    (thắng/hòa) cần tổng toàn bàn nên chậm hơn. Yêu cầu: ván chưa kết thúc, `move` là ô trống.
    """
    win, delta, _ = _scan(game, move)
    player = game.current_player()
    if win:
        return win_score(game.k) - evaluate(game, player)
    if game.board.count(0) == 1:  # nước cuối lấp đầy bàn mà không thắng → hòa, điểm 0
        return -evaluate(game, player)
    return delta


def move_score(game: KInRow, move: int) -> int:
    """Điểm ưu tiên nước đi (greedy / move ordering / rollout), ba bậc:

    1. nước thắng ngay → WIN;
    2. nước chặn k-1 quân của đối thủ (ô nằm trong cửa sổ đối thủ có k-1 quân, không có quân
       mình) → `delta_eval + BLOCK`;
    3. còn lại → `delta_eval`.

    Tách bậc vì delta thuần cho nước tạo open-four (~+1700) cao hơn nước chặn four (+1000)
    nên sẽ thua ngay. Biên độ delta thường < BLOCK nên bậc 2 luôn trên bậc 3.
    """
    k = game.k
    win, delta, block = _scan(game, move)
    if win:
        return win_score(k)
    if game.board.count(0) == 1:
        delta = -evaluate(game, game.current_player())
    return delta + block_bonus(k) if block else delta
