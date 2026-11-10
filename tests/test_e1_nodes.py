"""Test E1 (đếm nút Minimax vs Alpha-Beta). Chỉ dùng thế nhỏ cho nhanh."""

from __future__ import annotations

from gameai.experiments.e1_nodes import (
    G3,
    G15,
    VARIANTS_3,
    build_game,
    make_position,
    run_position,
    summarize,
    variants_15,
)


def test_make_position_deterministic_and_nonterminal() -> None:
    for spec, plies in ((G3, 5), (G3, 6), (G15, 10)):
        a, sa = make_position(spec, plies)
        b, sb = make_position(spec, plies)
        assert (a, sa) == (b, sb) and len(a) == plies
        assert not build_game(spec, a).is_terminal()


def test_3x3_midgame_values_equal_and_savings() -> None:
    moves, _ = make_position(G3, 3)
    rows = run_position("3x3", "t", G3, moves, None, VARIANTS_3, repeats=2)
    by = {r["variant"]: r for r in rows}
    assert set(by) == {"minimax", "ab", "ab_order", "ab_order_tt"}
    for name, r in by.items():
        assert r["value"] == by["minimax"]["value"], name
        assert r["move_optimal"] == 1, name  # nước chọn có giá trị minimax bằng giá trị gốc
    assert by["minimax"]["move_same_as_minimax"] == 1 and by["ab"]["move_same_as_minimax"] == 1
    assert by["ab"]["nodes"] < by["minimax"]["nodes"]
    assert by["ab_order"]["nodes"] < by["ab"]["nodes"]
    expected = round(100 * (1 - by["ab"]["nodes"] / by["minimax"]["nodes"]), 2)
    assert by["ab"]["nodes_saving_vs_minimax_pct"] == expected
    assert by["ab_order"]["nodes_saving_vs_ab_pct"] == round(
        100 * (1 - by["ab_order"]["nodes"] / by["ab"]["nodes"]), 2
    )
    assert "nodes_saving_vs_ab_pct" not in by["ab"]  # ab là mốc, không tự so với chính nó


def test_15x15_depth2_equal_to_minimax_and_skip_minimax() -> None:
    moves, _ = make_position(G15, 6)
    rows = run_position("15x15", "t", G15, moves, 2, variants_15(2), repeats=1)
    by = {r["variant"]: r for r in rows}
    assert set(by) == {"minimax", "ab_evalonly", "ab", "ab_order"}
    assert len({r["value"] for r in rows}) == 1  # eval và delta_eval cho cùng giá trị lá
    assert by["ab"]["nodes"] == by["ab_evalonly"]["nodes"] < by["minimax"]["nodes"]
    rows3 = run_position("15x15", "t", G15, moves, 3, variants_15(3), repeats=1)
    assert {r["variant"] for r in rows3} == {"ab", "ab_order"}  # depth 3 không có Minimax
    assert len({r["value"] for r in rows3}) == 1
    by3 = {r["variant"]: r for r in rows3}
    assert by3["ab_order"]["nodes"] < by3["ab"]["nodes"]
    rows_skip = run_position("15x15", "t", G15, moves, 2, variants_15(2), 1, skip_minimax=True)
    assert "minimax" not in {r["variant"] for r in rows_skip}
    assert all("value_same_as_minimax" not in r for r in rows_skip)


def test_summarize_pooled_vs_mean() -> None:
    def row(pos: str, variant: str, nodes: int, t: float, **kw: object) -> dict[str, object]:
        return {"board": "b", "pos_id": pos, "depth": 2, "variant": variant, "nodes": nodes,
                "time": t, **kw}  # fmt: skip

    rows = [
        row("p0", "minimax", 1000, 1.0),
        row(
            "p0",
            "ab",
            100,
            0.1,
            value_same_as_minimax=1,
            move_same_as_minimax=1,
            nodes_saving_vs_minimax_pct=90.0,
        ),  # fmt: skip
        row("p1", "minimax", 10, 0.1),
        row(
            "p1",
            "ab",
            10,
            0.1,
            value_same_as_minimax=1,
            move_same_as_minimax=0,
            nodes_saving_vs_minimax_pct=0.0,
        ),  # fmt: skip
    ]
    s = {r["variant"]: r for r in summarize(rows)}
    assert s["ab"]["nodes_saving_vs_minimax_pooled_pct"] == round(100 * (1 - 110 / 1010), 2)
    assert s["ab"]["nodes_saving_vs_minimax_mean_pct"] == 45.0  # trung bình từng thế ≠ gộp
    assert s["ab"]["values_same_as_minimax"] == "2/2" and s["ab"]["moves_same_as_minimax"] == "1/2"
    assert s["minimax"]["nodes_saving_vs_minimax_pooled_pct"] == ""


def test_3x3_empty_board_exact_node_counts() -> None:
    rows = run_position("3x3", "e", G3, [], None, VARIANTS_3, repeats=1)
    by = {r["variant"]: r for r in rows}
    assert by["minimax"]["nodes"] == 549_946 and by["ab"]["nodes"] == 20_866
    assert by["ab_order"]["nodes"] == 1_856 and by["ab_order_tt"]["nodes"] == 990
    assert all(r["value"] == 0 and r["move_optimal"] == 1 for r in rows)
