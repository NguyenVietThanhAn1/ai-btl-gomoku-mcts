"""Test arena.py + agents/registry.py (P4.1, D-13)."""

from __future__ import annotations

import random

import pytest

from gameai.agents.alphabeta import AlphaBetaAgent
from gameai.agents.greedy import GreedyAgent
from gameai.agents.mcts import MCTSAgent
from gameai.agents.minimax import MinimaxAgent
from gameai.agents.random_agent import RandomAgent
from gameai.agents.registry import AgentSpec, GameSpec, make_agent, make_game
from gameai.arena import (
    derive_seed,
    play_game,
    play_match,
    play_seeded_game,
    random_opening_moves,
)
from gameai.core.game import DRAW, P1, P2
from gameai.games.kinrow import KInRow
from gameai.heuristics.kinrow_rollout import KInRowHeavyRollout

G3 = GameSpec("kinrow", {"n": 3, "k": 3})
G15 = GameSpec("kinrow", {"n": 15, "k": 5})
MCTS50 = AgentSpec("mcts", {"iterations": 50}, label="mcts50")
GREEDY = AgentSpec("greedy", label="greedy")
RANDOM = AgentSpec("random", label="random")


# ---------------------------------------------------------------- registry


def test_make_game_kinrow():
    g = make_game(G15)
    assert isinstance(g, KInRow) and (g.n, g.k) == (15, 5)


def test_make_agent_kinds():
    assert isinstance(make_agent(RANDOM, 1), RandomAgent)
    assert isinstance(make_agent(GREEDY, 1), GreedyAgent)
    assert isinstance(make_agent(AgentSpec("minimax", {"depth": None}), 1), MinimaxAgent)
    ab = make_agent(
        AgentSpec(
            "alphabeta",
            {"depth": 2, "eval": "evaluate", "delta": "delta_eval", "order": "move_score"},
        ),
        1,
    )
    assert isinstance(ab, AlphaBetaAgent)
    m = make_agent(
        AgentSpec(
            "mcts",
            {
                "time_limit": 0.1,
                "iterations": None,
                "rollout": "heavy_kinrow",
                "temperature": 300,
                "rollout_limit": 10,
                "value_scale": 500,
            },
        ),
        1,
    )
    assert isinstance(m, MCTSAgent)


def test_make_agent_heavy_kinrow_policy_object():
    m = make_agent(
        AgentSpec("mcts", {"iterations": 5, "rollout": "heavy_kinrow", "temperature": 300}), 1
    )
    assert isinstance(m.policy, KInRowHeavyRollout)
    assert m.policy.temperature == 300


def test_make_agent_fresh_objects():
    a, b = make_agent(MCTS50, 3), make_agent(MCTS50, 3)
    assert a is not b


def test_make_agent_seed_controls_choice():
    g = make_game(G15)
    g.play(112)  # sau nước giữa bàn, mọi candidate của O cùng điểm (greedy.md)
    moves = {make_agent(GREEDY, s).select_move(g) for s in range(10)}
    assert len(moves) > 1  # nhiều nước bằng điểm → seed khác cho nước khác
    assert make_agent(GREEDY, 4).select_move(g) == make_agent(GREEDY, 4).select_move(g)


def test_make_agent_unseeded_option():
    assert make_agent(AgentSpec("minimax", {"seeded": False}), 123).rng is None
    assert make_agent(AgentSpec("minimax"), 123).rng is not None


def test_make_agent_dotted_path():
    import arena_helpers

    a = make_agent(AgentSpec("arena_helpers:IllegalAgent"), 0)
    assert isinstance(a, arena_helpers.IllegalAgent)


@pytest.mark.parametrize(
    "spec",
    [
        AgentSpec("nope"),
        AgentSpec("greedy", {"score": "no_such_fn"}),
        AgentSpec("mcts", {"bogus": 1}),
        AgentSpec("mcts", {"rollout": "weird"}),
    ],
)
def test_make_agent_bad_config_raises(spec):
    with pytest.raises((ValueError, TypeError)):
        make_agent(spec, 0)


def test_spec_requires_json_params():
    with pytest.raises(TypeError):
        AgentSpec("mcts", {"value_fn": lambda g: 0.5}).to_dict()


def test_spec_name_and_dict():
    assert MCTS50.name == "mcts50"
    assert AgentSpec("greedy").name == "greedy"
    d = MCTS50.to_dict()
    assert d == {"kind": "mcts", "params": {"iterations": 50}, "label": "mcts50"}


# ---------------------------------------------------------------- seeds / opening


def test_derive_seed_deterministic_and_distinct():
    assert derive_seed(3, "A") == derive_seed(3, "A")
    assert len({derive_seed(s, t) for s in range(5) for t in ("A", "B", "opening")}) == 15


def test_random_opening_deterministic_near_center_not_terminal():
    seqs = []
    for s in range(6):
        g = KInRow(15, 5)
        ms = random_opening_moves(g, 4, random.Random(s))
        assert len(ms) == 4 and list(g.move_history) == ms
        assert not g.is_terminal()
        g2 = KInRow(15, 5)
        assert random_opening_moves(g2, 4, random.Random(s)) == ms
        assert ms[0] == 7 * 15 + 7  # bàn trống: candidate duy nhất là tâm
        for m in ms:
            r, c = divmod(m, 15)
            assert abs(r - 7) <= 6 and abs(c - 7) <= 6
        seqs.append(tuple(ms))
    assert len(set(seqs)) > 1


def test_random_opening_never_terminal_3x3():
    for s in range(50):
        g = KInRow(3, 3)
        random_opening_moves(g, 5, random.Random(s))
        assert not g.is_terminal()


def test_random_opening_zero():
    g = KInRow(3, 3)
    assert random_opening_moves(g, 0, random.Random(0)) == []


# ---------------------------------------------------------------- play_game


def test_play_game_normal_3x3():
    rec = play_game(KInRow(3, 3), MinimaxAgent(), MinimaxAgent())
    assert rec.winner == DRAW and rec.termination == "normal" and rec.error == ""
    assert rec.n_moves == 9
    assert [m.player for m in rec.moves] == [P1, P2] * 4 + [P1]
    assert all(m.time >= 0 for m in rec.moves)
    assert all("nodes" in m.stats for m in rec.moves)
    assert len(set(rec.move_sequence)) == 9


def test_play_game_winner_recorded():
    rec = play_game(KInRow(3, 3), MinimaxAgent(), RandomAgent(seed=1))
    assert rec.winner in (P1, DRAW)
    g = KInRow(3, 3)
    for m in rec.move_sequence:
        g.play(m)
    assert g.winner() == rec.winner


def test_play_game_stats_are_copies():
    rec = play_game(KInRow(3, 3), MCTSAgent(iterations=20, seed=1), RandomAgent(seed=1))
    s0 = rec.moves[0].stats
    assert s0["iterations"] == 20
    assert rec.moves[0].stats is not rec.moves[2].stats


def test_play_game_max_moves_draw():
    rec = play_game(KInRow(3, 3), RandomAgent(seed=1), RandomAgent(seed=2), max_moves=2)
    assert rec.winner == DRAW and rec.termination == "max_moves" and rec.n_moves == 2


def test_play_game_exception_loses():
    import arena_helpers

    rec = play_game(KInRow(3, 3), RandomAgent(seed=0), arena_helpers.RaisingAgent(fail_at=1))
    assert rec.termination == "exception" and rec.winner == P1 and rec.error_player == P2
    assert "RuntimeError" in rec.error and "boom" in rec.error and "\n" not in rec.error
    assert rec.moves[-1].move is None


def test_play_game_illegal_move_loses():
    import arena_helpers

    rec = play_game(KInRow(3, 3), arena_helpers.IllegalAgent(), RandomAgent(seed=0))
    assert rec.termination == "illegal_move" and rec.winner == P2 and rec.error_player == P1
    assert rec.n_moves == 1 and rec.moves[0].move == -1 and rec.moves[0].stats["nodes"] == 7


def test_play_game_mutation_loses():
    import arena_helpers

    rec = play_game(KInRow(3, 3), RandomAgent(seed=0), arena_helpers.MutatingAgent())
    assert rec.termination == "mutated_game" and rec.winner == P1 and rec.error_player == P2


def test_play_game_from_opening_position():
    g = KInRow(3, 3)
    g.play(4)  # O đi trước trong phần do agent chơi
    rec = play_game(g, MinimaxAgent(), MinimaxAgent(), opening=(4,))
    assert rec.opening == (4,)
    assert rec.moves[0].player == P2 and rec.winner == DRAW
    assert rec.n_moves == 8


# ---------------------------------------------------------------- seeded game / match


def test_play_seeded_game_ids_and_seeds():
    mg = play_seeded_game(G3, MCTS50, GREEDY, pair_seed=5, a_is_x=True)
    assert mg.game_id == "5-AX" and mg.seed_a == derive_seed(5, "A")
    assert mg.seed_b == derive_seed(5, "B")
    assert mg.record.moves[0].player == P1
    mg2 = play_seeded_game(G3, MCTS50, GREEDY, pair_seed=5, a_is_x=False)
    assert mg2.game_id == "5-BX" and (mg2.seed_a, mg2.seed_b) == (mg.seed_a, mg.seed_b)


def test_side_mapping_and_result_a():
    for a_is_x in (True, False):
        mg = play_seeded_game(G3, AgentSpec("minimax"), RANDOM, pair_seed=1, a_is_x=a_is_x)
        a_player = P1 if a_is_x else P2
        for m in mg.record.moves:
            assert m.side == ("A" if m.player == a_player else "B")
        w = mg.record.winner
        expect = 0.5 if w == DRAW else (1.0 if w == a_player else 0.0)
        assert mg.result_a == expect
        assert mg.result_a >= 0.5  # minimax hoàn hảo không thua random


def test_play_seeded_game_deterministic_iteration_budget():
    a = play_seeded_game(G3, MCTS50, GREEDY, pair_seed=2, a_is_x=False)
    b = play_seeded_game(G3, MCTS50, GREEDY, pair_seed=2, a_is_x=False)
    assert a.record.move_sequence == b.record.move_sequence
    assert a.record.winner == b.record.winner
    assert [m.stats["nodes"] for m in a.record.moves] == [m.stats["nodes"] for m in b.record.moves]


def test_play_seeded_game_fresh_agents_each_game():
    # nếu agent bị dùng lại giữa các ván, rng đã tiêu thụ → ván thứ hai khác ván đơn lẻ
    first = play_seeded_game(G3, MCTS50, MCTS50, pair_seed=9, a_is_x=True)
    play_seeded_game(G3, MCTS50, MCTS50, pair_seed=8, a_is_x=True)
    again = play_seeded_game(G3, MCTS50, MCTS50, pair_seed=9, a_is_x=True)
    assert first.record.move_sequence == again.record.move_sequence


def test_play_seeded_game_random_opening():
    a = play_seeded_game(
        G15, GREEDY, GREEDY, pair_seed=3, a_is_x=True, random_opening=3, max_moves=4
    )
    b = play_seeded_game(
        G15, GREEDY, GREEDY, pair_seed=3, a_is_x=False, random_opening=3, max_moves=4
    )
    assert len(a.record.opening) == 3 and a.record.opening == b.record.opening
    others = {
        play_seeded_game(
            G15, GREEDY, GREEDY, pair_seed=s, a_is_x=True, random_opening=3, max_moves=1
        ).record.opening
        for s in range(6)
    }
    assert len(others) > 1
    # sau 3 quân, O đi; A cầm X nên nước đầu do B đi
    assert a.record.moves[0].player == P2 and a.record.moves[0].side == "B"


def test_play_seeded_game_build_error_propagates():
    with pytest.raises(ValueError, match="bad config"):
        play_seeded_game(G3, AgentSpec("arena_helpers:BrokenInitAgent"), RANDOM, 0, True)


def test_play_match_swaps_and_seeds():
    games = play_match(G3, MCTS50, GREEDY, n_pairs=3, base_seed=10)
    assert [g.game_id for g in games] == ["10-AX", "10-BX", "11-AX", "11-BX", "12-AX", "12-BX"]
    assert [g.a_is_x for g in games] == [True, False] * 3
    again = play_match(G3, MCTS50, GREEDY, n_pairs=3, base_seed=10)
    assert [g.record.move_sequence for g in games] == [g.record.move_sequence for g in again]


def test_each_agent_uses_its_own_seed():
    # Greedy cầm O sau nước giữa bàn: mọi candidate cùng điểm → nước đi phụ thuộc seed
    for s in range(5):
        for a_is_x in (True, False):
            mg = play_seeded_game(G15, GREEDY, GREEDY, pair_seed=s, a_is_x=a_is_x, max_moves=2)
            g = make_game(G15)
            g.play(mg.record.moves[0].move)
            o_seed = mg.seed_b if a_is_x else mg.seed_a
            assert mg.record.moves[1].move == make_agent(GREEDY, o_seed).select_move(g)
