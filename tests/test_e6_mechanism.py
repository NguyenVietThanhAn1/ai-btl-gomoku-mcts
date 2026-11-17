"""Test kiểm chứng cơ chế E6 (P7.1): dựng lại cây khớp choice_task, thống kê gốc, bảng theo nhóm."""

from __future__ import annotations

from pathlib import Path

from gameai.agents.mcts import Node
from gameai.experiments import e6_mechanism as m
from gameai.experiments import e6_tactics as e6
from gameai.experiments.e5_rollout import _append_csv

N = 15
C = 7 * N + 7  # ô chặn của BLOCK_MOVES
BLOCK_MOVES = [7 * N + 2, 7 * N + 3, 10 * N + 10, 7 * N + 4, 10 * N + 12, 7 * N + 5, 12 * N + 10,
               7 * N + 6]  # fmt: skip
POS = {"pos_id": "block-x", "type": "block", "moves": ";".join(map(str, BLOCK_MOVES)),
       "correct_cells": str(C)}  # fmt: skip
CPS = (10, 30, 80)


def _refs(rollout: str, seed: int) -> dict[int, dict[str, str]]:
    rows = e6.choice_task(POS, rollout, seed, checkpoints=CPS)
    return {r["iter"]: {k: str(v) for k, v in r.items()} for r in rows}


def test_task_matches_choice_task():
    for roll in ("rand", "h300"):
        refs = _refs(roll, 0)
        rows = m.mechanism_task(POS, roll, 0, refs, checkpoints=CPS)
        assert [r["iter"] for r in rows] == list(CPS)
        for r in rows:
            assert r["matches_raw"] == 1
            assert str(r["move"]) == refs[r["iter"]]["move"]
            assert r["correct"] == int(r["move"] == C)
            if r["correct"]:
                assert r["wn_chosen"] == r["wn_correct"]


def test_mismatch_detected():
    refs = _refs("rand", 0)
    refs[CPS[1]] = {**refs[CPS[1]], "n_chosen": str(int(refs[CPS[1]]["n_chosen"]) + 1)}
    rows = m.mechanism_task(POS, "rand", 0, refs, checkpoints=CPS)
    assert [r["matches_raw"] for r in rows] == [1, 0, 1]
    assert m.mechanism_task(POS, "rand", 0, {}, checkpoints=CPS)[0]["matches_raw"] == 0


def _node(move: int, w: float, n: int, parent: Node | None, pjm: int = 1) -> Node:
    x = Node(move, parent, pjm, [])
    x.W, x.N = w, n
    if parent is not None:
        parent.children.append(x)
    return x


def test_root_row_hand_tree():
    root = _node(-1, 0, 12, None, pjm=-1)
    good = _node(C, 4, 5, root)
    a = _node(1, 3, 6, root)  # nút sai top, đã mở ô thắng của đối thủ
    _node(C, 2, 2, a, pjm=-1)
    _node(2, 0, 1, a, pjm=-1)
    _node(3, 0, 1, root)  # nút sai, W = 0
    r = m.root_row(root, a, {C})
    assert r["correct"] == 0 and r["n_chosen"] == 6 and r["wn_chosen"] == 0.5
    assert r["n_correct"] == 5 and r["wn_correct"] == 0.8
    assert r["n_wrong"] == 2 and r["frac_wrong_zero"] == 0.5 and r["max_n_wrong"] == 6
    assert r["n_wrong_top"] == 6 and r["children_wrong_top"] == 2
    assert r["refute_expanded"] == 1 and r["n_refute"] == 2 and r["wn_refute"] == 1.0
    r2 = m.root_row(root, good, {C})
    assert r2["correct"] == 1 and r2["wn_chosen"] == 0.8 and r2["n_wrong_top"] == 6


def test_root_row_unrefuted():
    root = _node(-1, 0, 3, None, pjm=-1)
    _node(C, 1, 1, root)
    a = _node(1, 2, 2, root)
    _node(4, 0, 1, a, pjm=-1)
    r = m.root_row(root, a, {C})
    assert r["refute_expanded"] == 0 and r["n_refute"] == 0 and r["wn_refute"] == ""
    assert r["frac_wrong_zero"] == 0.0


def test_build_table_groups(tmp_path: Path):
    raw = m.raw_path(tmp_path)
    base = {"move": 0, "matches_raw": 1, "n_chosen": 5, "n_correct": 3, "wn_correct": 0.5,
            "n_children": 50, "n_wrong": 49, "frac_wrong_zero": 0.5, "max_n_wrong": 5,
            "n_wrong_top": 5, "wn_wrong_top": 0.6, "children_wrong_top": 3, "n_refute": 0,
            "wn_refute": "", "git_commit": "x", "git_dirty": 0}  # fmt: skip
    for pos, correct, wn, ref in (("p1", 1, 0.5, 0), ("p1", 0, 0.7, 1), ("p2", 0, 0.9, 0)):
        for roll in ("rand", "h300"):
            for it in e6.CHECKPOINTS:
                row = {**base, "pos_id": pos, "rollout": roll, "seed": 0, "iter": it,
                       "correct": correct, "wn_chosen": wn, "refute_expanded": ref}  # fmt: skip
                _append_csv(raw, m.RAW_COLUMNS, row)
    out = m.build_table(tmp_path, tmp_path)
    assert len(out) == 2 * len(e6.CHECKPOINTS) * 3
    row = next(r for r in out if r["rollout"] == "h300" and r["iter"] == 100
               and r["group"] == "correct=0")  # fmt: skip
    assert row["n_runs"] == 2 and row["n_pos"] == 2
    assert abs(row["wn_chosen"] - 0.8) < 1e-9
    assert row["refute_rate"] == 0.5
    assert row["wn_wrong_top_refuted"] == 0.6
    allr = next(r for r in out if r["rollout"] == "h300" and r["iter"] == 100
                and r["group"] == "all")  # fmt: skip
    assert allr["n_runs"] == 3 and abs(allr["correct_rate"] - 1 / 3) < 1e-9
    assert (tmp_path / "e6_mechanism.csv").exists()
