"""Bộ sinh nước độc lập của e7_term_check (P8.4, D-25)."""

import json

from gameai.experiments import e7_term_check as tc
from gameai.experiments.e7_xiangqi import classify_game
from gameai.games.xiangqi import START_FEN, Xiangqi

CHECKMATE = "3k5/9/9/9/9/9/9/9/r8/1r2K4 w - - 0 1"
STALEMATE = "5k3/9/9/9/4r4/9/9/9/r8/3K5 w - - 0 1"


def test_independent_perft_start():
    g, s = tc.parse_fen(START_FEN)
    assert (tc.perft(g, s, 1), tc.perft(g, s, 2)) == (44, 1920)


def test_independent_matches_game_on_mate_and_stalemate():
    for fen, chk in ((CHECKMATE, True), (STALEMATE, False)):
        g, s = tc.parse_fen(fen)
        assert tc.legal_moves(g, s) == [] and tc.attacked(g, s) is chk
        game = Xiangqi.from_fen(fen)
        assert game.legal_moves() == [] and game.in_check() is chk


def test_check_row_ok_and_flying_general():
    spec = json.dumps({"kind": "xiangqi", "params": {"fen": CHECKMATE}})
    row = {"game_id": "0-AX", "opening": "", "moves": "", "winner": "-1",
           "termination": "normal", "game_spec": spec}  # fmt: skip
    assert classify_game(row)[0] == "mate"
    r = tc.check_row("c4", row)
    assert r["ok"] == 1 and r["indep_check"] == 1
    # lộ mặt tướng: Tướng Đỏ e0 không được sang d0 (cùng cột với Tướng Đen d9, giữa trống)
    g, s = tc.parse_fen("3k5/9/9/9/9/9/9/9/9/4K4 w - - 0 1")
    assert tc.attacked(g, s) is False
    dests = sorted(dst for _, dst in tc.legal_moves(g, s))
    assert dests == [(8, 4), (9, 5)]
    assert len(Xiangqi.from_fen("3k5/9/9/9/9/9/9/9/9/4K4 w - - 0 1").legal_moves()) == 2


def test_sample_games_deterministic(tmp_path):
    from gameai.experiments.e7_xiangqi import _write

    cols = ["game_id", "opening", "moves", "winner", "termination", "game_spec"]
    for pt in tc.POINTS:
        rows = [
            {"game_id": f"{pt}-{i}", "opening": "", "moves": "", "winner": "-1",
             "termination": "normal",
             "game_spec": json.dumps({"kind": "xiangqi", "params": {"fen": fen}})}
            for i, fen in enumerate((CHECKMATE, STALEMATE))
        ]  # fmt: skip
        _write(tmp_path / f"e7_{pt}.csv", cols, rows)
    a = tc.sample_games(tmp_path, n_each=2)
    b = tc.sample_games(tmp_path, n_each=2)
    assert [r["game_id"] for _, r in a] == [r["game_id"] for _, r in b]
    assert [classify_game(r)[0] for _, r in a] == ["stalemate"] * 2 + ["mate"] * 2
    assert all(tc.check_row(pt, r)["ok"] == 1 for pt, r in a)
