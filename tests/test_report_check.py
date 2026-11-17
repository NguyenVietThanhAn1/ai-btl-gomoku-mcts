"""Test P7.2 report_check: số có nguồn khớp CSV / mục summary, bảng src-table giống byte, số trần,
const D-xx, ảnh, đánh số caption, đếm từ Tóm tắt."""

from __future__ import annotations

from pathlib import Path

import pytest

from gameai.experiments import report_check as rc

DEC = "### D-18 (x) — E3\n- c ∈ {0.5, 1.0, 1.4, 2.0} × iter 1000, 5000; 0,5 s\n"


@pytest.fixture
def src(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """ROOT giả: results/tables/t.csv + summary_kinrow.md."""
    td = tmp_path / "results" / "tables"
    td.mkdir(parents=True)
    (td / "t.csv").write_text(
        "part,c,it,win_rate,wins,draws,losses,nodes,cpu\n"
        "g,1.4,5000,0.92,46,0,4,553574,Intel i9\n"
        "g,2.0,5000,0.96,48,0,2,1416,Intel i9\n",
        encoding="utf-8",
    )
    (td / "summary_kinrow.md").write_text(
        "# S\n\n## E5 — rollout\n\n- hiệu 0,62 [0,48; 0,76].\n\n### Bảng E5 — x\n\n"
        "| a | b |\n|---|---|\n| 1 | 0,50 |\n\n## E6 — y\n\n- 0,38\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(rc, "ROOT", tmp_path)
    return tmp_path


def run(text: str, base: Path) -> list[str]:
    issues, _ = rc.check_text(text, decisions=DEC, base=base)
    return [str(i) for i in issues]


T = "results/tables/t.csv"


def test_csv_value_ok_and_mismatch(src: Path):
    ok = f"thắng 0,92 <!-- src: {T} | c=1.4,it=5000 | win_rate --> trận."
    assert run(ok, src) == []
    bad = f"thắng 0,93 <!-- src: {T} | c=1.4,it=5000 | win_rate -->"
    assert any("cần '0,92'" in m for m in run(bad, src))
    # số chữ số thập phân theo token
    assert run(f"0,9 <!-- src: {T} | c=1.4 | win_rate -->", src) == []


def test_filter_must_hit_one_row(src: Path):
    assert any("2 hàng" in m for m in run(f"0,92 <!-- src: {T} | it=5000 | win_rate -->", src))
    assert any("0 hàng" in m for m in run(f"0,92 <!-- src: {T} | c=9 | win_rate -->", src))


def test_transforms_grouping_wdl_string(src: Path):
    assert run(f"92 % <!-- src: {T} | c=1.4 | win_rate | x100 -->", src) == []
    assert run(f"553 574 nút <!-- src: {T} | c=1.4 | nodes --> nút", src) != []  # chữ chen giữa
    assert run(f"553 574 <!-- src: {T} | c=1.4 | nodes -->", src) == []
    assert run(f"1416 <!-- src: {T} | c=2.0 | nodes -->", src) == []
    assert run(f"46/0/4 <!-- src: {T} | c=1.4 | wins/draws/losses -->", src) == []
    assert run(f"CPU Intel i9 <!-- src: {T} | c=1.4 | cpu -->", src) == []
    # không khớp một phần số: 10,92 ≠ 0,92
    assert run(f"10,92 <!-- src: {T} | c=1.4 | win_rate -->", src) != []


def test_summary_anchor(src: Path):
    assert run("hiệu 0,62 <!-- src: summary_kinrow.md#E5 -->", src) == []
    assert any("không có trong mục" in m
               for m in run("hiệu 0,38 <!-- src: summary_kinrow.md#E5 -->", src))  # fmt: skip
    assert any("tiêu đề khớp" in m for m in run("0,62 <!-- src: summary_kinrow.md#E9 -->", src))


def test_src_table_byte_equal(src: Path):
    good = "<!-- src-table: summary_kinrow.md#Bảng E5 -->\n\n| a | b |\n|---|---|\n| 1 | 0,50 |\n"
    assert run(good, src) == []  # số trong bảng không bị báo "trần"
    bad = good.replace("0,50", "0,51")
    assert any("bảng khác summary" in m for m in run(bad, src))


def test_bare_numbers_and_const(src: Path):
    msgs = run("Tỷ lệ 0,92 và 5000 ván, 12 %, nhưng 3×3, k=5, E3, h300, D-18 thì bỏ qua.", src)
    bare = [m for m in msgs if "không có nguồn" in m]
    assert len(bare) == 3  # 0,92 · 5000 · 12
    assert run("c ∈ {0,5; 1,0; 1,4; 2,0}, 5000 iter <!-- const: D-18 -->", src) == []
    assert any("D-99" in m for m in run("5000 <!-- const: D-99 -->", src))
    assert run("`0,5` và $c = 1{,}4$ và [D-18](../docs/DECISIONS.md#100)", src) == []


def test_images_captions_abstract(src: Path):
    (src / "a.png").write_bytes(b"")
    assert run("![Hình 1. a](a.png)\n\n![Hình 2. b](a.png)\n\n**Bảng 1.** t", src) == []
    assert run("![Hình B.1. phụ lục](a.png)", src) == []  # phụ lục: không đánh số chung
    msgs = run("![Hình 1. a](none.png)\n\n![Hình 3. b](a.png)\n\n**Bảng 2.** t", src)
    assert any("ảnh không tồn tại" in m for m in msgs)
    assert sum("không liên tiếp" in m for m in msgs) == 2
    assert any("thiếu caption" in m for m in run("![x](a.png)", src))
    assert any("không dùng dòng" in m for m in run("**Hình 1.** a", src))
    text = "## Tóm tắt\n\n" + "từ " * 201 + "<!-- bỏ -->\n\n## 1 Giới thiệu\n"
    issues, words = rc.check_text(text, decisions=DEC, base=src)
    assert words == 201 and any("Tóm tắt" in str(i) for i in issues)


def test_references_section_ignored(src: Path):
    assert run("## Tài liệu tham khảo\n\n1. Kocsis 2006, 282–293.\n", src) == []


def test_fenced_code_and_example_marker(src: Path):
    assert run("```\nUCT = 1 + 1,414·1,048 = 2,48\n```\n", src) == []
    (src / "ex.md").write_text("x", encoding="utf-8")
    assert run("UCT(X2) = 2,48 <!-- example: ex.md -->", src) == []
    assert any("không có file" in m for m in run("2,48 <!-- example: none.md -->", src))
    assert any("thiếu đường dẫn" in m for m in run("2,48 <!-- example: -->", src))


def test_ci_span(src: Path):
    """`x [lo; hi]` một comment: neo summary cần cả chuỗi; CSV cần cột x,lo,hi."""
    (src / "results" / "tables" / "c.csv").write_text(
        "k,win_rate,win_lo,win_hi\na,0.62,0.481,0.741\n", encoding="utf-8"
    )
    c = "results/tables/c.csv"
    assert (
        run(f"thắng 0,62 [0,48; 0,74] <!-- src: {c} | k=a | win_rate,win_lo,win_hi -->", src) == []
    )
    bad = run(f"0,62 [0,48; 0,75] <!-- src: {c} | k=a | win_rate,win_lo,win_hi -->", src)
    assert any("cần '0,62 [0,48; 0,74]'" in m for m in bad)
    assert run("hiệu 0,62 [0,48; 0,76] <!-- src: summary_kinrow.md#E5 -->", src) == []
    msgs = run("hiệu 0,62 [0,48; 0,77] <!-- src: summary_kinrow.md#E5 -->", src)
    assert any("không có trong mục" in m for m in msgs)
    # số khác trong câu vẫn phải có nguồn riêng
    assert len(run("0,99 và 0,62 [0,48; 0,76] <!-- src: summary_kinrow.md#E5 -->", src)) == 1


def test_const_token_list(src: Path):
    ok = (
        f"ở 1000 và 5000 iteration, c = 2,0 thắng 0,92 <!-- src: {T} | c=1.4 | win_rate --> "
        "<!-- const: D-18 | 1000 5000 2,0 -->"
    )
    assert run(ok, src) == []
    # token không liệt kê vẫn phải có nguồn; token liệt kê phải có trong D-xx
    assert any("'0,77'" in m for m in run("0,77 ở 1000 <!-- const: D-18 | 1000 -->", src))
    assert any("không có trong D-18" in m for m in run("2500 <!-- const: D-18 | 2500 -->", src))


def test_range_span_anchor(src: Path):
    (src / "results" / "tables" / "summary_kinrow.md").write_text(
        "## E3 — x\n\n- thắng 0,915–0,980.\n", encoding="utf-8"
    )
    assert run("thắng 0,915–0,980 <!-- src: summary_kinrow.md#E3 -->", src) == []
    assert run("thắng 0,915–0,990 <!-- src: summary_kinrow.md#E3 -->", src) != []
