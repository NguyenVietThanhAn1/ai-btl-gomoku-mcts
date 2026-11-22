"""MCTS cờ tướng (P8.3, D-24): cắt rollout + eval, tactics, tất định, time_limit, trận nhanh."""

import pytest

from gameai.agents.registry import AgentSpec, make_agent
from gameai.experiments.p82_ab_check import GREEDY, RANDOM, run_match
from gameai.experiments.p83_mcts_check import XQ_MCTS_L, XQ_MCTS_SCALE, xq_mcts_spec
from gameai.games.xiangqi import RED, Xiangqi, move_to_iccs

MATE1 = "4k4/R8/9/9/9/9/9/9/9/3K3R1 w - - 0 1"
FREE_ROOK = "3k5/9/9/9/r8/9/9/9/9/R3K4 w - - 0 1"
SINGLE_ESCAPE = "5k3/9/9/9/4r4/9/9/9/4K4/9 w - - 0 1"
ITERS = 300


def mcts(seed=1, iterations=ITERS, tactics=True, time_limit=None, **kw):
    return make_agent(
        xq_mcts_spec(time_limit=time_limit, iterations=iterations, tactics=tactics, **kw), seed
    )


def mates_of(g):
    out = []
    for m in g.legal_moves():
        g.play(m)
        if g.winner() == RED:
            out.append(m)
        g.undo()
    return out


def test_spec_uses_registry_defaults():
    assert XQ_MCTS_L == 10 and XQ_MCTS_SCALE == 2000.0
    a = mcts(iterations=5)
    assert a.rollout_limit == XQ_MCTS_L


def test_mate_in_one_with_tactics():
    g = Xiangqi(MATE1)
    mates = mates_of(g)
    assert mates
    for seed in range(5):
        a = mcts(seed=seed)
        assert a.select_move(g) in mates
        assert a.stats["tactic"] == 1 and a.stats["iterations"] == 0


def test_mate_in_one_without_tactics_rate_recorded():
    """Tắt tactics: không đòi đúng; chỉ ghi tỉ lệ (số đo ở D-24)."""
    g = Xiangqi(MATE1)
    mates = set(mates_of(g))
    hit = sum(mcts(seed=s, tactics=False).select_move(g) in mates for s in range(10))
    print(f"mate-in-1, tactics off, {ITERS} iter: {hit}/10")
    assert 0 <= hit <= 10


def test_takes_free_rook():
    g = Xiangqi(FREE_ROOK)
    for seed in range(5):
        assert move_to_iccs(mcts(seed=seed, iterations=1000).select_move(g)) == "a0a5"


def test_in_check_returns_only_legal_move():
    g = Xiangqi(SINGLE_ESCAPE)
    assert g.in_check()
    legal = g.legal_moves()
    for tactics in (True, False):
        m = mcts(tactics=tactics, iterations=50).select_move(g)
        assert m in legal and move_to_iccs(m) == "e1d1"


def test_in_check_move_always_legal_midgame():
    g = Xiangqi("3k5/9/9/9/R3r4/9/9/9/9/4K4 w - - 0 1")
    assert g.in_check()
    m = mcts(iterations=100).select_move(g)
    assert m in g.legal_moves()


def test_deterministic_given_seed_and_iterations():
    g = Xiangqi(FREE_ROOK)
    a, b = mcts(seed=7, iterations=200), mcts(seed=7, iterations=200)
    assert a.select_move(g) == b.select_move(g)
    assert a.last_root_stats() == b.last_root_stats()


def test_does_not_mutate_game():
    g = Xiangqi(FREE_ROOK)
    fen = g.to_fen()
    mcts(iterations=100).select_move(g)
    assert g.to_fen() == fen


def test_time_limit_respected_and_stats():
    g = Xiangqi(FREE_ROOK)
    a = make_agent(xq_mcts_spec(time_limit=0.2, tactics=False), 1)
    a.select_move(g)
    assert a.stats["iterations"] >= 1
    assert 0.2 <= a.stats["time"] < 0.6
    assert a.stats["rollout_plies"] > 0


def test_spec_id_distinguishes_params():
    s1, s2 = xq_mcts_spec(rollout_limit=0), xq_mcts_spec(rollout_limit=10)
    assert isinstance(s1, AgentSpec) and s1.params != s2.params


@pytest.mark.slow
def test_quick_match_vs_random_and_greedy():
    """5 khai cuộc × 2 bên, 300 iteration cố định, khai cuộc ngẫu nhiên có seed."""
    a = xq_mcts_spec(time_limit=None, iterations=300, tactics=True, label="mcts")
    for opp in (RANDOM, GREEDY):
        res = run_match(a, opp, n_pairs=5, base_seed=900, max_plies=200)
        print(opp.label, res["W"], res["D"], res["L"], res["score"])
        assert res["errors"] == 0
        assert (
            res["score"] >= 0.9
        )  # đo 1 lần (2026-11-23): 10/0/0 vs cả hai; ngưỡng chốt, không chỉnh
