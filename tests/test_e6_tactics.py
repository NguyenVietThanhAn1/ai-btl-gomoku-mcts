"""Test E6 (D-21): ô thắng ngay, phân loại thế, trích thế, checkpoint, sanity, spec, bảng."""

from __future__ import annotations

import csv
import json
import random
from pathlib import Path

import pytest

from gameai.agents.mcts import TACTIC_BLOCK, TACTIC_WIN, MCTSAgent
from gameai.agents.registry import make_agent
from gameai.arena import derive_seed
from gameai.core.game import P1, P2
from gameai.experiments import e6_tactics as e6
from gameai.experiments.e5_rollout import mcts_spec
from gameai.games.kinrow import KInRow

N = 15


def rc(r: int, c: int) -> int:
    return r * N + c


def play_seq(moves: list[int]) -> KInRow:
    g = KInRow(N, 5)
    for m in moves:
        g.play(m)
    return g


def brute_win_cells(g: KInRow, player: int) -> set[int]:
    """Quét mọi ô trống; người đi kiểm bằng play/undo, đối thủ bằng đếm chuỗi."""
    if g.is_terminal():
        return set()
    out = set()
    for m in g.legal_moves():
        if player == g.current_player():
            g.play(m)
            if g.winner() == player:
                out.add(m)
            g.undo()
        elif e6.is_win_cell(g.board, N, 5, m, 1 if player == P1 else 2):
            out.add(m)
    return out


# Thế loại 1: O có four ngang hàng 7 cột 3–6, đầu trái bị X chặn ở cột 2 → chặn duy nhất ở cột 7.
# X đi (X: 5 quân rải rác + chặn; O: 4 quân).
BLOCK_MOVES = [rc(7, 2), rc(7, 3), rc(10, 10), rc(7, 4), rc(10, 12), rc(7, 5), rc(12, 10), rc(7, 6)]


def test_win_cells_matches_brute_force_both_sides():
    rng = random.Random(3)
    for _ in range(6):
        g = KInRow(N, 5)
        tr = e6.WinTracker(g)
        while not g.is_terminal() and len(g.move_history) < 70:
            for p in (P1, P2):
                assert tr.cells[p] == brute_win_cells(g, p)
                assert e6.win_cells(g, p) == tr.cells[p]
            # ưu tiên đặt gần chuỗi cho có nhiều four
            tr.play(rng.choice(g.candidate_moves()))


def test_classify_block_and_open4_and_win():
    g = play_seq(BLOCK_MOVES)
    me = g.current_player()
    assert me == P1
    mine, opp = e6.win_cells(g, me), e6.win_cells(g, -me)
    assert mine == set() and opp == {rc(7, 7)}
    assert e6.classify(mine, opp) == "block"
    # open four của O (không bị chặn ở cột 2) → 2 ô thắng → open4
    g2 = play_seq(
        [rc(0, 0), rc(7, 3), rc(10, 10), rc(7, 4), rc(10, 12), rc(7, 5), rc(12, 10), rc(7, 6)]
    )
    assert e6.win_cells(g2, P2) == {rc(7, 2), rc(7, 7)}
    assert e6.classify(e6.win_cells(g2, P1), e6.win_cells(g2, P2)) == "open4"
    # four gãy XX_XX của O cũng là 1 ô thắng
    g3 = play_seq(
        [rc(0, 0), rc(7, 3), rc(10, 10), rc(7, 4), rc(10, 12), rc(7, 6), rc(12, 10), rc(7, 7)]
    )
    assert e6.win_cells(g3, P2) == {rc(7, 5)}
    # thêm 1 nước của X → lượt O, O có thắng ngay → win
    g4 = play_seq(BLOCK_MOVES + [rc(0, 0)])
    assert e6.classify(e6.win_cells(g4, P2), e6.win_cells(g4, P1)) == "win"
    assert e6.classify(set(), set()) == "quiet"


def test_keeps_win():
    # O đi; O có open three hàng 7 cột 4–6 và đã có... dựng: O có four mở được sau 1 nước
    # O: (7,4)(7,5)(7,6); O đi (7,3) → open four (7,2),(7,7) → keeps_win; X không có ô thắng.
    g = play_seq([rc(0, 0), rc(7, 4), rc(0, 2), rc(7, 5), rc(0, 4), rc(7, 6), rc(14, 14)])
    assert g.current_player() == P2
    assert e6.keeps_win(g, rc(7, 3))
    assert not e6.keeps_win(g, rc(3, 3))


def test_stratum_of():
    assert e6.stratum_of(10) == "<60"
    assert e6.stratum_of(59) == "<60"
    assert e6.stratum_of(60) == "60-100"
    assert e6.stratum_of(100) == "60-100"
    assert e6.stratum_of(101) == ">100"


def _write_games(path: Path, games: list[list[int]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, ["game_id", "moves"])
        w.writeheader()
        for i, mv in enumerate(games):
            w.writerow({"game_id": f"{i}-AX", "moves": ";".join(map(str, mv))})


def test_extract_positions_deterministic_dedup_one_per_game(tmp_path: Path):
    # Ván 1: tới thế BLOCK rồi X chặn, O đi tiếp xa; ván 2 trùng ván 1 → khử trùng.
    game = BLOCK_MOVES + [rc(7, 7), rc(1, 1), rc(2, 2)]
    _write_games(tmp_path / "e3_greedy_c1.4_i100.csv", [game, game])
    _write_games(tmp_path / "e5_mref_rand_i1000.csv", [game])
    (tmp_path / "e5quick_mref_rand_i250.csv").write_text("game_id,moves\n0-AX,112\n")
    cands, counts = e6.extract_positions(tmp_path)
    assert counts["_meta"]["games"] == 3  # quick bị bỏ
    assert counts["block"]["games"] == 3
    assert counts["block"]["distinct"] == 1
    assert len(cands["block"]) == 1
    p = cands["block"][0]
    assert p["ply"] == len(BLOCK_MOVES) and p["correct"] == [rc(7, 7)]
    sel_q = e6.select_positions(cands, quick=True)
    sel_f = e6.select_positions(cands, quick=False)
    assert {s["pos_id"] for s in sel_q} <= {s["pos_id"] for s in sel_f}
    again, _ = e6.extract_positions(tmp_path)
    assert [x["hash"] for x in again["block"]] == [x["hash"] for x in cands["block"]]


@pytest.mark.parametrize("rollout", ["rand", "h300"])
def test_checkpoint_equals_separate_runs(rollout: str):
    g = play_seq(BLOCK_MOVES)
    cps = (20, 60, 150)
    for seed in (0, 1):
        agent = make_agent(e6.spec_off(rollout, cps[-1]), seed)
        got = [(k, agent._final_child(root).move, len(root.children))
               for k, root, _ in e6.checkpoint_moves(g, agent, cps)]  # fmt: skip
        for k, move, n_children in got:
            ref = make_agent(e6.spec_off(rollout, k), seed)
            assert ref.select_move(g) == move
            assert len(ref.root.children) == n_children
            assert ref.stats["iterations"] == k


def test_choice_task_rows():
    pos = {"pos_id": "block-x", "type": "block", "moves": ";".join(map(str, BLOCK_MOVES)),
           "correct_cells": str(rc(7, 7))}  # fmt: skip
    rows = e6.choice_task(pos, "rand", 0, checkpoints=(10, 30))
    assert [r["iter"] for r in rows] == [10, 30]
    for r in rows:
        assert r["correct"] == int(r["move"] == rc(7, 7))
        assert r["keeps_win"] == ""


def test_sanity_tactics_on():
    g = play_seq(BLOCK_MOVES)
    a = MCTSAgent(iterations=1, check_tactics=True, seed=0)
    assert a.select_move(g) == rc(7, 7) and a.stats["tactic"] == TACTIC_BLOCK
    g4 = play_seq(BLOCK_MOVES + [rc(0, 0)])
    assert a.select_move(g4) == rc(7, 7) and a.stats["tactic"] == TACTIC_WIN


def test_specs_match_e3_e5():
    for r in ("rand", "h300"):
        on = mcts_spec(r, iterations=1000)
        off = e6.spec_off(r, 1000)
        assert {**on.params, "check_tactics": False} == off.params
        assert on.params["check_tactics"] is True
        assert off.name == f"{r}off_i1000"
    # spec h300 bật trùng raw E3 (nếu có file)
    f = e6.RAW_DIR / "e3_greedy_c1.4_i1000.csv"
    if f.exists():
        with f.open(encoding="utf-8") as fh:
            row = next(csv.DictReader(fh))
        assert json.loads(row["spec_a"])["params"] == mcts_spec("h300", iterations=1000).params


def test_match_points_and_paths():
    pts = e6.match_points()
    assert [(p.part, p.iters) for p in pts] == [("mref", 1000), ("self", 1000), ("self", 5000),
                                                ("greedy", 1000), ("greedy", 5000)]  # fmt: skip
    paths = {e6.match_raw(p.part, p.spec_a.name, q) for p in pts for q in (True, False)}
    assert len(paths) == 2 * len(pts)
    for p in pts:
        assert p.spec_a.params["check_tactics"] is False
    assert e6.prefix(True) == "e6quick_"


def test_boot_ci_deterministic():
    by = {"a": (3, 5), "b": (0, 5), "c": (5, 5)}
    assert e6._boot_ci(by, n_boot=200) == e6._boot_ci(by, n_boot=200)
    lo, hi = e6._boot_ci(by, n_boot=500)
    assert 0 <= lo <= 8 / 15 <= hi <= 1
    assert e6._boot_ci({"a": (2, 2)}, n_boot=50) == (1.0, 1.0)


def test_choice_table_strata_and_nolose():
    positions = [{"pos_id": "w1", "stratum": "<60"}, {"pos_id": "w2", "stratum": ">100"}]
    rows = []
    for pid, correct, kw in (("w1", "1", "0"), ("w2", "0", "1")):
        for s in range(2):
            rows.append({"pos_id": pid, "type": "win", "rollout": "rand", "seed": str(s),
                         "iter": "100", "correct": correct, "keeps_win": kw,
                         "correct_expanded": "1", "n_correct": "3"})  # fmt: skip
    sanity = [
        {"pos_id": "w1", "type": "win", "ok": "1"},
        {"pos_id": "w2", "type": "win", "ok": "1"},
    ]
    t = e6.choice_table(rows, positions, sanity)
    allr = next(r for r in t if r["rollout"] == "rand" and r["stratum"] == "all")
    assert allr["correct_rate"] == 0.5 and allr["nolose_rate"] == 1.0 and allr["n_pos"] == 2
    lo = next(r for r in t if r["rollout"] == "rand" and r["stratum"] == "<60")
    assert lo["correct_rate"] == 1.0 and lo["n_pos"] == 1
    on = next(r for r in t if r["rollout"] == "on" and r["stratum"] == "all")
    assert on["correct_rate"] == 1.0


def test_side_rows_skip_ply0():
    pt = e6.match_points()[1]
    moves = [
        {"game_id": "0-AX", "ply": "0", "side": "A", "tactic": "2", "agent_time": "0.001"},
        {"game_id": "0-AX", "ply": "2", "side": "A", "tactic": "2", "agent_time": "0.05"},
        {"game_id": "0-AX", "ply": "4", "side": "A", "tactic": "0", "agent_time": "1.0"},
        {"game_id": "0-AX", "ply": "1", "side": "B", "tactic": "1", "agent_time": "0.01"},
    ]
    rate, tm = e6._side_rows(pt, "x", "on", "A", "e6", moves)
    assert rate["n_moves"] == 2 and rate["n_ply0"] == 1 and rate["t2"] == 1
    assert rate["pct_direct"] == 0.5
    assert tm["mean_search_time"] == 1.0 and tm["mean_direct_time"] == 0.05


def test_seed_derivation_shared_between_rollouts():
    assert derive_seed(3, "block-abc") == derive_seed(3, "block-abc")
    assert derive_seed(3, "block-abc") != derive_seed(4, "block-abc")
