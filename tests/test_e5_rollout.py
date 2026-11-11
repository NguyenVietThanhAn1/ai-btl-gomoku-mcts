"""Test E5 (D-20): spec, mref, tái dùng E3, so sánh cặp, kiểm tra hợp lệ, cờ tốc độ, bảng, hình."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import pytest

from gameai.agents.mcts import MCTSAgent
from gameai.agents.registry import AgentSpec, GameSpec, make_agent, make_game
from gameai.arena import derive_seed
from gameai.experiments import e3_c_sweep as e3
from gameai.experiments import e5_rollout as e5
from gameai.experiments.common import read_rows, run_match

# ---------------------------------------------------------------- spec / điểm


def test_specs_differ_only_in_rollout() -> None:
    r = e5.mcts_spec("rand", iterations=1000).params
    h = e5.mcts_spec("h300", iterations=1000).params
    assert r["check_tactics"] is True and h["check_tactics"] is True
    assert r["c"] == h["c"] == 1.4
    common = {k: v for k, v in r.items() if k != "rollout"}
    assert {k: v for k, v in h.items() if k not in ("rollout", "temperature")} == common
    assert r["rollout"] == "random"
    assert (h["rollout"], h["temperature"]) == ("heavy_kinrow", 300)


def test_time_spec_has_no_iteration_budget() -> None:
    s = e5.mcts_spec("h300", time_limit=0.5)
    assert s.params["iterations"] is None and s.params["time_limit"] == 0.5
    assert s.name == "h300_t0.5"
    agent = make_agent(s, 0)
    assert isinstance(agent, MCTSAgent)
    with pytest.raises(ValueError):
        e5.budget_tag()
    with pytest.raises(ValueError):
        e5.budget_tag(100, 0.5)
    with pytest.raises(ValueError):
        e5.mcts_spec("heavy", iterations=10)


@pytest.mark.parametrize("it", e5.ITER_GREEDY)
def test_h300_spec_matches_e3(it: int) -> None:
    assert e5.mcts_spec("h300", iterations=it).params == e3.mcts_spec(15, 1.4, it).params
    raw = e5.RAW_DIR / f"e3_greedy_c1.4_i{it}.csv"
    if not raw.exists():
        pytest.skip("không có raw E3")
    row = read_rows(raw)[0]
    assert json.loads(row["spec_a"])["params"] == e5.mcts_spec("h300", iterations=it).params
    assert json.loads(row["spec_b"])["params"] == e5.GREEDY.params
    assert int(row["base_seed"]) == 0


def test_time_points_use_two_workers_and_iter_points_default() -> None:
    for step in e5.TIME_STEPS:
        for quick in (False, True):
            pts = e5.points(step, quick)
            assert pts and all(
                p.workers == e5.WORKERS_TIME and p.budget_type == "time" for p in pts
            )
            assert {p.budget for p in pts} == set(e5.TIMES)
    for step in (*e5.ITER_STEPS, "ab2-pilot", "ab2"):
        assert all(p.workers is None and p.budget_type == "iter" for p in e5.points(step, False))


def test_grid_sizes_and_quick_subset() -> None:
    full = {p.key for p in e5.all_points(False)}
    quick = {p.key for p in e5.all_points(True)}
    assert quick <= full
    assert len(e5.points("greedy-iter", False)) == 2 * len(e5.ITER_GREEDY)
    assert len(e5.points("mref-iter", False)) == 2 * len(e5.ITER_MAIN)
    assert len(e5.points("h2h-iter", False)) == len(e5.ITER_MAIN)
    assert all(p.n_pairs == e5.N_PAIRS for p in e5.points("greedy-time", False))
    assert all(p.n_pairs == e5.QUICK_PAIRS for p in e5.points("greedy-time", True))
    # quick có điểm kiểm tra hợp lệ rand_i1000 vs mref
    assert ("mref", "iter", 1000.0, "rand") in quick
    pilot = [p for p in e5.points("ab2-pilot", False) if p.rollout == "rand"]
    assert pilot[0].n_pairs == e5.PILOT_PAIRS and pilot[0].budget == e5.AB2_ITER


def test_raw_paths_unique() -> None:
    for quick in (False, True):
        pts = e5.all_points(quick)
        paths = [e5.raw_path(p, quick) for p in pts]
        assert len(set(paths)) == len(paths)


def test_e3_candidates_only_h300_iter_greedy_and_ab2() -> None:
    for p in e5.all_points(False):
        if p.e3_path is not None:
            assert p.rollout == "h300" and p.budget_type == "iter" and p.part in ("greedy", "ab2")
    ab2 = {p.rollout: p for p in e5.points("ab2", False)}
    assert ab2["h300"].e3_path is not None and ab2["rand"].e3_path is None
    assert ab2["rand"].spec_b == e3.AB2


# ---------------------------------------------------------------- mref


def test_mref_built_by_registry_with_separate_seed_stream() -> None:
    assert e5.MREF.params == {"iterations": 1000, "c": 1.4, "check_tactics": True}
    small = AgentSpec(e5.MREF.kind, {**e5.MREF.params, "iterations": 60})
    g = make_game(GameSpec("kinrow", {"n": 7, "k": 4}))
    for m in (24, 25, 17):
        g.play(m)
    a = make_agent(small, 5)
    assert isinstance(a, e5.MRefAgent)
    ref = MCTSAgent(
        iterations=60,
        c=1.4,
        rollout_policy="random",
        check_tactics=True,
        seed=derive_seed(5, "mref"),
    )
    assert a.select_move(g) == ref.select_move(g)
    assert a.last_root_stats() == ref.last_root_stats()


# ---------------------------------------------------------------- tái dùng E3


def _fake_e3(path: Path, n_games: int = 4, **over: str) -> Path:
    spec_a = e5.mcts_spec("h300", iterations=100)
    row = {
        "game_id": "",
        "pair_seed": "",
        "result_a": "1.0",
        "spec_a": json.dumps(spec_a.to_dict()),
        "spec_b": json.dumps(e5.GREEDY.to_dict()),
        "game_spec": json.dumps(e5.GAME15.to_dict()),
        "base_seed": "0",
        "git_dirty": "0",
        "git_commit": "abc1234",
    }
    row.update(over)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, list(row))
        w.writeheader()
        for i in range(n_games):
            w.writerow(
                {
                    **row,
                    "game_id": f"{i // 2}-{'AX' if i % 2 == 0 else 'BX'}",
                    "pair_seed": str(i // 2),
                }
            )
    return path


def test_e3_reusable_ok_and_failures(tmp_path: Path) -> None:
    spec_a = e5.mcts_spec("h300", iterations=100)
    ok = _fake_e3(tmp_path / "ok.csv")
    assert e5.e3_reusable(ok, spec_a, e5.GREEDY, 2, diff_empty=lambda c: True)[0]
    # code đổi từ commit E3
    res = e5.e3_reusable(ok, spec_a, e5.GREEDY, 2, diff_empty=lambda c: False)
    assert not res[0] and "code" in res[1]
    # thiếu ván
    assert not e5.e3_reusable(ok, spec_a, e5.GREEDY, 3, diff_empty=lambda c: True)[0]
    # spec lệch (c khác), dirty, base_seed khác, game khác
    bad_a = AgentSpec("mcts", {**spec_a.params, "c": 2.0})
    assert not e5.e3_reusable(ok, bad_a, e5.GREEDY, 2, diff_empty=lambda c: True)[0]
    assert not e5.e3_reusable(ok, spec_a, e3.AB2, 2, diff_empty=lambda c: True)[0]
    for over in (
        {"git_dirty": "1"},
        {"base_seed": "7"},
        {"game_spec": json.dumps(GameSpec("kinrow", {"n": 3, "k": 3}).to_dict())},
    ):
        f = _fake_e3(tmp_path / "bad.csv", **over)
        assert not e5.e3_reusable(f, spec_a, e5.GREEDY, 2, diff_empty=lambda c: True)[0]
    assert not e5.e3_reusable(tmp_path / "none.csv", spec_a, e5.GREEDY, 2)[0]


def test_e3_label_ignored(tmp_path: Path) -> None:
    spec_a = e5.mcts_spec("h300", iterations=100)
    e3_spec = AgentSpec("mcts", spec_a.params, label="c1.4_i100")
    f = _fake_e3(tmp_path / "x.csv", spec_a=json.dumps(e3_spec.to_dict()))
    assert e5.e3_reusable(f, spec_a, e5.GREEDY, 2, diff_empty=lambda c: True)[0]


def test_real_e3_files_reusable_now() -> None:
    pts = [p for p in e5.all_points(False) if p.e3_path is not None]
    if not all(Path(p.e3_path).exists() for p in pts):
        pytest.skip("không có raw E3")
    for p in pts:
        ok, reason = e5.e3_reusable(p.e3_path, p.spec_a, p.spec_b, e5.N_PAIRS)
        assert ok, reason


# ---------------------------------------------------------------- thống kê


def _rows(results: dict[str, float]) -> list[dict[str, str]]:
    return [{"game_id": g, "result_a": str(v)} for g, v in results.items()]


def test_paired_diff_by_hand() -> None:
    h = _rows({"0-AX": 1.0, "0-BX": 1.0, "1-AX": 0.0, "1-BX": 1.0, "9-AX": 1.0})
    r = _rows({"0-AX": 0.0, "0-BX": 1.0, "1-AX": 0.0, "1-BX": 0.0})
    d = e5.paired_diff(h, r)  # d = [1, 0, 0, 1] trên 4 game_id chung
    assert d["n"] == 4
    assert d["mean_h300"] == 0.75 and d["mean_rand"] == 0.25 and d["diff"] == 0.5
    sd = math.sqrt(1 / 3)  # stdev([1,0,0,1])
    assert d["sd_diff"] == pytest.approx(sd)
    assert d["paired_lo"] == pytest.approx(0.5 - 1.96 * sd / 2)
    hw_i = 1.96 * math.sqrt(0.25 / 4 + 0.25 / 4)  # var([1,1,0,1]) = var([0,1,0,0]) = 0.25
    assert d["indep_hi"] == pytest.approx(0.5 + hw_i)
    assert e5.paired_diff(h, [])["n"] == 0


def test_check_validity() -> None:
    base = {
        "label_a": "rand_i1000",
        "label_b": "mref",
        "n": 50,
        "wins": 24,
        "win_rate": 0.48,
        "distinct_games": 50,
    }
    assert e5.check_validity({**base, "win_lo": 0.35, "win_hi": 0.62})["valid"] == 1
    v = e5.check_validity({**base, "win_lo": 0.55, "win_hi": 0.80})
    assert v["valid"] == 0 and v["contains_half"] == 0 and v["distinct_games"] == 50


def test_ab2_gate_reuses_d18_rule() -> None:
    assert not e5.gate_passes(1) and e5.gate_passes(2)


def test_rate_rows_flags() -> None:
    def row(part: str, t: float, roll: str, a: float, b: float = math.nan) -> dict:
        return {
            "split": "all",
            "budget_type": "time",
            "budget": t,
            "rollout": roll,
            "a_search_iterations_per_move": a,
            "b_search_iterations_per_move": b,
        }

    tables = {
        "h2h": [row("h2h", 0.5, "h300", 500, 1000)],
        "greedy": [
            row("greedy", 0.5, "rand", 1000),
            row("greedy", 2.0, "rand", 2000 * 1.5),
            row("greedy", 0.5, "h300", 500),
        ],
        "mref": [row("mref", 2.0, "h300", 2000), {**row("mref", 2.0, "rand", 1), "split": "A=X"}],
    }
    out = e5.rate_rows(tables, {"rand": 2000.0, "h300": 1000.0})
    assert len(out) == 6  # h2h hai bên + 3 greedy + 1 mref (bỏ dòng không phải "all")
    rand = [r for r in out if r["rollout"] == "rand"]
    assert {r["rate_iter_per_s"] for r in rand} == {2000.0, 1500.0}
    fast = next(r for r in rand if r["rate_iter_per_s"] == 1500.0)
    assert fast["dev_bench"] == -0.25 and fast["flag_bench"] == 1
    assert fast["peer_median"] == 2000.0 and fast["flag_peer"] == 1
    ok = next(r for r in out if r["part"] == "h2h" and r["side"] == "B")
    assert ok["flag_bench"] == 0 and ok["dev_bench"] == 0.0
    h = [r for r in out if r["rollout"] == "h300"]
    assert all(r["flag_peer"] == 0 for r in h)


# ---------------------------------------------------------------- bench, bảng, hình, ước tính


def test_bench_tiny(tmp_path: Path) -> None:
    rows = e5.bench(seconds=0.05, plies=(6,), seeds=(0,), path=tmp_path / "b.csv")
    assert [r["rollout"] for r in rows] == ["rand", "h300"]
    assert all(r["iterations"] > 0 and r["iter_per_s"] > 0 for r in rows)
    assert set(e5.bench_rates(read_rows(tmp_path / "b.csv"))) == {"rand", "h300"}


def test_build_tables_and_figures_end_to_end(tmp_path: Path) -> None:
    raw, tab, fig = tmp_path / "raw", tmp_path / "tab", tmp_path / "fig"
    pts = {p.key: p for p in e5.points("greedy-iter", True)}
    for roll in ("rand", "h300"):
        p = pts[("greedy", "iter", 100.0, roll)]
        run_match(
            e5.raw_path(p, True, raw),
            e5.GAME15,
            p.spec_a,
            p.spec_b,
            1,
            workers=1,
            allow_code_change=True,
        )
    out = e5.build_tables(True, raw, tab, reuse_check=lambda *a, **k: (False, "test"))
    g = read_rows(tab / "e5quick_greedy.csv")
    assert len(g) == 6 and {r["rollout"] for r in g} == {"rand", "h300"}
    assert {r["source"] for r in g} == {"e5"}
    for col in ("budget_type", "budget", "raw", "win_lo", "a_search_iterations_per_move"):
        assert col in g[0]
    paired = read_rows(tab / "e5quick_paired.csv")
    assert len(paired) == 1 and int(paired[0]["n"]) == 2
    for col in ("paired_lo", "paired_hi", "indep_lo", "indep_hi"):
        assert col in paired[0]
    assert out["validity"] == []
    files = e5.make_figures(True, tab, fig)
    assert [f.name for f in files] == ["e5quick_iter.png", "e5quick_time.png"]
    assert all(f.stat().st_size > 0 for f in files)


def test_run_point_writes_runinfo(tmp_path: Path) -> None:
    p = e5.Point(
        "greedy", "iter", 50, "rand", e5.mcts_spec("rand", iterations=50), e5.GREEDY, 1, None
    )
    assert e5.run_point(p, "greedy-iter", True, 1, True, raw_dir=tmp_path) == "e5"
    info = read_rows(tmp_path / "e5quick_runinfo.csv")
    assert len(info) == 1
    r = info[0]
    assert r["workers"] == "1" and r["cpu"] and int(r["logical_cpus"]) >= 1 and r["source"] == "e5"


def test_estimate_full_from_fake_quick(tmp_path: Path) -> None:
    raw, tab = tmp_path / "raw", tmp_path / "tab"
    raw.mkdir()
    for p in e5.all_points(True):
        if p.e3_path is not None:
            continue
        f = e5.raw_path(p, True, raw)
        with f.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, ["a_time_sum", "b_time_sum"])
            w.writeheader()
            w.writerow({"a_time_sum": str(p.budget / 1000 + 1), "b_time_sum": "1"})
    out = e5.estimate_full(raw, tab, workers=4)
    steps = [r["step"] for r in out]
    assert steps[-1].startswith("total") and "h2h-time" in steps and "ab2" in steps
    by = {r["step"]: r for r in out}
    assert by["h2h-time"]["workers"] == e5.WORKERS_TIME and by["h2h-iter"]["workers"] == 4
    # h2h-iter: 1000 không có trong quick → fit; 250, 5000 đo được
    assert "h300_i1000 fit" in by["h2h-iter"]["note"]
    assert by["h2h-iter"]["games"] == 3 * 2 * e5.N_PAIRS
    assert by["ab2"]["games"] == 2 * (e5.N_PAIRS - e5.PILOT_PAIRS)
    assert (tab / "e5quick_estimate.csv").exists()
