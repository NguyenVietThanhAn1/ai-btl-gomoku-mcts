import pytest

from gameai.agents.base import Agent
from gameai.agents.random_agent import RandomAgent
from gameai.games.kinrow import KInRow


def play_game(game, agents):
    while not game.is_terminal():
        agent = agents[0] if game.current_player() == 1 else agents[1]
        game.play(agent.select_move(game))
    return game.winner()


def test_agent_is_abstract():
    with pytest.raises(TypeError):
        Agent()  # type: ignore[abstract]


def test_stats_is_dict_and_name():
    a = RandomAgent(seed=0)
    assert a.stats == {}
    assert a.name == "RandomAgent"


def test_move_is_legal_and_game_unchanged():
    g = KInRow(3, 3)
    g.play(4)
    before = g.key()
    a = RandomAgent(seed=1)
    for _ in range(50):
        assert a.select_move(g) in g.legal_moves()
    assert g.key() == before


def test_same_seed_same_moves():
    g = KInRow(15, 5)
    m1 = [RandomAgent(seed=7).select_move(g) for _ in range(3)]
    a, b = RandomAgent(seed=42), RandomAgent(seed=42)
    assert [a.select_move(g) for _ in range(20)] == [b.select_move(g) for _ in range(20)]
    assert len(set(m1)) == 1  # mỗi agent mới cùng seed -> cùng nước đầu


def test_does_not_use_global_random():
    import random

    g = KInRow(15, 5)
    random.seed(1)
    a = RandomAgent(seed=3).select_move(g)
    random.seed(2)
    b = RandomAgent(seed=3).select_move(g)
    assert a == b


def test_use_candidates_subset():
    g = KInRow(15, 5)
    g.play(112)
    a = RandomAgent(seed=0, use_candidates=True)
    cands = set(g.candidate_moves())
    assert all(a.select_move(g) in cands for _ in range(50))


def test_full_game_terminates_3x3():
    for s in range(20):
        g = KInRow(3, 3)
        w = play_game(g, (RandomAgent(seed=s), RandomAgent(seed=s + 100)))
        assert w in (1, -1, 0)


def test_full_game_terminates_15x15():
    g = KInRow(15, 5)
    assert play_game(g, (RandomAgent(seed=1), RandomAgent(seed=2))) in (1, -1, 0)


def test_terminal_raises():
    g = KInRow(3, 3)
    for m in (0, 3, 1, 4, 2):
        g.play(m)
    assert g.is_terminal()
    with pytest.raises(AssertionError):
        RandomAgent(seed=0).select_move(g)
