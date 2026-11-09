"""KInRowHeavyRollout phải tương đương HeavyRollout(move_score, T): cùng điểm, cùng chuỗi nước."""

import random

import pytest

from gameai.agents.mcts import MCTSAgent
from gameai.agents.rollout import HeavyRollout
from gameai.games.kinrow import KInRow
from gameai.heuristics.kinrow_eval import move_score
from gameai.heuristics.kinrow_rollout import KInRowHeavyRollout


def random_start(n: int, k: int, n_moves: int, seed: int) -> KInRow:
    """Khai cuộc ngẫu nhiên (trên candidate); dừng sớm nếu ván kết thúc trước khi đủ nước."""
    g = KInRow(n, k)
    r = random.Random(seed)
    for _ in range(n_moves):
        if g.is_terminal():
            break
        g.play(r.choice(g.candidate_moves()))
    return g


def reference_scores(g: KInRow) -> list[int]:
    return [move_score(g, m) for m in g.candidate_moves()]


def rollout(policy, g: KInRow, rng: random.Random) -> list[int]:
    seq = []
    while not g.is_terminal():
        m = policy(g, rng)
        seq.append(m)
        g.play(m)
    return seq


def setup15(xs, os_):
    g = KInRow(15, 5)
    for i in range(max(len(xs), len(os_))):
        if i < len(xs):
            g.play(xs[i][0] * 15 + xs[i][1])
        if i < len(os_):
            g.play(os_[i][0] * 15 + os_[i][1])
    return g


# X có four (7,5..8), (7,4) bị O chặn; các nước sau đó ở xa → đe dọa KHÔNG nằm quanh 2 nước cuối.
FAR_X = [(7, 5), (7, 6), (7, 7), (7, 8), (2, 2), (2, 12)]
FAR_O = [(7, 4), (12, 2), (12, 12), (0, 14), (14, 0), (13, 7)]
WIN_FAR = (FAR_X, FAR_O)  # X đi, thắng ở (7, 9)
BLOCK_FAR = ([*FAR_X, (1, 1)], FAR_O)  # O đi, phải chặn ở (7, 9)

BOARDS = [(15, 5), (7, 4), (5, 4), (3, 3)]


# ------------------------------------------------- điểm từng bước = move_score


@pytest.mark.parametrize("n, k", BOARDS)
def test_scores_equal_move_score_at_every_step(n, k):
    pol = KInRowHeavyRollout(100.0)
    for seed in range(8):
        g = random_start(n, k, seed % 5 + (0 if n == 3 else 2), seed)
        rng = random.Random(seed)
        steps = 0
        while not g.is_terminal():
            assert pol.move_scores(g) == reference_scores(g)
            g.play(pol(g, rng))
            steps += 1
        assert steps >= 0


def test_scores_cover_last_empty_cell_draw_case():
    """Nước lấp ô trống cuối mà không thắng: move_score dùng −evaluate → phải khớp."""
    g = KInRow(3, 3)
    for m in [0, 1, 2, 4, 3, 5, 7, 6]:  # X O X / X O O / O X . → còn ô 8
        g.play(m)
    assert not g.is_terminal() and g.candidate_moves() == [8]
    assert KInRowHeavyRollout().move_scores(g) == reference_scores(g)


@pytest.mark.parametrize("pos, move", [(WIN_FAR, (7, 9)), (BLOCK_FAR, (7, 9))])
def test_threat_far_from_last_moves(pos, move):
    g = setup15(*pos)
    pol = KInRowHeavyRollout(100.0)
    assert pol.move_scores(g) == reference_scores(g)
    rng = random.Random(3)
    assert all(pol(g, rng) == move[0] * 15 + move[1] for _ in range(20))


# ------------------------------------------------- cùng seed → cùng chuỗi nước


@pytest.mark.parametrize("n, k", BOARDS)
@pytest.mark.parametrize("temperature", [1.0, 100.0, 1000.0])
def test_identical_rollouts_to_reference(n, k, temperature):
    ref = HeavyRollout(move_score, temperature)
    fast = KInRowHeavyRollout(temperature)
    for seed in range(6):
        start = random_start(n, k, seed % 4 + (0 if n == 3 else 4), seed)
        a = rollout(ref, start.clone(), random.Random(100 + seed))
        b = rollout(fast, start.clone(), random.Random(100 + seed))
        assert a == b


@pytest.mark.parametrize("pos", [WIN_FAR, BLOCK_FAR])
def test_identical_rollouts_from_threat_positions(pos):
    for seed in range(5):
        a = rollout(HeavyRollout(move_score, 300.0), setup15(*pos), random.Random(seed))
        b = rollout(KInRowHeavyRollout(300.0), setup15(*pos), random.Random(seed))
        assert a == b


# ------------------------------------------------- đồng bộ trạng thái nội bộ


def test_resync_across_games_undo_and_clone():
    pol = KInRowHeavyRollout()
    rng = random.Random(0)
    a = random_start(15, 5, 8, 1)
    b = random_start(15, 5, 12, 2)
    for _ in range(3):
        a.play(pol(a, rng))
    assert pol.move_scores(b) == reference_scores(b)  # ván khác
    assert pol.move_scores(a) == reference_scores(a)  # quay lại ván cũ
    a.undo()
    a.undo()
    assert pol.move_scores(a) == reference_scores(a)  # undo (lịch sử ngắn hơn)
    undone = a.move_history[-1]
    a.undo()
    a.play(next(m for m in a.candidate_moves() if m != undone))
    assert pol.move_scores(a) == reference_scores(a)  # undo rồi đi nước khác, cùng độ dài
    c = a.clone()
    c.play(c.candidate_moves()[0])
    assert pol.move_scores(c) == reference_scores(c)  # clone
    assert pol.move_scores(a) == reference_scores(a)
    pol.move_scores(a)  # gọi lại không đổi gì
    assert pol.move_scores(a) == reference_scores(a)


def test_does_not_mutate_game():
    g = random_start(15, 5, 10, 4)
    before = (bytes(g.board), g.move_history, g.current_player(), g.candidate_moves())
    KInRowHeavyRollout()(g, random.Random(1))
    assert (bytes(g.board), g.move_history, g.current_player(), g.candidate_moves()) == before


def test_invalid_temperature_and_name():
    with pytest.raises(ValueError):
        KInRowHeavyRollout(0.0)
    with pytest.raises(ValueError):
        KInRowHeavyRollout(-1.0)
    assert KInRowHeavyRollout().temperature == 100.0
    assert KInRowHeavyRollout.name == "heavy_kinrow"


# ------------------------------------------------- trong MCTS: cùng cây với bản chuẩn


@pytest.mark.parametrize(
    "start, iterations, limit",
    [
        ((3, 3, 2, 7), 400, None),
        ((15, 5, 8, 3), 120, None),
        ((15, 5, 12, 5), 150, 10),
    ],
)
def test_mcts_same_tree_as_reference(start, iterations, limit):
    n, k, n_moves, seed = start
    g = random_start(n, k, n_moves, seed)
    results = []
    for pol in (HeavyRollout(move_score, 100.0), KInRowHeavyRollout(100.0)):
        agent = MCTSAgent(iterations=iterations, rollout_policy=pol, rollout_limit=limit, seed=11)
        move = agent.select_move(g)
        stats = {key: v for key, v in agent.stats.items() if key != "time"}
        results.append((move, agent.last_root_stats(), stats))
    assert results[0] == results[1]
