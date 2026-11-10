"""Test E3 (D-18): spec, lưới, luật chọn c + cổng AB2, Minimax có cache, bảng, hình, ước tính."""

from __future__ import annotations

import csv

import pytest

from gameai.agents.minimax import MinimaxAgent
from gameai.agents.registry import make_agent
from gameai.experiments import e3_c_sweep as e3
from gameai.games.kinrow import KInRow


def test_mcts_spec_3x3_random_rollout_no_tactics():
    s = e3.mcts_spec(3, 0.5, 250)
    assert s.kind == "mcts"
    assert s.params == {"iterations": 250, "c": 0.5, "check_tactics": False}
    assert s.label == "c0.5_i250"


def test_mcts_spec_15x15_h300_with_tactics():
    s = e3.mcts_spec(15, 2.0, 5000)
    assert s.params == {"iterations": 5000, "c": 2.0, "rollout": "heavy_kinrow",
                        "temperature": 300, "check_tactics": True}  # fmt: skip
    assert "time_limit" not in s.params and "rollout_limit" not in s.params


@pytest.mark.parametrize("name", list(e3.PARTS))
def test_points_labels_unique_and_quick_subset(name):
    part = e3.PARTS[name]
    full = e3.points(part, False)
    quick = e3.points(part, True)
    assert len({e3.label_for(c, it) for c, it in full}) == len(full)
    assert set(quick) <= set(full)


def test_grid_sizes_and_games_per_point():
    assert len(e3.points(e3.PARTS["3x3_random"], False)) == 24
    assert e3.PARTS["3x3_random"].n_pairs * 2 == 200
    assert e3.PARTS["3x3_minimax"].n_pairs * 2 == 100
    assert e3.PARTS["greedy"].n_pairs * 2 == 50
    assert e3.PARTS["ab2"].iterations == (2500, 5000)
    assert e3.PILOT_PAIRS * 2 == 20


def _greedy_table(rates: dict[float, float], it: int = 5000) -> list[dict]:
    rows = [{"split": "all", "c": c, "iterations": it, "win_rate": w} for c, w in rates.items()]
    rows += [{"split": "A=X", "c": 0.5, "iterations": it, "win_rate": 1.0}]  # bị bỏ qua
    rows += [{"split": "all", "c": 0.5, "iterations": 1000, "win_rate": 1.0}]  # iter khác
    return rows


@pytest.mark.parametrize(
    "rates, expected",
    [
        ({0.5: 0.2, 1.0: 0.6, 1.4: 0.4, 2.0: 0.1}, 1.0),  # max rõ
        ({0.5: 0.6, 1.0: 0.2, 1.4: 0.6, 2.0: 0.6}, 1.4),  # hòa có 1.4
        ({0.5: 0.6, 1.0: 0.2, 1.4: 0.4, 2.0: 0.6}, 2.0),  # hòa không có 1.4 → gần 1.4 nhất
        ({0.5: 0.6, 1.0: 0.6, 1.4: 0.4, 2.0: 0.6}, 1.0),
    ],
)
def test_choose_pilot_c(rates, expected):
    assert e3.choose_pilot_c(_greedy_table(rates)) == expected


def test_choose_pilot_c_reads_csv_strings():
    rows = [{"split": "all", "c": "0.5", "iterations": "5000", "win_rate": "0.3"},
            {"split": "all", "c": "2.0", "iterations": "5000", "win_rate": "0.5"}]  # fmt: skip
    assert e3.choose_pilot_c(rows) == 2.0
    with pytest.raises(ValueError):
        e3.choose_pilot_c(rows, iterations=2500)


@pytest.mark.parametrize("wins, ok", [(0, False), (1, False), (2, True), (20, True)])
def test_gate(wins, ok):
    assert e3.gate_passes(wins) is ok


def test_cached_minimax_built_by_registry_and_caches():
    e3._MINIMAX_CACHE.clear()
    spec = e3.PARTS["3x3_minimax"].opponent
    a = make_agent(spec, 1)
    assert isinstance(a, e3.CachedMinimaxAgent)
    g = KInRow(3, 3)
    for m in (0, 4, 8):  # X 0, O 4, X 8 → O phải đi cạnh
        g.play(m)
    m1 = a.select_move(g)
    assert a.stats["cache_hit"] == 0 and a.stats["nodes"] > 0
    m2 = make_agent(spec, 2).select_move(g)
    b = make_agent(spec, 3)
    b.select_move(g)
    assert b.stats["cache_hit"] == 1 and b.stats["nodes"] == 0
    optimal = {m for m, v in MinimaxAgent().root_values(g) if v == 0}
    assert {m1, m2} <= optimal == {1, 3, 5, 7}


def test_cached_minimax_blocks_and_randomizes_among_optimal():
    e3._MINIMAX_CACHE.clear()
    g = KInRow(3, 3)
    for m in (0, 4, 1):  # X dọa 0-1-2 → O phải chặn 2
        g.play(m)
    assert e3.CachedMinimaxAgent(seed=0).select_move(g) == 2
    empty = KInRow(3, 3)
    picks = {e3.CachedMinimaxAgent(seed=s).select_move(empty) for s in range(30)}
    assert len(picks) > 1  # bàn trống: mọi ô đều hòa → chọn ngẫu nhiên
    assert len(e3._MINIMAX_CACHE) == 2


def test_run_part_end_to_end_tiny(tmp_path):
    table = e3.run_part("3x3_random", quick=True, workers=1, allow_code_change=True,
                        pts=[(1.4, 20), (0.5, 20)], n_pairs=1,
                        raw_dir=tmp_path / "raw", table_dir=tmp_path / "tables")  # fmt: skip
    assert len(table) == 6  # 2 điểm × 3 split
    assert {(r["c"], r["iterations"]) for r in table} == {(1.4, 20), (0.5, 20)}
    assert (tmp_path / "raw" / "e3quick_3x3_random_c1.4_i20.csv").exists()
    with (tmp_path / "tables" / "e3quick_3x3_random.csv").open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert list(rows[0]) == e3.TABLE_COLUMNS
    assert all(int(r["n"]) in (1, 2) for r in rows)
    assert sum(int(r["n"]) for r in rows if r["split"] == "all") == 4


def test_fit_cost_exact_line():
    a, b = e3.fit_cost([(100, 1.0 + 0.001 * 100), (1000, 2.0), (5000, 6.0)])
    assert a == pytest.approx(1.0) and b == pytest.approx(0.001)
    assert e3.fit_cost([(100, 2.0), (100, 4.0)]) == (3.0, 0.0)


def test_estimate_full_from_fake_quick(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    for part in ("3x3_random", "3x3_minimax", "greedy", "ab2"):
        for it in (100, 5000):
            with (raw / f"e3quick_{part}_c1.4_i{it}.csv").open("w", newline="") as f:
                w = csv.DictWriter(f, ["a_time_sum", "b_time_sum"])
                w.writeheader()
                w.writerow({"a_time_sum": 0.001 * it, "b_time_sum": 1.0})
    (raw / "e3quick_greedy_c1.4_i100_moves.csv").write_text("x\n1\n")  # bị bỏ qua
    out = {r["part"]: r for r in e3.estimate_full(raw, tmp_path)}
    g = out["greedy"]
    assert g["games"] == 24 * 50
    # Σ_iter 50·4·(1 + 0.001·iter) = 200·(6 + 9.35) giây
    assert g["seq_minutes"] == pytest.approx(round(200 * 15.35 / 60, 1))
    assert out["ab2_full"]["games"] == 8 * 50 - 20
    assert out["ab2_pilot"]["games"] == 20
    assert (tmp_path / "e3quick_estimate.csv").exists()


def test_plot_panels_writes_png(tmp_path):
    rows = []
    for c in e3.C_VALUES:
        for it in (100, 1000, 5000):
            p = min(1.0, 0.5 + it / 10000 + c / 10)
            rows.append({"split": "all", "c": str(c), "iterations": str(it), "win_rate": p,
                         "win_lo": p - 0.1, "win_hi": min(1.0, p + 0.05), "nonloss_rate": p,
                         "nonloss_lo": p - 0.1, "nonloss_hi": 1.0})  # fmt: skip
    path = e3.plot_panels([(rows, "win", "a"), (rows, "nonloss", "b")], tmp_path / "f.png", "t")
    assert path.exists() and path.read_bytes()[:4] == b"\x89PNG"
