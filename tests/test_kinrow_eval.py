import random

import pytest

from gameai.games.kinrow import KInRow, O, X, cell_of
from gameai.heuristics.kinrow_eval import (
    block_bonus,
    delta_eval,
    evaluate,
    move_score,
    win_score,
    windows,
    windows_through,
)


def rc(r: int, c: int, n: int = 15) -> int:
    return r * n + c


def setup(n: int, k: int, xs=(), os=(), to_move: int = X) -> KInRow:
    """Đặt quân trực tiếp lên board (eval chỉ đọc board và lượt đi)."""
    g = KInRow(n, k)
    for m in xs:
        g.board[m] = cell_of(X)
    for m in os:
        g.board[m] = cell_of(O)
    g._player = to_move
    return g


def random_positions(n: int, k: int, games: int, seed: int):
    """Sinh các vị trí chưa kết thúc từ playout ngẫu nhiên (cùng một đối tượng, đã mutate)."""
    rng = random.Random(seed)
    for _ in range(games):
        g = KInRow(n, k)
        while not g.is_terminal():
            yield g
            g.play(rng.choice(g.candidate_moves()))


def test_cell_of():
    assert cell_of(X) == 1
    assert cell_of(O) == 2


def test_empty_board_is_zero():
    g = KInRow(15, 5)
    assert evaluate(g, X) == 0
    assert evaluate(g, O) == 0


def test_window_counts_and_geometry():
    wins = windows(15, 5)
    assert len(wins) == 572
    for cells in wins:
        step = cells[1] - cells[0]
        assert step in (1, 15, 16, 14)
        assert all(b - a == step for a, b in zip(cells, cells[1:], strict=False))
        rows = [c // 15 for c in cells]
        cols = [c % 15 for c in cells]
        # không quấn hàng: hàng/cột đổi đều theo hướng
        assert len({b - a for a, b in zip(rows, rows[1:], strict=False)}) == 1
        assert len({b - a for a, b in zip(cols, cols[1:], strict=False)}) == 1
    through = windows_through(15, 5)
    assert max(len(t) for t in through) <= 20
    assert sum(len(t) for t in through) == 572 * 5


def test_terminal_scores():
    g = KInRow(3, 3)
    for m in (0, 3, 1, 4, 2):
        g.play(m)
    assert evaluate(g, X) == win_score(3)
    assert evaluate(g, O) == -win_score(3)


def test_draw_is_zero():
    g = KInRow(3, 3)
    for m in (0, 1, 2, 4, 3, 5, 7, 6, 8):
        g.play(m)
    assert g.winner() == 0
    assert evaluate(g, X) == 0
    assert evaluate(g, O) == 0


@pytest.mark.parametrize(("n", "k"), [(3, 3), (7, 4), (15, 5)])
def test_antisymmetric(n, k):
    for g in random_positions(n, k, games=15, seed=1):
        assert evaluate(g, X) == -evaluate(g, O)


def test_pattern_ordering():
    row = 7
    xs = lambda cols: [rc(row, c) for c in cols]  # noqa: E731
    open_four = evaluate(setup(15, 5, xs([5, 6, 7, 8])), X)
    four = evaluate(setup(15, 5, xs([5, 6, 7, 8]), [rc(row, 9)]), X)
    open_three = evaluate(setup(15, 5, xs([6, 7, 8])), X)
    three = evaluate(setup(15, 5, xs([6, 7, 8]), [rc(row, 5)]), X)
    two = evaluate(setup(15, 5, xs([7, 8])), X)
    assert open_four > four > open_three > three > two > 0


def test_block_cell_beats_open_four_creation_by_delta_alone():
    """Minh họa lý do tách bậc: delta thuần thích tạo open-four hơn chặn four."""
    xs = [rc(7, 6), rc(7, 7), rc(7, 8), rc(10, 4)]
    os = [rc(10, 5), rc(10, 6), rc(10, 7), rc(10, 8)]
    g = setup(15, 5, xs, os)
    assert delta_eval(g, rc(7, 9)) > delta_eval(g, rc(10, 9))


@pytest.mark.parametrize(
    ("n", "k"), [(3, 3), (5, 4), (7, 4), pytest.param(15, 5, marks=pytest.mark.slow)]
)
def test_delta_eval_matches_brute_force(n, k):
    checked = 0
    for g in random_positions(n, k, games=12, seed=2):
        mover = g.current_player()
        before = evaluate(g, mover)
        for m in g.candidate_moves():
            g.play(m)
            after = evaluate(g, mover)
            g.undo()
            assert delta_eval(g, m) == after - before
            checked += 1
    assert checked > 100


def test_delta_eval_does_not_mutate():
    g = setup(15, 5, [rc(7, 7)], [rc(8, 8)], to_move=X)
    key, hist = g.key(), len(g._history)
    delta_eval(g, rc(7, 8))
    move_score(g, rc(7, 8))
    assert g.key() == key
    assert len(g._history) == hist


def best_moves(g: KInRow) -> set[int]:
    scores = {m: move_score(g, m) for m in g.legal_moves()}
    top = max(scores.values())
    return {m for m, s in scores.items() if s == top}


def test_block_opponent_four_over_making_open_four():
    # X (người đi) có open-three; O có four, đầu trái bị X chặn → ô thắng duy nhất của O là (10, 9)
    xs = [rc(7, 6), rc(7, 7), rc(7, 8), rc(10, 4)]
    os = [rc(10, 5), rc(10, 6), rc(10, 7), rc(10, 8)]
    g = setup(15, 5, xs, os, to_move=X)
    assert best_moves(g) == {rc(10, 9)}
    assert move_score(g, rc(10, 9)) > move_score(g, rc(7, 9))


def test_win_beats_block_when_both_have_four():
    xs = [rc(7, 5), rc(7, 6), rc(7, 7), rc(7, 8)]
    os = [rc(7, 4), rc(10, 5), rc(10, 6), rc(10, 7), rc(10, 8)]
    g = setup(15, 5, xs, os, to_move=X)
    assert best_moves(g) == {rc(7, 9)}
    assert move_score(g, rc(7, 9)) == win_score(5)
    assert move_score(g, rc(7, 9)) > move_score(g, rc(10, 9))


def test_3x3_win_and_block():
    g = KInRow(3, 3)
    for m in (0, 3, 1, 4):  # X: 0,1  O: 3,4  — X thắng ở 2, O đe dọa ở 5
        g.play(m)
    assert move_score(g, 2) == win_score(3)
    assert move_score(g, 5) > move_score(g, 6)
    assert best_moves(g) == {2}

    g = setup(3, 3, [0, 8], [3, 4], to_move=X)  # X không thắng được, phải chặn ô 5
    assert best_moves(g) == {5}
    assert move_score(g, 5) >= block_bonus(3)


def test_final_move_draw_branch():
    g = KInRow(3, 3)
    for m in (0, 1, 2, 4, 3, 5, 7, 6):  # còn đúng ô 8, nước đó hòa
        g.play(m)
    assert g.legal_moves() == [8]
    assert delta_eval(g, 8) == -evaluate(g, X)
    g.play(8)
    assert g.winner() == 0


def test_regular_delta_stays_below_block_bonus():
    for n, k in ((7, 4), (15, 5)):
        worst = 0
        for g in random_positions(n, k, games=10, seed=3):
            for m in g.candidate_moves():
                if move_score(g, m) != win_score(k):
                    worst = max(worst, abs(delta_eval(g, m)))
        assert worst < block_bonus(k)


def test_block_bonus_below_win():
    for k in (3, 4, 5):
        assert 0 < block_bonus(k) < win_score(k)
