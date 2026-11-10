"""Test E2 (vét cạn + cấu hình). Dùng iteration nhỏ cho nhanh."""

from __future__ import annotations

from gameai.agents.registry import GameSpec, make_agent, make_game
from gameai.core.game import P1, P2
from gameai.experiments.e2_never_lose import (
    exhaustive_check,
    mcts_spec,
    opponent_spec,
    summarize_exhaustive,
)

G3 = GameSpec("kinrow", {"n": 3, "k": 3})


def test_exhaustive_counts_and_determinism() -> None:
    spec = mcts_spec(20)
    for player in (P1, P2):
        a = exhaustive_check(make_game(G3), spec, 7, player)
        b = exhaustive_check(make_game(G3), spec, 7, player)
        assert a == b  # cùng base_seed → cùng cây
        assert a["branches"] == a["wins"] + a["draws"] + a["losses"] > 0
        assert a["mcts_decisions"] > 0


def test_exhaustive_loss_example_is_real_loss_and_seed_matters() -> None:
    spec = mcts_spec(5)  # rất ít iteration → chắc chắn có nhánh thua
    res = exhaustive_check(make_game(G3), spec, 1, P2)
    assert res["losses"] > 0
    g = make_game(G3)
    for m in str(res["loss_example"]).split():
        g.play(int(m))
    assert g.is_terminal() and g.winner() == P1  # MCTS cầm O thua
    others = {exhaustive_check(make_game(G3), spec, s, P2)["branches"] for s in range(4)}
    assert len(others) > 1  # seed khác → MCTS đi khác → số nhánh khác


def test_exhaustive_mcts_moves_follow_key_seed() -> None:
    """MCTS đi ở thế gốc đúng bằng agent dựng với derive_seed(base_seed, repr(key))."""
    from gameai.arena import derive_seed

    spec = mcts_spec(20)
    g = make_game(G3)
    expect = make_agent(spec, derive_seed(3, repr(g.key()))).select_move(g)
    res = exhaustive_check(make_game(G3), spec, 3, P1)  # MCTS đi trước: nước đầu = nước ở gốc
    first = {int(x.split()[0]) for x in [str(res["loss_example"])] if x}
    assert first <= {expect}  # nếu có chuỗi thua thì nó bắt đầu bằng đúng nước đó
    other = make_agent(spec, derive_seed(4, repr(g.key()))).select_move(g)
    assert isinstance(other, int)


def test_by_role_mistakes_and_extension_rule(monkeypatch, capsys) -> None:
    from gameai.experiments import e2_never_lose as e2

    rows = [
        {"iterations": 10, "base_seed": 0, "mcts_player": 1, "branches": 5, "losses": 0,
         "draws": 1, "wins": 4, "mistakes": {}},
        {"iterations": 10, "base_seed": 0, "mcts_player": -1, "branches": 7, "losses": 2,
         "draws": 1, "wins": 4, "mistakes": {((4,), 1): 2}},
    ]  # fmt: skip
    by_role = e2.summarize_by_role(rows)
    assert [(r["mcts_player"], r["seeds_zero_loss"], r["n_seeds"]) for r in by_role] == [
        (1, 1, 1), (-1, 0, 1)]  # fmt: skip
    mrows = e2.mistake_rows(rows)
    assert len(mrows) == 1 and mrows[0]["move_type"] == "edge"
    assert (mrows[0]["opp_last_type"], mrows[0]["ply"]) == ("center", 1)
    (agg,) = e2.summarize_mistakes(mrows)
    assert (agg["mistakes"], agg["losing_leaves"]) == (1, 2)
    # luật mở rộng: không seed thua ở iter cao nhất → không chạy gì; có → chạy đúng seed đó
    top = max(e2.ITERATIONS)
    calls = []
    monkeypatch.setattr(e2, "_run_tasks", lambda tasks, stem, w: calls.append(tasks) or [])
    assert e2.run_extension([{**rows[0], "iterations": top}], True, 1) == [] and not calls
    e2.run_extension([{**rows[1], "iterations": top, "base_seed": 7}], True, 1)
    assert sorted(calls[0]) == sorted(
        (it, 7, p) for it in e2.EXT_ITERATIONS for p in (1, -1))  # fmt: skip


def test_solve_values() -> None:
    from gameai.experiments.e2_never_lose import solve

    g = make_game(G3)
    assert solve(g, {}) == 0  # bàn trống 3×3 là hòa
    for m in (0, 3, 1, 4):  # X: 0,1 — O: 3,4 → X đi, thắng ngay ở 2
        g.play(m)
    assert solve(g, {}) == 1


def test_summarize_exhaustive() -> None:
    rows = [
        {"iterations": 10, "base_seed": 0, "mcts_player": 1, "branches": 5, "losses": 0,
         "draws": 1, "wins": 4, "loss_example": ""},
        {"iterations": 10, "base_seed": 0, "mcts_player": -1, "branches": 7, "losses": 2,
         "draws": 1, "wins": 4, "loss_example": "0 1 2"},
    ]  # fmt: skip
    (s,) = summarize_exhaustive(rows)
    assert (s["branches"], s["losses"], s["runs_with_loss"], s["loss_example"]) == (
        12,
        2,
        1,
        "0 1 2",
    )


def test_specs() -> None:
    assert mcts_spec(100).params["check_tactics"] is False
    assert opponent_spec("minimax", 100).params["depth"] is None
    assert opponent_spec("mcts", 250).label == "mcts250_opp"


def test_first_mistake_is_real_and_counts_match() -> None:
    from gameai.experiments.e2_never_lose import move_type, solve

    res = exhaustive_check(make_game(G3), mcts_spec(5), 1, P2)
    assert sum(res["mistakes"].values()) == res["losses"]  # mỗi nhánh thua đúng một nước sai đầu
    cache: dict = {}
    for (prefix, m), _ in res["mistakes"].items():
        g = make_game(G3)
        for x in prefix:
            g.play(x)
        before = solve(g, cache)
        g.play(m)
        assert -solve(g, cache) < before  # nước đó thực sự làm giá trị giảm
    assert [move_type(x) for x in (None, 4, 0, 1)] == ["none", "center", "corner", "edge"]
