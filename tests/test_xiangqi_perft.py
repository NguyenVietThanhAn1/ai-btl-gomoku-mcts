"""Perft cờ tướng vs số chuẩn chessprogramming.org (11 thế). D1–3 mặc định; D4 là `slow`."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from gameai.experiments.p81_perft import FIELDS, POSITIONS, run_perft
from gameai.games.xiangqi import Xiangqi, perft

CASES = [(name, fen, d, exp[d - 1]) for name, fen, exp in POSITIONS for d in (1, 2, 3)]
CASES_D4 = [(name, fen, 4, exp[3]) for name, fen, exp in POSITIONS]


@pytest.mark.parametrize(("name", "fen", "depth", "expected"), CASES, ids=lambda v: str(v)[:12])
def test_perft_depth_1_to_3(name: str, fen: str, depth: int, expected: int) -> None:
    assert perft(Xiangqi(fen), depth) == expected


@pytest.mark.slow
@pytest.mark.parametrize(("name", "fen", "depth", "expected"), CASES_D4, ids=lambda v: str(v)[:12])
def test_perft_depth_4(name: str, fen: str, depth: int, expected: int) -> None:
    assert perft(Xiangqi(fen), depth) == expected


def test_perft_leaves_game_untouched() -> None:
    g = Xiangqi()
    g.play(Xiangqi().legal_moves()[0])
    fen, key, board, kings, ply = g.to_fen(), g.key(), list(g.board), list(g._kings), g.ply
    assert perft(g, 3) > 0
    assert (g.to_fen(), g.key(), g.board, g._kings, g.ply) == (fen, key, board, kings, ply)
    assert g._key == g._compute_key()


def test_perft_depth_zero_and_terminal() -> None:
    assert perft(Xiangqi(), 0) == 1
    mate = Xiangqi("3k5/9/9/9/9/9/9/9/r8/1r2K4 w")  # Đỏ bị chiếu bí bởi hai xe Đen
    assert perft(mate, 1) == 0 and perft(mate, 3) == 0


def test_perft_ignores_repetition_and_max_plies() -> None:
    assert perft(Xiangqi(max_plies=1), 3) == 79666


def test_committed_csv_matches_reference() -> None:
    path = Path(__file__).resolve().parent.parent / "results" / "tables" / "p81_perft.csv"
    if not path.exists():
        pytest.skip("chưa sinh results/tables/p81_perft.csv")
    with path.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert rows and list(rows[0]) == FIELDS
    expected = {(n, d): e[d - 1] for n, _, e in POSITIONS for d in range(1, 5)}
    assert len(rows) == len(expected)
    for r in rows:
        assert int(r["expected"]) == expected[(r["position"], int(r["depth"]))]
        assert int(r["nodes"]) == int(r["expected"]) and r["ok"] == "1"


def test_run_perft_quick_rows() -> None:
    rows = run_perft(1)
    assert len(rows) == len(POSITIONS) and all(r["ok"] for r in rows)
