"""VCF (Victory by Continuous Fours) cho k-in-a-row: chuỗi nước "four" ép thắng + hook ở gốc."""

from __future__ import annotations

import time
from collections.abc import Callable

from gameai.games.kinrow import _DIRS, KInRow, cell_of

RootHook = Callable[[KInRow], "tuple[int | None, list[int] | None]"]


class _Timeout(Exception):
    pass


def completion_cells(game: KInRow, move: int, stone: int) -> set[int]:
    """Các ô mà `stone` chỉ cần thêm một quân là đủ k, **nếu** đặt `move` (ô trống) trước.

    Một cửa sổ k ô qua `move` đếm là "four" khi không có quân địch, đúng k−2 quân của `stone`
    (ngoài `move`) và đúng 1 ô trống khác (= ô hoàn thành). Không mutate `game`. Cửa sổ đã có
    k−1 quân (đặt `move` là thắng ngay) không tính ở đây.
    """
    n, k, board = game.n, game.k, game.board
    r, c = divmod(move, n)
    out: set[int] = set()
    for dr, dc in _DIRS:
        for s in range(-(k - 1), 1):
            r0, c0 = r + s * dr, c + s * dc
            r1, c1 = r0 + (k - 1) * dr, c0 + (k - 1) * dc
            if not (0 <= r0 < n and 0 <= c0 < n and 0 <= r1 < n and 0 <= c1 < n):
                continue
            own, empty, n_empty = 0, -1, 0
            for i in range(k):
                idx = (r0 + i * dr) * n + c0 + i * dc
                if idx == move:
                    continue
                v = board[idx]
                if v == stone:
                    own += 1
                elif v == 0:
                    n_empty += 1
                    empty = idx
                else:
                    own = -1
                    break
            if own == k - 2 and n_empty == 1:
                out.add(empty)
    return out


def win_cells(game: KInRow, stone: int) -> list[int]:
    """Ô trống (trong `candidate_moves`) mà `stone` đặt vào là thắng ngay."""
    return [e for e in game.candidate_moves() if game._wins_at(e, stone)]


def _as_mover(game: KInRow, attacker: int) -> KInRow:
    """Bản sao mà `attacker` là người đi (bỏ lượt nội bộ nếu cần; không đụng `game`)."""
    g = game.clone()
    if g.current_player() != attacker:
        g._player = attacker
    return g


class _Vcf:
    def __init__(self, deadline: float | None) -> None:
        self.deadline = deadline
        self.nodes = 0

    def attack(self, g: KInRow, depth: int) -> int | None:
        """Nước đầu của một chuỗi thắng ép (≤ `depth` four) cho người đang đi, hoặc None."""
        self.nodes += 1
        if self.deadline is not None and time.perf_counter() >= self.deadline:
            raise _Timeout
        att = g.current_player()
        stone, ostone = cell_of(att), cell_of(-att)
        cands = g.candidate_moves()
        for e in cands:
            if g._wins_at(e, stone):
                return e  # thắng ngay (không tốn độ sâu)
        if depth <= 0:
            return None
        threats = [e for e in cands if g._wins_at(e, ostone)]
        if len(threats) > 1:
            return None  # đối thủ có ≥ 2 ô thắng: một four không cứu được
        moves = []
        for m in cands:
            if threats and m != threats[0]:
                continue  # đối thủ đang đe dọa: chỉ four đồng thời chặn mới hợp lệ
            comps = completion_cells(g, m, stone)
            if comps:
                moves.append((-len(comps), m, comps))
        moves.sort(key=lambda t: t[0])  # sort ổn định: double-four trước, rồi thứ tự ô
        for neg, m, comps in moves:
            if neg <= -2:
                return m  # hai ô hoàn thành khác nhau: đối thủ không chặn nổi cả hai
            (c,) = comps
            g.play(m)
            g.play(c)  # đối thủ buộc chặn đúng ô này
            try:
                found = self.attack(g, depth - 1)
            finally:
                g.undo()
                g.undo()
            if found is not None:
                return m
        return None


def vcf_search(
    game: KInRow, attacker: int, max_depth: int, deadline: float | None = None
) -> tuple[int | None, bool]:
    """(nước đầu của VCF cho `attacker` | None, đã hết giờ?). `attacker` không cần là người đi."""
    if game.is_terminal():
        return None, False
    g = _as_mover(game, attacker)
    try:
        return _Vcf(deadline).attack(g, max_depth), False
    except _Timeout:
        return None, True


def find_vcf(
    game: KInRow, attacker: int, max_depth: int, deadline: float | None = None
) -> int | None:
    """Nước đầu của VCF (≤ `max_depth` four) cho `attacker`; None nếu không có / hết giờ."""
    return vcf_search(game, attacker, max_depth, deadline)[0]


def make_root_hook(vcf_depth: int = 8, vcf_time: float = 0.3) -> RootHook:
    """Hook ở gốc: `hook(game) -> (nước đi ngay | None, tập nước cho gốc | None)`.

    1. Mình thắng ngay / có VCF → (nước, None).
    2. Đối thủ có ≥ 2 ô thắng ngay → (None, None) (đã thua); đúng 1 → (ô đó, None).
    3. Đối thủ (nếu được đi) có VCF → thử từng ứng viên, giữ nước khiến hết VCF:
       1 nước → (nước, None); nhiều → (None, danh sách); không nước nào → (None, None).
    Hết `vcf_time` (tổng cho cả ba bước) ở bước nào cũng → (None, None) (không giới hạn gốc).
    """

    def hook(game: KInRow) -> tuple[int | None, list[int] | None]:
        deadline = time.perf_counter() + vcf_time
        me = game.current_player()
        mv, timed_out = vcf_search(game, me, vcf_depth, deadline)
        if mv is not None:
            return mv, None
        if timed_out:
            return None, None
        cands = game.candidate_moves()
        threats = [e for e in cands if game._wins_at(e, cell_of(-me))]
        if len(threats) > 1:
            return None, None
        if threats:
            return threats[0], None
        omv, timed_out = vcf_search(game, -me, vcf_depth, deadline)
        if omv is None:
            return None, None
        order = [omv] + [m for m in cands if m != omv]
        safe: list[int] = []
        for m in order:
            g = game.clone()
            g.play(m)
            found, timed_out = vcf_search(g, -me, vcf_depth, deadline)
            if timed_out:
                return None, None
            if found is None:
                safe.append(m)
        if not safe:
            return None, None
        if len(safe) == 1:
            return safe[0], None
        return None, sorted(safe)

    return hook
