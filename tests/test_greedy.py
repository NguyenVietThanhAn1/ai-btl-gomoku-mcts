import pytest

from gameai.agents.greedy import GreedyAgent
from gameai.agents.random_agent import RandomAgent
from gameai.games.kinrow import KInRow, O, X
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


def play_game(game, agents):
    while not game.is_terminal():
        agent = agents[0] if game.current_player() == X else agents[1]
        game.play(agent.select_move(game))
    return game.winner()


def test_takes_immediate_win():
    xs = [(7, 5), (7, 6), (7, 7), (7, 8)]
    os_ = [(7, 4), (10, 5), (10, 6), (10, 7)]  # O có open-three, X có four chặn trái
    g = setup(xs, os_)
    assert GreedyAgent(move_score, seed=0).select_move(g) == pos((7, 9))


def test_blocks_four_over_attacking():
    xs = [(10, 4), (7, 6), (7, 7), (7, 8)]  # X có open-three (tạo open-four là mồi)
    os_ = [(10, 5), (10, 6), (10, 7), (10, 8)]  # O có four, đầu trái bị chặn
    g = setup(xs, os_)
    assert GreedyAgent(move_score, seed=0).select_move(g) == pos((10, 9))


def test_choice_is_argmax_and_stats():
    g = setup([(7, 7), (6, 8)], [(7, 8), (8, 8)])
    agent = GreedyAgent(move_score, seed=3)
    move = agent.select_move(g)
    cands = g.candidate_moves()
    best = max(move_score(g, m) for m in cands)
    assert move_score(g, move) == best
    assert agent.stats["nodes"] == len(cands)
    assert agent.stats["value"] == best
    assert agent.stats["iterations"] == 0
    assert agent.stats["time"] >= 0


def best_set(g):
    scores = {m: move_score(g, m) for m in g.candidate_moves()}
    top = max(scores.values())
    return {m for m, s in scores.items() if s == top}


def test_tie_break_random_but_reproducible():
    g = KInRow(N, 5)
    g.play(pos((7, 7)))  # bàn đối xứng → nhiều nước bằng điểm cho O
    ties = best_set(g)
    assert len(ties) > 1
    picks = [GreedyAgent(move_score, seed=s).select_move(g) for s in range(10)]
    assert set(picks) <= ties
    assert len(set(picks)) > 1
    again = [GreedyAgent(move_score, seed=s).select_move(g) for s in range(10)]
    assert picks == again


def test_does_not_mutate_game():
    g = setup([(7, 7)], [(8, 8)])
    before = (g.key(), g.candidate_moves(), g.winner())
    GreedyAgent(move_score, seed=0).select_move(g)
    assert (g.key(), g.candidate_moves(), g.winner()) == before


def test_custom_score_fn_and_legal_moves():
    g = KInRow(3, 3)
    g.play(4)
    agent = GreedyAgent(lambda game, m: -m, use_candidates=False)
    assert agent.select_move(g) == 0  # ô trống có index nhỏ nhất
    assert agent.stats["nodes"] == 8


@pytest.mark.parametrize("seed", range(4))
def test_beats_random_15x15(seed):
    greedy = GreedyAgent(move_score, seed=seed)
    rnd = RandomAgent(seed=seed, use_candidates=True)
    assert play_game(KInRow(N, 5), (greedy, rnd)) == X
    assert play_game(KInRow(N, 5), (rnd, greedy)) == O


def test_rejects_finished_game():
    g = KInRow(3, 3)
    for m in [0, 3, 1, 4, 2]:
        g.play(m)
    assert g.is_terminal()
    with pytest.raises(AssertionError):
        GreedyAgent(move_score, seed=0).select_move(g)
