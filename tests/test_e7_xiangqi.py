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


def test_exploratory_d3_d4_specs():
    # d3/d4 (khám phá): MCTS L10 1 s tactics bật vs AB cùng cấu hình a1/a2; không nằm trong (d)/all
    for point, depth in (("d3", 1), ("d4", 2)):
        a, b = e7.FIXED_POINTS[point]
        assert a == e7.mcts(10) and a.params["time_limit"] == 1.0 and a.params["check_tactics"]
        assert b == e7.FIXED_POINTS[f"a{depth}"][0] and b.params["depth"] == depth
        assert "time_limit" not in b.params or b.params["time_limit"] is None
    assert set(e7.X_POINTS).isdisjoint(e7.D_POINTS) and "dx" in e7.PARTS


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


def test_estimate_uses_cli_workers_not_stale_quick_file(tmp_path):
    # file quick cũ khuyến nghị 2 worker → ước tính vẫn dùng --workers (ở đây 1)
    (tmp_path / "e7quick_workers.csv").write_text(
        "workers,median_iter_per_s,recommend\ndrop,0.25,2\n", encoding="utf-8"
    )
    cols = ["game_id", "a_time_sum", "b_time_sum"]
    rows = [{"game_id": f"{i}-AX", "a_time_sum": 10.0, "b_time_sum": 14.0} for i in range(4)]
    e7._write(e7.raw_path("d3", True, tmp_path), cols, rows)
    ctx = ctx_for(tmp_path)
    e7.write_estimate(ctx)
    est = {r["part"]: r for r in read_rows(tmp_path / "e7quick_estimate.csv")}
    assert est["d3"]["workers"] == "1"
    assert float(est["d3"]["full_min"]) == pytest.approx(24.0 * 2 * e7.N_PAIRS / 60, abs=1e-3)
    ctx.workers = 3
    e7.write_estimate(ctx)
    est = {r["part"]: r for r in read_rows(tmp_path / "e7quick_estimate.csv")}
    assert float(est["d3"]["full_min"]) == pytest.approx(24.0 * 2 * e7.N_PAIRS / 3 / 60, abs=1e-3)


def test_branching_stats_hand_game():
    """D-39: replay khai cuộc + nước; đếm nước hợp lệ mỗi thế có tác tử đi; iteration chỉ của MCTS
    L10 có search (bỏ tactic 1/2), chia cho số nước hợp lệ ở gốc."""
    g = Xiangqi()
    opening = [iccs_to_move("h2e2")]
    g.play(opening[0])
    n1 = len(g.legal_moves())  # thế ply 0 sau khai cuộc (Đen đi)
    m1 = iccs_to_move("h9g7")
    g.play(m1)
    n2 = len(g.legal_moves())
    m2 = iccs_to_move("h0g2")
    row = {
        "game_id": "1-AX",
        "game_spec": json.dumps({"kind": "xiangqi", "params": {"max_plies": 200}}),
        "opening": str(opening[0]),
        "label_a": "mcts_L10",
        "label_b": "random",
    }
    moves = [  # cố tình đảo thứ tự: hàm phải sắp theo ply
        {"game_id": "1-AX", "ply": "1", "side": "B", "move": str(m2), "tactic": "",
         "iterations": "0"},
        {"game_id": "1-AX", "ply": "0", "side": "A", "move": str(m1), "tactic": "0",
         "iterations": "300"},
    ]  # fmt: skip
    st = e7.branching_stats([row], moves)
    assert st["legal"] == [n1, n2]
    assert st["iters"] == [300.0] and st["per_root"] == [300.0 / n1]
    moves[1]["tactic"] = "1"  # nước đi thẳng nhờ tactics → không tính iteration
    assert e7.branching_stats([row], moves)["iters"] == []
    row["label_a"] = "mcts_L0"  # chỉ MCTS L10
    assert e7.branching_stats([row], moves)["iters"] == []


def test_build_tables_rerun_identical(tmp_path):
    """`build_tables` tất định: chạy hai lần cho bảng giống byte (plots --check dựa vào đây)."""
    raw = tmp_path / "raw"
    raw.mkdir()
    src = e7.RAW_DIR
    for p in ("d3",):
        for suffix in ("", "_moves"):
            f = src / f"e7_{p}{suffix}.csv"
            if not f.exists():
                pytest.skip("không có raw E7")
            (raw / f.name).write_bytes(f.read_bytes())
    t1, t2, fig = tmp_path / "t1", tmp_path / "t2", tmp_path / "fig"
    for t in (t1, t2):
        t.mkdir()
        _, tables, _ = e7.build_tables(raw, t, fig)
    assert {p.name for p in tables} == {"e7_matches.csv", "e7_branching.csv"}
    for name in ("e7_matches.csv", "e7_branching.csv"):
        assert (t1 / name).read_bytes() == (t2 / name).read_bytes()
    br = read_rows(t1 / "e7_branching.csv")
    assert [r["point"] for r in br] == ["d3", "all"] and br[1]["iter_per_move_mean"] == ""
