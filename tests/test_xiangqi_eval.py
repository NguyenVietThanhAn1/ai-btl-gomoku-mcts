"""Lượng giá cờ tướng (P8.2): delta = hiệu evaluate, đối xứng Đỏ/Đen, bảng, mvv_lva."""

import random

from gameai.experiments.p82_ab_check import midgame_fens
from gameai.games.xiangqi import BLACK, RED, START_FEN, A, B, C, N, P, R, Xiangqi, iccs_to_move
from gameai.heuristics import xiangqi_eval as xe


def random_positions(n_games: int, plies: int, seed: int):
    """(game, move) mọi nước được chọn trong các ván ngẫu nhiên có seed (game trước khi đi)."""
    rng = random.Random(seed)
    for _ in range(n_games):
        g = Xiangqi()
        for _ in range(plies):
            if g.is_terminal():
                break
            m = rng.choice(g.legal_moves())
            yield g, m
            g.play(m)


def flip_colors(fen: str) -> str:
    """Lật rank + đổi màu quân (Đỏ ↔ Đen): thế đối xứng gương qua giữa bàn."""
    board, side, *rest = fen.split()
    rows = [row.swapcase() for row in reversed(board.split("/"))]
    return " ".join(["/".join(rows), "b" if side == "w" else "w", *rest])


def mirror_files(fen: str) -> str:
    board, *rest = fen.split()
    rows = [row[::-1] for row in board.split("/")]
    return " ".join(["/".join(rows), *rest])


def test_delta_equals_evaluate_difference_both_sides_with_captures():
    n = captures = 0
    sides = set()
    for g, m in random_positions(25, 90, seed=5):
        mover = g.current_player()
        before = xe.evaluate(g, mover)
        d = xe.delta_eval(g, m)
        captures += g.board[m % 90] != 0
        g.play(m)
        assert xe.evaluate(g, mover) - before == d
        g.undo()
        sides.add(mover)
        n += 1
    assert n > 1500 and captures > 50 and sides == {RED, BLACK}


def test_start_position_is_balanced():
    g = Xiangqi()
    assert xe.evaluate(g, RED) == 0 == xe.evaluate(g, BLACK)


def test_evaluate_is_zero_sum_between_sides():
    for fen in midgame_fens(10, seed=1):
        g = Xiangqi(fen)
        assert xe.evaluate(g, RED) == -xe.evaluate(g, BLACK)


def test_evaluate_does_not_depend_on_side_to_move():
    for fen in midgame_fens(6, seed=2):
        w = Xiangqi(fen.replace(" b ", " w "))
        b = Xiangqi(fen.replace(" w ", " b "))
        assert xe.evaluate(w, RED) == xe.evaluate(b, RED)


def test_color_flip_negates_evaluate():
    for fen in [START_FEN, *midgame_fens(12, seed=3)]:
        g, f = Xiangqi(fen), Xiangqi(flip_colors(fen))
        assert xe.evaluate(g, RED) == xe.evaluate(f, BLACK)
        assert xe.evaluate(g, BLACK) == xe.evaluate(f, RED)


def test_left_right_mirror_keeps_evaluate():
    for fen in [START_FEN, *midgame_fens(12, seed=4)]:
        assert xe.evaluate(Xiangqi(fen), RED) == xe.evaluate(Xiangqi(mirror_files(fen)), RED)


def test_pst_tables_shape_and_symmetry():
    assert len(xe.PST_RED) == 8 and all(len(t) == 90 for t in xe.PST_RED)
    for t in range(1, 8):
        for rank in range(10):
            for file in range(9):
                assert xe.PST_RED[t][rank * 9 + file] == xe.PST_RED[t][rank * 9 + 8 - file]


def test_material_order_and_pawn_river_bonus():
    m = xe.MATERIAL
    assert m[R] > m[C] >= m[N] > m[A] == m[B] > m[P]
    for file in range(9):
        assert xe.PST_RED[P][5 * 9 + file] > xe.PST_RED[P][4 * 9 + file]  # qua sông > chưa qua


def test_hand_trace_example_matches_docs():
    g = Xiangqi("3k5/9/9/9/r8/9/9/9/9/R3K4 w - - 0 1")
    assert xe.evaluate(g, RED) == -20  # xe Đỏ 900; xe Đen 900 + 5×4 (đã tiến) = 920
    move = iccs_to_move("a0a5")
    assert xe.delta_eval(g, move) == 945  # +25 (xe tiến 5 hàng) + 920 (ăn xe Đen)
    g.play(move)
    assert xe.evaluate(g, RED) == 925


def test_mvv_lva_capture_order():
    g = Xiangqi("3k5/9/9/9/r8/9/9/9/9/R3K4 w - - 0 1")
    assert xe.mvv_lva(g, iccs_to_move("a0a5")) == xe.CAPTURE_BASE + 10 * 900 - 900
    # tốt Đỏ ăn xe Đen > xe Đỏ ăn xe Đen > tốt Đỏ ăn tốt Đen
    pawn_x_rook = Xiangqi("3k5/9/9/9/r8/P8/9/9/9/4K4 w - - 0 1")
    # tốt Đỏ ở a4 chưa qua sông, chỉ tiến lên a5 ăn xe
    assert pawn_x_rook.board[iccs_to_move("a4a5") % 90] == -R
    s_pr = xe.mvv_lva(pawn_x_rook, iccs_to_move("a4a5"))
    s_rr = xe.mvv_lva(g, iccs_to_move("a0a5"))
    pawn_x_pawn = Xiangqi("3k5/9/9/9/p8/P8/9/9/9/4K4 w - - 0 1")
    s_pp = xe.mvv_lva(pawn_x_pawn, iccs_to_move("a4a5"))
    assert s_pr > s_rr > s_pp


def test_every_capture_beats_every_quiet_move():
    n_cap = n_quiet = 0
    for g, _m in random_positions(10, 80, seed=9):
        moves = g.legal_moves()
        caps = [x for x in moves if g.board[x % 90]]
        quiet = [x for x in moves if not g.board[x % 90]]
        if caps and quiet:
            assert min(xe.mvv_lva(g, x) for x in caps) > max(xe.mvv_lva(g, x) for x in quiet)
            n_cap += len(caps)
            n_quiet += len(quiet)
        assert [xe.mvv_lva(g, x) for x in moves] == [xe.mvv_lva(g, x) for x in moves]
    assert n_cap > 50 and n_quiet > 500


def test_mvv_lva_check_adds_bonus_only_for_checks_and_restores_game():
    g = Xiangqi("3k5/9/9/9/9/9/9/9/9/R3K4 w - - 0 1")
    fen = g.to_fen()
    key = g.key()
    checking = iccs_to_move("a0d0")  # xe lên cột d: chiếu tướng Đen ở d9
    quiet = iccs_to_move("a0a1")
    assert xe.mvv_lva_check(g, checking) == xe.mvv_lva(g, checking) + 5_000
    assert xe.mvv_lva_check(g, quiet) == xe.mvv_lva(g, quiet)
    assert g.to_fen() == fen and g.key() == key


def test_random_games_cover_every_piece_type():
    seen = {abs(g.board[m // 90]) for g, m in random_positions(25, 90, seed=5)}
    assert seen == set(range(1, 8))
