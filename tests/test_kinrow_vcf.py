import random
import time

from gameai.core.game import P1, P2
from gameai.games.kinrow import KInRow, cell_of
from gameai.heuristics.kinrow_vcf import (
    completion_cells,
    find_vcf,
    make_root_hook,
    vcf_search,
    win_cells,
)

X, O = P1, P2  # noqa: E741


def rc(r: int, c: int, n: int = 15) -> int:
    return r * n + c


def build(xs, os, n: int = 15, k: int = 5) -> KInRow:
    """Dựng thế bằng play xen kẽ X, O (X đi trước). len(xs) == len(os): X đi; hơn 1: O đi."""
    assert len(xs) - len(os) in (0, 1)
    g = KInRow(n, k)
    for i, x in enumerate(xs):
        g.play(x)
        assert not g.is_terminal()
        if i < len(os):
            g.play(os[i])
            assert not g.is_terminal()
    return g


# Chuỗi 2 four: X hàng 7 cột 3-5 (O chặn (7,2)) → (7,6) tạo four (hoàn thành (7,7));
# O buộc chặn; rồi cột 6 có 5,6,7 → (8,6) tạo four-mở (hai đầu) → thắng.
CHAIN_X = [rc(7, 3), rc(7, 4), rc(7, 5), rc(5, 6), rc(6, 6)]
CHAIN_O = [rc(7, 2), rc(0, 0), rc(0, 4), rc(13, 13), rc(13, 9)]


def chain(os=CHAIN_O) -> KInRow:
    return build(CHAIN_X, os)


def test_completion_cells_basic():
    g = chain()
    assert completion_cells(g, rc(7, 6), cell_of(X)) == {rc(7, 7)}  # đầu kia (7,2) là O
    assert completion_cells(g, rc(0, 7), cell_of(X)) == set()
    g2 = build([rc(7, 5), rc(7, 6), rc(7, 7)], [rc(0, 0), rc(0, 2), rc(2, 0)])
    assert completion_cells(g2, rc(7, 8), cell_of(X)) == {rc(7, 4), rc(7, 9)}  # four mở


def test_vcf_chain_found_and_depth_limit():
    g = chain()
    assert find_vcf(g, X, 2) == rc(7, 6)
    assert find_vcf(g, X, 1) is None  # cần 2 four liên tiếp
    assert find_vcf(g, X, 8) == rc(7, 6)


def test_vcf_chain_replays_to_a_win():
    g = chain()
    for _ in range(4):
        m = find_vcf(g, X, 8)
        assert m is not None
        if g._wins_at(m, cell_of(X)):
            g.play(m)
            break
        comps = completion_cells(g, m, cell_of(X))
        g.play(m)
        if len(comps) >= 2:
            g.play(sorted(comps)[0])  # đối thủ chặn một đầu
            m2 = find_vcf(g, X, 8)
            assert g._wins_at(m2, cell_of(X))
            g.play(m2)
            break
        g.play(next(iter(comps)))
    assert g.winner() == X


def test_open_three_is_vcf_depth_one():
    g = build([rc(7, 5), rc(7, 6), rc(7, 7)], [rc(0, 0), rc(0, 2), rc(2, 0)])
    assert find_vcf(g, X, 1) in (rc(7, 4), rc(7, 8))  # four mở (hoặc ô tạo hai đầu)


def test_win_now_returned_first():
    g = build([rc(7, 3), rc(7, 4), rc(7, 5), rc(7, 6)], [rc(0, 0), rc(0, 2), rc(2, 0), rc(2, 2)])
    assert find_vcf(g, X, 0) in (rc(7, 2), rc(7, 7))
    assert vcf_search(g, X, 0) == (find_vcf(g, X, 0), False)


def test_no_vcf_when_four_is_dead():
    # hai đầu hàng 7 bị chặn: (7,6) chỉ tạo "four chết" (không có ô hoàn thành)
    os = [rc(7, 2), rc(7, 7), rc(0, 4), rc(13, 13), rc(13, 9)]
    g = chain(os)
    assert completion_cells(g, rc(7, 6), cell_of(X)) == set()
    assert find_vcf(g, X, 8) is None


def test_no_vcf_when_opponent_has_immediate_win():
    # O đã có four sát mép (cột 0, hàng 11–14): X không thể đi four mà bỏ qua ô thắng (10,0)
    os = [rc(7, 2), rc(11, 0), rc(12, 0), rc(13, 0), rc(14, 0)]
    g = chain(os)
    assert win_cells(g, cell_of(O)) == [rc(10, 0)]
    assert find_vcf(g, X, 8) is None


def test_attacker_not_to_move_uses_pass():
    g = build(CHAIN_X, CHAIN_O[:4])  # O đi
    assert g.current_player() == O
    assert find_vcf(g, X, 2) == rc(7, 6)
    assert g.current_player() == O and len(g.move_history) == 9  # không đụng `game`


def test_deadline_cuts_search():
    g = chain()
    assert vcf_search(g, X, 8, time.perf_counter() - 1) == (None, True)
    assert find_vcf(g, X, 8, time.perf_counter() - 1) is None


def test_hook_takes_own_vcf_and_win():
    hook = make_root_hook(8, 5.0)
    assert hook(chain()) == (rc(7, 6), None)
    g = build([rc(7, 3), rc(7, 4), rc(7, 5), rc(7, 6)], [rc(0, 0), rc(0, 2), rc(2, 0), rc(2, 2)])
    mv, rest = hook(g)
    assert mv in (rc(7, 2), rc(7, 7)) and rest is None


def test_hook_forced_block_single_and_double_threat():
    hook = make_root_hook(8, 5.0)
    xs = [rc(7, 3), rc(7, 4), rc(7, 5), rc(7, 6), rc(0, 0)]
    os = [rc(0, 2), rc(2, 0), rc(2, 2), rc(13, 13)]
    g = build(xs, os)  # O đi, X có four hở một đầu? (7,2),(7,7) đều trống → đã thua
    assert hook(g) == (None, None)
    g = build(xs, [rc(7, 2), *os[1:]])  # chỉ còn (7,7)
    assert hook(g) == (rc(7, 7), None)


def test_hook_defends_against_opponent_vcf():
    """Đối thủ có VCF: hook trả đúng tập nước khiến hết VCF (đối chiếu từng ứng viên)."""
    hook = make_root_hook(8, 30.0)
    g = build(CHAIN_X, CHAIN_O[:4])  # O đi, X có VCF 2 four
    mv, rest = hook(g)
    safe = []
    for m in g.candidate_moves():
        h = g.clone()
        h.play(m)
        if find_vcf(h, X, 8) is None:
            safe.append(m)
    assert len(safe) >= 2 and mv is None
    assert rest == sorted(safe)
    assert {rc(7, 6), rc(7, 7)} <= set(safe)  # chiếm ô four hoặc ô hoàn thành
    assert rc(10, 10) not in safe


def test_hook_noop_without_threats_and_timeout_is_unrestricted():
    g = build([rc(7, 7), rc(8, 8)], [rc(7, 8), rc(9, 9)])
    assert make_root_hook(8, 5.0)(g) == (None, None)
    assert make_root_hook(8, 0.0)(build(CHAIN_X, CHAIN_O[:4])) == (None, None)


def test_k4_small_board():
    g = build([rc(4, 2, 9), rc(4, 3, 9)], [rc(0, 0, 9), rc(8, 8, 9)], n=9, k=4)
    assert find_vcf(g, X, 1) == rc(4, 4, 9) or find_vcf(g, X, 1) == rc(4, 1, 9)


# ---- đối chiếu với bản "ngây thơ" theo đúng định nghĩa (bàn 7×7, k=4) ----------------------
def _wins_via(g: KInRow, m: int, depth: int) -> bool:
    if depth <= 0:
        return False
    me = g.current_player()
    g.play(m)
    try:
        if g.is_terminal():
            return False
        wins_after = [i for i in range(g.n * g.n) if not g.board[i] and g._wins_at(i, cell_of(me))]
        if not wins_after:
            return False
        for r in [i for i in range(g.n * g.n) if not g.board[i]]:
            g.play(r)
            try:
                if g.is_terminal():
                    return False  # đối thủ thắng / hòa
                if not _attacker_wins(g, depth - 1):
                    return False
            finally:
                g.undo()
        return True
    finally:
        g.undo()


def _attacker_wins(g: KInRow, depth: int) -> bool:
    me = g.current_player()
    empties = [i for i in range(g.n * g.n) if not g.board[i]]
    if any(g._wins_at(e, cell_of(me)) for e in empties):
        return True
    return any(_wins_via(g, m, depth) for m in empties)


def random_position(rng: random.Random, n: int, k: int, plies: int) -> KInRow | None:
    g = KInRow(n, k, radius=2)
    for _ in range(plies):
        m = rng.choice(g.legal_moves())
        g.play(m)
        if g.is_terminal():
            return None
    return g


def test_vcf_matches_naive_definition_on_random_positions():
    rng = random.Random(1234)
    checked = found = 0
    while checked < 120:
        g = random_position(rng, 7, 4, rng.randint(6, 12))
        if g is None:
            continue
        checked += 1
        me = g.current_player()
        has_now = any(g._wins_at(e, cell_of(me)) for e in g.candidate_moves())
        mv = find_vcf(g, me, 3)
        expected = _attacker_wins(g.clone(), 3)
        assert (mv is not None) == expected, g.render()
        if mv is not None:
            found += 1
            if not has_now:
                assert _wins_via(g.clone(), mv, 3), g.render()
    assert found >= 5  # mẫu có đủ ca dương
