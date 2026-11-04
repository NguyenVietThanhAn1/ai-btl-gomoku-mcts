import random

import pytest

from gameai.agents.alphabeta import AlphaBetaAgent
from gameai.agents.minimax import WIN_SCORE, MinimaxAgent
from gameai.core.game import DRAW
from gameai.games.kinrow import KInRow, X
from gameai.heuristics.kinrow_eval import delta_eval, evaluate, move_score

COMBOS = [
    {},
    {"order_fn": move_score},
    {"use_tt": True},
    {"order_fn": move_score, "use_tt": True},
]


def play_game(game, agents):
    while not game.is_terminal():
        agent = agents[0] if game.current_player() == X else agents[1]
        game.play(agent.select_move(game))
    return game.winner()


def setup(n, k, moves):
    g = KInRow(n, k)
    for m in moves:
        g.play(m)
    return g


def random_states(n, k, count, min_len, max_len, seed):
    rng = random.Random(seed)
    states = []
    while len(states) < count:
        g = KInRow(n, k)
        for _ in range(rng.randint(min_len, max_len)):
            if g.is_terminal():
                break
            g.play(rng.choice(g.legal_moves()))
        if not g.is_terminal():
            states.append(g)
    return states


def test_same_value_as_minimax_3x3():
    states = [KInRow(3, 3)] + random_states(3, 3, 25, 1, 7, seed=1)
    for g in states:
        mm = MinimaxAgent()
        mm_values = dict(mm.root_values(g))
        best_mm = max(mm_values.values())
        for opts in COMBOS:
            ab = AlphaBetaAgent(**opts)
            move, v = ab.search(g)
            assert v == best_mm, (opts, g.render())
            assert mm_values[move] == best_mm  # nước AB chọn là tối ưu
            assert ab.stats["nodes"] <= mm.stats["nodes"]


def test_fewer_nodes_than_minimax_on_empty_3x3():
    g = KInRow(3, 3)
    plain = AlphaBetaAgent()
    plain.select_move(g)
    assert plain.stats["nodes"] < 549946 // 10
    assert plain.stats["cutoffs"] > 0
    tt = AlphaBetaAgent(use_tt=True, order_fn=move_score)
    tt.select_move(g)
    assert tt.stats["tt_hits"] > 0
    assert tt.stats["nodes"] < plain.stats["nodes"]
    assert set(plain.stats) >= {"nodes", "iterations", "time", "value", "cutoffs", "tt_hits"}


@pytest.mark.parametrize("depth", [2, 3])
def test_depth_limited_same_value_as_minimax_7x7(depth):
    states = random_states(7, 4, 2 if depth == 3 else 5, 3, 8, seed=depth)
    for g in states:
        mm_v = MinimaxAgent(depth=depth, eval_fn=evaluate).value(g)
        for opts in COMBOS:
            ab_eval = AlphaBetaAgent(depth=depth, eval_fn=evaluate, **opts)
            ab_delta = AlphaBetaAgent(depth=depth, eval_fn=evaluate, delta_fn=delta_eval, **opts)
            assert ab_eval.value(g) == mm_v, g.render()
            assert ab_delta.value(g) == mm_v, g.render()


def pos(n, rc):
    return rc[0] * n + rc[1]


def interleave(n, xs, os_):
    moves = []
    for a, b in zip(xs, os_, strict=True):
        moves += [pos(n, a), pos(n, b)]
    return moves


def strong_ab(depth=2):
    return AlphaBetaAgent(depth=depth, eval_fn=evaluate, delta_fn=delta_eval, order_fn=move_score)


@pytest.mark.parametrize("agent_fn", [strong_ab, lambda: AlphaBetaAgent(depth=2, eval_fn=evaluate)])
def test_15x15_depth2_wins_immediately(agent_fn):
    n = 15
    xs = [(7, 5), (7, 6), (7, 7), (7, 8)]
    os_ = [(7, 4), (10, 5), (10, 6), (10, 7)]  # O có open-three, X có four chặn trái
    g = setup(n, 5, interleave(n, xs, os_))
    assert g.current_player() == X
    assert agent_fn().select_move(g) == pos(n, (7, 9))


@pytest.mark.parametrize("agent_fn", [strong_ab, lambda: AlphaBetaAgent(depth=2, eval_fn=evaluate)])
def test_15x15_depth2_blocks_four(agent_fn):
    n = 15
    xs = [(10, 4), (7, 6), (7, 7), (7, 8)]  # X có open-three (tấn công hấp dẫn)
    os_ = [(10, 5), (10, 6), (10, 7), (10, 8)]  # O có four, đầu trái bị chặn
    g = setup(n, 5, interleave(n, xs, os_))
    assert g.current_player() == X
    assert agent_fn().select_move(g) == pos(n, (10, 9))


def test_does_not_mutate_game():
    g = setup(15, 5, [112, 113, 97])
    before = (g.key(), g.candidate_moves(), g.winner())
    strong_ab().select_move(g)
    assert (g.key(), g.candidate_moves(), g.winner()) == before


@pytest.mark.parametrize("seed", [None, 0, 1])
def test_ab_vs_ab_3x3_draws(seed):
    a = AlphaBetaAgent(seed=seed, use_tt=True)
    b = AlphaBetaAgent(seed=None if seed is None else seed + 7, order_fn=move_score)
    assert play_game(KInRow(3, 3), (a, b)) == DRAW


def test_seeded_tie_break_varies_but_stays_optimal():
    g = KInRow(3, 3)
    mm_values = dict(MinimaxAgent().root_values(g))
    moves = {AlphaBetaAgent(seed=s, use_tt=True).select_move(g) for s in range(8)}
    assert len(moves) > 1
    assert all(mm_values[m] == 0 for m in moves)


def test_invalid_depth():
    with pytest.raises(ValueError):
        AlphaBetaAgent(depth=0)


def test_win_fast_prefers_shorter_win():
    # X: 0, 1, 4; O: 3, 8 → X thắng ngay ở 2 (hoặc 7); AB phải chọn thắng ngay, giá trị = W − 1.
    g = setup(3, 3, [0, 3, 1, 8, 4, 6])
    move, v = AlphaBetaAgent(use_tt=True).search(g)
    g.play(move)
    assert g.winner() == X
    assert v == MinimaxAgent().value(setup(3, 3, [0, 3, 1, 8, 4, 6]))


def test_tt_mate_score_matches_minimax():
    # X: 0, 4; O: 1, 8; X đi → tạo fork (vd. ô 6) thắng ở ply 3: giá trị = WIN_SCORE − 3.
    g = setup(3, 3, [0, 1, 4, 8])
    expected = MinimaxAgent().value(g)
    assert expected == WIN_SCORE - 3
    for opts in COMBOS:
        assert AlphaBetaAgent(**opts).value(g) == expected
