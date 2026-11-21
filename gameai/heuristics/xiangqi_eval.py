"""Lượng giá cờ tướng: vật chất + bảng điểm theo ô (PST), `delta_eval` O(1), `mvv_lva` (P8.2, D-23).

Bảng **tự thiết kế theo nguyên tắc** (công thức đơn giản, giải thích được), không lấy từ nguồn
ngoài và không tinh chỉnh bằng dữ liệu. Xem `xiangqi_eval.md`.
"""

from __future__ import annotations

from gameai.games.xiangqi import NUM_SQ, RED, A, B, C, N, P, R, Xiangqi

# Giá trị vật chất (chọn theo quy ước phổ biến, là tham số thiết kế). Chỉ số = loại quân (K..P).
MATERIAL: tuple[int, ...] = (0, 0, 200, 200, 400, 900, 450, 100)
#                          _  K  A    B    N    R    C    P

# Giá trị dùng để sắp xếp "quân rẻ ăn trước" (LVA): tướng đi ăn xếp sau mọi quân khác.
_LVA: tuple[int, ...] = (0, 1000, 200, 200, 400, 900, 450, 100)
CAPTURE_BASE = 10_000  # mọi nước ăn quân xếp trên mọi nước yên tĩnh (|delta| < CAPTURE_BASE)


def _center(file: int) -> int:
    """4 ở cột giữa (e), 0 ở hai biên (a, i)."""
    return 4 - abs(file - 4)


def _bonus(piece: int, rank: int, file: int) -> int:
    """Điểm cộng theo ô, góc nhìn Đỏ (rank 0 = hàng cuối nhà Đỏ, rank ≥ 5 = nửa sân Đen)."""
    if piece == P:
        if rank < 5:  # chưa qua sông: chỉ tiến được, không có điểm vị trí
            return 0
        bonus = 100 + 20 * (rank - 5) if rank < 9 else 100  # qua sông +100; càng gần đáy càng cao
        bonus += 5 * _center(file)
        if rank >= 7 and 3 <= file <= 5:  # trước cung địch
            bonus += 20
        return bonus
    if piece == N:  # mã: trung tâm tốt, biên xấu, tiến lên tốt
        return 8 * _center(file) + 5 * min(rank, 7)
    if piece == R:  # xe: cột giữa + tiến lên
        return 4 * _center(file) + 5 * rank
    if piece == C:  # pháo: cột giữa mạnh hơn, tiến lên ít hơn xe
        return 6 * _center(file) + 3 * min(rank, 6)
    if piece == A:  # sĩ: ô giữa cung (e1) giữ được cả cung
        return 20 if (rank, file) == (1, 4) else 0
    if piece == B:  # tượng: ô giữa (e2) tốt nhất, ô tiến (c4, g4) khá, ô biên (a3, i3) nhẹ
        return {(2, 4): 20, (4, 2): 10, (4, 6): 10, (2, 0): 5, (2, 8): 5}.get((rank, file), 0)
    return 0  # tướng: không có điểm vị trí


def _build_tables() -> tuple[tuple[tuple[int, ...], ...], tuple[tuple[int, ...], ...]]:
    """(PST Đỏ[loại][ô], SCORE[quân + 7][ô]) — SCORE là đóng góp vào (Đỏ − Đen)."""
    red = [[0] * NUM_SQ for _ in range(8)]
    for t in range(1, 8):
        for sq in range(NUM_SQ):
            rank, file = divmod(sq, 9)
            red[t][sq] = MATERIAL[t] + _bonus(t, rank, file)
    score = [[0] * NUM_SQ for _ in range(15)]
    for t in range(1, 8):
        for sq in range(NUM_SQ):
            rank, file = divmod(sq, 9)
            score[7 + t][sq] = red[t][sq]
            score[7 - t][sq] = -red[t][(9 - rank) * 9 + file]  # Đen: cùng bảng, lật rank
    return tuple(tuple(r) for r in red), tuple(tuple(r) for r in score)


PST_RED, _SCORE = _build_tables()


def piece_value(piece: int, sq: int) -> int:
    """Điểm của một quân (có dấu: Đỏ dương, Đen âm) đứng ở ô `sq` — đóng góp vào Đỏ − Đen."""
    return _SCORE[piece + 7][sq]


def evaluate(game: Xiangqi, player: int) -> int:
    """Điểm theo góc nhìn `player` = `sign × (Σ Đỏ − Σ Đen)`; không phụ thuộc bên sắp đi."""
    score = _SCORE
    total = 0
    for sq, p in enumerate(game.board):
        if p:
            total += score[p + 7][sq]
    return total if player == RED else -total


def delta_eval(game: Xiangqi, move: int) -> int:
    """`evaluate(sau) − evaluate(trước)` theo góc nhìn người sắp đi; gọi *trước* `play`."""
    frm, to = divmod(move, NUM_SQ)
    board = game.board
    p = board[frm]
    score = _SCORE
    row = score[p + 7]
    d = row[to] - row[frm]
    v = board[to]
    if v:
        d -= score[v + 7][to]
    return d if p > 0 else -d


def mvv_lva(game: Xiangqi, move: int) -> int:
    """Điểm sắp nước (cao = duyệt trước): ăn quân giá trị cao bằng quân rẻ trước (MVV-LVA).

    Ăn quân: `CAPTURE_BASE + 10×giá trị nạn nhân − giá trị quân đi`. Nước yên tĩnh: `delta_eval`
    (thay đổi vật chất+PST), luôn nhỏ hơn `CAPTURE_BASE`.
    """
    frm, to = divmod(move, NUM_SQ)
    board = game.board
    v = board[to]
    if v:
        return CAPTURE_BASE + 10 * MATERIAL[abs(v)] - _LVA[abs(board[frm])]
    return delta_eval(game, move)


def mvv_lva_check(game: Xiangqi, move: int, check_bonus: int = 5_000) -> int:
    """`mvv_lva` + thưởng `check_bonus` nếu nước này chiếu đối thủ (tốn: `play`+`in_check`+`undo`).

    Với `check_bonus` < `CAPTURE_BASE` − |delta|, nước chiếu yên tĩnh vẫn xếp dưới mọi nước ăn
    quân; nước ăn quân có chiếu được cộng thêm. Chỉ bật nếu đo cho thấy giảm thời gian (D-23).
    """
    base = mvv_lva(game, move)
    game.play(move)
    gives_check = game.in_check()
    game.undo()
    return base + check_bonus if gives_check else base
