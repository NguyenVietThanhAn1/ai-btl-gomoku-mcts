import pytest

from gameai.agents.registry import AgentSpec, make_agent
from gameai.experiments import p64_strength as p
from gameai.games.kinrow import KInRow


def test_openings_valid_distinct_deterministic():
    ops = p.make_openings(40, 0)
    assert ops == p.make_openings(40, 0)  # tất định theo seed
    seqs = [op for _, op in ops]
    assert len(set(seqs)) == 40  # đôi một khác nhau
    for _, op in ops:
        assert 2 <= len(op) <= 4
        g = KInRow(15, 5)
        for m in op:
            assert m in g.candidate_moves()  # quanh tâm (trong candidate)
            g.play(m)
        assert not g.is_terminal() and not p.has_immediate_win(g)
    assert ops[0][1][0] == 7 * 15 + 7  # nước đầu luôn ở tâm (candidate bàn trống)


def test_has_immediate_win_detects_four():
    g = KInRow(15, 5)
    for m in (112, 0, 113, 2, 114, 4, 115, 6):  # X có 4 liền, tới lượt X
        g.play(m)
    assert p.has_immediate_win(g)
    assert not p.has_immediate_win(KInRow(15, 5))


def test_hard_spec_only_changes_top_k():
    base = p.AB15_HARD.params
    for name, ks in p.TOP_KS.items():
        spec = p.hard_spec(ks)
        assert spec.params["top_k"] == list(ks) and spec.label == f"ab_hard_{name}"
        assert {k: v for k, v in spec.params.items() if k != "top_k"} == {
            k: v for k, v in base.items() if k != "top_k"
        }
        make_agent(spec, 0)


def test_summarize_counts_duplicates_and_distinct_openings():
    def row(op, moves, res, ax):
        return {"result_a": res, "opening": op, "moves": moves, "a_is_x": ax,
                "termination": "normal", "a_mean_s": "1.0", "a_max_s": "2.0"}  # fmt: skip

    rows = [
        row("1 2", "3 4", 1, 1),
        row("1 2", "3 4", 1, 1),
        row("5 6", "7", 0.5, 0),
        row("5 6", "8", 0, 0),
    ]
    s = p.summarize(rows)
    assert s["n"] == 4 and s["wins"] == 2 and s["draws"] == 1 and s["losses"] == 1
    assert s["score"] == 0.625 and s["distinct_openings"] == 2 and s["duplicate_games"] == 1
    assert s["score_as_x"] == 1.0 and s["score_as_o"] == 0.25
    assert 0 < s["lo"] < s["score"] < s["hi"] < 1


def test_run_cell_plays_pairs_with_swapped_sides_and_resumes(tmp_path):
    spec = AgentSpec("random", label="r")
    ops = p.make_openings(2, 0)
    out = tmp_path / "c.csv"
    rows = p.run_cell("t", spec, spec, ops, 2, out)
    assert len(rows) == 4
    assert {r["game_id"] for r in rows} == {f"{ps}-{s}" for ps, _ in ops for s in ("AX", "BX")}
    assert {r["opening"] for r in rows} == {" ".join(map(str, op)) for _, op in ops}
    again = p.run_cell("t", spec, spec, ops, 2, out)  # resume: không chơi lại
    assert len(again) == 4 and len(out.read_text(encoding="utf-8").splitlines()) == 5
    with pytest.raises(SystemExit):
        p.run_cell("t", AgentSpec("greedy", label="g"), spec, ops, 2, out)


def test_out_dir_inside_results_is_refused():
    with pytest.raises(SystemExit):
        p.main(["--quick", "--out", str(p.ROOT / "results" / "tables")])
