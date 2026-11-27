"""Test P7.1 plots: so byte, lọc cặp pilot, tóm tắt E2 từ raw, định dạng số, summary_kinrow."""

from __future__ import annotations

import csv
import re
import shutil
from pathlib import Path

import pytest

from gameai.experiments import e2_never_lose as e2
from gameai.experiments import e5_rollout as e5
from gameai.experiments import e6_tactics as e6
from gameai.experiments import plots
from gameai.experiments.common import read_rows

TABLES = plots.TABLE_DIR


def test_vn_format():
    assert plots.vn(0.5) == "0,50"
    assert plots.vn(549946, 0) == "549 946"
    assert plots.vn(2252, 0) == "2252"
    assert plots.vn(0.12345, 3) == "0,123"
    assert plots.ci(0.1, 0.25) == "[0,10; 0,25]"


def test_ci_rounding_rule_and_minus():
    """D-30: thêm một chữ số khi làm tròn đổi kết luận chứa 0 / 0,5 hoặc biên ≠ 0 thành 0."""
    assert plots.ci(0.004037904, 0.155962096) == "[0,004; 0,156]"  # E5 mref 2 s
    assert plots.ci(0.241, 0.4994) == "[0,241; 0,499]"  # 0,499 → 0,50 sẽ "chứa 0,5"
    assert plots.ci(0.0035, 0.105) == "[0,004; 0,105]"  # Wilson, biên ≠ 0 → 0,00
    assert plots.ci(0.0, 0.07) == "[0,00; 0,07]"  # biên đúng bằng 0: không đổi
    assert plots.ci(-0.0149, 0.0949) == "[−0,01; 0,09]"  # vẫn chứa 0: không đổi
    assert plots.vn(-0.001) == "0,00"  # −0 không mang dấu
    assert plots.vn(-1, 0) == "−1"


def test_one_requires_unique():
    rows = [{"a": "1", "b": "x"}, {"a": "1", "b": "y"}]
    assert plots._one(rows, a=1, b="y")["b"] == "y"
    with pytest.raises(KeyError):
        plots._one(rows, a=1)
    with pytest.raises(KeyError):
        plots._one(rows, a=2)


def test_compare(tmp_path: Path):
    new = tmp_path / "new"
    new.mkdir()
    (new / "same.csv").write_bytes(b"a,b\r\n1,2\r\n")
    (new / "diff.csv").write_bytes(b"a,b\n1,3\n")
    (new / "fresh.csv").write_bytes(b"a\n")
    ref = {"same.csv": b"a,b\n1,2\n", "diff.csv": b"a,b\n1,2\n"}
    bad = dict(plots.compare(new, tmp_path, ["same.csv", "diff.csv", "fresh.csv"],
                             ref=lambda p: ref.get(p.name)))  # fmt: skip
    assert "same.csv" not in bad
    assert bad["diff.csv"].startswith("khác từ dòng 2")
    assert bad["fresh.csv"].startswith("mới")


def _write(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def test_match_keeps_first_pairs(tmp_path: Path):
    raw = tmp_path / "x.csv"
    _write(raw, [{"game_id": f"g{i}", "pair_seed": i // 2} for i in range(10)])
    _write(tmp_path / "x_moves.csv", [{"game_id": f"g{i}", "ply": 0} for i in range(10)])
    rows, moves = plots._match(raw, n_pairs=2)
    assert [r["game_id"] for r in rows] == ["g0", "g1", "g2", "g3"]
    assert {m["game_id"] for m in moves} == {"g0", "g1", "g2", "g3"}
    assert len(plots._match(raw)[0]) == 10


def test_e2_mistakes_from_raw_strings():
    """Tóm tắt từ raw (chuỗi đã ép int) = tóm tắt từ dòng gốc (int) — gồm thứ tự sắp xếp."""
    src = [
        {"iterations": it, "mcts_player": p, "ply": ply, "move_type": mt, "opp_last_type": ot,
         "losing_leaves": n}
        for it, p, ply, mt, ot, n in ((1000, 1, 2, "edge", "corner", 3), (100, -1, 1, "center",
                                      "edge", 5), (100, 1, 3, "edge", "edge", 1))
    ]  # fmt: skip
    as_str = [{k: str(v) for k, v in r.items()} for r in src]
    conv = [{**m, **{k: int(m[k]) for k in ("iterations", "mcts_player", "ply", "losing_leaves")}}
            for m in as_str]  # fmt: skip
    assert e2.summarize_mistakes(conv) == e2.summarize_mistakes(src)


needs_tables = pytest.mark.skipif(
    not (TABLES / "e1_summary.csv").exists() or not (TABLES / "e6_paired.csv").exists(),
    reason="cần results/tables đầy đủ",
)


@needs_tables
def test_summary_numbers_come_from_csv(tmp_path: Path):
    for f in TABLES.glob("*.csv"):
        shutil.copy2(f, tmp_path / f.name)
    path = plots.write_summary_md(tmp_path, plots.FIG_DIR)
    text = path.read_text(encoding="utf-8")
    for e in ("E1", "E2", "E3", "E4", "E5", "E6"):
        assert f"## {e} - " in text
    s = read_rows(TABLES / "e1_summary.csv")
    mm = plots._one(s, board="3x3", variant="minimax")
    assert plots.vn(mm["nodes_sum"], 0) in text
    e2t = max(read_rows(TABLES / "e2_exhaustive.csv"), key=lambda r: int(r["iterations"]))
    assert f"{e2t['iterations']} iter → {e2t['losses']} nhánh" in text
    gp = plots._one(read_rows(TABLES / "e6_paired.csv"), part="greedy", iters=5000)
    assert f"hiệu {plots.vn(gp['diff'])}" in text
    # mọi tên file được nhắc tới đều tồn tại
    for name in re.findall(r"`(e\d_[a-z0-9_]+\.(?:csv|png))`", text):
        assert (tmp_path / name).exists() or (plots.FIG_DIR / name).exists(), name


@needs_tables
def test_summary_report_tables_wdl_and_e4_15x15(tmp_path: Path):
    """P7.2: mỗi bảng cho báo cáo có tiêu đề `###` riêng (không trùng); W/D/L E3 khớp CSV và
    W + D + L = n; ví dụ E4 15×15 có cột tham chiếu."""
    for f in TABLES.glob("*.csv"):
        shutil.copy2(f, tmp_path / f.name)
    text = plots.write_summary_md(tmp_path, plots.FIG_DIR).read_text(encoding="utf-8")
    heads = [ln for ln in text.splitlines() if ln.startswith("### ")]
    assert len(heads) == len(set(heads))
    for name in ("e3_3x3_random", "e3_3x3_minimax", "e3_greedy", "e3_ab2"):
        assert any(f"`{name}.csv`" in h and "W/D/L" in h for h in heads), name
        for r in read_rows(TABLES / f"{name}.csv"):
            if r["split"] != "all":
                continue
            assert int(r["wins"]) + int(r["draws"]) + int(r["losses"]) == int(r["n"])
            assert f"{r['wins']}/{r['draws']}/{r['losses']}" in text
    sens = [r for r in read_rows(TABLES / "e4_roots_examples.csv")
            if r["example"] == "sensitivity"]  # fmt: skip
    assert any("ví dụ gốc 15×15" in h for h in heads)
    assert "W/N tham chiếu" in text
    assert f"| {sens[0]['move']} | " in text and plots.vn(sens[0]["ref_wn"], 3) in text


@needs_tables
def test_check_outputs_compares_summary(tmp_path: Path):
    """`--check` so cả summary_kinrow.md và summary_xiangqi.md (report lấy chúng làm src): giống bản
    tham chiếu → không báo; lệch một chữ → báo đúng tên file, đúng dòng; chưa commit → "mới"."""
    for f in TABLES.glob("*.csv"):
        shutil.copy2(f, tmp_path / f.name)
    bad = plots.check_outputs(tmp_path, plots.FIG_DIR, [], ref=lambda p: None)
    assert bad == [("summary_kinrow.md", "mới (chưa commit)"),
                   ("summary_xiangqi.md", "mới (chưa commit)")]  # fmt: skip
    refs = {n: (tmp_path / n).read_bytes() for n in ("summary_kinrow.md", "summary_xiangqi.md")}
    assert plots.check_outputs(tmp_path, plots.FIG_DIR, [], ref=lambda p: refs[p.name]) == []
    old = refs["summary_kinrow.md"].replace("tỷ lệ rand/h300".encode(), "tỉ lệ rand/h300".encode())
    assert old != refs["summary_kinrow.md"]
    bad = plots.check_outputs(
        tmp_path, plots.FIG_DIR, [], ref=lambda p: {**refs, "summary_kinrow.md": old}[p.name]
    )
    ((name, why),) = bad
    assert name == "summary_kinrow.md" and why.startswith("khác từ dòng ")


@needs_tables
def test_summary_xiangqi_from_csv(tmp_path: Path):
    """D-39: bảng E7 cho báo cáo sinh từ CSV; tiêu đề `###` không trùng; d3/d4 chỉ ở bảng khám phá;
    W/D/L khớp CSV; không dùng gạch dài."""
    for f in TABLES.glob("e7_*.csv"):
        shutil.copy2(f, tmp_path / f.name)
    text = plots.write_summary_xiangqi(tmp_path).read_text(encoding="utf-8")
    heads = [ln for ln in text.splitlines() if ln.startswith("### ")]
    assert len(heads) == len(set(heads)) == 5
    assert "—" not in text and "–" not in text
    explore = text.split("khám phá d3/d4")[1].split("### ")[0]
    confirmed = text.split("các trận chốt trước")[1].split("### ")[0]
    for r in read_rows(TABLES / "e7_matches.csv"):
        if r["split"] != "all":
            continue
        cell = f"| {r['point']} | "
        assert (cell in explore) == (r["point"] in ("d3", "d4"))
        if r["point"] not in ("d3", "d4"):
            assert cell in confirmed and f"{r['wins']}/{r['draws']}/{r['losses']}" in confirmed


@needs_tables
def test_e1_table_shows_times_sign_not_x(tmp_path: Path):
    """Bảng E1 hiển thị "3×3"/"15×15" (không "3x3"/"15x15"); giá trị board trong CSV không đổi."""
    for f in TABLES.glob("*.csv"):
        shutil.copy2(f, tmp_path / f.name)
    text = plots.write_summary_md(tmp_path, plots.FIG_DIR).read_text(encoding="utf-8")
    assert "| 3×3 | full | minimax |" in text and "| 15×15 | 2 | minimax |" in text
    assert "| 3x3 |" not in text and "| 15x15 |" not in text
    assert {r["board"] for r in read_rows(TABLES / "e1_summary.csv")} == {"3x3", "15x15"}


def test_tables_do_not_depend_on_head(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Sinh lại bảng E5/E6 phải giống byte dù HEAD đã đổi code agent sau `kinrow-final`:
    giả lập so với HEAD luôn "có đổi" (False) → plots vẫn ghim tag, ra bảng giống byte."""
    if not plots.pinned_tag_exists():
        pytest.skip("không có tag kinrow-final")
    real = e5.git_diff_empty

    def fake(commit, paths=e5.CODE_PATHS, target="HEAD"):
        return False if target == "HEAD" else real(commit, paths, target)

    monkeypatch.setattr(e5, "git_diff_empty", fake)
    assert fake("HEAD") is False  # HEAD bị giả là "đã đổi"
    for f in TABLES.glob("*.csv"):
        shutil.copy2(f, tmp_path / f.name)
    t5 = e5.build_tables(False, plots.RAW_DIR, tmp_path, reuse_check=plots.pinned_reuse)
    t6 = e6.build_tables(False, plots.RAW_DIR, tmp_path, reuse_check=plots.pinned_reuse)
    names = [f"e5_{n}.csv" for n in t5] + [f"e6_{n}.csv" for n in t6]
    assert names
    for n in names:
        if (TABLES / n).exists():
            assert (tmp_path / n).read_bytes() == (TABLES / n).read_bytes(), n
