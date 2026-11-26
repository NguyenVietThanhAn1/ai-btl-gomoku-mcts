"""Xuất `report/report.pdf` từ `report/report.md` (P7.3, D-40): pandoc → HTML (MathML) → Chrome.

    python -m gameai.tools.build_pdf            # build + kiểm
    python -m gameai.tools.build_pdf --keep DIR # giữ HTML trung gian để soát

Không cài gói Python; cần `pandoc` và Chrome/Edge (biến môi trường PANDOC / CHROME để chỉ đường).
"""

from __future__ import annotations

import argparse
import html
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "report" / "report.md"
OUT = ROOT / "report" / "report.pdf"
PANDOC_FORMAT = "gfm+tex_math_dollars+yaml_metadata_block+implicit_figures"
BROWSERS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]
MIN_TABLE_PT = 8.0
SINGLE_PANEL_PX = 1400  # hình thí nghiệm hẹp hơn mức này chỉ có một đồ thị → in nhỏ lại

CSS = """
@page { size: A4; margin: 18mm 20mm 18mm 20mm;
  @bottom-center { content: counter(page); font: 10pt "Times New Roman", serif; } }
@page :first { @bottom-center { content: none; } }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body { width: 170mm; margin: 0; font: 11.5pt/1.38 "Times New Roman", serif; color: #000; }
p { margin: 0 0 6pt; text-align: justify; orphans: 2; widows: 2; }
h1, h2, h3, h4 { font-family: "Times New Roman", serif; line-height: 1.25; break-after: avoid; }
h2 { font-size: 15pt; margin: 14pt 0 7pt; }
h3 { font-size: 12.5pt; margin: 10pt 0 5pt; }
h4 { font-size: 11.5pt; margin: 8pt 0 4pt; }
ul, ol { margin: 0 0 6pt; padding-left: 18pt; }
li { margin-bottom: 2pt; }
a { color: inherit; text-decoration: none; }
code { font-family: Consolas, monospace; font-size: 0.88em; overflow-wrap: anywhere; }
pre { background: #f5f5f5; border: 0.5pt solid #ccc; padding: 5pt 7pt; margin: 0 0 7pt;
  font-size: 9pt; line-height: 1.3; white-space: pre-wrap; break-inside: avoid; }
pre code { font-size: 1em; overflow-wrap: normal; }
math { font-family: "Cambria Math", math; }
math[display="block"] { margin: 4pt 0 8pt; break-inside: avoid; }
table { border-collapse: collapse; margin: 0 auto 9pt; font-size: 9.5pt; line-height: 1.25;
  max-width: 100%; }
th, td { border: 0.5pt solid #777; padding: 2pt 4pt; vertical-align: top; }
th { background: #ececec; }
thead { display: table-header-group; }
tr { break-inside: avoid; }
.keep { break-inside: avoid; }
.caption { break-after: avoid; text-align: left; margin-top: 4pt; }
figure { margin: 6pt 0 10pt; text-align: center; break-inside: avoid; }
figure img { max-width: 100%; max-height: 205mm; }
figure img.single { width: 120mm; }
figcaption { font-size: 10.5pt; margin-top: 3pt; text-align: justify; }
.title { text-align: center; font-size: 18pt; font-weight: bold; margin: 6mm 0 3mm; }
.subtitle { text-align: center; font-size: 12.5pt; margin: 0 0 8mm; }
.toc { break-before: page; break-after: page; }
.toc h2 { margin-top: 0; }
.toc div { display: flex; align-items: baseline; font-size: 11pt; line-height: 1.5; }
.toc div.l3 { padding-left: 16pt; font-size: 10.5pt; line-height: 1.4; }
.toc div.l2 { font-weight: bold; margin-top: 3pt; }
.toc .dots { flex: 1; border-bottom: 0.7pt dotted #888; margin: 0 4pt; }
"""

# Thu bảng rộng (sàn MIN_TABLE_PT), công thức và khối mã rộng; ghi lại những gì vẫn tràn lề.
FIT_JS = """
(function () {
  var W = document.body.clientWidth + 0.5, smallest = 99, bad = [];
  document.querySelectorAll('table').forEach(function (t, i) {
    var pt = 9.5;
    t.style.maxWidth = 'none';
    while (t.offsetWidth > W && pt > %MIN%) { pt -= 0.25; t.style.fontSize = pt + 'pt'; }
    smallest = Math.min(smallest, pt);
    if (t.offsetWidth > W) bad.push('table' + (i + 1));
  });
  function width(e) { return Math.max(e.getBoundingClientRect().width, e.scrollWidth); }
  document.querySelectorAll('math[display="block"]').forEach(function (m) {
    var pt = 11.5;
    while (width(m) > W && pt > 9.5) { pt -= 0.25; m.style.fontSize = pt + 'pt'; }
  });
  // Khối mã: thu chữ (≥ 8 pt) để không xuống dòng giữa chừng; vẫn rộng thì mới cho xuống dòng.
  document.querySelectorAll('pre').forEach(function (p) {
    var pt = 9;
    p.style.whiteSpace = 'pre';
    while (p.scrollWidth > p.clientWidth && pt > 8) { pt -= 0.25; p.style.fontSize = pt + 'pt'; }
    if (p.scrollWidth > p.clientWidth) { p.style.whiteSpace = 'pre-wrap'; p.style.fontSize = ''; }
  });
  document.querySelectorAll('math[display="block"], pre, img').forEach(function (e, i) {
    if (width(e) > W) bad.push(e.tagName + i + ':' + Math.round(width(e)));
  });
  document.body.setAttribute('data-overflow', bad.join(' '));
  document.body.setAttribute('data-min-table-pt', smallest);
})();
""".replace("%MIN%", str(MIN_TABLE_PT))


def strip_comments(md: str) -> str:
    """Bỏ mọi comment HTML (nguồn số liệu) cùng khoảng trắng đứng trước."""
    return re.sub(r"[ \t]*<!--.*?-->", "", md, flags=re.S)


def typography(md: str) -> str:
    """Giữ "95 %" và "938 419" cùng dòng; dấu phẩy thập phân `0{,}5` trong công thức không bị giãn.

    pandoc dịch `{,}` thành toán tử (có khoảng trắng) nên tạm đổi thành "." — `decimal_commas`
    đổi lại trong MathML.
    """
    md = re.sub(r"(\d) %", lambda m: m[1] + chr(0xA0) + "%", md)
    md = re.sub(r"(?<=\d) (?=\d{3}(?!\d))", chr(0xA0), md)  # "938 419" không tách dòng
    return re.sub(r"(\d)\{,\}(\d)", r"\1.\2", md)


def decimal_commas(body: str) -> str:
    return re.sub(r"<mn>(\d+)\.(\d+)</mn>", r"<mn>\1,\2</mn>", body)


def front_matter(md: str) -> dict[str, str]:
    m = re.match(r"---\r?\n(.*?)\r?\n---", md, flags=re.S)
    return dict(re.findall(r'^(\w+):\s*"?(.*?)"?\s*$', m.group(1), flags=re.M)) if m else {}


def plain(fragment: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", fragment)).strip()


def number_headings(body: str) -> tuple[str, list[tuple[int, str, str]]]:
    """Gán id ASCII `sec-N` cho h2/h3, trả (html, [(cấp, id, chữ)])."""
    toc: list[tuple[int, str, str]] = []

    def sub(m: re.Match[str]) -> str:
        level, inner = int(m.group(1)), m.group(2)
        ident = f"sec-{len(toc) + 1}"
        toc.append((level, ident, plain(inner)))
        return f'<h{level} id="{ident}">{inner}</h{level}>'

    return re.sub(r"<h([23])[^>]*>(.*?)</h\1>", sub, body, flags=re.S), toc


CAPTION_KIND = {"bảng": "tab", "hình": "fig"}


def label_captions(body: str) -> tuple[str, dict[str, list[str]]]:
    """Nhãn "Bảng N." / "Hình N." thành neo `tab-N` / `fig-N`; trả (html, số theo thứ tự)."""
    found: dict[str, list[str]] = {"tab": [], "fig": []}

    def anchor(kind: str, num: str, label: str) -> str:
        found[kind].append(num)
        ident = f"{kind}-{num}"
        return f'<a id="{ident}" href="#{ident}">{label}</a>'

    body = re.sub(
        r"<p><strong>(Bảng ((?:B\.)?\d+)\.)</strong>",
        lambda m: f'<p class="caption"><strong>{anchor("tab", m[2], m[1])}</strong>',
        body,
    )
    body = re.sub(
        r"(<figcaption[^>]*>)\s*(Hình ((?:B\.)?\d+)\.)",
        lambda m: m[1] + anchor("fig", m[3], m[2]),
        body,
    )
    return body, found


def link_mentions(body: str, found: dict[str, list[str]]) -> tuple[str, list[str]]:
    """Nối "Bảng N" / "Hình N" trong lời văn tới neo; trả (html, nhắc tới số không tồn tại)."""
    skip = {"a", "pre", "code", "math", "h2", "h3", "h4", "figcaption"}
    depth, missing, out = 0, [], []

    def sub(m: re.Match[str]) -> str:
        kind, num = CAPTION_KIND[m[1].lower()], m[2]
        if num not in found[kind]:
            missing.append(m[0])
            return m[0]
        return f'<a href="#{kind}-{num}">{m[0]}</a>'

    for part in re.split(r"(<[^>]+>)", body):
        tag = re.match(r"<(/?)([a-zA-Z0-9]+)", part)
        if tag:
            if tag[2] in skip and not part.endswith("/>"):
                depth += -1 if tag[1] else 1
        elif depth == 0:
            part = re.sub(r"\b([Bb]ảng|[Hh]ình)\s((?:B\.)?\d+)\b", sub, part)
        out.append(part)
    return "".join(out), missing


def sequence_errors(found: dict[str, list[str]]) -> list[str]:
    """Số bảng/hình phải liên tục: 1, 2, … và B.1, B.2, … theo thứ tự xuất hiện."""
    errors = []
    for kind, nums in found.items():
        for prefix in ("", "B."):
            group = [n for n in nums if n.startswith("B.") == bool(prefix)]
            if group != [f"{prefix}{i}" for i in range(1, len(group) + 1)]:
                errors.append(f"{kind} {prefix or 'thân'}: {group}")
    return errors


def absolute_images(body: str, base: Path) -> tuple[str, list[str]]:
    missing: list[str] = []

    def sub(m: re.Match[str]) -> str:
        path = (base / html.unescape(m[1])).resolve()
        if not path.is_file():
            missing.append(m[1])
        narrow = (
            path.is_file()
            and path.parent.parent.name == "results"
            and int.from_bytes(path.read_bytes()[16:20], "big") < SINGLE_PANEL_PX  # PNG IHDR
        )
        return f'src="{path.as_uri()}"' + (' class="single"' if narrow else "")

    return re.sub(r'src="([^"]+)"', sub, body), missing


def toc_html(toc: list[tuple[int, str, str]], pages: dict[str, int]) -> str:
    rows = [
        f'<div class="l{lv}"><a href="#{i}">{html.escape(text)}</a><span class="dots"></span>'
        f"<span>{pages.get(i, '00')}</span></div>"
        for lv, i, text in toc
    ]
    return '<nav class="toc"><h2>Mục lục</h2>' + "".join(rows) + "</nav>"


def pandoc_body(md: str) -> str:
    exe = os.environ.get("PANDOC") or shutil.which("pandoc")
    if not exe:
        raise SystemExit("Không thấy pandoc (đặt biến môi trường PANDOC).")
    r = subprocess.run(
        [exe, "-f", PANDOC_FORMAT, "-t", "html5", "--math-method=mathml", "--wrap=none"],
        input=md, capture_output=True, text=True, encoding="utf-8", check=True,
    )  # fmt: skip
    if r.stderr.strip():  # công thức pandoc không dịch được chỉ báo bằng warning
        raise SystemExit(f"pandoc cảnh báo:\n{r.stderr}")
    return r.stdout


def prepare(src: Path) -> tuple[dict[str, str], str, list[tuple[int, str, str]]]:
    """report.md → (front matter, thân HTML đã xử lý, mục lục). Lỗi cấu trúc → SystemExit."""
    md = src.read_text(encoding="utf-8")
    meta = front_matter(md)
    body = decimal_commas(pandoc_body(typography(strip_comments(md))))
    body = re.sub(r"<colgroup>.*?</colgroup>", "", body, flags=re.S)  # để cột tự co
    body = re.sub(r'<(table|col|tr) style="[^"]*"', r"<\1", body)
    body, toc = number_headings(body)
    body, found = label_captions(body)
    body, bad_refs = link_mentions(body, found)
    body, bad_images = absolute_images(body, src.parent)
    # Giữ chú thích bảng đi cùng bảng.
    body = re.sub(
        r'(<p class="caption">(?:(?!</p>).)*</p>\s*<table.*?</table>)',
        r'<div class="keep">\1</div>',
        body,
        flags=re.S,
    )
    errors = sequence_errors(found)
    errors += [f"nhắc tới bảng/hình không có: {r}" for r in bad_refs]
    errors += [f"thiếu ảnh: {p}" for p in bad_images]
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"bảng: {len(found['tab'])}, hình: {len(found['fig'])}, mục: {len(toc)}")
    return meta, body, toc


def page_html(meta: dict[str, str], body: str, toc: list, pages: dict[str, int]) -> str:
    title, subtitle = html.escape(meta.get("title", "")), html.escape(meta.get("subtitle", ""))
    # Trang đầu: tiêu đề + Tóm tắt (mục đầu); mục lục sang trang riêng, thân bài sang trang mới.
    second = f'<h2 id="{toc[1][1]}"'
    cut = body.index(second)
    return (
        f'<!DOCTYPE html><html lang="{meta.get("lang", "vi")}"><head><meta charset="utf-8">'
        f"<title>{title}</title><style>{CSS}</style></head><body>"
        f'<div class="title">{title}</div><div class="subtitle">{subtitle}</div>'
        f"{body[:cut]}{toc_html(toc, pages)}{body[cut:]}<script>{FIT_JS}</script></body></html>"
    )


# ---------------------------------------------------------------- Chrome + đọc PDF
def browser() -> str:
    exe = os.environ.get("CHROME") or next((p for p in BROWSERS if Path(p).is_file()), None)
    if not exe:
        raise SystemExit("Không thấy Chrome/Edge (đặt biến môi trường CHROME).")
    return exe


def run_browser(page: Path, profile: Path, *flags: str) -> str:
    cmd = [browser(), "--headless", "--disable-gpu", "--no-first-run",
           f"--user-data-dir={profile}", *flags, page.as_uri()]  # fmt: skip
    r = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180
    )
    if r.returncode != 0:
        raise SystemExit(f"trình duyệt lỗi {r.returncode}:\n{r.stderr[-2000:]}")
    return r.stdout


def pdf_objects(data: bytes) -> dict[int, bytes]:
    """Object của PDF do Chrome (Skia) sinh: không dùng object stream nên đọc thẳng được."""
    found = re.finditer(rb"(?:^|\n)(\d+) 0 obj\b(.*?)\bendobj", data, flags=re.S)
    return {int(m[1]): m[2] for m in found}


def pdf_pages(objs: dict[int, bytes]) -> list[int]:
    """Số object của các trang, đúng thứ tự."""
    catalog = next(v for v in objs.values() if re.search(rb"/Type\s*/Catalog", v))
    order: list[int] = []

    def walk(num: int) -> None:
        kids = re.search(rb"/Kids\s*\[(.*?)\]", objs[num], flags=re.S)
        if kids is None:
            order.append(num)
            return
        for k in re.findall(rb"(\d+) 0 R", kids[1]):
            walk(int(k))

    walk(int(re.search(rb"/Pages\s+(\d+) 0 R", catalog)[1]))
    return order


def pdf_dests(objs: dict[int, bytes]) -> dict[str, int]:
    """Tên đích nội bộ → số trang (từ 1)."""
    page_no = {num: i + 1 for i, num in enumerate(pdf_pages(objs))}
    catalog = next(v for v in objs.values() if re.search(rb"/Type\s*/Catalog", v))
    ref = re.search(rb"/Dests\s+(\d+) 0 R", catalog)
    table = objs[int(ref[1])] if ref else catalog
    return {
        m[1].decode().replace("#2D", "-").replace("#2E", "."): page_no[int(m[2])]
        for m in re.finditer(rb"/((?:sec|tab|fig)[^\s\[/]+)\s*\[\s*(\d+) 0 R", table)
    }


def pdf_fonts(objs: dict[int, bytes]) -> tuple[list[str], list[str]]:
    """(font đã nhúng, font không nhúng) theo /FontDescriptor."""
    ok, bad = set(), set()
    for v in objs.values():
        if re.search(rb"/Type\s*/FontDescriptor", v):
            name = re.search(rb"/FontName\s*/([^\s/>\]]+)", v)[1].decode().split("+")[-1]
            (ok if re.search(rb"/FontFile[23]?\s", v) else bad).add(name)
    return sorted(ok), sorted(bad)


def build(src: Path = SRC, out: Path = OUT, keep: Path | None = None) -> dict[str, int]:
    meta, body, toc = prepare(src)
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        work = keep or Path(tmp)
        work.mkdir(parents=True, exist_ok=True)
        page, pdf = work / "report.html", work / "report.pdf"
        profile = Path(tmp) / "profile"
        pages: dict[str, int] = {}
        wanted: set[str] = set()
        for _ in range(3):  # lượt 1 lấy số trang cho mục lục, lượt sau kiểm ổn định
            text = page_html(meta, body, toc, pages)
            wanted = set(re.findall(r'href="#([^"]+)"', text))
            page.write_text(text, encoding="utf-8")
            run_browser(page, profile, "--no-pdf-header-footer", f"--print-to-pdf={pdf}")
            objs = pdf_objects(pdf.read_bytes())
            dests = pdf_dests(objs)
            if dests == pages:
                break
            pages = dests
        else:
            raise SystemExit("số trang mục lục không ổn định sau 3 lượt")
        dom = run_browser(page, profile, "--dump-dom")
        overflow = re.search(r'data-overflow="([^"]*)"', dom)
        min_pt = re.search(r'data-min-table-pt="([^"]*)"', dom)
        if overflow is None or overflow[1]:
            raise SystemExit(f"tràn lề: {overflow[1] if overflow else 'không chạy được JS'}")
        if wanted - set(pages):
            raise SystemExit(f"liên kết không có đích: {sorted(wanted - set(pages))}")
        embedded, missing = pdf_fonts(objs)
        if missing:
            raise SystemExit(f"font chưa nhúng: {missing}")
        shutil.copyfile(pdf, out)
    total = len(pdf_pages(objs))
    print(f"font nhúng: {', '.join(embedded)}")
    print(f"cỡ chữ bảng nhỏ nhất: {min_pt[1]} pt; liên kết nội bộ: {len(wanted)}, đủ đích")
    print(f"{out}: {total} trang, {out.stat().st_size / 1e6:.2f} MB")
    return pages


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--keep", type=Path, help="giữ HTML/PDF trung gian ở thư mục này")
    ap.add_argument("--pages", action="store_true", help="in trang của từng mục/bảng/hình")
    args = ap.parse_args(argv)
    pages = build(out=args.out.resolve(), keep=args.keep and args.keep.resolve())
    if args.pages:
        print(" ".join(f"{k}={v}" for k, v in pages.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
