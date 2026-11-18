"""AlphaBetaAgent mở rộng P6.4: top_k, root_hook, tham số VCF trong spec (mặc định tắt = cũ)."""

import json
import math
import random

import pytest

from gameai.agents.alphabeta import AlphaBetaAgent
from gameai.agents.registry import AgentSpec, make_agent
from gameai.games.kinrow import KInRow
from gameai.heuristics.kinrow_eval import delta_eval, evaluate, move_score

FNS = {"eval_fn": evaluate, "delta_fn": delta_eval, "order_fn": move_score}


def mid_game(n: int, k: int, plies: int, seed: int) -> KInRow:
    rng = random.Random(seed)
    while True:
        g = KInRow(n, k)
        for _ in range(plies):
            g.play(rng.choice(g.candidate_moves()))
            if g.is_terminal():
                break
        if not g.is_terminal():
            return g


def test_new_params_off_is_identical_to_default():
    for seed in range(4):
        g = mid_game(15, 5, 10 + seed, seed)
        a = AlphaBetaAgent(depth=2, use_tt=True, **FNS)
        b = AlphaBetaAgent(depth=2, use_tt=True, top_k=None, root_hook=None, **FNS)
        ra, rb = a.search(g.clone()), b.search(g.clone())
        assert ra == rb and a.stats["nodes"] == b.stats["nodes"]


def test_top_k_validation():
    for bad in (0, -1, [], [3, 0], 2.5):
        with pytest.raises(ValueError):
            AlphaBetaAgent(depth=2, order_fn=move_score, top_k=bad)
    with pytest.raises(ValueError, match="order_fn"):
        AlphaBetaAgent(depth=2, top_k=5)
    AlphaBetaAgent(depth=2, order_fn=move_score, top_k=(8, 4))


def test_top_k_prunes_and_root_move_is_within_top_k():
    for seed in range(4):
        g = mid_game(15, 5, 12, seed)
        full = AlphaBetaAgent(depth=3, **FNS)
        k = AlphaBetaAgent(depth=3, top_k=(4, 3, 2), **FNS)
        full.search(g.clone())
        move, _ = k.search(g.clone())
        assert k.stats["nodes"] < full.stats["nodes"]
        ranked = sorted(g.candidate_moves(), key=lambda m: move_score(g, m), reverse=True)
        assert move in ranked[:4]
        assert move in g.legal_moves()


def test_top_k_int_equals_constant_tuple_and_large_k_equals_full():
    g = mid_game(15, 5, 12, 3)
    a = AlphaBetaAgent(depth=3, top_k=5, **FNS)
    b = AlphaBetaAgent(depth=3, top_k=(5, 5, 5), **FNS)
    assert a.search(g.clone()) == b.search(g.clone())
    big = AlphaBetaAgent(depth=3, top_k=10_000, **FNS)
    full = AlphaBetaAgent(depth=3, **FNS)
    assert big.search(g.clone()) == full.search(g.clone())
    assert big.stats["nodes"] == full.stats["nodes"]


def test_top_k_with_tt_runs_and_returns_legal_move():
    g = mid_game(15, 5, 14, 5)
    a = AlphaBetaAgent(depth=3, use_tt=True, top_k=(6, 4), **FNS)
    move, value = a.search(g)
    assert move in g.legal_moves() and math.isfinite(value)


def test_root_hook_forced_move_skips_search():
    g = mid_game(15, 5, 10, 1)
    target = g.candidate_moves()[0]
    a = AlphaBetaAgent(depth=3, root_hook=lambda game: (target, None), **FNS)
    move, value = a.search(g)
    assert move == target and math.isnan(value)
    assert a.stats["nodes"] == 1 and a.stats["root_hook"] == 1
    assert a.select_move(g) == target


def test_root_hook_restricts_root_moves():
    g = mid_game(15, 5, 10, 2)
    allowed = sorted(g.candidate_moves())[3:6]
    a = AlphaBetaAgent(depth=2, root_hook=lambda game: (None, list(allowed)), **FNS)
    move, _ = a.search(g)
    assert move in allowed
    # tập hook không giao với ứng viên → dùng nguyên tập hook
    far = [g.legal_moves()[-1]]
    assert far[0] not in g.candidate_moves()
    b = AlphaBetaAgent(depth=1, root_hook=lambda game: (None, far), **FNS)
    assert b.search(g)[0] == far[0]


def test_root_hook_noop_equals_default():
    g = mid_game(15, 5, 11, 4)
    a = AlphaBetaAgent(depth=2, **FNS)
    b = AlphaBetaAgent(depth=2, root_hook=lambda game: (None, None), **FNS)
    assert a.search(g.clone()) == b.search(g.clone())
    assert a.stats["nodes"] == b.stats["nodes"]


def test_registry_builds_vcf_hook_from_spec():
    p = {"depth": 2, "eval": "evaluate", "delta": "delta_eval", "order": "move_score",
         "top_k": [6, 4], "vcf_depth": 8, "vcf_time": 0.3}  # fmt: skip
    spec = AgentSpec("alphabeta", p, label="x")
    json.dumps(spec.to_dict())
    hash(spec.name)
    agent = make_agent(spec, 0)
    assert isinstance(agent, AlphaBetaAgent) and agent.root_hook is not None
    g = mid_game(15, 5, 12, 6)
    assert agent.select_move(g) in g.legal_moves()


def test_registry_vcf_params_validation_and_default_off():
    with pytest.raises(ValueError, match="vcf_time"):
        make_agent(AgentSpec("alphabeta", {"depth": 2, "vcf_depth": 8}), 0)
    with pytest.raises(ValueError, match="vcf_depth"):
        make_agent(AgentSpec("alphabeta", {"depth": 2, "vcf_time": 0.3}), 0)
    assert make_agent(AgentSpec("alphabeta", {"depth": 2}), 0).root_hook is None


def test_vcf_hook_wins_by_vcf_in_alphabeta():
    """Có VCF ở gốc → AB đi đúng nước VCF mà không tìm (depth 1 cũng thắng)."""
    from tests.test_kinrow_vcf import CHAIN_O, CHAIN_X, build, rc  # noqa: PLC0415

    g = build(CHAIN_X, CHAIN_O)
    spec = AgentSpec("alphabeta", {"depth": 1, "eval": "evaluate", "vcf_depth": 8, "vcf_time": 5.0})
    agent = make_agent(spec, 0)
    assert agent.select_move(g) == rc(7, 6)
    assert agent.stats["root_hook"] == 1
