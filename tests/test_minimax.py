import pytest

from gameai.agents.minimax import WIN_SCORE, MinimaxAgent, terminal_score
from gameai.agents.random_agent import RandomAgent
from gameai.core.game import DRAW
from gameai.games.kinrow import KInRow, O, X
from gameai.heuristics.kinrow_eval import evaluate


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


def test_full_tree_3x3_node_count_and_value():
    # Cây trò chơi tic-tac-toe đầy đủ có 549 946 nút (kể cả gốc), giá trị = hòa.
    a = MinimaxAgent()
    g = KInRow(3, 3)
    assert a.value(g) == 0
    assert a.stats["nodes"] == 549946
    assert a.stats["time"] > 0


def test_terminal_score_prefers_fast_win():
    assert terminal_score(X, X, 1) > terminal_score(X, X, 3) > 0
    assert terminal_score(O, X, 1) < terminal_score(O, X, 3) < 0
    assert terminal_score(DRAW, X, 2) == 0
    assert terminal_score(X, X, 0) == WIN_SCORE


def test_takes_immediate_win_3x3():
    # X: 0, 1; O: 3, 4; X đi → thắng ở 2 (O cũng dọa 5 nhưng thắng ngay tốt hơn).
    g = setup(3, 3, [0, 3, 1, 4])
    assert MinimaxAgent().select_move(g) == 2


def test_blocks_immediate_loss_3x3():
    # X: 0, 8; O: 4, 1 → O dọa cột giữa (7). X phải chặn 7.
    g = setup(3, 3, [0, 4, 8, 1])
    assert MinimaxAgent().select_move(g) == 7


def test_does_not_mutate_game():
    g = setup(3, 3, [4, 0])
    before = (g.key(), g.legal_moves(), g.winner())
    MinimaxAgent().select_move(g)
    assert (g.key(), g.legal_moves(), g.winner()) == before


def test_root_values_cover_all_moves():
    g = setup(3, 3, [4])
    vals = MinimaxAgent().root_values(g)
    assert sorted(m for m, _ in vals) == sorted(g.legal_moves())
    assert max(v for _, v in vals) == 0  # O đi sau X ở giữa vẫn giữ được hòa


@pytest.mark.parametrize("seed", [None, 0, 1])
def test_minimax_vs_minimax_3x3_draws(seed):
    a, b = MinimaxAgent(seed=seed), MinimaxAgent(seed=None if seed is None else seed + 100)
    assert play_game(KInRow(3, 3), (a, b)) == DRAW


@pytest.mark.parametrize("seed", range(5))
def test_minimax_never_loses_to_random_3x3(seed):
    mm = MinimaxAgent(seed=seed)
    rnd = RandomAgent(seed=seed)
    assert play_game(KInRow(3, 3), (mm, rnd)) in (X, DRAW)
    assert play_game(KInRow(3, 3), (rnd, mm)) in (O, DRAW)


def test_depth_limited_counts_and_eval():
    g = KInRow(3, 3)
    a = MinimaxAgent(depth=1)
    a.select_move(g)
    assert a.stats["nodes"] == 1 + 9
    a = MinimaxAgent(depth=2)
    a.select_move(g)
    assert a.stats["nodes"] == 1 + 9 + 9 * 8


def test_invalid_depth():
    with pytest.raises(ValueError):
        MinimaxAgent(depth=0)


def test_depth_limited_with_eval_wins_and_blocks_7x7():
    # 7×7, k=4, hàng 3: X ở cột 1, 2, 3 (open-three) → depth 1 phải đi thắng ở cột 0 hoặc 4.
    n = 7
    g = setup(n, 4, [3 * n + 1, 0, 3 * n + 2, 6, 3 * n + 3, 6 * n])
    assert g.current_player() == X
    move = MinimaxAgent(depth=1, eval_fn=evaluate).select_move(g)
    assert move in (3 * n + 0, 3 * n + 4)

    # O có three hàng 5 cột 2..4, đầu trái bị X chặn (5,1) → nước thắng duy nhất (5,5); X phải chặn.
    g = setup(n, 4, [5 * n + 1, 5 * n + 2, 0, 5 * n + 3, 6, 5 * n + 4])
    assert g.current_player() == X
    a = MinimaxAgent(depth=2, eval_fn=evaluate)
    assert a.select_move(g) == 5 * n + 5
    assert a.stats["nodes"] > 1
