"""P7.2: đối chiếu mọi số trong `report/report.md` với nguồn trong `results/` (D-30).

Cú pháp (comment HTML, pandoc bỏ qua) — chi tiết trong `report_check.md`:

- `0,92 <!-- src: results/tables/X.csv | k=v,k=v | cột [| x100,abs] -->`: lọc đúng 1 hàng; văn bản
  ngay trước comment phải kết thúc bằng giá trị định dạng VN (số chữ số thập phân theo token).
- `0,62 <!-- src: summary_kinrow.md#E5 -->`: token có nguyên văn trong mục có tiêu đề bắt đầu `E5`.
- `<!-- src-table: summary_kinrow.md#Bảng E1 -->` + bảng ngay sau: giống byte bảng đầu của mục.
- `<!-- const: D-18 -->`: số trên dòng là hằng số thiết kế (D-xx phải có trong DECISIONS).
- `<!-- example: gameai/agents/mcts.md -->`: số trên dòng thuộc ví dụ tính tay lấy từ file `.md` đó
  (không phải số liệu đo); file phải tồn tại. Khối code ``` bỏ qua hoàn toàn.

    python -m gameai.experiments.report_check            # report/report.md
    python -m gameai.experiments.report_check FILE.md
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from gameai.experiments.plots import ci, vn

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "report" / "report.md"
DECISIONS = ROOT / "docs" / "DECISIONS.md"
ABSTRACT_HEADING = "Tóm tắt"
REFS_HEADING = "Tài liệu tham khảo"
MAX_ABSTRACT_WORDS = 200

COMMENT = re.compile(r"<!--(.*?)-->", re.S)
# số VN: nhóm nghìn bằng khoảng trắng hoặc liền, phẩy thập phân, dấu âm; không dính chữ/dấu chấm
NUM = re.compile(r"(?<![\w.,/-])-?(?:\d{1,3}(?: \d{3})+|\d+)(?:,\d+)?(?![\w,]|\.\d)")
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
CAPTION = re.compile(r"^\*\*(Hình|Bảng) (\d+)\.\*\*")
FIG_CAPTION = re.compile(r"!\[Hình (\d+)\. ")  # caption hình = alt text kiểu pandoc
IMAGE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)")
CODE = re.compile(r"`[^`]*`")
MATH = re.compile(r"\$[^$]*\$")
LINK_TARGET = re.compile(r"\]\([^)]*\)")
# ký tự điều khiển trừ \n, \r (TAB cũng cấm): dấu hiệu escape hỏng khi ghi file, vd. "\tfrac" → TAB
CONTROL = re.compile(r"[\x00-\x09\x0b\x0c\x0e-\x1f]")


class SourceError(Exception):
    """Nguồn không khớp / không đọc được."""


@dataclass
class Issue:
    line: int
    msg: str

    def __str__(self) -> str:
        return f"L{self.line}: {self.msg}"


# ---------------------------------------------------------------- nguồn


def resolve(path: str) -> Path:
    """Đường dẫn nguồn tương đối gốc repo; tên trần `summary_kinrow.md` → `results/tables/`."""
    p = ROOT / path
    return p if p.exists() else ROOT / "results" / "tables" / path


def in_results(p: Path) -> bool:
    return (ROOT / "results").resolve() in p.resolve().parents


def md_sections(text: str) -> list[tuple[int, str, list[str]]]:
    """[(cấp, tiêu đề, các dòng thân tới tiêu đề cùng cấp/cao hơn kế tiếp)]."""
    lines = text.splitlines()
    heads = [(i, len(m.group(1)), m.group(2)) for i, ln in enumerate(lines)
             if (m := HEADING.match(ln))]  # fmt: skip
    out = []
    for j, (i, lvl, title) in enumerate(heads):
        end = next((k for k, lv, _ in heads[j + 1 :] if lv <= lvl), len(lines))
        out.append((lvl, title, lines[i + 1 : end]))
    return out


def find_section(text: str, anchor: str) -> list[str]:
    """Thân mục có tiêu đề bắt đầu bằng `anchor` (phải duy nhất)."""
    hit = [body for _, title, body in md_sections(text) if title.startswith(anchor)]
    if len(hit) != 1:
        raise SourceError(f"neo '#{anchor}': {len(hit)} tiêu đề khớp")
    return hit[0]


def table_span(lines: list[str], start: int = 0) -> tuple[int, int]:
    """(đầu, cuối) của khối bảng md đầu tiên từ `start`; (start, start) nếu không có."""
    s = next((i for i in range(start, len(lines)) if lines[i].startswith("|")), None)
    if s is None:
        return start, start
    e = s
    while e < len(lines) and lines[e].startswith("|"):
        e += 1
    return s, e


def csv_value(path: Path, filt: str, col: str) -> str:
    """Giá trị cột (`a/b/c` → ghép bằng `/`) của đúng một hàng khớp `k=v,…` (`-` = không lọc)."""
    with path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    conds = [c.split("=", 1) for c in filt.split(",") if c.strip() and c.strip() != "-"]
    hit = [r for r in rows if all(r.get(k.strip()) == v.strip() for k, v in conds)]
    if len(hit) != 1:
        raise SourceError(f"{path.name} | {filt}: {len(hit)} hàng")
    cols = [c.strip() for c in col.split("/")]
    missing = [c for c in cols if c not in hit[0]]
    if missing:
        raise SourceError(f"{path.name}: không có cột {missing}")
    return "/".join(hit[0][c] for c in cols)


def norm(s: str) -> str:
    return s.replace("−", "-").replace(" ", " ")


def last_number(before: str) -> re.Match[str]:
    toks = list(NUM.finditer(norm(before)))
    if not toks:
        raise SourceError("không có số trước comment")
    return toks[-1]


def expected_text(raw: str, before: str, transforms: list[str]) -> str:
    """Chuỗi phải đứng ngay trước comment. Số → `vn` với số chữ số thập phân của token đứng trước;
    nhóm nghìn theo token (5000 hay 5 000 đều được nếu giá trị khớp). W/D/L, chuỗi → nguyên văn."""
    if "/" in raw:
        return raw
    try:
        v = float(raw)
    except ValueError:
        return raw
    if "x100" in transforms:
        v *= 100
    if "abs" in transforms:
        v = abs(v)
    tok = last_number(before).group(0)
    d = len(tok.split(",")[1]) if "," in tok else 0
    s = vn(v, d)
    return tok if s.replace(" ", "") == tok.replace(" ", "") else s


# ---------------------------------------------------------------- từng loại comment


_N = r"-?(?:\d{1,3}(?: \d{3})+|\d+)(?:,\d+)?"
# đoạn được một comment neo summary phủ: `x [lo; hi]` hoặc khoảng giá trị `a–b`
CI_TAIL = re.compile(rf"({_N} \[[^\[\]]*\]|{_N}–{_N})$")


def _value_digits(before: str) -> int:
    """Số chữ số thập phân của `x` trong `x [lo; hi]` cuối văn bản (không thì token cuối)."""
    m = CI_TAIL.search(norm(before))
    tok = m.group(1).split(" [")[0] if m and "[" in m.group(1) else last_number(before).group(0)
    return len(tok.split(",")[1]) if "," in tok else 0


def ci_text(raw: str, before: str) -> str:
    """Cột `x,lo,hi` → chuỗi `x [lo; hi]`; `x` theo số chữ số thập phân của token trong report,
    biên theo `plots.ci` (luật làm tròn D-30: có thể thêm một chữ số)."""
    vals = [float(v) for v in raw.split(",")]
    if len(vals) != 3:
        raise SourceError("cột dạng khoảng cần đúng 3 cột: giá trị,cận dưới,cận trên")
    d = _value_digits(before)
    return f"{vn(vals[0], d)} {ci(vals[1], vals[2], d)}"


def rounding_rule_hit(lo: float, hi: float, d: int) -> bool:
    """Làm tròn [lo; hi] tới d chữ số vi phạm luật D-30 (đổi kết luận chứa 0 / 0,5, hoặc biên ≠ 0
    thành 0) — khi đó `plots.ci` thêm một chữ số."""
    return ci(lo, hi, d) != f"[{vn(lo, d)}; {vn(hi, d)}]"


def check_src(body: str, before: str, read: dict[Path, str]) -> int | None:
    """Kiểm `src:`; trả vị trí bắt đầu đoạn được phủ (mọi số từ đó tới comment không bị báo
    'số trần'). Đoạn = một số, hoặc `x [lo; hi]` (khoảng tin cậy) nếu văn bản kết thúc bằng `]`."""
    parts = [s.strip() for s in body[len("src:") :].split("|")]
    path, _, anchor = parts[0].partition("#")
    p = resolve(path)
    if not p.exists():
        raise SourceError(f"không có file {parts[0]}")
    if not in_results(p):
        raise SourceError(f"nguồn ngoài results/: {parts[0]}")
    if anchor:
        b = norm(before)
        m = CI_TAIL.search(b)
        span = (m.group(1), m.start(1)) if m else (last_number(before).group(0),
                                                     last_number(before).start())  # fmt: skip
        text = read.setdefault(p, p.read_text(encoding="utf-8"))
        if span[0] not in norm("\n".join(find_section(text, anchor))):
            raise SourceError(f"'{span[0]}' không có trong mục '#{anchor}'")
        return span[1]
    if len(parts) < 3:
        raise SourceError("cần 'file | lọc | cột'")
    cols = [c.strip() for c in parts[2].split(",")]
    raws = [csv_value(p, parts[1], c) for c in cols]
    tf = [t.strip() for t in parts[3].split(",")] if len(parts) > 3 else []
    raw = ",".join(raws)
    exp = ci_text(raw, before) if len(cols) > 1 else expected_text(raw, before, tf)
    exp, b = norm(exp), norm(before)
    ok = b.endswith(exp) and (len(b) == len(exp) or not re.match(r"[\d,]", b[-len(exp) - 1]))
    if not ok:
        if len(cols) == 3:
            v = [float(x) for x in raw.split(",")]
            if rounding_rule_hit(v[1], v[2], _value_digits(before)):
                raise SourceError(
                    f"D-30: không làm tròn biên CI khi làm tròn đổi kết luận chứa 0 / 0,5 hoặc "
                    f"biến biên ≠ 0 thành 0 — cần '{exp}' (nguồn: {raw})"
                )
        raise SourceError(f"cần '{exp}' ngay trước comment (nguồn: {raw})")
    return len(b) - len(exp)


def check_table(body: str, lines: list[str], i: int, read: dict[Path, str]) -> tuple[int, int]:
    """Kiểm `src-table:`; trả (đầu, cuối) khối bảng trong report để bỏ qua khi quét số."""
    path, _, anchor = body[len("src-table:") :].strip().partition("#")
    p = resolve(path.strip())
    text = read.setdefault(p, p.read_text(encoding="utf-8"))
    sec = find_section(text, anchor.strip())
    ws, we = table_span(sec)
    gs, ge = table_span(lines, i + 1)
    want, got = sec[ws:we], lines[gs:ge]
    if not want:
        raise SourceError(f"không có bảng trong mục '#{anchor.strip()}'")
    if got != want:
        pairs = zip(got, want, strict=False)
        k = next((j for j, (a, b) in enumerate(pairs) if a != b), min(len(got), len(want)))
        raise SourceError(f"bảng khác summary từ dòng {k + 1} ({len(got)} vs {len(want)} dòng)")
    return gs, ge


def check_example(body: str) -> list[str]:
    paths = body[len("example:") :].split()
    if not paths:
        return ["example: thiếu đường dẫn file .md nguồn"]
    return [f"example: không có file {p}" for p in paths if not (ROOT / p).exists()]


def decision_text(decisions: str, d: str) -> str | None:
    """Nội dung mục `### D-xx` (tới tiêu đề kế tiếp); None nếu không có."""
    m = re.search(rf"^#+ {d} .*?(?=^#+ |\Z)", decisions, re.M | re.S)
    return m.group(0) if m else None


def _values(text: str) -> set[float]:
    """Mọi số trong văn bản (dấu chấm hoặc phẩy thập phân, nhóm nghìn bằng khoảng trắng)."""
    out = set()
    for t in re.findall(r"\d+(?:[  ]\d{3})*(?:[.,]\d+)?", text):
        out.add(float(t.replace(" ", "").replace(" ", "").replace(",", ".")))
    return out


def check_const(body: str, decisions: str) -> tuple[list[str], set[str] | None]:
    """`const: D-xx …` (cả dòng) hoặc `const: D-xx … | tok tok` (chỉ các token liệt kê; mỗi token
    phải có trong văn bản của một D-xx đã nêu). Trả (lỗi, token được miễn; None = cả dòng)."""
    head, sep, toks = body[len("const:") :].partition("|")
    ids = re.findall(r"D-\d+", head)
    errs, texts = [], []
    for d in ids:
        t = decision_text(decisions, d)
        if t is None:
            errs.append(f"const: {d} không có trong DECISIONS")
        else:
            texts.append(t)
    if not sep:
        return errs, None
    allowed = set(toks.split())
    vals = set().union(*(_values(t) for t in texts)) if texts else set()
    for tok in allowed:
        if float(norm(tok).replace(" ", "").replace(",", ".")) not in vals:
            errs.append(f"const: '{tok}' không có trong {', '.join(ids)}")
    return errs, allowed


# ---------------------------------------------------------------- quét file


def mask(line: str) -> str:
    """Thay code `…`, công thức `$…$`, comment, đích link/ảnh bằng khoảng trắng (giữ vị trí)."""
    for pat in (COMMENT, CODE, MATH, LINK_TARGET):
        line = pat.sub(lambda m: " " * len(m.group(0)), line)
    return line


def is_strict(tok: str, after: str) -> bool:
    """Số bắt buộc có nguồn: có phần thập phân, ≥ 100, hoặc theo sau là %."""
    t = tok.lstrip("-")
    return "," in t or int(t.replace(" ", "")) >= 100 or after.lstrip().startswith("%")


def check_text(
    text: str, decisions: str | None = None, base: Path = REPORT.parent
) -> tuple[list[Issue], int]:
    """Trả (lỗi, số từ của Tóm tắt). `base` = thư mục của file report (ảnh tương đối)."""
    if decisions is None:
        decisions = DECISIONS.read_text(encoding="utf-8") if DECISIONS.exists() else ""
    issues: list[Issue] = []
    lines = text.splitlines()
    read: dict[Path, str] = {}
    skip: set[int] = set()
    section = ""
    captions = {"Hình": 0, "Bảng": 0}
    fence = False
    for m in CONTROL.finditer(text):
        n = text.count("\n", 0, m.start()) + 1
        issues.append(Issue(n, f"ký tự điều khiển {m.group(0)!r} (escape hỏng? vd. \\tfrac)"))
    for i, line in enumerate(lines):
        n = i + 1
        if line.lstrip().startswith("```"):
            fence = not fence
            continue
        if fence:
            continue
        if m := HEADING.match(line):
            section = m.group(2)
            continue
        if section.startswith(REFS_HEADING):
            continue
        found = [("Bảng", int(m.group(2)))] if (m := CAPTION.match(line)) else []
        if m and m.group(1) == "Hình":
            issues.append(
                Issue(n, "caption hình đặt trong ![Hình n. …](…), không dùng dòng **Hình**")
            )
            found = []
        found += [("Hình", int(k)) for k in FIG_CAPTION.findall(line)]
        for kind, k in found:
            if k != captions[kind] + 1:
                issues.append(Issue(n, f"{kind} {k}: số thứ tự không liên tiếp"))
            captions[kind] = k
        for alt, img in IMAGE.findall(line):
            if not (base / img).exists():
                issues.append(Issue(n, f"ảnh không tồn tại: {img}"))
            if not alt.startswith("Hình "):
                issues.append(Issue(n, f"ảnh thiếu caption 'Hình …': {img}"))
        if i in skip:
            continue
        const_line, covered, exempt = False, [], set()
        for cm in COMMENT.finditer(line):
            body = cm.group(1).strip()
            before = line[: cm.start()].rstrip().removesuffix("%").rstrip()
            try:
                if body.startswith("const:"):
                    errs, allowed = check_const(body, decisions)
                    issues += [Issue(n, e) for e in errs]
                    if allowed is None:
                        const_line = True
                    else:
                        exempt |= allowed
                elif body.startswith("example:"):
                    const_line = True
                    issues += [Issue(n, e) for e in check_example(body)]
                elif body.startswith("src-table:"):
                    skip.update(range(*check_table(body, lines, i, read)))
                elif body.startswith("src:"):
                    start = check_src(body, before, read)
                    if start is not None:
                        covered.append((start, cm.start()))
            except (SourceError, OSError) as e:
                issues.append(Issue(n, f"{body[:50]}…: {e}"))
        if const_line:
            continue
        masked = norm(mask(line))
        for m in NUM.finditer(masked):
            if m.group(0).replace(" ", "") in exempt:  # token liệt kê viết liền: 20000
                continue
            if is_strict(m.group(0), masked[m.end() :]) and not any(
                a <= m.start() < b for a, b in covered
            ):
                issues.append(Issue(n, f"số '{m.group(0)}' không có nguồn (src/const)"))
    words = abstract_words(text)
    if words > MAX_ABSTRACT_WORDS:
        issues.append(Issue(0, f"Tóm tắt {words} từ > {MAX_ABSTRACT_WORDS}"))
    return issues, words


def abstract_words(text: str) -> int:
    """Số từ của mục Tóm tắt (bỏ comment)."""
    for _, title, body in md_sections(text):
        if title.startswith(ABSTRACT_HEADING):
            return len(COMMENT.sub(" ", "\n".join(body)).split())
    return 0


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("path", nargs="?", default=str(REPORT))
    args = ap.parse_args(argv)
    path = Path(args.path)
    text = path.read_text(encoding="utf-8")
    issues, words = check_text(text, base=path.resolve().parent)
    for it in issues:
        print(f"  x {it}")
    n_src = len(re.findall(r"<!--\s*src:", text))
    n_tab = len(re.findall(r"<!--\s*src-table:", text))
    n_ex = len(re.findall(r"<!--\s*example:", text))
    n_const = len(re.findall(r"<!--\s*const:", text))
    print(f"[report_check] {n_src} số có nguồn, {n_tab} bảng src-table, {n_const} dòng const, "
          f"{n_ex} dòng ví dụ tay, Tóm tắt {words} từ, {len(issues)} lỗi")  # fmt: skip
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
