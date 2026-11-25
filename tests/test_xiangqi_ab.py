"""Alpha-Beta cờ tướng (P8.2, D-23): = Minimax d2, ordering, chiến thuật, ID, lặp thế, trận thử."""

import pytest

from gameai.agents.alphabeta import AlphaBetaAgent
from gameai.agents.minimax import WIN_SCORE, MinimaxAgent
from gameai.agents.registry import FUNCTIONS, AgentSpec, GameSpec, make_agent, make_game
from gameai.core.game import DRAW
from gameai.experiments.p81_perft import POSITIONS
from gameai.experiments.p82_ab_check import GREEDY, RANDOM, ab_spec, midgame_fens, run_match
from gameai.games.xiangqi import RED, START_FEN, Xiangqi, iccs_to_move, move_to_iccs
from gameai.heuristics import xiangqi_eval as xe


def ab(depth, order=True, delta=True, **kw):
    return AlphaBetaAgent(
        depth=depth,
        eval_fn=xe.evaluate,
        delta_fn=xe.delta_eval if delta else None,
        order_fn=xe.mvv_lva if order else None,
        **kw,
    )


PERFT_FENS = [fen for _, fen, _ in POSITIONS]
MID_FENS = midgame_fens(4, seed=11)


# ------------------------------------------------------------------ AB = Minimax
MODES = {
    "eval": dict(order=False, delta=False),
    "delta": dict(order=False, delta=True),
    "delta+order": dict(order=True, delta=True),
    "delta+order+tt": dict(order=True, delta=True, use_tt=True),
}


@pytest.mark.parametrize("mode", MODES)
def test_root_value_equals_minimax_depth2_on_14_positions(mode):
    assert len(PERFT_FENS) + len(MID_FENS) >= 14
    for fen in PERFT_FENS + MID_FENS:
        g = Xiangqi(fen)
        expected = MinimaxAgent(depth=2, eval_fn=xe.evaluate).value(g)
        agent = ab(2, **MODES[mode])
        move, value = agent.search(g)
        assert value == expected, (mode, fen)
        assert move in g.legal_moves()
        assert g.to_fen() == Xiangqi(fen).to_fen()  # không đổi game


def test_root_value_equals_minimax_depth3():
    for fen in [START_FEN, MID_FENS[0]]:
        g = Xiangqi(fen)
        expected = MinimaxAgent(depth=3, eval_fn=xe.evaluate).value(g)
        assert ab(3).search(g)[1] == expected
        assert ab(3, use_tt=True).search(g)[1] == expected


def test_mvv_lva_ordering_reduces_nodes_same_value():
    plain = ordered = 0
    for fen in [START_FEN, *MID_FENS]:
        a0, a1 = ab(3, order=False), ab(3)
        v0 = a0.search(Xiangqi(fen))[1]
        v1 = a1.search(Xiangqi(fen))[1]
        assert v0 == v1
        plain += a0.stats["nodes"]
        ordered += a1.stats["nodes"]
    assert ordered < plain


# ------------------------------------------------------------------ chiến thuật
def test_takes_free_rook_depth2():
    g = Xiangqi("3k5/9/9/9/r8/9/9/9/9/R3K4 w - - 0 1")
    move, value = ab(2).search(g)
    assert move_to_iccs(move) == "a0a5"
    assert value > 0


def test_does_not_take_defended_pawn_with_rook_depth2():
    # xe Đen a9 bảo vệ tốt a5: Xa0xa5? rồi Xa9xa5 → mất xe (900) lấy tốt (100)
    g = Xiangqi("r4k3/9/9/9/p8/9/9/9/9/R3K4 w - - 0 1")
    move, value = ab(2).search(g)
    assert move_to_iccs(move) != "a0a5"
    assert value > -500  # a0a5 cho giá trị ≈ −800 + PST


def test_escapes_check_by_capturing_checker():
    g = Xiangqi("3k5/9/9/9/R3r4/9/9/9/9/4K4 w - - 0 1")
    assert g.in_check()
    move, _ = ab(2).search(g)
    assert move_to_iccs(move) == "a5e5"  # ăn xe đang chiếu (lựa chọn khác là Tg f0)


def test_escapes_check_with_single_legal_move():
    g = Xiangqi("5k3/9/9/9/4r4/9/9/9/4K4/9 w - - 0 1")
    assert g.in_check()
    legal = g.legal_moves()
    assert [move_to_iccs(m) for m in legal] == ["e1d1"]
    move, value = ab(2).search(g)
    assert move == legal[0] and abs(value) < WIN_SCORE / 2
    g.play(move)
    assert g.winner() is None


def test_mate_in_one_found_at_depth_1():
    g = Xiangqi("4k4/R8/9/9/9/9/9/9/9/3K3R1 w - - 0 1")
    mates = []
    for m in g.legal_moves():
        g.play(m)
        if g.winner() == RED:
            mates.append(m)
        g.undo()
    assert mates  # có chiếu bí 1 nước
    agent = ab(1)
    move, value = agent.search(g)
    assert move in mates and value == WIN_SCORE - 1


def test_mate_in_two_found_at_depth_3_not_before():
    g = Xiangqi("4k4/9/R8/9/9/9/9/9/9/3K3R1 w - - 0 1")
    for depth in (1, 2):  # chưa thấy chiếu bí
        assert abs(ab(depth).search(g)[1]) < WIN_SCORE / 2
    move, value = ab(3).search(g)
    assert value == WIN_SCORE - 3  # ta – đáp – ta: chiếu bí ở ply 3
    g.play(move)
    replies = g.legal_moves()
    assert replies
    for reply in replies:  # mọi nước đáp đều bị chiếu bí ngay
        g.play(reply)
        assert ab(1).search(g)[1] == WIN_SCORE - 1
        g.undo()


# ------------------------------------------------------------------ iterative deepening
def test_id_tiny_time_limit_still_returns_depth1_move():
    g = Xiangqi(START_FEN)
    agent = ab(6, time_limit=1e-9)
    move = agent.select_move(g)
    assert move in g.legal_moves()
    assert agent.stats["depth_reached"] >= 1 and agent.stats["timed_out"] == 1


def test_id_spare_time_equals_fixed_depth():
    for fen in [START_FEN, MID_FENS[1]]:
        g = Xiangqi(fen)
        fixed = ab(3)
        timed = ab(3, time_limit=60.0)
        assert timed.search(g) == fixed.search(g)
        assert timed.stats["depth_reached"] == 3 and timed.stats["timed_out"] == 0


# ------------------------------------------------------------------ lặp thế + TT
def _repeating_position() -> Xiangqi:
    """Đỏ (Tg d0, Xe, Tốt) vs Tướng Đen; sau c3c4 lặp chu kỳ 4 nước 2 lần (Xa0, Tg e9, Đen đi)."""
    g = Xiangqi("4k4/9/9/9/9/9/2P6/9/9/R2K5 w - - 0 1")
    for m in "c3c4 e9f9 a0a1 f9e9 a1a0 e9f9 a0a1 f9e9".split():
        g.play(iccs_to_move(m))
    assert g.winner() is None and g.current_player() == RED
    return g


def test_repetition_third_occurrence_is_draw_value_without_tt():
    g = _repeating_position()
    repeat = iccs_to_move("a1a0")  # tạo lần lặp thứ 3 → hòa
    hook = lambda game: (None, {repeat})  # noqa: E731 — chỉ xét nước lặp ở gốc
    seen = ab(2, root_hook=hook, use_tt=False).search(g)
    assert seen == (repeat, 0)  # AB thấy hòa (0) dù Đỏ hơn xe
    fresh = Xiangqi(g.to_fen())  # cùng thế, không lịch sử → không hòa
    value = ab(2, root_hook=hook, use_tt=False).search(fresh)[1]
    assert value > 0
    g.play(repeat)
    assert g.winner() == DRAW


def test_tt_with_repetition_history_only_observed():
    # Ghi nhận (D-22 "graph history interaction"): KHÔNG khẳng định nước đúng, chỉ chạy + hợp lệ.
    g = _repeating_position()
    for tt_mode in ("exact", "deep"):
        agent = ab(3, use_tt=True, tt_mode=tt_mode)
        move, value = agent.search(g)
        assert move in g.legal_moves()
        assert isinstance(value, (int, float))


# ------------------------------------------------------------------ registry
def test_registry_xiangqi_game_and_functions():
    assert isinstance(make_game(GameSpec("xiangqi")), Xiangqi)
    assert make_game(GameSpec("xiangqi", {"max_plies": 50})).max_plies == 50
    assert FUNCTIONS["xq_evaluate"] is xe.evaluate
    assert FUNCTIONS["xq_delta"] is xe.delta_eval
    assert FUNCTIONS["xq_mvv_lva"] is xe.mvv_lva
    agent = make_agent(ab_spec(2), None)
    assert isinstance(agent, AlphaBetaAgent)
    g = make_game(GameSpec("xiangqi"))
    assert agent.select_move(g) in g.legal_moves()
    with pytest.raises(ValueError):
        make_agent(AgentSpec("alphabeta", {"depth": 2, "eval": "xq_khong_co"}), None)


# ---------------------------------------------------- trận thử (khai cuộc ngẫu nhiên có seed)
# Đo MỘT lần (seed 0, 5 khai cuộc × 2 ván đổi bên, max_plies 200): AB depth 2 vs Random 10/0/0,
# vs Greedy(xq_delta) 10/0/0, 5 khai cuộc phân biệt, 0 ván trùng chuỗi nước. Ngưỡng chốt từ số
# đó (D-23); không chỉnh lại cho qua.
@pytest.mark.parametrize(
    ("name", "opponent", "min_wins", "min_score"),
    [("random", RANDOM, 8, 0.9), ("greedy_xq", GREEDY, 8, 0.8)],
)
def test_ab2_beats_baselines_from_random_openings(name, opponent, min_wins, min_score):
    res = run_match(ab_spec(2), opponent, n_pairs=5, base_seed=0, max_plies=200)
    assert res["errors"] == 0
    assert res["distinct_openings"] == 5 and len(res["games"]) == 10
    assert res["L"] == 0, name
    assert res["W"] >= min_wins and res["score"] >= min_score
