"""Cờ tướng (Xiangqi) 9×10 theo thiết kế D-22. Đỏ = P1 đi trước, Đen = P2."""

from __future__ import annotations

import random
from collections.abc import Hashable

from gameai.core.game import DRAW, P1, P2

RED = P1
BLACK = P2

# Quân: số nguyên có dấu, Đỏ dương, Đen âm, 0 = ô trống.
K, A, B, N, R, C, P = 1, 2, 3, 4, 5, 6, 7

START_FEN = "rheakaehr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RHEAKAEHR w - - 0 1"

NUM_SQ = 90
_FILES = "abcdefghi"
# FEN: chữ in hoa = Đỏ. Nhận cả n/b và h/e; xuất ra theo quy ước của nguồn perft (H, E).
_FEN_IN = {"k": K, "a": A, "b": B, "e": B, "n": N, "h": N, "r": R, "c": C, "p": P}
_FEN_OUT = {K: "K", A: "A", B: "E", N: "H", R: "R", C: "C", P: "P"}
_ASCII = {K: "K", A: "A", B: "B", N: "N", R: "R", C: "C", P: "P"}

DEFAULT_MAX_PLIES = 300


# --- bảng hình nước, tính một lần lúc import ---------------------------------------
def _on(r: int, f: int) -> bool:
    return 0 <= r < 10 and 0 <= f < 9


def _palace(r: int, f: int) -> int:
    """0 = ngoài cung, 1 = cung Đỏ, 2 = cung Đen."""
    if 3 <= f <= 5:
        if 0 <= r <= 2:
            return 1
        if 7 <= r <= 9:
            return 2
    return 0


def _build_tables() -> tuple:
    rays, king, adv, ele, kn, pawn = [], [], [], [], [], ([], [])
    for sq in range(NUM_SQ):
        r, f = divmod(sq, 9)
        # 4 tia (lên, xuống, trái, phải), mỗi tia là tuple ô theo thứ tự xa dần
        rr = []
        for dr, df in ((1, 0), (-1, 0), (0, -1), (0, 1)):
            ray, y, x = [], r + dr, f + df
            while _on(y, x):
                ray.append(y * 9 + x)
                y += dr
                x += df
            rr.append(tuple(ray))
        rays.append(tuple(rr))
        pal = _palace(r, f)
        # tướng: 1 bước dọc/ngang trong cùng cung; sĩ: 1 bước chéo trong cùng cung
        king.append(
            tuple(
                (r + dr) * 9 + f + df
                for dr, df in ((1, 0), (-1, 0), (0, -1), (0, 1))
                if pal and _on(r + dr, f + df) and _palace(r + dr, f + df) == pal
            )
        )
        adv.append(
            tuple(
                (r + dr) * 9 + f + df
                for dr, df in ((1, 1), (1, -1), (-1, 1), (-1, -1))
                if pal and _on(r + dr, f + df) and _palace(r + dr, f + df) == pal
            )
        )
        # tượng: nhảy chéo 2 ô (đích, ô mắt), không qua sông (cùng nửa sân)
        ele.append(
            tuple(
                ((r + 2 * dr) * 9 + f + 2 * df, (r + dr) * 9 + f + df)
                for dr, df in ((1, 1), (1, -1), (-1, 1), (-1, -1))
                if _on(r + 2 * dr, f + 2 * df) and (r <= 4) == (r + 2 * dr <= 4)
            )
        )
        # mã: (đích, ô chân); chân là ô liền kề theo hướng đi thẳng
        moves = []
        for dr, df in ((1, 0), (-1, 0), (0, -1), (0, 1)):
            leg_r, leg_f = r + dr, f + df
            if not _on(leg_r, leg_f):
                continue
            for pr, pf in ((df, dr), (-df, -dr)):
                tr, tf = r + 2 * dr + pr, f + 2 * df + pf
                if _on(tr, tf):
                    moves.append((tr * 9 + tf, leg_r * 9 + leg_f))
        kn.append(tuple(moves))
        # tốt: Đỏ tiến lên (rank tăng), qua sông (rank ≥ 5) thêm đi ngang; Đen ngược lại
        for side, fwd, crossed in ((0, 1, r >= 5), (1, -1, r <= 4)):
            dests = []
            if _on(r + fwd, f):
                dests.append((r + fwd) * 9 + f)
            if crossed:
                dests += [r * 9 + f + df for df in (-1, 1) if _on(r, f + df)]
            pawn[side].append(tuple(dests))
    # bảng ngược để dò chiếu: những ô mà từ đó mã/tốt tấn công ô `sq`
    kn_att: list[list[tuple[int, int]]] = [[] for _ in range(NUM_SQ)]
    for n_sq in range(NUM_SQ):
        for dest, leg in kn[n_sq]:
            kn_att[dest].append((n_sq, leg))
    pawn_att: tuple[list[list[int]], list[list[int]]] = (
        [[] for _ in range(NUM_SQ)],
        [[] for _ in range(NUM_SQ)],
    )
    for side in (0, 1):
        for p_sq in range(NUM_SQ):
            for dest in pawn[side][p_sq]:
                pawn_att[side][dest].append(p_sq)
    return (
        tuple(rays),
        tuple(king),
        tuple(adv),
        tuple(ele),
        tuple(kn),
        (tuple(pawn[0]), tuple(pawn[1])),
        tuple(tuple(x) for x in kn_att),
        (tuple(tuple(x) for x in pawn_att[0]), tuple(tuple(x) for x in pawn_att[1])),
    )


_RAYS, _KING, _ADV, _ELE, _KN, _PAWN, _KN_ATT, _PAWN_ATT = _build_tables()


def _build_zobrist() -> tuple[list[list[int]], int]:
    rng = random.Random(20261117)  # hằng số cố định → key tái lập giữa các lần chạy
    table = [[rng.getrandbits(64) for _ in range(NUM_SQ)] for _ in range(14)]
    return table, rng.getrandbits(64)


_Z, _Z_SIDE = _build_zobrist()


def _zi(piece: int) -> int:
    """Chỉ số hàng Zobrist: 0–6 Đỏ, 7–13 Đen."""
    return piece - 1 if piece > 0 else 6 - piece


# --- nước đi ---------------------------------------------------------------------
def make_move(frm: int, to: int) -> int:
    return frm * NUM_SQ + to


def split_move(move: int) -> tuple[int, int]:
    return divmod(move, NUM_SQ)


def sq_to_iccs(sq: int) -> str:
    r, f = divmod(sq, 9)
    return f"{_FILES[f]}{r}"


def move_to_iccs(move: int) -> str:
    """`int` → "h2e2" (file a–i, rank 0–9; rank 0 = hàng cuối bên Đỏ)."""
    frm, to = divmod(move, NUM_SQ)
    return sq_to_iccs(frm) + sq_to_iccs(to)


def iccs_to_move(text: str) -> int:
    s = text.strip().lower()
    if len(s) != 4:
        raise ValueError(f"ICCS không hợp lệ: {text!r}")
    sqs = []
    for file_ch, rank_ch in ((s[0], s[1]), (s[2], s[3])):
        if file_ch not in _FILES or not rank_ch.isdigit():
            raise ValueError(f"ICCS không hợp lệ: {text!r}")
        sqs.append(int(rank_ch) * 9 + _FILES.index(file_ch))
    return sqs[0] * NUM_SQ + sqs[1]


class Xiangqi:
    """Bàn 90 ô, `sq = rank*9 + file`. Chi tiết API + hạn chế: xem `xiangqi.md`."""

    def __init__(self, fen: str = START_FEN, max_plies: int = DEFAULT_MAX_PLIES) -> None:
        self.max_plies = max_plies
        self.board: list[int] = [0] * NUM_SQ
        self._player = RED
        self._kings = [-1, -1]  # ô tướng Đỏ, ô tướng Đen
        self._ply = 0
        self._stack: list[tuple[int, int]] = []  # (move, quân bị ăn)
        self._counts: dict[int, int] = {}
        self._legal: list[int] | None = None
        self._win: int | None | bool = False  # False = chưa tính
        self._load_fen(fen)
        self._key = self._compute_key()
        self._counts[self._key] = 1

    # --- FEN ---------------------------------------------------------------------
    def _load_fen(self, fen: str) -> None:
        parts = fen.split()
        if not parts:
            raise ValueError("FEN rỗng")
        rows = parts[0].split("/")
        if len(rows) != 10:
            raise ValueError("FEN phải có 10 hàng")
        board = [0] * NUM_SQ
        for i, row in enumerate(rows):
            rank, file = 9 - i, 0
            for ch in row:
                if ch.isdigit():
                    file += int(ch)
                    continue
                kind = _FEN_IN.get(ch.lower())
                if kind is None or file > 8:
                    raise ValueError(f"FEN lỗi ở hàng {row!r}")
                board[rank * 9 + file] = kind if ch.isupper() else -kind
                file += 1
            if file != 9:
                raise ValueError(f"FEN hàng {row!r} không đủ 9 cột")
        side = parts[1].lower() if len(parts) > 1 else "w"
        if side not in ("w", "r", "b"):
            raise ValueError(f"bên đi không hợp lệ: {side!r}")
        self.board = board
        self._player = BLACK if side == "b" else RED
        self._kings = [board.index(K) if K in board else -1, board.index(-K) if -K in board else -1]
        if min(self._kings) < 0 or board.count(K) != 1 or board.count(-K) != 1:
            raise ValueError("FEN phải có đúng một tướng mỗi bên")

    def to_fen(self) -> str:
        rows = []
        for rank in range(9, -1, -1):
            row, empty = "", 0
            for file in range(9):
                p = self.board[rank * 9 + file]
                if p == 0:
                    empty += 1
                    continue
                if empty:
                    row += str(empty)
                    empty = 0
                ch = _FEN_OUT[abs(p)]
                row += ch if p > 0 else ch.lower()
            rows.append(row + (str(empty) if empty else ""))
        side = "w" if self._player == RED else "b"
        return f"{'/'.join(rows)} {side} - - 0 {1 + self._ply // 2}"

    @classmethod
    def from_fen(cls, fen: str, max_plies: int = DEFAULT_MAX_PLIES) -> Xiangqi:
        return cls(fen, max_plies)

    def _compute_key(self) -> int:
        key = _Z_SIDE if self._player == BLACK else 0
        for sq, p in enumerate(self.board):
            if p:
                key ^= _Z[_zi(p)][sq]
        return key

    # --- trạng thái ----------------------------------------------------------------
    def current_player(self) -> int:
        return self._player

    @property
    def ply(self) -> int:
        return self._ply

    @property
    def move_history(self) -> tuple[int, ...]:
        return tuple(m for m, _ in self._stack)

    def key(self) -> Hashable:
        return self._key

    def _draw_rule(self) -> bool:
        return self._counts[self._key] >= 3 or self._ply >= self.max_plies

    def legal_moves(self) -> list[int]:
        """Nước hợp lệ (cache theo ply). Ván đã hòa theo luật lặp/giới hạn → []."""
        if self._legal is None:
            self._legal = self._gen_legal()
        if not self._legal or self._draw_rule():
            return []
        return list(self._legal)

    def candidate_moves(self) -> list[int]:
        return self.legal_moves()

    def winner(self) -> int | None:
        """Hết nước hợp lệ → bên sắp đi thua; lặp thế lần 3 hoặc `max_plies` → hòa."""
        if self._win is not False:
            return self._win  # type: ignore[return-value]
        has_move = bool(self._legal) if self._legal is not None else self._has_legal_move()
        if not has_move:
            result: int | None = -self._player
        elif self._draw_rule():
            result = DRAW
        else:
            result = None
        self._win = result
        return result

    def is_terminal(self) -> bool:
        return self.winner() is not None

    # --- đi / hoàn tác -------------------------------------------------------------
    def play(self, move: int) -> None:
        frm, to = divmod(move, NUM_SQ)
        assert self.board[frm] * self._player > 0 and self.board[to] * self._player <= 0
        captured = self._make_raw(frm, to)
        self._stack.append((move, captured))
        self._player = -self._player
        self._key ^= _Z_SIDE
        self._ply += 1
        self._counts[self._key] = self._counts.get(self._key, 0) + 1
        self._legal = None
        self._win = False

    def undo(self) -> None:
        move, captured = self._stack.pop()
        count = self._counts[self._key] - 1
        if count:
            self._counts[self._key] = count
        else:
            del self._counts[self._key]
        self._player = -self._player
        self._key ^= _Z_SIDE
        self._ply -= 1
        frm, to = divmod(move, NUM_SQ)
        self._unmake_raw(frm, to, captured)
        self._legal = None
        self._win = False

    def _make_raw(self, frm: int, to: int) -> int:
        """Đặt quân (cập nhật bàn, key phần quân, vị trí tướng); không đổi lượt/ply."""
        board = self.board
        piece = board[frm]
        captured = board[to]
        key = self._key ^ _Z[_zi(piece)][frm] ^ _Z[_zi(piece)][to]
        if captured:
            key ^= _Z[_zi(captured)][to]
        self._key = key
        board[to] = piece
        board[frm] = 0
        if piece == K:
            self._kings[0] = to
        elif piece == -K:
            self._kings[1] = to
        return captured

    def _unmake_raw(self, frm: int, to: int, captured: int) -> None:
        board = self.board
        piece = board[to]
        key = self._key ^ _Z[_zi(piece)][frm] ^ _Z[_zi(piece)][to]
        if captured:
            key ^= _Z[_zi(captured)][to]
        self._key = key
        board[frm] = piece
        board[to] = captured
        if piece == K:
            self._kings[0] = frm
        elif piece == -K:
            self._kings[1] = frm

    # --- sinh nước -------------------------------------------------------------------
    def _pseudo(self) -> list[int]:
        """Nước giả hợp lệ của bên sắp đi (chưa kiểm tướng bị chiếu / lộ mặt)."""
        b = self.board
        s = self._player
        sidx = 0 if s > 0 else 1
        pawn_tab = _PAWN[sidx]
        out: list[int] = []
        add = out.append
        for frm in range(NUM_SQ):
            p = b[frm]
            if p * s <= 0:
                continue
            t = p if p > 0 else -p
            base = frm * NUM_SQ
            if t == R:
                for ray in _RAYS[frm]:
                    for to in ray:
                        q = b[to]
                        if q == 0:
                            add(base + to)
                        else:
                            if q * s < 0:
                                add(base + to)
                            break
            elif t == C:
                for ray in _RAYS[frm]:
                    jumped = False
                    for to in ray:
                        q = b[to]
                        if not jumped:
                            if q == 0:
                                add(base + to)
                            else:
                                jumped = True
                        elif q != 0:
                            if q * s < 0:
                                add(base + to)
                            break
            elif t == N:
                for to, leg in _KN[frm]:
                    if b[leg] == 0 and b[to] * s <= 0:
                        add(base + to)
            elif t == P:
                for to in pawn_tab[frm]:
                    if b[to] * s <= 0:
                        add(base + to)
            elif t == B:
                for to, eye in _ELE[frm]:
                    if b[eye] == 0 and b[to] * s <= 0:
                        add(base + to)
            elif t == A:
                for to in _ADV[frm]:
                    if b[to] * s <= 0:
                        add(base + to)
            else:  # K
                for to in _KING[frm]:
                    if b[to] * s <= 0:
                        add(base + to)
        return out

    def _king_attacked(self, s: int) -> bool:
        """Tướng bên `s` có đang bị tấn công không (gồm lộ mặt tướng)."""
        b = self.board
        ksq = self._kings[0 if s > 0 else 1]
        e = -s  # dấu của quân đối phương
        for ray in _RAYS[ksq]:
            screen = False
            for sq in ray:
                q = b[sq]
                if q == 0:
                    continue
                if not screen:
                    if q * e > 0:
                        t = q if q > 0 else -q
                        # xe tấn công; tướng đối phương trên cùng một cột = lộ mặt
                        if t == R or t == K:
                            return True
                    screen = True
                else:
                    if q == e * C:
                        return True
                    break
        e_knight = e * N
        for n_sq, leg in _KN_ATT[ksq]:
            if b[n_sq] == e_knight and b[leg] == 0:
                return True
        e_pawn = e * P
        for p_sq in _PAWN_ATT[0 if e > 0 else 1][ksq]:
            if b[p_sq] == e_pawn:
                return True
        return False

    def in_check(self) -> bool:
        """Bên sắp đi đang bị chiếu."""
        return self._king_attacked(self._player)

    def _gen_legal(self) -> list[int]:
        s = self._player
        out = []
        for mv in self._pseudo():
            frm, to = divmod(mv, NUM_SQ)
            captured = self._make_raw(frm, to)
            if not self._king_attacked(s):
                out.append(mv)
            self._unmake_raw(frm, to, captured)
        return out

    def _has_legal_move(self) -> bool:
        s = self._player
        for mv in self._pseudo():
            frm, to = divmod(mv, NUM_SQ)
            captured = self._make_raw(frm, to)
            ok = not self._king_attacked(s)
            self._unmake_raw(frm, to, captured)
            if ok:
                return True
        return False

    # --- tiện ích ---------------------------------------------------------------------
    def clone(self) -> Xiangqi:
        g = Xiangqi.__new__(Xiangqi)
        g.max_plies = self.max_plies
        g.board = list(self.board)
        g._player = self._player
        g._kings = list(self._kings)
        g._ply = self._ply
        g._stack = list(self._stack)
        g._counts = dict(self._counts)
        g._key = self._key
        g._legal = None if self._legal is None else list(self._legal)
        g._win = self._win
        return g

    def render(self) -> str:
        lines = []
        for rank in range(9, -1, -1):
            cells = []
            for file in range(9):
                p = self.board[rank * 9 + file]
                if p == 0:
                    cells.append(".")
                else:
                    ch = _ASCII[abs(p)]
                    cells.append(ch if p > 0 else ch.lower())
            lines.append(f"{rank} " + " ".join(cells))
        lines.append("  " + " ".join(_FILES))
        return "\n".join(lines)


def perft(game: Xiangqi, depth: int) -> int:
    """Số nút lá ở độ sâu `depth` (chỉ luật đi nước; bỏ qua lặp thế và `max_plies`, D-22).

    Trả `game` về đúng trạng thái ban đầu. Độ sâu cuối chỉ đếm số nước (bulk counting).
    """
    if depth <= 0:
        return 1

    def rec(d: int) -> int:
        moves = game._gen_legal()
        if d == 1:
            return len(moves)
        total = 0
        for mv in moves:
            frm, to = divmod(mv, NUM_SQ)
            captured = game._make_raw(frm, to)
            game._player = -game._player
            total += rec(d - 1)
            game._player = -game._player
            game._unmake_raw(frm, to, captured)
        return total

    return rec(depth)
