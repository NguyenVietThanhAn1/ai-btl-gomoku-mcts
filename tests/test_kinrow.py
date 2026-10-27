import pytest

from gameai.core.game import DRAW, P1, P2, Game
from gameai.games.kinrow import KInRow, O, X


def play_seq(g: KInRow, moves: list[int]) -> None:
    for m in moves:
        g.play(m)


def idx(g: KInRow, r: int, c: int) -> int:
    return r * g.n + c


def win_line(n: int, k: int, cells: list[tuple[int, int]]) -> KInRow:
    """X đặt `cells` (nước cuối là nước thắng), O đi các ô xa để không cản."""
    g = KInRow(n, k)
    fillers = [(n - 1, c) for c in range(n)] if cells[0][0] != n - 1 else [(0, c) for c in range(n)]
    for i, (r, c) in enumerate(cells):
        g.play(r * n + c)
        if i < len(cells) - 1:
            fr, fc = fillers[i]
            g.play(fr * n + fc)
    return g


def test_aliases_and_protocol():
    assert (X, O) == (P1, P2)
    assert isinstance(KInRow(3, 3), Game)


def test_initial_state():
    g = KInRow(3, 3)
    assert g.current_player() == X
    assert not g.is_terminal() and g.winner() is None
    assert sorted(g.legal_moves()) == list(range(9))


@pytest.mark.parametrize(
    "cells",
    [
        [(1, 0), (1, 1), (1, 2)],  # ngang
        [(0, 1), (1, 1), (2, 1)],  # dọc
        [(0, 0), (1, 1), (2, 2)],  # chéo chính
        [(0, 2), (1, 1), (2, 0)],  # chéo phụ
    ],
)
def test_win_all_directions_3x3(cells):
    # O đi các ô hàng cuối/đầu không tạo ba; kiểm tra bằng nước thắng cuối
    g = KInRow(3, 3)
    others = [c for c in range(9) if divmod(c, 3) not in cells]
    for i, (r, c) in enumerate(cells):
        g.play(r * 3 + c)
        if i < 2:
            g.play(others[i])
    assert g.is_terminal() and g.winner() == X
    assert g.legal_moves() == []


def test_win_middle_move_completes_line():
    # Nước cuối nằm GIỮA đoạn: X ở 0,2 rồi lấp 1
    g = KInRow(15, 5)
    cells = [0, 1, 3, 4]
    o = [15 * 5 + i for i in range(4)]
    for i, c in enumerate(cells):
        g.play(c)
        g.play(o[i])
    assert not g.is_terminal()
    g.play(2)
    assert g.winner() == X


def test_win_o_player():
    g = KInRow(15, 5)
    play_seq(g, [0, 20, 30, 21, 60, 22, 90, 23, 120, 24])
    assert g.winner() == O


def test_win_at_edges_and_corners():
    g = win_line(15, 5, [(0, 10), (0, 11), (0, 12), (0, 13), (0, 14)])
    assert g.winner() == X
    g = win_line(15, 5, [(10, 14), (11, 14), (12, 14), (13, 14), (14, 14)])
    assert g.winner() == X
    g = win_line(15, 5, [(14, 10), (13, 11), (12, 12), (11, 13), (10, 14)])
    assert g.winner() == X
    g = win_line(15, 5, [(10, 0), (11, 1), (12, 2), (13, 3), (14, 4)])
    assert g.winner() == X


def test_four_in_row_is_not_win_for_k5():
    g = win_line(15, 5, [(5, 5), (5, 6), (5, 7), (5, 8)])
    assert not g.is_terminal() and g.winner() is None


def test_no_wraparound_across_rows():
    # (0,13),(0,14),(1,0),(1,1),(1,2) liền nhau trong mảng 1 chiều nhưng không thẳng hàng
    g = KInRow(15, 5)
    cells = [(0, 13), (0, 14), (1, 0), (1, 1), (1, 2)]
    for i, (r, c) in enumerate(cells):
        g.play(r * 15 + c)
        if i < 4:
            g.play(10 * 15 + i)
    assert g.winner() is None


def test_longer_than_k_still_wins():
    g = KInRow(15, 5)
    cells = [0, 1, 2, 3, 5]  # 5 chưa liền 0..3, rồi nối ô 4
    o = [15 * 7 + 2 * i for i in range(5)]
    for i, c in enumerate(cells):
        g.play(c)
        g.play(o[i])
    assert g.winner() is None
    g.play(4)
    assert g.winner() == X


def test_draw_3x3():
    g = KInRow(3, 3)
    # X O X / X O O / O X X  (không ai có 3 thẳng hàng)
    play_seq(g, [0, 1, 2, 4, 3, 5, 7, 6, 8])
    assert g.is_terminal() and g.winner() == DRAW
    assert g.legal_moves() == [] and g.candidate_moves() == []


def test_undo_restores_everything():
    g = KInRow(3, 3)
    play_seq(g, [0, 3, 1, 4])
    key, cands, legal = g.key(), g.candidate_moves(), g.legal_moves()
    g.play(2)
    assert g.winner() == X
    g.undo()
    assert g.winner() is None and not g.is_terminal()
    assert g.current_player() == X
    assert g.key() == key
    assert g.candidate_moves() == cands and g.legal_moves() == legal


def test_undo_all_back_to_empty():
    g = KInRow(15, 5)
    empty_key = g.key()
    play_seq(g, [112, 113, 100, 90, 7])
    for _ in range(5):
        g.undo()
    assert g.key() == empty_key
    assert g.candidate_moves() == [112]


def test_undo_after_draw():
    g = KInRow(3, 3)
    play_seq(g, [0, 1, 2, 4, 3, 5, 7, 6, 8])
    g.undo()
    assert g.winner() is None and g.current_player() == X
    assert g.legal_moves() == [8]


def test_clone_is_independent():
    g = KInRow(15, 5)
    play_seq(g, [112, 113])
    c = g.clone()
    c.play(100)
    c.play(101)
    assert g.key() != c.key()
    assert 100 in g.legal_moves() and 100 not in c.legal_moves()
    g.undo()
    assert c.key() != g.key()
    # clone vẫn undo được
    c.undo()
    c.undo()
    assert c.candidate_moves() == sorted(c.candidate_moves())
    assert c.current_player() == X


def test_key_distinguishes_positions():
    a = KInRow(3, 3)
    b = KInRow(3, 3)
    play_seq(a, [0, 1])  # X@0 O@1
    play_seq(b, [1, 0])  # X@1 O@0 -> bàn khác (cùng lượt)
    assert a.key() != b.key()
    k0 = KInRow(3, 3).key()
    assert a.key() != k0


def test_key_includes_player_to_move():
    # Cùng bàn (1 quân X ở giữa) nhưng khác lượt phải khác key.
    a = KInRow(3, 3)
    a.play(4)  # O đi
    b = a.clone()
    b.board[4] = X
    b._player = X  # ép lượt X trên cùng bàn
    assert a.key() != b.key()


def test_key_hashable_and_equal_for_transposition():
    a = KInRow(3, 3)
    b = KInRow(3, 3)
    play_seq(a, [0, 4, 8])
    play_seq(b, [8, 4, 0])
    assert a.key() == b.key() and hash(a.key()) == hash(b.key())


def test_candidates_subset_nonempty_empty_board():
    g = KInRow(15, 5)
    assert g.candidate_moves() == [7 * 15 + 7]
    assert set(g.candidate_moves()) <= set(g.legal_moves())


def test_candidates_3x3_is_all_empties():
    g = KInRow(3, 3)
    assert sorted(g.candidate_moves()) == list(range(9))
    g.play(4)
    assert sorted(g.candidate_moves()) == [0, 1, 2, 3, 5, 6, 7, 8]
    g.play(0)
    assert sorted(g.candidate_moves()) == [1, 2, 3, 5, 6, 7, 8]


def test_candidates_radius_15x15():
    g = KInRow(15, 5)
    g.play(7 * 15 + 7)
    cands = g.candidate_moves()
    assert len(cands) == 24  # 5x5 trừ ô đã đặt
    rows = {m // 15 for m in cands}
    cols = {m % 15 for m in cands}
    assert rows == set(range(5, 10)) and cols == set(range(5, 10))
    assert 7 * 15 + 7 not in cands


def test_candidates_clipped_at_corner():
    g = KInRow(15, 5)
    g.play(0)
    assert len(g.candidate_moves()) == 8  # 3x3 trừ ô góc


def test_custom_radius_and_matches_bruteforce():
    g = KInRow(9, 4, radius=1)
    play_seq(g, [40, 41, 22])
    stones = [i for i in range(81) if g.board[i]]
    expected = sorted(
        m
        for m in range(81)
        if not g.board[m]
        and any(max(abs(m // 9 - s // 9), abs(m % 9 - s % 9)) <= 1 for s in stones)
    )
    assert g.candidate_moves() == expected


def test_candidates_always_subset_during_random_playout():
    import random

    rng = random.Random(1)
    g = KInRow(15, 5)
    played = 0
    while not g.is_terminal() and played < 60:
        cands = g.candidate_moves()
        assert cands and set(cands) <= set(g.legal_moves())
        g.play(rng.choice(cands))
        played += 1
    for _ in range(played):
        g.undo()
    assert g.candidate_moves() == [112]


def test_legal_moves_empty_when_terminal_and_render():
    g = KInRow(3, 3)
    play_seq(g, [0, 3, 1, 4, 2])
    assert g.legal_moves() == []
    out = g.render()
    assert "X" in out and "O" in out


def test_invalid_params():
    with pytest.raises(ValueError):
        KInRow(3, 4)
