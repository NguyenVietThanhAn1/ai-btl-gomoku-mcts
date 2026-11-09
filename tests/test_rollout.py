import math
import random

import pytest

from gameai.agents.rollout import (
    HeavyRollout,
    RandomRollout,
    make_policy,
    sigmoid_value,
)
from gameai.core.game import P1
from gameai.games.kinrow import KInRow
from gameai.heuristics.kinrow_eval import move_score

N = 15


def pos(rc):
    return rc[0] * N + rc[1]


def setup(xs, os_):
    g = KInRow(N, 5)
    for a, b in zip(xs, os_, strict=True):
        g.play(pos(a))
        g.play(pos(b))
    return g


# X thắng ở (7, 9)
WIN_POS = ([(7, 5), (7, 6), (7, 7), (7, 8)], [(7, 4), (10, 5), (10, 6), (10, 7)])
# X phải chặn ở (10, 9)
BLOCK_POS = ([(10, 4), (7, 6), (7, 7), (7, 8)], [(10, 5), (10, 6), (10, 7), (10, 8)])


def test_random_rollout_returns_candidate_and_is_reproducible():
    g = setup([(7, 7), (6, 8)], [(7, 8), (8, 8)])
    cands = set(g.candidate_moves())
    pol = RandomRollout()
    a = [pol(g, random.Random(5)) for _ in range(3)]
    r1, r2 = random.Random(9), random.Random(9)
    seq1 = [pol(g, r1) for _ in range(20)]
    seq2 = [pol(g, r2) for _ in range(20)]
    assert all(m in cands for m in a + seq1)
    assert seq1 == seq2


def test_heavy_takes_immediate_win():
    g = setup(*WIN_POS)
    pol = HeavyRollout(move_score)
    rng = random.Random(0)
    assert all(pol(g, rng) == pos((7, 9)) for _ in range(30))


def test_heavy_blocks_four():
    g = setup(*BLOCK_POS)
    pol = HeavyRollout(move_score)
    rng = random.Random(1)
    assert all(pol(g, rng) == pos((10, 9)) for _ in range(30))


def test_heavy_temperature_controls_spread():
    g = setup([(7, 7), (6, 8)], [(7, 8), (8, 8)])
    scores = {m: move_score(g, m) for m in g.candidate_moves()}
    top = max(scores.values())
    argmax = {m for m, s in scores.items() if s == top}
    rng = random.Random(2)
    cold = HeavyRollout(move_score, temperature=1e-3)
    assert all(cold(g, rng) in argmax for _ in range(100))
    hot = HeavyRollout(move_score, temperature=1e12)  # ~ đều
    assert len({hot(g, rng) for _ in range(300)}) > 20


def test_heavy_invalid_temperature():
    with pytest.raises(ValueError):
        HeavyRollout(move_score, temperature=0)


def test_make_policy():
    assert isinstance(make_policy("random"), RandomRollout)
    heavy = make_policy("heavy", move_score)
    assert isinstance(heavy, HeavyRollout) and heavy.score_fn is move_score
    custom = RandomRollout()
    assert make_policy(custom) is custom
    with pytest.raises(ValueError):
        make_policy("heavy")
    with pytest.raises(ValueError):
        make_policy("greedy")


def test_sigmoid_value():
    seen = []

    def fake_eval(value):
        def f(game, player):
            seen.append(player)
            return value

        return f

    g = KInRow(3, 3)
    assert sigmoid_value(fake_eval(0), 100)(g) == 0.5
    hi = sigmoid_value(fake_eval(1e12), 100)(g)
    lo = sigmoid_value(fake_eval(-1e12), 100)(g)  # không tràn số
    assert hi == pytest.approx(1.0) and lo == pytest.approx(0.0)
    a = sigmoid_value(fake_eval(150), 100)(g)
    b = sigmoid_value(fake_eval(-150), 100)(g)
    assert a + b == pytest.approx(1.0)
    assert a == pytest.approx(1 / (1 + math.exp(-1.5)))
    assert set(seen) == {P1}  # luôn lượng giá theo góc nhìn P1
    with pytest.raises(ValueError):
        sigmoid_value(fake_eval(0), 0)
