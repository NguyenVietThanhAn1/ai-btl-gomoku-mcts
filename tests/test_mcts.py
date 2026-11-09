import math
import random

import pytest

from gameai.agents.mcts import (
    TACTIC_BLOCK,
    TACTIC_NONE,
    TACTIC_RESTRICT,
    TACTIC_WIN,
    MCTSAgent,
    Node,
    backpropagate,
    select_child,
    uct,
)
from gameai.agents.minimax import MinimaxAgent
from gameai.agents.random_agent import RandomAgent
from gameai.agents.rollout import sigmoid_value
from gameai.core.game import DRAW, P1, P2
from gameai.games.kinrow import KInRow, O, X
from gameai.heuristics.kinrow_eval import evaluate, move_score

# ----------------------------------------------------------------- helpers


def kinrow(n, k, moves):
    g = KInRow(n, k)
    for m in moves:
        g.play(m)
    return g


def p15(rc):
    return rc[0] * 15 + rc[1]


def setup15(xs, os_):
    """Đặt quân xen kẽ X, O, X, ... (len(xs) = len(os_) hoặc len(os_) + 1)."""
    seq = []
    for i, a in enumerate(xs):
        seq.append(p15(a))
        if i < len(os_):
            seq.append(p15(os_[i]))
    return kinrow(15, 5, seq)


def play_game(game, agent_x, agent_o):
    while not game.is_terminal():
        agent = agent_x if game.current_player() == X else agent_o
        game.play(agent.select_move(game))
    return game.winner()


def walk(root):
    stack = [root]
    while stack:
        v = stack.pop()
        yield v
        stack.extend(v.children)


def winning_moves(g):
    me, wins = g.current_player(), []
    for m in g.candidate_moves():
        g.play(m)
        if g.winner() == me:
            wins.append(m)
        g.undo()
    return wins


def safe_moves(g):
    """Nước mà sau đó đối thủ không thắng ngay (tính độc lập với MCTSAgent)."""
    safe = []
    for m in g.candidate_moves():
        g.play(m)
        lost = g.winner() is None and bool(winning_moves(g))
        g.undo()
        if not lost:
            safe.append(m)
    return safe


class Pile:
    """Game bốc sỏi: lấy 1..max_take viên, ai lấy viên cuối thắng (test MCTS ngoài KInRow)."""

    def __init__(self, n, max_take=3):
        self.n, self.max_take = n, max_take
        self.player, self.hist, self._winner = P1, [], None

    def current_player(self):
        return self.player

    def legal_moves(self):
        return [] if self._winner is not None else list(range(1, min(self.max_take, self.n) + 1))

    def candidate_moves(self):
        return self.legal_moves()

    def play(self, m):
        self.hist.append(m)
        self.n -= m
        if self.n == 0:
            self._winner = self.player
        self.player = -self.player

    def undo(self):
        self.n += self.hist.pop()
        self.player = -self.player
        self._winner = None

    def is_terminal(self):
        return self._winner is not None

    def winner(self):
        return self._winner

    def clone(self):
        c = Pile(self.n, self.max_take)
        c.player, c.hist, c._winner = self.player, list(self.hist), self._winner
        return c

    def key(self):
        return (self.n, self.player)

    def render(self):
        return str(self.n)


# X thắng ở (7, 9)
WIN15 = ([(7, 5), (7, 6), (7, 7), (7, 8)], [(7, 4), (10, 5), (10, 6), (10, 7)])
# X phải chặn ở (10, 9); X có open-three làm mồi
BLOCK15 = ([(10, 4), (7, 6), (7, 7), (7, 8)], [(10, 5), (10, 6), (10, 7), (10, 8)])

# ------------------------------------------------- UCT và backprop (unit)


def test_uct_formula_and_select_child():
    parent = Node(None, None, P2, [])
    parent.N = 10
    stats = [(3.0, 4), (1.0, 1), (5.0, 6)]
    for i, (w, n) in enumerate(stats):
        ch = Node(i, parent, P1, [])
        ch.W, ch.N = w, n
        parent.children.append(ch)
    c = math.sqrt(2)
    expected = [w / n + c * math.sqrt(math.log(10) / n) for w, n in stats]
    for ch, e in zip(parent.children, expected, strict=True):
        assert uct(ch, math.log(10), c) == pytest.approx(e)
    assert select_child(parent, c).move == max(range(3), key=lambda i: expected[i])  # = 1
    assert select_child(parent, 0.0).move == 1  # c = 0: W/N lớn nhất (1/1)
    parent.children[1].W = 0.0
    assert select_child(parent, 0.0).move == 2  # 5/6 > 3/4


def test_backpropagate_flips_by_player_just_moved():
    root = Node(None, None, O, [])  # X đi ở gốc
    a = Node(0, root, X, [])
    b = Node(1, a, O, [])
    backpropagate(b, 1.0)  # X (P1) thắng
    assert (root.W, a.W, b.W) == (0.0, 1.0, 0.0)
    backpropagate(b, 0.0)  # O thắng
    assert (root.W, a.W, b.W) == (1.0, 1.0, 1.0)
    backpropagate(b, 0.5)  # hòa
    assert (root.W, a.W, b.W) == (1.5, 1.5, 1.5)
    assert (root.N, a.N, b.N) == (3, 3, 3)
    backpropagate(a, 0.25)  # z thực (value_fn): node của O nhận 1 − z
    assert (root.W, a.W) == (2.25, 1.75)


# ------------------------------------------ góc nhìn: thắng ngay / chặn 3×3


@pytest.mark.parametrize(
    "moves, win",
    [
        ([0, 3, 1, 4], 2),  # X đi: thắng ở 2 (O cũng dọa 5)
        ([0, 3, 1, 4, 8], 5),  # O đi: thắng ở 5 (X cũng dọa 2)
    ],
)
@pytest.mark.parametrize("seed", [0, 1, 2])
def test_immediate_win_3x3_without_tactics(moves, win, seed):
    g = kinrow(3, 3, moves)
    agent = MCTSAgent(iterations=1000, seed=seed)
    assert agent.select_move(g) == win
    row = next(r for r in agent.last_root_stats() if r[0] == win)
    assert row[3] == 1.0  # con thắng: mọi lượt thăm đều thắng cho người vừa đi → W/N = 1 đúng
    assert agent.stats["value"] == 1.0


@pytest.mark.parametrize(
    "moves, block",
    [
        ([4, 0, 8, 1], 2),  # X đi, O dọa hàng 0
        ([4, 1, 0], 8),  # O đi, X dọa chéo 0-4-8
    ],
)
@pytest.mark.parametrize("seed", [0, 1, 2])
def test_must_block_3x3_without_tactics(moves, block, seed):
    g = kinrow(3, 3, moves)
    assert MCTSAgent(iterations=1000, seed=seed).select_move(g) == block


def tactical_positions_3x3(count, seed):
    """Thế 3×3 (tất định) có nước thắng ngay ("win"), hoặc không có mà đúng 1 nước an toàn
    ("block").

    Trả (game, kind, expected, immediate). "win": expected = mọi nước **thắng chắc** theo Minimax
    (gồm nước thắng ngay) — MCTS không chiết khấu độ sâu nên nước thắng chắc sau vài ply có thể có
    W/N = 1 bằng hệt nước thắng ngay (D-11); immediate = các nước thắng ngay. "block": expected =
    {ô chặn} (nước không thua duy nhất), immediate = ∅.
    """
    rng = random.Random(seed)
    found, seen = [], set()
    while len(found) < count:
        g = KInRow(3, 3)
        while not g.is_terminal():
            if g.key() not in seen and len(g.legal_moves()) > 1:
                wins = winning_moves(g)
                safe = [] if wins else safe_moves(g)
                if wins:
                    forced = {m for m, v in MinimaxAgent().root_values(g) if v > 0}
                    assert set(wins) <= forced
                    seen.add(g.key())
                    found.append((g.clone(), "win", forced, set(wins)))
                elif len(safe) == 1:
                    seen.add(g.key())
                    found.append((g.clone(), "block", set(safe), set()))
            g.play(rng.choice(g.legal_moves()))
    return found[:count]


def test_tactical_position_suite_3x3_without_tactics():
    """Done P3 (làm rõ ở D-11): MCTS 3×3, 1000 iter, tắt tactics — có nước thắng thì chọn nước thắng
    chắc (không bỏ thắng) và mọi nước thắng ngay đều có W/N = 1 ở gốc; phải chặn thì chặn đúng ô."""
    positions = tactical_positions_3x3(30, seed=2026)
    assert {g.current_player() for g, _, _, _ in positions} == {X, O}
    assert {kind for _, kind, _, _ in positions} == {"win", "block"}
    for i, (g, kind, expected, immediate) in enumerate(positions):
        agent = MCTSAgent(iterations=1000, seed=i)
        move = agent.select_move(g)
        assert move in expected, f"{kind}\n{g.render()}"
        wn = {r[0]: r[3] for r in agent.last_root_stats()}
        assert all(wn[m] == 1.0 for m in immediate), g.render()


def test_forced_win_ties_with_immediate_win():
    """Ghi nhận: O thắng ngay ở 1, nhưng O đi 8 cũng thắng chắc (3 đường dọa) → cả hai W/N = 1."""
    g = kinrow(3, 3, [2, 4, 3, 7, 5])  # . . X / X O X / . O .  — O đi
    agent = MCTSAgent(iterations=1000, seed=9)
    move = agent.select_move(g)
    rows = {r[0]: r for r in agent.last_root_stats()}
    assert rows[1][3] == 1.0 and rows[8][3] == 1.0
    assert move in (1, 8)


# ------------------------------------------------- bất biến của cây (c)


def check_tree(root, iterations, exact):
    """Gốc: N = ΣN_c, W = Σ(N_c − W_c). Node khác (không terminal): N = 1 + ΣN_c và
    phần 'tự thân' W − Σ(N_c − W_c) ∈ {0, 0.5, 1} (exact) hoặc ∈ [0, 1] (có value_fn)."""
    eps = 1e-9
    assert root.N == iterations == sum(ch.N for ch in root.children)
    assert root.W == pytest.approx(sum(ch.N - ch.W for ch in root.children))
    count = 0
    for v in walk(root):
        count += 1
        if v is root:
            continue
        if not v.children and not v.untried:  # trạng thái kết thúc: mọi lượt thăm dừng ở đây
            r = v.W / v.N
            assert (min(abs(r - t) for t in (0.0, 0.5, 1.0)) < eps) if exact else (0 <= r <= 1)
            continue
        assert v.N == 1 + sum(ch.N for ch in v.children)
        own = v.W - sum(ch.N - ch.W for ch in v.children)
        if exact:
            assert min(abs(own - t) for t in (0.0, 0.5, 1.0)) < eps
        else:
            assert -eps <= own <= 1 + eps
    return count


@pytest.mark.parametrize(
    "n, k, moves, iters",
    [
        (3, 3, [], 1000),
        (3, 3, [4, 0], 500),
        (7, 4, [24, 25, 17], 600),
    ],
)
def test_tree_invariants_exact(n, k, moves, iters):
    agent = MCTSAgent(iterations=iters, seed=3)  # value_fn=None → z ∈ {0, 0.5, 1}
    agent.select_move(kinrow(n, k, moves))
    count = check_tree(agent.root, iters, exact=True)
    assert count == agent.stats["nodes"]


def test_tree_invariants_with_value_fn():
    agent = MCTSAgent(iterations=400, rollout_limit=3, value_fn=sigmoid_value(evaluate, 50), seed=4)
    agent.select_move(kinrow(7, 4, [24, 25, 17]))
    check_tree(agent.root, 400, exact=False)


def test_value_fn_perspective_x_and_o():
    """value_fn trả 'P1 luôn thắng' + rollout_limit=0: con của gốc X có W/N = 1, của gốc O có 0."""
    opening_x = setup15([(7, 7), (7, 8)], [(8, 7), (6, 6)])  # X đi
    opening_o = setup15([(7, 7), (7, 8)], [(8, 7)])  # O đi
    for g, expected in ((opening_x, 1.0), (opening_o, 0.0)):
        agent = MCTSAgent(iterations=200, rollout_limit=0, value_fn=lambda _g: 1.0, seed=0)
        agent.select_move(g)
        assert {r[3] for r in agent.last_root_stats()} == {expected}


def test_rollout_cut_without_value_fn_scores_draw():
    g = setup15([(7, 7), (7, 8)], [(8, 7), (6, 6)])
    agent = MCTSAgent(iterations=200, rollout_limit=0, seed=0)
    agent.select_move(g)
    assert {r[3] for r in agent.last_root_stats()} == {0.5}
    assert agent.stats["rollout_plies"] == 0


# --------------------------------------------------------- check_tactics


def test_tactics_win_15x15():
    g = setup15(*WIN15)
    agent = MCTSAgent(iterations=50, check_tactics=True, seed=0)
    assert agent.select_move(g) == p15((7, 9))
    assert agent.stats["tactic"] == TACTIC_WIN
    assert agent.stats["iterations"] == 0 and agent.stats["nodes"] == 0
    assert agent.stats["value"] == 1.0
    assert agent.last_root_stats() == []


@pytest.mark.parametrize(
    "xs, os_, block",
    [
        (*BLOCK15, (10, 9)),  # X chặn four của O
        ([(7, 5), (7, 6), (7, 7), (7, 8)], [(7, 4), (0, 0), (0, 14)], (7, 9)),  # O chặn four của X
    ],
)
def test_tactics_block_15x15(xs, os_, block):
    g = setup15(xs, os_)
    agent = MCTSAgent(iterations=50, check_tactics=True, seed=0)
    assert agent.select_move(g) == p15(block)
    assert agent.stats["tactic"] == TACTIC_BLOCK
    assert agent.stats["iterations"] == 0
    assert math.isnan(agent.stats["value"])


def test_tactics_lost_position_still_searches():
    """O có open-four (2 ô thắng): không nước nào an toàn → search bình thường."""
    g = setup15([(0, 0), (0, 2), (2, 0), (14, 14)], [(10, 5), (10, 6), (10, 7), (10, 8)])
    agent = MCTSAgent(iterations=50, check_tactics=True, seed=0)
    move = agent.select_move(g)
    assert move in g.candidate_moves()
    assert agent.stats["tactic"] == TACTIC_NONE
    assert agent.stats["iterations"] == 50


def test_tactics_quiet_position_identical_to_off():
    """Không có thắng/chặn: tactics không tiêu RNG → cùng seed cho cùng cây như khi tắt."""
    g = setup15([(7, 7), (7, 8)], [(8, 7), (6, 6)])
    on = MCTSAgent(iterations=150, check_tactics=True, seed=5)
    off = MCTSAgent(iterations=150, check_tactics=False, seed=5)
    assert on.select_move(g) == off.select_move(g)
    assert on.last_root_stats() == off.last_root_stats()
    assert on.stats["tactic"] == TACTIC_NONE


def test_tactics_on_generic_game_block_and_restrict():
    # 5 viên: lấy 2 hoặc 3 thì đối thủ lấy hết → chỉ lấy 1 là an toàn
    agent = MCTSAgent(iterations=100, check_tactics=True, seed=0)
    assert agent.select_move(Pile(5)) == 1
    assert agent.stats["tactic"] == TACTIC_BLOCK
    # 6 viên: lấy 3 thua ngay; an toàn {1, 2} → search chỉ trên đó, nước đúng là 2 (để lại 4)
    agent = MCTSAgent(iterations=1000, check_tactics=True, seed=0)
    assert agent.select_move(Pile(6)) == 2
    assert agent.stats["tactic"] == TACTIC_RESTRICT
    assert {r[0] for r in agent.last_root_stats()} == {1, 2}


def test_generic_game_without_tactics():
    for n, best in ((6, 2), (7, 3), (9, 1)):
        assert MCTSAgent(iterations=2000, seed=n).select_move(Pile(n)) == best


@pytest.mark.xfail(
    strict=False,
    reason="Ghi nhận (D-11, E6): MCTS thuần 1000 iter, rollout random không chặn được four trên "
    "15×15 — gốc ~100 con, mỗi con ~10 lượt thăm nên hiếm khi mở rộng tới ô thắng của đối thủ.",
)
def test_15x15_block_without_tactics_is_unreliable():
    for seed in range(3):
        g = setup15(*BLOCK15)
        assert MCTSAgent(iterations=1000, seed=seed).select_move(g) == p15((10, 9))


# ---------------------------------------------------- chọn nước cuối, stats


def test_final_move_max_n_and_max_wn():
    g = kinrow(3, 3, [4])
    a = MCTSAgent(iterations=300, final_move="max_n", seed=11)
    b = MCTSAgent(iterations=300, final_move="max_wn", seed=11)
    ma, mb = a.select_move(g), b.select_move(g)
    rows = a.last_root_stats()
    assert rows == b.last_root_stats()  # final_move không ảnh hưởng tới search
    assert ma == max(rows, key=lambda r: (r[2], r[1]))[0]
    assert mb == max(rows, key=lambda r: (r[3], r[2]))[0]
    assert [r[2] for r in rows] == sorted((r[2] for r in rows), reverse=True)
    assert all(r[3] == r[1] / r[2] for r in rows)


def test_stats_keys_and_value():
    agent = MCTSAgent(iterations=200, seed=1)
    move = agent.select_move(kinrow(3, 3, [0]))
    s = agent.stats
    for key in ("iterations", "nodes", "time", "value", "max_depth", "rollout_plies", "tactic"):
        assert key in s
    row = next(r for r in agent.last_root_stats() if r[0] == move)
    assert s["value"] == row[3]
    assert s["iterations"] == 200 and s["time"] > 0 and s["max_depth"] >= 1
    assert s["tactic"] == TACTIC_NONE


@pytest.mark.parametrize("tactics", [False, True])
def test_does_not_mutate_game(tactics):
    for g in (kinrow(3, 3, [4, 0]), setup15(*BLOCK15)):
        key, cands = g.key(), g.candidate_moves()
        MCTSAgent(iterations=30, check_tactics=tactics, seed=0).select_move(g)
        assert g.key() == key and g.candidate_moves() == cands and g.winner() is None


def test_heavy_rollout_policy():
    agent = MCTSAgent(iterations=300, rollout_policy="heavy", score_fn=move_score, seed=0)
    assert agent.select_move(kinrow(3, 3, [0, 3, 1, 4])) == 2
    g = setup15([(7, 7), (7, 8)], [(8, 7), (6, 6)])
    agent = MCTSAgent(
        iterations=30,
        rollout_policy="heavy",
        score_fn=move_score,
        rollout_limit=4,
        value_fn=sigmoid_value(evaluate, 200),
        seed=0,
    )
    assert agent.select_move(g) in g.candidate_moves()
    assert agent.stats["rollout_plies"] <= 4 * 30


# --------------------------------------------------------------- ngân sách


def test_iteration_budget_exact():
    agent = MCTSAgent(iterations=137, seed=0)
    agent.select_move(kinrow(3, 3, []))
    assert agent.stats["iterations"] == agent.root.N == 137
    assert sum(r[2] for r in agent.last_root_stats()) == 137
    assert agent.stats["nodes"] == sum(1 for _ in walk(agent.root))


def test_time_budget():
    g = setup15([(7, 7)], [(7, 8)])
    agent = MCTSAgent(iterations=None, time_limit=0.05, seed=0)
    agent.select_move(g)
    assert agent.stats["iterations"] >= 1
    assert 0.05 <= agent.stats["time"] < 0.25
    both = MCTSAgent(iterations=10**9, time_limit=0.03, seed=0)  # dừng theo thời gian
    both.select_move(g)
    assert both.stats["time"] < 0.25
    few = MCTSAgent(iterations=5, time_limit=10.0, seed=0)  # dừng theo iteration
    few.select_move(g)
    assert few.stats["iterations"] == 5
    tiny = MCTSAgent(iterations=None, time_limit=1e-9, seed=0)  # vẫn chạy ≥ 1 iteration
    assert tiny.select_move(g) in g.candidate_moves()
    assert tiny.stats["iterations"] >= 1


@pytest.mark.parametrize(
    "kwargs",
    [
        {"iterations": None, "time_limit": None},
        {"iterations": 0},
        {"time_limit": 0},
        {"c": -0.1},
        {"rollout_limit": -1},
        {"final_move": "max_w"},
        {"rollout_policy": "greedy"},
        {"rollout_policy": "heavy"},  # thiếu score_fn
    ],
)
def test_invalid_params(kwargs):
    with pytest.raises(ValueError):
        MCTSAgent(**kwargs)


def test_terminal_game_rejected():
    g = kinrow(3, 3, [0, 3, 1, 4, 2])
    with pytest.raises(AssertionError):
        MCTSAgent(iterations=10).select_move(g)


# ------------------------------------------------------------------- seed


def test_same_seed_same_move_and_stats():
    for g in (kinrow(3, 3, []), setup15([(7, 7), (7, 8)], [(8, 7), (6, 6)])):
        a, b = MCTSAgent(iterations=300, seed=7), MCTSAgent(iterations=300, seed=7)
        assert a.select_move(g) == b.select_move(g)
        assert a.last_root_stats() == b.last_root_stats()


def test_same_seed_same_game_sequence():
    def sequence():
        g, agent, moves = KInRow(15, 5), MCTSAgent(iterations=80, seed=21), []
        for _ in range(5):
            m = agent.select_move(g)
            g.play(m)
            moves.append(m)
        return moves

    assert sequence() == sequence()


def test_different_seeds_vary():
    g = setup15([(7, 7)], [])  # O đi: nhiều nước gần như bằng nhau
    moves = {MCTSAgent(iterations=150, seed=s).select_move(g) for s in range(8)}
    assert len(moves) >= 2


# --------------------------------------------------------------- đối đầu


def test_never_loses_to_random_3x3():
    for i in range(20):
        mcts, rnd = MCTSAgent(iterations=1000, seed=i), RandomAgent(seed=1000 + i)
        if i % 2 == 0:
            assert play_game(KInRow(3, 3), mcts, rnd) in (X, DRAW)
        else:
            assert play_game(KInRow(3, 3), rnd, mcts) in (O, DRAW)


@pytest.mark.slow
def test_beats_random_15x15():
    """~10 s: 300 iter thắng RandomAgent(candidate) ở cả hai lượt."""
    mcts, rnd = MCTSAgent(iterations=300, seed=0), RandomAgent(seed=100, use_candidates=True)
    assert play_game(KInRow(15, 5), mcts, rnd) == X
    mcts, rnd = MCTSAgent(iterations=300, seed=1), RandomAgent(seed=101, use_candidates=True)
    assert play_game(KInRow(15, 5), rnd, mcts) == O


@pytest.mark.slow
def test_never_loses_to_minimax_3x3():
    """Done P3: 20 ván vs Minimax hoàn hảo 3×3, đổi lượt, check_tactics=False, 1000 iter (~19 s)."""
    for i in range(20):
        mcts, mm = MCTSAgent(iterations=1000, check_tactics=False, seed=i), MinimaxAgent(seed=i)
        if i % 2 == 0:
            assert play_game(KInRow(3, 3), mcts, mm) in (X, DRAW), f"ván {i}"
        else:
            assert play_game(KInRow(3, 3), mm, mcts) in (O, DRAW), f"ván {i}"
