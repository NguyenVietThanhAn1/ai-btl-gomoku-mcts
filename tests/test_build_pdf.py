"""P7.3: phần xử lý văn bản / đọc PDF của build_pdf (không cần pandoc hay Chrome)."""

from __future__ import annotations

from gameai.tools import build_pdf as bp


def test_strip_comments_keeps_text_and_table_cells():
    md = "giảm 99,76 <!-- src: a.csv | k=v | col --> % (0,05 <!-- src: b -->).\n| 1 <!-- c|d --> |"
    assert bp.strip_comments(md) == "giảm 99,76 % (0,05).\n| 1 |"


def test_typography_keeps_every_digit():
    out = bp.typography("99,76 % và 95 %; $v = 0{,}614$")
    assert out == "99,76\u00a0% và 95\u00a0%; $v = 0.614$"
    assert bp.typography("938 419 nút, E7 2000") == "938 419 nút, E7 2000"
    assert bp.decimal_commas("<mn>0.614</mn><mo>,</mo><mn>5</mn>") == (
        "<mn>0,614</mn><mo>,</mo><mn>5</mn>"
    )


def test_captions_mentions_and_sequence():
    body = (
        "<p><strong>Bảng 1.</strong> a</p><p>xem Bảng 1, Hình B.1, Bảng 9, <code>Bảng 7</code></p>"
        "<figure><figcaption>Hình B.1. x</figcaption></figure>"
    )
    body, found = bp.label_captions(body)
    assert found == {"tab": ["1"], "fig": ["B.1"]}
    body, missing = bp.link_mentions(body, found)
    assert missing == ["Bảng 9"]
    assert '<a href="#tab-1">Bảng 1</a>' in body and '<a href="#fig-B.1">Hình B.1</a>' in body
    assert "<code>Bảng 7</code>" in body
    assert bp.sequence_errors(found) == []
    assert bp.sequence_errors({"tab": ["1", "3"], "fig": ["B.2"]})


def test_pdf_pages_and_dests():
    pdf = (
        b"%PDF-1.4\n1 0 obj\n<</Type /Catalog /Pages 2 0 R /Dests 5 0 R>>\nendobj\n"
        b"2 0 obj\n<</Type /Pages /Kids [3 0 R 4 0 R]>>\nendobj\n"
        b"3 0 obj\n<</Type /Page>>\nendobj\n4 0 obj\n<</Type /Page>>\nendobj\n"
        b"5 0 obj\n<</sec-1 [3 0 R /XYZ 0 0 0] /tab#2DB.1 [4 0 R /XYZ 0 0 0]>>\nendobj\n"
    )
    objs = bp.pdf_objects(pdf)
    assert bp.pdf_pages(objs) == [3, 4]
    assert bp.pdf_dests(objs) == {"sec-1": 1, "tab-B.1": 2}
