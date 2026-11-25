"""P6.3: script đo thời gian/nước GUI (chỉ 3×3, bench giả để nhanh)."""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402

from gameai.experiments import p63_gui_timing as t  # noqa: E402
from gameai.experiments.common import read_rows  # noqa: E402
from gameai.gui.presets import DIFFICULTY  # noqa: E402


def test_measure_level_3x3_columns():
    pygame.init()
    key = (3, "alphabeta", "hard")
    row = t.measure_level(3, key, DIFFICULTY[key], "random_human", 2, pygame.Surface((1280, 720)),
                          "AC")  # fmt: skip
    assert set(row) == set(t.TIMING_COLUMNS)
    assert row["source"] == "E1" and row["games"] == 2 and row["ai_moves"] >= 2
    assert row["note"] == t.NOTE and row["max_s"] >= 0


def test_run_writes_tables_and_keeps_other_board(tmp_path, monkeypatch):
    fake = [{"rollout": "rand", "plies": 8, "seed": 0, "iterations": 10, "agent_time": 1.0,
             "iter_per_s": 10.0}]  # fmt: skip
    monkeypatch.setattr(t, "bench", lambda **kw: [dict(r) for r in fake])
    monkeypatch.setattr(t, "QUICK_GAMES", {3: 1, 15: 1})
    (tmp_path / "e5_bench.csv").write_text("rollout,plies,seed,iter_per_s\nrand,8,0,20\n")
    old = {c: "" for c in t.TIMING_COLUMNS} | {"board": "15", "kind": "mcts", "level": "hard"}
    t._write(tmp_path / "p63quick_gui_timing.csv", t.TIMING_COLUMNS, [old])
    rows = t.run([3], quick=True, table_dir=tmp_path)
    assert len(rows) == 6
    table = read_rows(tmp_path / "p63quick_gui_timing.csv")
    assert [r["board"] for r in table].count("3") == 6 and table[-1]["board"] == "15"
    info = read_rows(tmp_path / "p63quick_gui_runinfo.csv")
    assert len(info) == 1 and info[0]["bench_speed_vs_e5"] == "0.5" and info[0]["boards"] == "3"
    assert read_rows(tmp_path / "p63quick_bench.csv")[0]["speed_vs_e5"] == "0.5"


def test_measure_level_has_fps_columns():
    pygame.init()
    key = (3, "mcts", "easy")
    row = t.measure_level(3, key, DIFFICULTY[key], "random_human", 1, pygame.Surface((1280, 720)),
                          "AC")  # fmt: skip
    assert "fps_think" in row and "fps_worst" in row
    assert row["fps_think"] == "" or 0 < row["fps_think"] <= 1000


def test_filters_and_tag_write_elsewhere(tmp_path, monkeypatch):
    fake = [{"rollout": "rand", "plies": 8, "seed": 0, "iterations": 10, "agent_time": 1.0,
             "iter_per_s": 10.0}]  # fmt: skip
    monkeypatch.setattr(t, "bench", lambda **kw: [dict(r) for r in fake])
    monkeypatch.setattr(t, "QUICK_GAMES", {3: 1, 15: 1})
    monkeypatch.setattr(t, "TAG", "p64x")
    rows = t.run([3], quick=True, table_dir=tmp_path / "o", kinds=["alphabeta"], levels=["hard"])
    assert [(r["kind"], r["level"]) for r in rows] == [("alphabeta", "hard")]
    assert (tmp_path / "o" / "p64xquick_gui_timing.csv").exists()
    assert not list((tmp_path / "o").glob("p63*"))


def test_refuses_to_overwrite_report_tables():
    import pytest

    with pytest.raises(SystemExit):
        t.main(["--levels", "hard", "--allow-battery"])  # lọc mà không --tag / --table-dir
    with pytest.raises(SystemExit):
        t.main(["--tag", "p63x", "--allow-battery"])


def test_xiangqi_board_key_and_short_games(tmp_path, monkeypatch):
    """P6.2: --boards xiangqi → 6 mức cờ tướng, ván cắt ngắn, bảng xếp 3 / 15 / xiangqi."""
    assert [t.parse_board(b) for b in t.BOARD_CHOICES] == [3, 15, "xiangqi"]
    assert t.GAMES["xiangqi"].params["max_plies"] == t.XQ_TIMING_PLIES
    assert sorted(["xiangqi", "15", "3"], key=t.board_order) == ["3", "15", "xiangqi"]
    monkeypatch.setattr(t, "bench", lambda **kw: [])
    seen = []

    def fake_measure(board, key, lv, opp, n, surface, power):
        seen.append((board, key, opp))
        return {c: "" for c in t.TIMING_COLUMNS} | {"board": board, "kind": key[1], "level": key[2]}

    monkeypatch.setattr(t, "measure_level", fake_measure)
    old = {c: "" for c in t.TIMING_COLUMNS} | {"board": "15", "kind": "mcts", "level": "hard"}
    t._write(tmp_path / "p63quick_gui_timing.csv", t.TIMING_COLUMNS, [old])
    t.run(["xiangqi"], quick=True, table_dir=tmp_path)
    assert len(seen) == 6 and {s[2] for s in seen} == {"random_human"}
    table = read_rows(tmp_path / "p63quick_gui_timing.csv")
    assert [r["board"] for r in table] == ["15"] + ["xiangqi"] * 6
