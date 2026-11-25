"""E7 cờ tướng (P8.4, D-25): lý do kết thúc, luật chốt trước, ordering, runner, tổng hợp."""

import argparse
import json

import pytest

from gameai.agents.registry import AgentSpec, GameSpec, make_agent
from gameai.experiments import e7_xiangqi as e7
from gameai.experiments.common import moves_path_for, read_rows
from gameai.experiments.p82_ab_check import RANDOM, ab_spec
from gameai.games.xiangqi import START_FEN, Xiangqi, iccs_to_move

CHECKMATE = "3k5/9/9/9/9/9/9/9/r8/1r2K4 w - - 0 1"  # Đỏ sắp đi, bị chiếu, hết nước
STALEMATE = "5k3/9/9/9/4r4/9/9/9/r8/3K5 w - - 0 1"  # Đỏ sắp đi, không bị chiếu, hết nước


def row_for(params: dict, moves: list[int], winner: int, termination: str = "normal") -> dict:
    return {
        "game_id": "0-AX",
        "game_spec": json.dumps({"kind": "xiangqi", "params": params}),
        "opening": "",
        "moves": ";".join(map(str, moves)),
        "winner": str(winner),
        "termination": termination,
    }


def test_classify_mate_and_stalemate():
    assert e7.classify_game(row_for({"fen": CHECKMATE}, [], -1)) == ("mate", 0)
    assert e7.classify_game(row_for({"fen": STALEMATE}, [], -1)) == ("stalemate", 0)


def test_classify_repetition_and_max_plies():
    cycle = [iccs_to_move(s) for s in ("h0g2", "h9g7", "g2h0", "g7h9")]
    term, ply = e7.classify_game(row_for({"max_plies": 200}, cycle * 2, 0))
    assert (term, ply) == ("repetition", 8)
    four = [iccs_to_move(s) for s in ("h0g2", "h9g7", "b0c2", "b9c7")]
    assert e7.classify_game(row_for({"max_plies": 4}, four, 0)) == ("max_plies", 4)


def test_classify_error_and_mismatch():
    assert e7.classify_game(row_for({}, [], 0, "exception"))[0] == "error"
    with pytest.raises(ValueError):
        e7.classify_game(row_for({"fen": CHECKMATE}, [], 0))


def test_l_verdict_three_branches():
    assert e7.l_verdict(0.8, 50) == "L0_stronger"
    assert e7.l_verdict(0.2, 50) == "L10_stronger"
    assert e7.l_verdict(0.51, 50) == "tie"


def test_best_rollout_rule():
    assert e7.best_rollout((0.5, 50), (0.55, 50)) == "L10"
    assert e7.best_rollout((0.1, 50), (0.8, 50)) == "L0"
    assert e7.best_rollout((0.9, 50), (0.8, 50)) == "Lend"


def test_specs_follow_d23_and_d25():
    ab = e7.ab_time(1.0)
    assert ab.params["tt_mode"] == "exact" and ab.params["use_tt"] is True
    assert ab.params["time_limit"] == 1.0 and ab.params["depth"] == 12
    assert "top_k" not in ab.params and ab.params["order"] == "xq_mvv_lva"
    make_agent(ab, None)
    for name, rollout in e7.ROLLOUTS.items():
        s = e7.mcts(rollout)
        assert s.params["check_tactics"] is True and s.params["rollout_limit"] == rollout
        assert s.params["time_limit"] == e7.C_TIME and s.name == f"mcts_{name}"
    assert make_agent(e7.mcts(None), 1).rollout_limit is None
    assert e7.d_specs("L10")["d2"][0].params["time_limit"] == 2.5


def test_side_game_stats_skips_direct_and_ab_moves():
    def mv(side, it, at, tactic="0", depth="", dr=""):
        return {"side": side, "time": "1.0", "iterations": it, "agent_time": at, "tactic": tactic,
                "rollout_plies": "50" if it not in ("", "0") else "", "max_depth": depth,
                "nodes": "10", "depth_reached": dr}  # fmt: skip

    moves = [mv("A", "100", "1.0", depth="3"), mv("A", "0", "0", tactic="1"),
             mv("A", "300", "1.0", depth="5"), mv("B", "0", "0.9", dr="4"),
             mv("B", "0", "0.8", dr="6")]  # fmt: skip
    a = e7.side_game_stats(moves, "A")
    assert a["iter_per_s"] == pytest.approx(200.0)
    assert a["tree_depth"] == pytest.approx(4.0)
    assert a["rollout_per_iter"] == pytest.approx(100 / 400)
    b = e7.side_game_stats(moves, "B")
    assert b["iter_per_s"] is None and b["depth_reached"] == [4, 6]


def test_ordering_values_match(tmp_path):
    rows = e7.run_ordering(False, tmp_path, fens=[START_FEN], depths=(2,))
    assert len(rows) == 3 and all(r["value_match"] == "1" for r in rows)
    again = e7.run_ordering(False, tmp_path, fens=[START_FEN], depths=(2,))
    assert len(read_rows(tmp_path / "e7_ordering.csv")) == 3 and len(again) == 3
    tab = {r["config"]: r for r in e7.ordering_table(again)}
    assert tab["none"]["nodes_vs_none"] == 1.0
    assert tab["mvv_lva"]["nodes_vs_none"] < 1.0
    assert tab["mvv_lva+tt"]["value_mismatch"] == 0


def ctx_for(tmp_path, pairs=1) -> e7.Ctx:
    ns = argparse.Namespace(quick=True, workers=1, allow_code_change=True, pairs=pairs,
                            raw_dir=tmp_path, table_dir=tmp_path, fig_dir=tmp_path,
                            skip_bench=True)  # fmt: skip
    return e7.Ctx(ns)


def test_run_point_resume_and_summary(tmp_path, monkeypatch):
    monkeypatch.setattr(e7, "GAME", GameSpec("xiangqi", {"max_plies": 16}))
    ctx = ctx_for(tmp_path)
    a = ab_spec(3, use_tt=True, time_limit=0.05, label="ab_t")  # ID → có depth_reached
    rows = e7.run_point(ctx, "a1", a, RANDOM)
    assert len(rows) == 2
    path = e7.raw_path("a1", True, tmp_path)
    before = path.read_bytes()
    e7.run_point(ctx, "a1", a, RANDOM)  # chạy lại: không chơi thêm
    assert path.read_bytes() == before
    moves = read_rows(moves_path_for(path))
    assert "depth_reached" in moves[0]
    assert all(int(m["depth_reached"]) >= 1 for m in moves if m["side"] == "A")
    assert all(m["depth_reached"] == "" for m in moves if m["side"] == "B")
    summ = e7.summarize_point("a1", rows, moves)
    assert [r["split"] for r in summ] == ["all", "A=Đỏ", "A=Đen"]
    s = summ[0]
    assert s["n"] == 2 and sum(s[f"term_{t}"] for t in e7.TERMS) == 2
    assert s["a_depth_reached_mean"] >= 1 and s["b_iter_per_s_mean"] is None
    assert len(read_rows(tmp_path / "e7quick_runinfo.csv")) == 2


def test_part_d_requires_c_and_stops_on_l0(tmp_path, monkeypatch):
    ctx = ctx_for(tmp_path)
    ctx.quick = False
    assert e7.part_d(ctx) == 2  # chưa có c1/c4
    monkeypatch.setattr(e7, "point_score", lambda p, q, d=None: (1.0 if p == "c4" else 0.5, 50))
    ctx.n_pairs = 25
    called = []
    monkeypatch.setattr(e7, "run_point", lambda *a, **k: called.append(a[1]))
    assert e7.part_d(ctx) == 3 and called == []
    monkeypatch.setattr(e7, "point_score", lambda p, q, d=None: (0.5, 50))
    assert e7.part_d(ctx) == 0 and called == ["d1", "d2"]


def test_mcts_spec_runs_one_move():
    g = Xiangqi()
    spec = AgentSpec("mcts", {**e7.mcts(10).params, "time_limit": 0.05})
    assert make_agent(spec, 1).select_move(g) in g.legal_moves()
