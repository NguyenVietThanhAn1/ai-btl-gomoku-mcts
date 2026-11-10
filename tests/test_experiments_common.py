"""Test experiments/common.py: run_match (CSV, resume, song song), summarize, wilson (P4.1)."""

from __future__ import annotations

import csv
import math

import pytest

from gameai.agents.registry import AgentSpec, GameSpec
from gameai.experiments import common
from gameai.experiments.common import (
    GAME_COLUMNS,
    MOVE_COLUMNS,
    ResumeError,
    moves_path_for,
    read_rows,
    run_match,
    summarize,
    wilson,
    write_summary,
)

G3 = GameSpec("kinrow", {"n": 3, "k": 3})
MCTS30 = AgentSpec("mcts", {"iterations": 30}, label="mcts30")
GREEDY = AgentSpec("greedy", label="greedy")
RANDOM = AgentSpec("random", label="random")
# AB tìm hết cây 3×3 + TT + ordering: chơi hoàn hảo, tất định, nhanh hơn Minimax nhiều
PERFECT = AgentSpec(
    "alphabeta", {"seeded": False, "use_tt": True, "order": "move_score"}, label="perfect"
)

# cột thay đổi giữa các lần chạy dù cùng seed
VOLATILE = {"finished_at", "workers"} | {c for c in GAME_COLUMNS if "time" in c}
VOLATILE_MOVES = {"time", "agent_time"}


def _stable(rows, volatile=VOLATILE):
    return sorted(
        (tuple((k, v) for k, v in r.items() if k not in volatile) for r in rows),
    )


def _run(path, n_pairs=2, workers=1, **kw):
    kw.setdefault("spec_a", MCTS30)
    kw.setdefault("spec_b", GREEDY)
    return run_match(path, G3, n_pairs=n_pairs, workers=workers, **kw)


# ---------------------------------------------------------------- wilson


def test_wilson_known_values():
    lo, hi = wilson(5, 10)
    assert lo == pytest.approx(0.2366, abs=1e-4) and hi == pytest.approx(0.7634, abs=1e-4)
    lo, hi = wilson(0, 10)
    assert lo == 0.0 and hi == pytest.approx(0.2775, abs=1e-4)
    lo, hi = wilson(10, 10)
    assert lo == pytest.approx(0.7225, abs=1e-4) and hi == 1.0
    assert all(math.isnan(x) for x in wilson(0, 0))


# ---------------------------------------------------------------- CSV


def test_csv_columns_and_rows(tmp_path):
    out = tmp_path / "m.csv"
    rows = _run(out, n_pairs=2)
    with open(out, newline="", encoding="utf-8") as f:
        header = next(csv.reader(f))
    assert header == GAME_COLUMNS
    with open(moves_path_for(out), newline="", encoding="utf-8") as f:
        assert next(csv.reader(f)) == MOVE_COLUMNS
    assert len(rows) == 4 and {r["game_id"] for r in rows} == {"0-AX", "0-BX", "1-AX", "1-BX"}
    for r in rows:
        assert set(r) == set(GAME_COLUMNS)
        assert r["label_a"] == "mcts30" and r["label_b"] == "greedy"
        assert r["termination"] == "normal"
        assert int(r["a_moves"]) + int(r["b_moves"]) == int(r["n_moves"])
        assert len(r["moves"].split(";")) == int(r["n_moves"])
        assert int(r["a_iterations_sum"]) == 30 * int(r["a_moves"])
        assert float(r["a_iterations_mean"]) == 30.0
        assert r["b_iterations_sum"] == "0"
        assert r["a_cutoffs_sum"] == ""  # MCTS không có cutoffs
        assert r["config_hash"] and r["git_commit"] and r["git_dirty"] in ("0", "1")
        assert r["workers"] == "1"
    moves = read_rows(moves_path_for(out))
    assert len(moves) == sum(int(r["n_moves"]) for r in rows)
    m0 = [m for m in moves if m["game_id"] == "0-AX" and m["ply"] == "0"][0]
    assert m0["side"] == "A" and m0["player"] == "1" and m0["iterations"] == "30"
    assert m0["agent_time"] != "" and m0["time"] != ""


def test_record_moves_false(tmp_path):
    out = tmp_path / "m.csv"
    _run(out, n_pairs=1, record_moves=False)
    assert not moves_path_for(out).exists()


# ---------------------------------------------------------------- determinism / swap


def test_same_seed_same_results(tmp_path):
    a = _run(tmp_path / "a.csv", n_pairs=3, base_seed=7)
    b = _run(tmp_path / "b.csv", n_pairs=3, base_seed=7)
    assert _stable(a) == _stable(b)
    c = _run(tmp_path / "c.csv", n_pairs=3, base_seed=8)
    assert _stable(a) != _stable(c)


def test_parallel_equals_sequential(tmp_path):
    seq = _run(tmp_path / "s.csv", n_pairs=3, workers=1)
    par = _run(tmp_path / "p.csv", n_pairs=3, workers=2)
    assert _stable(seq) == _stable(par)
    ms = read_rows(moves_path_for(tmp_path / "s.csv"))
    mp = read_rows(moves_path_for(tmp_path / "p.csv"))
    assert _stable(ms, VOLATILE_MOVES) == _stable(mp, VOLATILE_MOVES)
    assert {r["workers"] for r in par} == {"2"}


def test_swap_each_seed_two_games(tmp_path):
    rows = _run(tmp_path / "m.csv", n_pairs=3, base_seed=4, spec_a=PERFECT, spec_b=RANDOM)
    by_seed = {}
    for r in rows:
        by_seed.setdefault(r["pair_seed"], []).append(r["a_is_x"])
    assert by_seed == {"4": by_seed["4"], "5": by_seed["5"], "6": by_seed["6"]}
    assert all(sorted(v) == ["0", "1"] for v in by_seed.values())
    for r in rows:
        w = int(r["winner"])
        a_player = 1 if r["a_is_x"] == "1" else -1
        expect = 0.5 if w == 0 else (1.0 if w == a_player else 0.0)
        assert float(r["result_a"]) == expect
        assert expect >= 0.5  # minimax không thua random
    moves = read_rows(moves_path_for(tmp_path / "m.csv"))
    for m in moves:
        a_is_x = m["game_id"].endswith("AX")
        a_player = "1" if a_is_x else "-1"
        assert m["side"] == ("A" if m["player"] == a_player else "B")


# ---------------------------------------------------------------- resume


def test_resume_skips_done_and_matches_full_run(tmp_path):
    out = tmp_path / "m.csv"
    first = _run(out, n_pairs=2)
    done_at = {r["game_id"]: r["finished_at"] for r in first}
    rows = _run(out, n_pairs=4)
    assert len(rows) == 8 and len({r["game_id"] for r in rows}) == 8
    for r in rows:  # ván cũ không bị chơi lại
        if r["game_id"] in done_at:
            assert r["finished_at"] == done_at[r["game_id"]]
    full = _run(tmp_path / "full.csv", n_pairs=4)
    assert _stable(rows) == _stable(full)
    assert _stable(read_rows(moves_path_for(out)), VOLATILE_MOVES) == _stable(
        read_rows(moves_path_for(tmp_path / "full.csv")), VOLATILE_MOVES
    )


def test_resume_after_interrupted_write(tmp_path):
    out = tmp_path / "m.csv"
    _run(out, n_pairs=2)
    games = read_rows(out)
    # mô phỏng bị ngắt: bỏ dòng ván cuối nhưng giữ moves của nó (mồ côi) + dòng ván cắt dở
    lost = games[-1]["game_id"]
    lines = out.read_text(encoding="utf-8").splitlines(keepends=True)
    out.write_text("".join(lines[:-1]) + lines[-1][: len(lines[-1]) // 2], encoding="utf-8")
    mp = moves_path_for(out)
    with open(mp, "a", encoding="utf-8", newline="") as f:
        f.write("1-BX,0,A,1,4,0.0")  # dòng moves cắt dở, không có xuống dòng
    rows = _run(out, n_pairs=2)
    assert len(rows) == 4 and len({r["game_id"] for r in rows}) == 4
    assert lost in {r["game_id"] for r in rows}
    moves = read_rows(mp)
    per_game = {}
    for m in moves:
        per_game.setdefault(m["game_id"], []).append(int(m["ply"]))
    for r in rows:  # mỗi ván đúng một bộ moves, không trùng
        assert sorted(per_game[r["game_id"]]) == list(range(int(r["n_moves"])))
    assert mp.read_text(encoding="utf-8").endswith("\n")
    full = _run(tmp_path / "full.csv", n_pairs=2)
    assert _stable(rows) == _stable(full)


def test_resume_config_change_raises(tmp_path):
    out = tmp_path / "m.csv"
    _run(out, n_pairs=1)
    with pytest.raises(ResumeError, match="config"):
        _run(out, n_pairs=1, spec_a=AgentSpec("mcts", {"iterations": 31}, label="mcts30"))
    with pytest.raises(ResumeError, match="config"):
        _run(out, n_pairs=1, max_moves=5)
    with pytest.raises(ResumeError, match="config"):
        _run(out, n_pairs=1, base_seed=3)


def test_resume_header_mismatch_raises(tmp_path):
    out = tmp_path / "m.csv"
    out.write_text("a,b,c\n1,2,3\n", encoding="utf-8")
    with pytest.raises(ResumeError, match="header"):
        _run(out, n_pairs=1)


def test_resume_code_change(tmp_path, monkeypatch):
    out = tmp_path / "m.csv"
    _run(out, n_pairs=1)
    monkeypatch.setattr(common, "git_info", lambda: ("f" * 40, False))
    with pytest.raises(ResumeError, match="commit"):
        _run(out, n_pairs=2)
    rows = _run(out, n_pairs=2, allow_code_change=True)
    assert len(rows) == 4
    assert {r["git_commit"] for r in rows if r["pair_seed"] == "1"} == {"f" * 40}
    assert {r["git_commit"] for r in rows if r["pair_seed"] == "0"} != {"f" * 40}


def test_resume_dirty_flag_change_raises(tmp_path, monkeypatch):
    out = tmp_path / "m.csv"
    monkeypatch.setattr(common, "git_info", lambda: ("a" * 40, False))
    _run(out, n_pairs=1)
    monkeypatch.setattr(common, "git_info", lambda: ("a" * 40, True))
    with pytest.raises(ResumeError, match="commit"):
        _run(out, n_pairs=1)


# ---------------------------------------------------------------- errors


def test_faulty_agent_loses_batch_continues(tmp_path):
    out = tmp_path / "m.csv"
    bad = AgentSpec("arena_helpers:RaisingAgent", {"fail_at": 1}, label="raiser")
    rows = _run(out, n_pairs=2, spec_a=bad, spec_b=RANDOM, workers=2)
    assert len(rows) == 4
    for r in rows:
        assert r["termination"] == "exception" and r["error_side"] == "A"
        assert r["result_a"] == "0.0" and "boom" in r["error"]
    for kind, term in (("IllegalAgent", "illegal_move"), ("MutatingAgent", "mutated_game")):
        rows = _run(
            tmp_path / f"{kind}.csv",
            n_pairs=1,
            spec_a=RANDOM,
            spec_b=AgentSpec(f"arena_helpers:{kind}"),
        )
        assert {r["termination"] for r in rows} == {term}
        assert {r["error_side"] for r in rows} == {"B"} and {r["result_a"] for r in rows} == {"1.0"}


def test_build_error_stops_batch_before_writing(tmp_path):
    out = tmp_path / "m.csv"
    with pytest.raises(ValueError, match="bad config"):
        _run(out, n_pairs=2, spec_a=AgentSpec("arena_helpers:BrokenInitAgent"))
    assert not out.exists() or len(read_rows(out)) == 0
    with pytest.raises(ValueError):
        _run(tmp_path / "x.csv", n_pairs=1, spec_b=AgentSpec("no_such_kind"))


def test_max_moves_draw(tmp_path):
    rows = _run(tmp_path / "m.csv", n_pairs=1, spec_a=RANDOM, spec_b=RANDOM, max_moves=3)
    assert {r["termination"] for r in rows} == {"max_moves"}
    assert {r["winner"] for r in rows} == {"0"} and {r["n_moves"] for r in rows} == {"3"}


def test_random_opening_recorded(tmp_path):
    rows = _run(tmp_path / "m.csv", n_pairs=2, spec_a=RANDOM, spec_b=RANDOM, random_opening=2)
    for r in rows:
        assert len(r["opening"].split(";")) == 2 and r["random_opening"] == "2"
    by_seed = {}
    for r in rows:
        by_seed.setdefault(r["pair_seed"], set()).add(r["opening"])
    assert all(len(v) == 1 for v in by_seed.values())  # hai ván của một seed cùng khai cuộc
    off = _run(tmp_path / "off.csv", n_pairs=1, spec_a=RANDOM, spec_b=RANDOM)
    assert {r["opening"] for r in off} == {""}


# ---------------------------------------------------------------- summarize


def test_summarize_counts_and_splits(tmp_path):
    rows = _run(tmp_path / "m.csv", n_pairs=3, spec_a=PERFECT, spec_b=RANDOM)
    summ = summarize(rows)
    assert [s["split"] for s in summ] == ["all", "A=X", "A=O"]
    tot = summ[0]
    assert tot["label_a"] == "perfect" and tot["label_b"] == "random"
    assert tot["n"] == 6 and tot["wins"] + tot["draws"] + tot["losses"] == 6
    assert tot["losses"] == 0 and tot["nonloss_rate"] == 1.0
    assert tot["win_rate"] == pytest.approx(tot["wins"] / 6)
    lo, hi = wilson(tot["wins"], 6)
    assert (tot["win_lo"], tot["win_hi"]) == (pytest.approx(lo), pytest.approx(hi))
    assert tot["score"] == pytest.approx((tot["wins"] + 0.5 * tot["draws"]) / 6)
    assert summ[1]["n"] == summ[2]["n"] == 3
    assert summ[1]["wins"] + summ[2]["wins"] == tot["wins"]
    assert tot["errors"] == 0
    assert tot["a_nodes_per_move"] > 0 and tot["b_nodes_per_move"] == 0


def test_summarize_distinct_games_detects_duplicates(tmp_path):
    # hai agent tất định → mọi ván cùng lượt giống hệt nhau
    rows = _run(tmp_path / "m.csv", n_pairs=3, spec_a=PERFECT, spec_b=PERFECT)
    summ = {s["split"]: s for s in summarize(rows)}
    assert summ["A=X"]["distinct_games"] == 1 and summ["A=O"]["distinct_games"] == 1
    assert summ["all"]["distinct_games"] == 2  # khác vai A/B nên tính riêng
    rows = _run(tmp_path / "r.csv", n_pairs=3, spec_a=RANDOM, spec_b=RANDOM)
    assert {s["split"]: s for s in summarize(rows)}["all"]["distinct_games"] > 2


def test_summarize_groups_by_pair_and_counts_errors(tmp_path):
    a = _run(tmp_path / "a.csv", n_pairs=1, spec_a=PERFECT, spec_b=RANDOM)
    b = _run(
        tmp_path / "b.csv",
        n_pairs=1,
        spec_a=RANDOM,
        spec_b=AgentSpec("arena_helpers:IllegalAgent", label="illegal"),
    )
    summ = summarize(a + b)
    assert len(summ) == 6
    bad = [s for s in summ if s["label_b"] == "illegal" and s["split"] == "all"][0]
    assert bad["errors"] == 2 and bad["wins"] == 2


def test_write_summary(tmp_path):
    rows = _run(tmp_path / "m.csv", n_pairs=1, spec_a=PERFECT, spec_b=RANDOM)
    p = tmp_path / "tables" / "s.csv"
    write_summary(summarize(rows), p)
    got = read_rows(p)
    assert len(got) == 3 and got[0]["split"] == "all" and "win_lo" in got[0]


def test_add_runner_args_defaults():
    import argparse

    p = common.add_runner_args(argparse.ArgumentParser())
    ns = p.parse_args([])
    assert ns.workers == 4 and ns.allow_code_change is False and ns.quick is False
    ns = p.parse_args(["--workers", "2", "--allow-code-change", "--quick"])
    assert ns.workers == 2 and ns.allow_code_change is True and ns.quick is True


def _fake_game(gid, a_is_x, result_a):
    r = {c: "" for c in GAME_COLUMNS}
    r.update(game_id=gid, label_a="A", label_b="B", a_is_x=a_is_x, result_a=result_a,
             termination="normal", error_side="", n_moves="0", opening="", moves="",
             a_moves="4", a_iterations_sum="300")  # fmt: skip
    return r


def _fake_move(gid, ply, side, its, tactic):
    return {"game_id": gid, "ply": str(ply), "side": side, "iterations": str(its),
            "tactic": str(tactic)}  # fmt: skip


def test_summarize_search_iterations_skip_direct_moves():
    """Nước thắng/chặn ngay (tactic 1, 2; 0 iteration) bị bỏ; restrict (3) vẫn tính là search."""
    rows = [_fake_game("0-AX", "1", "1.0"), _fake_game("0-BX", "0", "0.0")]
    moves = [
        _fake_move("0-AX", 0, "A", 100, 0), _fake_move("0-AX", 1, "A", 0, 2),
        _fake_move("0-AX", 2, "A", 200, 3), _fake_move("0-AX", 3, "A", 0, 1),
        _fake_move("0-AX", 4, "B", "", ""), _fake_move("0-BX", 0, "A", 300, 0),
        _fake_move("0-BX", 1, "B", "", ""),
    ]  # fmt: skip
    by = {s["split"]: s for s in common.summarize(rows, moves)}
    # A: 3 nước có search (100, 200, 300) trên 5 nước → 200/nước, cột cũ không đổi quy ước
    assert by["all"]["a_search_moves"] == 3
    assert by["all"]["a_search_iterations_per_move"] == pytest.approx(200.0)
    assert by["A=X"]["a_search_moves"] == 2  # chỉ ván 0-AX: 100, 200
    assert by["A=X"]["a_search_iterations_per_move"] == pytest.approx(150.0)
    assert by["A=O"]["a_search_iterations_per_move"] == pytest.approx(300.0)
    # B không có khóa iterations (ô trống) → không có nước search, nan
    assert by["all"]["b_search_moves"] == 0
    assert math.isnan(by["all"]["b_search_iterations_per_move"])
    assert by["all"]["a_iterations_per_move"] == pytest.approx(300 * 2 / 8)  # cột cũ: tính mọi nước


def test_summarize_without_moves_gives_nan_search_columns():
    s = common.summarize([_fake_game("0-AX", "1", "1.0")])[0]
    assert math.isnan(s["a_search_moves"]) and math.isnan(s["a_search_iterations_per_move"])


def test_summarize_search_iterations_real_match(tmp_path):
    """Qua run_match thật: khớp nguyên văn với moves file; agent không tactic → bằng cột cũ."""
    out = tmp_path / "m.csv"
    rows = _run(out)
    moves = common.read_rows(common.moves_path_for(out))
    s = [x for x in common.summarize(rows, moves) if x["split"] == "all"][0]
    expect = [float(m["iterations"]) for m in moves if m["side"] == "A" and m["iterations"] != ""]
    assert s["a_search_moves"] == len(expect)
    assert s["a_search_iterations_per_move"] == pytest.approx(sum(expect) / len(expect))


def test_parallel_writes_each_game_as_it_finishes(tmp_path):
    """Song song: ván đầu phải có trong file trước khi batch kết thúc (không dồn về cuối)."""
    import threading
    import time

    out = tmp_path / "m.csv"
    slow = AgentSpec("arena_helpers:SlowAgent", {"sleep": 0.25}, label="slow")
    first_row_at: list[float] = []
    stop = threading.Event()

    def watch() -> None:
        while not stop.is_set():
            if out.exists() and out.read_bytes().count(b"\n") >= 2:  # header + 1 ván
                first_row_at.append(time.perf_counter())
                return
            time.sleep(0.01)

    t = threading.Thread(target=watch)
    t.start()
    rows = _run(out, n_pairs=2, spec_a=slow, spec_b=slow, workers=2)  # 4 ván, mỗi ván ≥ 1 s
    end = time.perf_counter()
    stop.set()
    t.join()
    assert len(rows) == 4
    assert first_row_at and end - first_row_at[0] > 0.8


def test_time_measured_by_arena_not_agent(tmp_path):
    # SlowAgent không ghi stats["time"] → agent_time trống, còn time (arena đo) ≥ thời gian ngủ
    out = tmp_path / "m.csv"
    slow = AgentSpec("arena_helpers:SlowAgent", {"sleep": 0.05}, label="slow")
    rows = _run(out, n_pairs=1, spec_a=slow, spec_b=RANDOM)
    moves = [m for m in read_rows(moves_path_for(out)) if m["side"] == "A"]
    assert moves and all(m["agent_time"] == "" and float(m["time"]) >= 0.05 for m in moves)
    assert all(float(r["a_time_mean"]) >= 0.05 for r in rows)


def test_worker_error_outside_game_stops_batch(tmp_path):
    # 3×3 không đặt được 9 quân khai cuộc mà ván chưa kết thúc → lỗi trong worker, ngoài ván
    with pytest.raises(ValueError, match="khai cuộc"):
        _run(
            tmp_path / "m.csv", n_pairs=2, spec_a=RANDOM, spec_b=RANDOM, random_opening=9, workers=2
        )
