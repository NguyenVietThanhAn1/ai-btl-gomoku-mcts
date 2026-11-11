"""Test E4 (D-19): thế 3×3, tiêu chí chọn ở gốc (khớp MCTSAgent), giá trị trò chơi, luật ví dụ,
bảng tổng (kể cả chẩn đoán), spec đối đầu, score CI, hình."""

from __future__ import annotations

import math

import pytest

from gameai.agents.mcts import MCTSAgent, Node
from gameai.agents.minimax import MinimaxAgent
from gameai.agents.registry import AgentSpec, make_agent
from gameai.experiments import e4_final_move as e4
from gameai.experiments.common import run_match
from gameai.experiments.e1_nodes import build_game

# X 0, O 3, X 1, O 4 → X đi: ô 2 thắng ngay; O dọa ô 5.
WIN_NOW = [0, 3, 1, 4]
# mcts.md: X ở 0, 7, 8; O ở 1, 4, 6; X đi → phải chặn ô 2.
MUST_BLOCK = [0, 1, 7, 4, 8, 6]


def test_enumerate_3x3_counts_unique_and_order():
    all_pos = e4.enumerate_3x3(min_moves=1)
    assert len(all_pos) == 4520  # 5478 thế đạt được − 958 thế kết thúc
    two = e4.enumerate_3x3()
    keys = [build_game(e4.GAME3, p).key() for p in two]
    assert len(set(keys)) == len(keys)
    single = [p for p in all_pos if len(build_game(e4.GAME3, p).legal_moves()) == 1]
    assert len(two) == len(all_pos) - len(single) and single
    assert all(len(build_game(e4.GAME3, p).legal_moves()) >= 2 for p in two)
    assert all(not build_game(e4.GAME3, p).is_terminal() for p in two)
    assert [len(p) for p in two] == sorted(len(p) for p in two)
    assert two[0] == []


def test_move_values_match_minimax_outcome():
    g = build_game(e4.GAME3, MUST_BLOCK)
    vals = e4.move_values(g, {})
    best = max(vals.values())
    assert [m for m, v in vals.items() if v == best] == [2]
    # cùng dấu với Minimax (thang WIN − ply)
    for m, v in MinimaxAgent(depth=None).root_values(build_game(e4.GAME3, MUST_BLOCK)):
        assert v > 0 if vals[m] == 1 else v < 0 if vals[m] == -1 else v == 0


def _node(move: int, w: float, n: int) -> Node:
    ch = Node(move, None, 1, [])
    ch.W, ch.N = w, n
    return ch


def test_choose_indices_tie_breaks_like_agent():
    # max_n: N rồi W; max_wn: W/N rồi N; bằng → con mở rộng trước
    kids = [_node(0, 1, 1), _node(1, 6, 10), _node(2, 7, 10), _node(3, 1, 1)]
    i_n, i_wn, i_lcb = e4.choose_indices(kids)
    assert (i_n, i_wn) == (2, 0)
    assert i_lcb == 2  # 7/10 có cận dưới Wilson cao hơn 1/1
    # mọi con N = 1: max_n (1, W) và max_wn (W/N, N) chọn cùng con thắng đầu tiên
    kids = [_node(0, 0, 1), _node(1, 1, 1), _node(2, 1, 1)]
    assert e4.choose_indices(kids)[:2] == (1, 1)


@pytest.mark.parametrize(("board", "moves", "it"), [(3, MUST_BLOCK[:2], 30), (3, [4], 200),
                                                     (15, None, 300)])  # fmt: skip
def test_root_rows_match_agent_choice(board, moves, it):
    spec = e4.GAME3 if board == 3 else e4.GAME15
    if moves is None:
        moves, _ = e4.make_position(e4.GAME15, 10)
    agent, _ = e4.search_root(spec, moves, it, seed=3)
    rows = e4.root_rows(agent, {"board": "x"})
    assert sum(r["N"] for r in rows) == it
    assert [r["child_order"] for r in rows] == list(range(len(rows)))
    for fm, col in (("max_n", "is_max_n"), ("max_wn", "is_max_wn")):
        a = make_agent(AgentSpec("mcts", e4.mcts_params(board, it, fm)), 3)
        assert isinstance(a, MCTSAgent)
        chosen = a.select_move(build_game(spec, moves))
        assert [r["move"] for r in rows if r[col]] == [chosen]
    assert sum(r["is_max_lcb"] for r in rows) == 1


def test_win_now_child_has_wn_1_and_is_max_n():
    agent, _ = e4.search_root(e4.GAME3, WIN_NOW, 1000, seed=0)
    assert agent.check_tactics is False
    vals = e4.move_values(build_game(e4.GAME3, WIN_NOW), {})
    rows = e4.root_rows(agent, {}, vals)
    win = next(r for r in rows if r["move"] == 2)
    assert win["wn"] == 1.0 and win["is_max_n"] and win["optimal"]
    assert agent.stats["iterations"] == 1000


def test_root_rows_optimal_flag():
    agent, _ = e4.search_root(e4.GAME3, MUST_BLOCK, 100, seed=0)
    rows = e4.root_rows(agent, {}, e4.move_values(build_game(e4.GAME3, MUST_BLOCK), {}))
    assert {r["move"]: r["optimal"] for r in rows} == {2: True, 3: False, 5: False}


def _fake(board, c, pid, it, plies, kids, seed=0):
    """kids: (move, W, N, optimal)."""
    nodes = [_node(m, w, n) for m, w, n, _ in kids]
    i_n, i_wn, i_lcb = e4.choose_indices(nodes)
    return [{"board": board, "kind": "search", "c": c, "pos_id": pid, "seed": seed,
             "iterations": it, "plies": plies, "child_order": i, "move": m, "W": w, "N": n,
             "is_max_n": i == i_n, "is_max_wn": i == i_wn, "is_max_lcb": i == i_lcb,
             "optimal": opt} for i, (m, w, n, opt) in enumerate(kids)]  # fmt: skip


def test_summary_and_examples_rule():
    it = e4.EXAMPLE_ITER_3
    rows = []
    # thế 0: khác, max_wn không tối ưu → ví dụ
    rows += _fake("3x3", e4.C, 0, it, 2, [(1, 1, 1, False), (2, 60, 99, True)])
    # thế 1: giống nhau
    rows += _fake("3x3", e4.C, 1, it, 3, [(1, 50, 90, True), (2, 5, 10, True)])
    # thế 2: khác nhưng max_wn tối ưu → không phải ví dụ
    rows += _fake("3x3", e4.C, 2, it, 4, [(1, 2, 2, True), (2, 60, 98, True)])
    # thế 3: khác, max_wn sai, nhiều quân nhất → ví dụ + trace
    rows += _fake("3x3", e4.C, 3, it, 6, [(1, 1, 1, False), (2, 60, 99, True)])
    ex = e4.example_positions_3x3(rows)
    assert ex == [("rule", 0), ("rule", 3), ("trace", 3)]
    summ = {(s["set"]): s for s in e4.summarize_roots(rows)}
    a = summ["all"]
    assert (a["n_positions"], a["n_differ"]) == (4, 3)
    assert a["differ_opt_max_n"] == 1.0 and math.isclose(a["differ_opt_max_wn"], 1 / 3)
    assert summ["has_bad"]["n_positions"] == 2  # thế 0 và 3 có nước không tối ưu
    assert a["max_n_wn_is_1"] == 0.0 and a["max_n_tied_median"] == 1


def test_examples_15_per_c_and_skip_tactic():
    rows = [{"board": "15x15", "kind": "search", "c": 1.4, "pos_id": 0, "seed": 0,
             "iterations": 50, "plies": 6, "move": ""}]  # tactic đi tắt  # fmt: skip
    rows += _fake("15x15", 1.4, 1, 50, 8, [(1, 1, 1, None), (2, 1, 1, None)])  # giống nhau
    rows += _fake("15x15", 0.5, 1, 250, 8, [(1, 9, 10, None), (2, 3, 3, None)], seed=2)
    rows += _fake("15x15", 0.5, 1, 1000, 8, [(1, 9, 10, None), (2, 3, 3, None)])
    assert e4.example_searches_15(rows) == [(0.5, 1, 0, 1000)]
    summ = e4.summarize_roots(rows)
    s14 = next(s for s in summ if s["c"] == 1.4)
    assert (s14["n_skipped_tactic"], s14["n_positions"], s14["n_differ"]) == (1, 1, 0)
    assert s14["max_n_wn_is_1"] == 1.0 and s14["max_n_tied_median"] == 2
    ex = e4.example_rows([], rows)
    assert {r["example"] for r in ex} == {"sensitivity"}


def test_mcts_spec_only_final_move_differs():
    for board in (3, 15):
        a, b = e4.mcts_spec(board, 50, "max_n"), e4.mcts_spec(board, 50, "max_wn")
        pa, pb = dict(a.params), dict(b.params)
        assert (pa.pop("final_move"), pb.pop("final_move")) == ("max_n", "max_wn")
        assert pa == pb and pa["c"] == 1.4 and pa["iterations"] == 50
        assert pa["check_tactics"] is (board == 15)
        assert (pa.get("rollout"), pa.get("temperature")) == (
            (None, None) if board == 3 else ("heavy_kinrow", 300)
        )
    assert list(e4.MATCH) == ["3x3"]
    assert e4.MATCH["3x3"][1:3] == ((10, 20, 50, 100, 250), 100)


def test_small_match_score_ci_and_plot(tmp_path):
    raw = tmp_path / "m.csv"
    rows = run_match(raw, e4.GAME3, e4.mcts_spec(3, 10, "max_n"), e4.mcts_spec(3, 10, "max_wn"),
                     3, workers=1, allow_code_change=True)  # fmt: skip
    assert len(rows) == 6
    lo, hi = e4.score_ci(rows, "all")
    xs = [float(r["result_a"]) for r in rows]
    m = sum(xs) / len(xs)
    assert lo <= m <= hi
    table = [{"board": "3x3", "iterations": it, "split": "all", "n": 10, "wins": w, "losses": lo_,
              "score": s, "score_lo": max(0, s - 0.1), "score_hi": min(1, s + 0.1)}
             for it, w, lo_, s in ((10, 10, 0, 1.0), (20, 0, 10, 0.0),
                                   (50, 3, 3, 0.5))]  # fmt: skip
    out = e4.plot_match(table, tmp_path / "f.png")
    assert out.exists() and out.stat().st_size > 0


def test_score_ci_constant_and_split():
    rows = [
        {"a_is_x": "1", "result_a": "0.5"},
        {"a_is_x": "0", "result_a": "0.5"},
        {"a_is_x": "1", "result_a": "1.0"},
        {"a_is_x": "0", "result_a": "0.0"},
    ]
    assert e4.score_ci(rows[:2], "all") == (0.5, 0.5)
    lo, hi = e4.score_ci(rows, "A=X")
    assert lo < 0.75 < hi
