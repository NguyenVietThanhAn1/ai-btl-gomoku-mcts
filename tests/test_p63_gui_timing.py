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
