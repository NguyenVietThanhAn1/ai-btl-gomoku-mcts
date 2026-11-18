"""P7.1: sinh lại mọi bảng/hình báo cáo k-in-row (E1–E6) từ `results/raw` + `summary_kinrow.md`.

Không chạy search/ván nào — chỉ đọc raw và gọi lại đúng hàm tóm tắt/vẽ của từng thí nghiệm.

    python -m gameai.experiments.plots           # ghi đè results/tables + results/figures
    python -m gameai.experiments.plots --check   # sinh vào thư mục tạm, so byte từng CSV
"""

from __future__ import annotations

import argparse
import shutil
import statistics
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from gameai.experiments import e2_never_lose as e2
from gameai.experiments import e3_c_sweep as e3
from gameai.experiments import e4_final_move as e4
from gameai.experiments import e5_rollout as e5
from gameai.experiments import e6_mechanism as e6m
from gameai.experiments import e6_tactics as e6
from gameai.experiments.common import (
    moves_path_for,
    read_rows,
    summarize,
    write_summary,
)
from gameai.experiments.e5_rollout import _keep_pairs

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "results" / "raw"
TABLE_DIR = ROOT / "results" / "tables"
FIG_DIR = ROOT / "results" / "figures"

# Bảng ĐO TRỰC TIẾP (không có raw dạng ván/search để tóm tắt lại): nguồn = chính bảng. E1 (giá trị,
# nút, thời gian), benchmark tốc độ, sanity tactics bật, chi phí `_tactics`, thống kê trích thế E6.
# Bảng khác đọc chúng (e5_rates ← e5_bench; e6_choice ← e6_sanity + e6_positions_summary).
E1_TABLES = ("e1_nodes.csv", "e1_summary.csv", "e1_positions.csv")
MEASURED = (
    *E1_TABLES,
    "e5_bench.csv",
    "e6_bench.csv",
    "e6_sanity.csv",
    "e6_cost_check.csv",
    "e6_positions_summary.csv",
)


def _match(raw: Path, n_pairs: int | None = None) -> tuple[list[dict[str, str]], list[dict]]:
    rows = read_rows(raw)
    moves = read_rows(moves_path_for(raw))
    if n_pairs is not None:
        rows = _keep_pairs(rows, n_pairs)
        ids = {r["game_id"] for r in rows}
        moves = [m for m in moves if m["game_id"] in ids]
    return rows, moves


# ---------------------------------------------------------------- E2


def e2_tables(raw_dir: Path, table_dir: Path) -> list[Path]:
    summary: list[dict[str, Any]] = []
    for it in e2.ITERATIONS:
        for opp in e2.OPPONENTS:
            summary += summarize(*_match(raw_dir / f"e2_{it}_vs_{opp}.csv"))
    out = [table_dir / "e2_play.csv"]
    write_summary(summary, out[0])
    for stem in ("e2_exhaustive", "e2_exhaustive_ext"):
        if not (raw_dir / f"{stem}.csv").exists():
            continue
        rows = read_rows(raw_dir / f"{stem}.csv")
        mrows = [
            {**m, **{k: int(m[k]) for k in ("iterations", "mcts_player", "ply", "losing_leaves")}}
            for m in read_rows(raw_dir / f"{stem}_mistakes.csv")
        ]
        for name, cols, data in (
            (stem, e2.EXH_SUMMARY_COLUMNS, e2.summarize_exhaustive(rows)),
            (f"{stem}_by_role", e2.BY_ROLE_COLUMNS, e2.summarize_by_role(rows)),
            (f"{stem}_mistakes", e2.MISTAKE_SUMMARY_COLUMNS, e2.summarize_mistakes(mrows)),
        ):
            e2._write(table_dir / f"{name}.csv", cols, data)
            out.append(table_dir / f"{name}.csv")
    return out


# ---------------------------------------------------------------- E3


def _e3_table(part: str, pts: list[tuple[float, int]], raw_dir: Path,
              n_pairs: int | None = None) -> list[dict[str, Any]]:  # fmt: skip
    table: list[dict[str, Any]] = []
    for c, it in pts:
        summ = summarize(*_match(e3.raw_path(part, c, it, False, raw_dir), n_pairs))
        table += [{"part": part, "c": c, "iterations": it, **s} for s in summ]
    return table


def e3_tables(raw_dir: Path, table_dir: Path) -> list[Path]:
    """Như `run_part` / `run_pilot` / `run_ab2`, nhưng chỉ đọc raw. Pilot = 10 cặp đầu của file
    AB2 cùng (c, 5000) (file được chạy tiếp tới 25 cặp ở bước ab2)."""
    out = []
    tables: dict[str, list[dict[str, Any]]] = {}
    for name in ("3x3_random", "3x3_minimax", "greedy"):
        tables[name] = _e3_table(name, e3.points(e3.PARTS[name], False), raw_dir)
    c = e3.choose_pilot_c(tables["greedy"])
    tables["ab2_pilot"] = _e3_table("ab2", [(c, e3.PILOT_ITER)], raw_dir, e3.PILOT_PAIRS)
    pts = [(c, it) for it in e3.AB2_ITERATIONS for c in e3.C_VALUES]
    if all(e3.raw_path("ab2", c, it, False, raw_dir).exists() for c, it in pts):
        tables["ab2"] = _e3_table("ab2", pts, raw_dir)
    for name, t in tables.items():
        e3.write_table(t, table_dir / f"e3_{name}.csv")
        out.append(table_dir / f"e3_{name}.csv")
    return out


# ---------------------------------------------------------------- E4


def e4_tables(raw_dir: Path, table_dir: Path) -> list[Path]:
    rows3, rows15 = (read_rows(raw_dir / f"e4_roots_{b}.csv") for b in ("3x3", "15x15"))
    e4.write_csv(e4.summarize_roots(rows3 + rows15), e4.SUMMARY_ROOT_COLUMNS,
                 table_dir / "e4_roots_summary.csv")  # fmt: skip
    e4.write_csv(e4.example_rows(rows3, rows15), e4.EXAMPLE_COLUMNS,
                 table_dir / "e4_roots_examples.csv")  # fmt: skip
    table: list[dict[str, Any]] = []
    for board, (_, iters, _, _) in e4.MATCH.items():
        for it in iters:
            raw = raw_dir / f"e4_match_{board}_i{it}.csv"
            rows, moves = _match(raw)
            summ = summarize(rows, moves)
            for s in summ:
                s["score_lo"], s["score_hi"] = e4.score_ci(rows, s["split"])
            table += [{"board": board, "iterations": it, **s} for s in summ]
    e4.write_csv(table, e4.MATCH_COLUMNS, table_dir / "e4_match.csv")
    return [table_dir / f"e4_{n}.csv" for n in ("roots_summary", "roots_examples", "match")]


# ---------------------------------------------------------------- tất cả


def regenerate(raw_dir: Path, table_dir: Path, fig_dir: Path) -> tuple[list[Path], list[Path]]:
    """Sinh bảng + hình E2–E6 vào `table_dir`/`fig_dir`. Trả (bảng, hình)."""
    table_dir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)
    tables = e2_tables(raw_dir, table_dir) + e3_tables(raw_dir, table_dir)
    tables += e4_tables(raw_dir, table_dir)
    t5 = e5.build_tables(False, raw_dir, table_dir)
    tables += [table_dir / f"e5_{n}.csv" for n in t5 if (table_dir / f"e5_{n}.csv").exists()]
    t6 = e6.build_tables(False, raw_dir, table_dir)
    tables += [table_dir / f"e6_{n}.csv" for n in t6 if (table_dir / f"e6_{n}.csv").exists()]
    if e6m.build_table(raw_dir, table_dir):
        tables.append(table_dir / "e6_mechanism.csv")
    figs = list(e3.make_figures(False, table_dir, fig_dir))
    figs.append(e4.plot_match(read_rows(table_dir / "e4_match.csv"), fig_dir / "e4_match.png"))
    figs += e5.make_figures(False, table_dir, fig_dir)
    figs += e6.make_figures(False, table_dir, fig_dir)
    m = e6m.make_figure(table_dir, fig_dir)
    if m:
        figs.append(m)
    return sorted(set(tables)), figs


def committed_bytes(path: Path) -> bytes | None:
    """Nội dung file ở HEAD (`git show`); None nếu chưa track."""
    rel = path.resolve().relative_to(ROOT).as_posix()
    r = subprocess.run(["git", "show", f"HEAD:{rel}"], cwd=ROOT, capture_output=True)
    return _lf(r.stdout) if r.returncode == 0 else None


def _lf(b: bytes) -> bytes:
    """Chuẩn hóa xuống dòng (git autocrlf) trước khi so byte."""
    return b.replace(b"\r\n", b"\n")


def compare(
    new_dir: Path,
    ref_dir: Path,
    names: list[str],
    ref: Callable[[Path], bytes | None] = committed_bytes,
) -> list[tuple[str, str]]:
    """So byte từng file mới sinh với bản tham chiếu (mặc định: bản đã commit của
    `ref_dir / tên`). Trả [(tên, lý do)] cho file khác hoặc chưa có."""
    bad = []
    for n in names:
        b = ref(ref_dir / n)
        a = _lf((new_dir / n).read_bytes())
        if b is None:
            bad.append((n, "mới (chưa commit)"))
        elif a != b:
            la, lb = a.decode("utf-8").splitlines(), b.decode("utf-8").splitlines()
            first = next((i for i, (x, y) in enumerate(zip(la, lb, strict=False)) if x != y),
                         min(len(la), len(lb)))  # fmt: skip
            bad.append((n, f"khác từ dòng {first + 1} ({len(la)} vs {len(lb)} dòng)"))
    return bad


# ---------------------------------------------------------------- summary_kinrow.md

REPORT_MAP = [
    ("5.1", "Minimax vs Alpha-Beta: số nút, thời gian, giá trị/nước", "E1", [],
     ["e1_summary.csv", "e1_nodes.csv", "e1_positions.csv"]),
    ("5.2", "MCTS 3×3 không thua: W/D/L + vét cạn nhánh đối thủ", "E2", [],
     ["e2_play.csv", "e2_exhaustive.csv", "e2_exhaustive_by_role.csv"]),
    ("5.3", "Hằng số c: iter – tỷ lệ thắng, mỗi c một đường; W/D/L 15×15", "E3",
     ["e3_3x3.png", "e3_greedy.png", "e3_ab2.png"],
     ["e3_3x3_random.csv", "e3_3x3_minimax.csv", "e3_greedy.csv", "e3_ab2_pilot.csv",
      "e3_ab2.csv"]),
    ("5.4", "Chọn nước N lớn nhất vs W/N lớn nhất: W, N, W/N ở gốc; đối đầu", "E4",
     ["e4_match.png"], ["e4_roots_examples.csv", "e4_roots_summary.csv", "e4_match.csv"]),
    ("5.5", "Rollout random vs heuristic h300 (cùng iteration, cùng thời gian)", "E5",
     ["e5_iter.png", "e5_time.png"],
     ["e5_paired.csv", "e5_h2h.csv", "e5_greedy.csv", "e5_mref.csv", "e5_ab2.csv",
      "e5_bench.csv", "e5_rates.csv"]),
    ("5.6", "Kiểm tra thắng ngay / chặn ngay (`check_tactics`) + cơ chế", "E6",
     ["e6_choice.png", "e6_match.png", "e6_mechanism.png"],
     ["e6_choice.csv", "e6_match.csv", "e6_paired.csv", "e6_mechanism.csv",
      "e6_cost_check.csv", "e6_time.csv", "e6_tactic_rate.csv"]),
]  # fmt: skip


def vn(x: Any, d: int = 2) -> str:
    """Số kiểu VN: dấu phẩy thập phân; số nguyên (d = 0) ≥ 10 000 nhóm nghìn bằng khoảng trắng."""
    v = float(x)
    if d == 0:
        s = f"{round(v):,}".replace(",", " ")
        return s if abs(v) >= 10_000 else s.replace(" ", "")
    return f"{v:.{d}f}".replace(".", ",")


def ci(lo: Any, hi: Any, d: int = 2) -> str:
    return f"[{vn(lo, d)}; {vn(hi, d)}]"


def _t(table_dir: Path, name: str) -> list[dict[str, str]]:
    return read_rows(table_dir / name)


def _one(rows: list[dict[str, str]], **kw: Any) -> dict[str, str]:
    """Đúng một dòng khớp mọi điều kiện (so chuỗi); khác → KeyError (không đoán)."""
    hit = [r for r in rows if all(str(r[k]) == str(v) for k, v in kw.items())]
    if len(hit) != 1:
        raise KeyError(f"{kw}: {len(hit)} dòng")
    return hit[0]


def _md_table(head: list[str], rows: list[list[str]]) -> list[str]:
    return ["| " + " | ".join(head) + " |", "|" + "---|" * len(head),
            *("| " + " | ".join(r) + " |" for r in rows)]  # fmt: skip


def _table(title: str, head: list[str], rows: list[list[str]]) -> list[str]:
    """Bảng cho báo cáo: tiêu đề `###` riêng (neo `src-table` của `report_check`) + bảng md."""
    return ["", f"### {title}", "", *_md_table(head, rows)]


def _pct(r: dict[str, str], k: str = "nodes_saving_vs_minimax_pooled_pct") -> str:
    return vn(r[k]) + " %" if r[k] else "—"


def section_e1(td: Path) -> list[str]:
    s = _t(td, "e1_summary.csv")
    m3, a3, o3, t3 = (_one(s, board="3x3", variant=v)
                      for v in ("minimax", "ab", "ab_order", "ab_order_tt"))  # fmt: skip
    m15, a15, o15 = (_one(s, board="15x15", depth="2", variant=v)
                     for v in ("minimax", "ab", "ab_order"))  # fmt: skip
    a153, o153 = (_one(s, board="15x15", depth="3", variant=v) for v in ("ab", "ab_order"))
    lines = [
        f"- 3×3 ({m3['n_positions']} thế): giá trị gốc AB = Minimax "
        f"{a3['values_same_as_minimax']}; nút gộp {vn(m3['nodes_sum'], 0)} → "
        f"{vn(a3['nodes_sum'], 0)} (−{_pct(a3)}) → {vn(o3['nodes_sum'], 0)} (+ordering, "
        f"−{_pct(o3)}) → {vn(t3['nodes_sum'], 0)} (+TT, −{_pct(t3)}).",
        f"- 15×15 depth 2 ({m15['n_positions']} thế): {vn(m15['nodes_sum'], 0)} → "
        f"{vn(a15['nodes_sum'], 0)} (−{_pct(a15)}) → {vn(o15['nodes_sum'], 0)} (ordering, "
        f"−{_pct(o15)}), nhưng thời gian ordering {vn(o15['time_sum'], 3)} s vs "
        f"{vn(a15['time_sum'], 3)} s; depth 3: {vn(a153['nodes_sum'], 0)} → "
        f"{vn(o153['nodes_sum'], 0)} nút, {vn(a153['time_sum'])} → {vn(o153['time_sum'])} s.",
    ]
    rows = [[r["board"], r["depth"], r["variant"], vn(r["nodes_sum"], 0), vn(r["time_sum"], 3),
             _pct(r), r["values_same_as_minimax"] or "—"] for r in s]  # fmt: skip
    return lines + _table("Bảng E1 — số nút và thời gian (tổng trên các thế, `e1_summary.csv`)",
                          ["bàn", "depth", "biến thể", "nút", "giây", "giảm nút vs Minimax",
                           "giá trị = Minimax"], rows)  # fmt: skip


def section_e2(td: Path) -> list[str]:
    play = [r for r in _t(td, "e2_play.csv") if r["split"] == "all"]
    exh = _t(td, "e2_exhaustive.csv")
    top = max(exh, key=lambda r: int(r["iterations"]))
    m5 = [r for r in play if r["label_a"] == f"mcts{top['iterations']}"]
    lines = [
        f"- Vét cạn (mọi chuỗi nước đối thủ): {top['iterations']} iter → {top['losses']} nhánh "
        f"thua / {vn(top['branches'], 0)} ({top['n_runs']} run = seed × vai); "
        + "; ".join(
            f"{r['iterations']} iter {r['losses']}/{vn(r['branches'], 0)}"
            for r in exh
            if r is not top
        )
        + ".",  # fmt: skip
        f"- Đấu {top['iterations']} iter ({m5[0]['n']} ván/cặp, đổi lượt): "
        + ", ".join(f"vs {r['label_b']} W/D/L {r['wins']}/{r['draws']}/{r['losses']}" for r in m5)
        + ".",
    ]
    rows = [[r["label_a"], r["label_b"], f"{r['wins']}/{r['draws']}/{r['losses']}",
             vn(r["nonloss_rate"]) + " " + ci(r["nonloss_lo"], r["nonloss_hi"])]
            for r in play]  # fmt: skip
    lines += _table(
        "Bảng E2 — W/D/L của MCTS 3×3 (`e2_play.csv`)",
        ["MCTS", "đối thủ", "W/D/L", "không thua [Wilson 95 %]"],
        rows,
    )
    role = _t(td, "e2_exhaustive_by_role.csv")

    def zero(it: str, pl: str) -> str:
        r = _one(role, iterations=it, mcts_player=pl)
        return f"{r['seeds_zero_loss']}/{r['n_seeds']}"

    rows = [[r["iterations"], r["n_runs"], vn(r["branches"], 0), r["losses"], r["runs_with_loss"],
             zero(r["iterations"], "1"), zero(r["iterations"], "-1")] for r in exh]  # fmt: skip
    return lines + _table(
        "Bảng E2 — vét cạn mọi chuỗi nước đáp của đối thủ (`e2_exhaustive.csv`, "
        "`e2_exhaustive_by_role.csv`)",
        ["iter", "run (seed × vai)", "nhánh (lá)", "nhánh thua", "run có thua",
         "seed không thua, MCTS = X", "seed không thua, MCTS = O"],
        rows,
    )  # fmt: skip


def section_e3(td: Path) -> list[str]:
    rnd = [r for r in _t(td, "e3_3x3_random.csv") if r["split"] == "all"]
    mm = [r for r in _t(td, "e3_3x3_minimax.csv") if r["split"] == "all"]
    gr = [r for r in _t(td, "e3_greedy.csv") if r["split"] == "all"]
    ab = [r for r in _t(td, "e3_ab2.csv") if r["split"] == "all"]
    pilot = _one(_t(td, "e3_ab2_pilot.csv"), split="all")
    wr = [float(r["win_rate"]) for r in rnd]
    lo_it = min(int(r["iterations"]) for r in mm)
    nl_lo = [float(r["nonloss_rate"]) for r in mm if int(r["iterations"]) == lo_it]
    nl_hi = sorted({float(r["nonloss_rate"]) for r in mm if int(r["iterations"]) >= 2500})
    best_ab = max(ab, key=lambda r: float(r["win_rate"]))
    its = sorted({int(r["iterations"]) for r in gr})
    cs = sorted({r["c"] for r in gr}, key=float)
    g = [r for r in gr if int(r["iterations"]) in (1000, 5000)]
    lines = [
        f"- 3×3 vs Random: thắng {vn(min(wr), 3)}–{vn(max(wr), 3)}; vs Minimax không thua "
        f"{vn(min(nl_lo))}–{vn(max(nl_lo))} ở {lo_it} iter → "
        + "–".join(dict.fromkeys(vn(x) for x in (nl_hi[0], nl_hi[-1])))
        + " từ 2500 iter (mọi c).",
        "- 15×15 vs Greedy (h300 + tactics): "
        + "; ".join(
            f"c = {vn(r['c'], 1)}, {r['iterations']} iter {vn(r['win_rate'])} "
            f"{ci(r['win_lo'], r['win_hi'])}"
            for r in g
        )
        + ".",  # fmt: skip
        f"- AB depth 2: pilot c = {vn(pilot['c'], 1)} thắng {pilot['wins']}/{pilot['n']}; tốt nhất "
        f"c = {vn(best_ab['c'], 1)}, {best_ab['iterations']} iter {vn(best_ab['win_rate'])} "
        f"{ci(best_ab['win_lo'], best_ab['win_hi'])}.",
    ]
    rows = [[str(it)] + [vn(_one(gr, c=c, iterations=it)["win_rate"]) for c in cs] for it in its]
    lines += _table("Bảng E3 — tỷ lệ thắng vs Greedy 15×15 (`e3_greedy.csv`)",
                    ["iter"] + [f"c = {vn(c, 1)}" for c in cs], rows)  # fmt: skip
    for name, rs, what in (
        ("e3_3x3_random.csv", rnd, "3×3 vs Random"),
        ("e3_3x3_minimax.csv", mm, "3×3 vs Minimax"),
        ("e3_greedy.csv", gr, "15×15 vs Greedy"),
        ("e3_ab2.csv", ab, "15×15 vs AB depth 2"),
    ):
        lines += _table(f"Bảng E3 — W/D/L của MCTS, {what}, {rs[0]['n']} ván/điểm (`{name}`)",
                        ["iter"] + [f"c = {vn(c, 1)}" for c in cs], _wdl_rows(rs, cs))  # fmt: skip
    return lines


def _wdl_rows(rows: list[dict[str, str]], cs: list[str]) -> list[list[str]]:
    """Hàng = iter, cột = c, ô `W/D/L` (đúng một dòng mỗi (c, iter))."""
    its = sorted({int(r["iterations"]) for r in rows})
    out = []
    for it in its:
        cells = []
        for c in cs:
            r = _one(rows, c=c, iterations=it)
            cells.append(f"{r['wins']}/{r['draws']}/{r['losses']}")
        out.append([str(it), *cells])
    return out


def section_e4(td: Path) -> list[str]:
    summ = [r for r in _t(td, "e4_roots_summary.csv") if r["set"] == "all"]
    m = [r for r in _t(td, "e4_match.csv") if r["split"] == "all"]
    s3 = [r for r in summ if r["board"] == "3x3"]
    s15 = [r for r in summ if r["board"] == "15x15"]
    tr = [r for r in _t(td, "e4_roots_examples.csv") if r["example"] == "trace"]
    dr = [float(r["differ_rate"]) * 100 for r in s3]
    lines = [
        f"- 3×3: max_n ≠ max_wn ở {vn(min(dr), 1)}–{vn(max(dr), 1)} % thế; khi khác, tỷ lệ giữ "
        "giá trị trò chơi (max_n / max_wn) "
        + ", ".join(
            f"{r['iterations']} iter {vn(r['differ_opt_max_n'], 3)} / "
            f"{vn(r['differ_opt_max_wn'], 3)}"
            for r in s3
            if r["differ_opt_max_n"]
        )
        + ".",  # fmt: skip
        "- 15×15: số search có max_n ≠ max_wn: "
        + ", ".join(
            f"c = {vn(r['c'], 1)}, {r['iterations']} iter {r['n_differ']}/{r['n_positions']}"
            for r in s15
        )
        + ".",  # fmt: skip
        f"- Đối đầu 3×3 max_n vs max_wn ({m[0]['n']} ván/điểm): score "
        + ", ".join(
            f"{r['iterations']} iter {vn(r['score'], 3)} {ci(r['score_lo'], r['score_hi'])}"
            for r in m
        )
        + ".",  # fmt: skip
    ]
    rows = [[r["move"], vn(r["W"], 1), r["N"], vn(r["wn"], 3),
             "✓" if r["is_max_n"] == "1" else "", "✓" if r["is_max_wn"] == "1" else "",
             r["value"]] for r in tr]  # fmt: skip
    lines += _table(f"Bảng E4 — ví dụ gốc 3×3, {tr[0]['iterations']} iter, c = {vn(tr[0]['c'], 1)} "
                    "(`e4_roots_examples.csv`, giá trị trò chơi theo góc người đi ở gốc)",
                    ["ô", "W", "N", "W/N", "max N", "max W/N", "giá trị"], rows)  # fmt: skip
    rows = [[r["iterations"], vn(r["n_positions"], 0), vn(float(r["differ_rate"]) * 100, 1) + " %",
             vn(r["differ_opt_max_n"], 3), vn(r["differ_opt_max_wn"], 3)] for r in s3]  # fmt: skip
    lines += _table(
        f"Bảng E4 — 3×3, mọi thế ≥ 2 nước, c = {vn(s3[0]['c'], 1)}: khi nào max_n ≠ max_wn "
        "(`e4_roots_summary.csv`)",
        ["iter", "số thế", "max_n ≠ max_wn", "giữ giá trị — max_n", "giữ giá trị — max_wn"],
        rows,
    )
    rows = [[vn(r["c"], 1), r["iterations"], f"{r['n_differ']}/{r['n_positions']}",
             vn(r["max_wn_is_1_rate"]), vn(r["max_n_N_tie_rate"])] for r in s15]  # fmt: skip
    lines += _table(
        "Bảng E4 — 15×15 (h300 + tactics): số search có max_n ≠ max_wn (`e4_roots_summary.csv`)",
        ["c", "iter", "max_n ≠ max_wn", "con max_wn có W/N = 1", "max_n hòa N với con khác"],
        rows,
    )
    sp = {(r["iterations"], r["split"]): r for r in _t(td, "e4_match.csv")}
    rows = [[r["iterations"], f"{r['wins']}/{r['draws']}/{r['losses']}",
             f"{vn(r['score'], 3)} {ci(r['score_lo'], r['score_hi'])}",
             vn(sp[(r["iterations"], "A=X")]["score"], 3),
             vn(sp[(r["iterations"], "A=O")]["score"], 3)] for r in m]  # fmt: skip
    lines += _table(
        f"Bảng E4 — đối đầu 3×3 max_n (A) vs max_wn (B), {m[0]['n']} ván/điểm (`e4_match.csv`)",
        ["iter", "W/D/L của max_n", "score max_n [95 %]", "score khi max_n đi trước",
         "score khi max_n đi sau"],
        rows,
    )  # fmt: skip
    sens = [r for r in _t(td, "e4_roots_examples.csv") if r["example"] == "sensitivity"]
    if sens:
        pos = sens[0]["pos_id"]
        ex = [r for r in sens if r["pos_id"] == pos]
        r0 = ex[0]
        rows = [[r["move"], vn(r["W"], 1), r["N"], vn(r["wn"], 3),
                 "✓" if r["is_max_n"] == "1" else "", "✓" if r["is_max_wn"] == "1" else "",
                 vn(r["ref_W"], 1), r["ref_N"], vn(r["ref_wn"], 3)] for r in ex]  # fmt: skip
        lines += _table(
            f"Bảng E4 — ví dụ gốc 15×15, thế {pos} ({r0['plies']} ply), {r0['iterations']} iter, "
            f"c = {vn(r0['c'], 1)}, so với tham chiếu {vn(r0['ref_iterations'], 0)} iter "
            "(`e4_roots_examples.csv`)",
            ["ô", "W", "N", "W/N", "max N", "max W/N", "W tham chiếu", "N tham chiếu",
             "W/N tham chiếu"], rows)  # fmt: skip
    return lines


def section_e5(td: Path) -> list[str]:
    p = _t(td, "e5_paired.csv")
    h2h = [r for r in _t(td, "e5_h2h.csv") if r["split"] == "all"]

    def h(bt: str, b: str) -> str:
        r = _one(h2h, budget_type=bt, budget=b)
        return f"{vn(r['win_rate'])} {ci(r['win_lo'], r['win_hi'])}"

    def d(part: str, bt: str, b: str) -> str:
        r = _one(p, part=part, budget_type=bt, budget=b)
        return (f"{vn(r['mean_h300'])} vs {vn(r['mean_rand'])}, hiệu {vn(r['diff'])} "
                f"{ci(r['paired_lo'], r['paired_hi'])}")  # fmt: skip

    bench = e5.bench_rates(_t(td, "e5_bench.csv"))
    val = _t(td, "e5_validity.csv")[0]
    lines = [
        f"- Cùng thời gian (kết luận chính): đối đầu h300 thắng rand {h('time', '0.5')} (0,5 s), "
        f"{h('time', '2.0')} (2 s).",
        f"- Tỷ lệ thắng h300 vs rand (hiệu cặp): vs Greedy 0,5 s {d('greedy', 'time', '0.5')}; "
        f"2 s {d('greedy', 'time', '2.0')}; vs mref 2 s {d('mref', 'time', '2.0')}.",
        f"- Cùng iteration vs Greedy: 1000 iter {d('greedy', 'iter', '1000.0')}; 5000 iter "
        f"{d('greedy', 'iter', '5000.0')}.",
        f"- Benchmark đơn luồng (`e5_bench.csv`, trung vị): rand {vn(bench['rand'], 0)} iter/s, "
        f"h300 "
        f"{vn(bench['h300'], 0)} iter/s, tỉ lệ rand/h300 = {vn(bench['rand'] / bench['h300'])}.",
        f"- Kiểm tra hợp lệ mref: rand 1000 iter vs mref thắng {val['wins']}/{val['n']} "
        f"{ci(val['win_lo'], val['win_hi'])} (chứa 0,5: "
        f"{'có' if val['contains_half'] == '1' else 'không'}).",
    ]
    lines += _table(
        "Bảng E5 — cùng thời gian/nước (so sánh công bằng; 2 worker)",
        ["đối thủ", "thời gian/nước", "rand: thắng [Wilson 95 %]", "h300: thắng [Wilson 95 %]",
         "iteration thực tế/nước rand / h300", "hiệu cặp h300 − rand [95 %]"],
        _e5_rows(td, "time"),
    )  # fmt: skip
    lines += _table(
        "Bảng E5 — cùng số iteration (thiên vị h300; 4 worker)",
        ["đối thủ", "iter/nước", "rand: thắng [Wilson 95 %]", "h300: thắng [Wilson 95 %]",
         "ván rand / h300", "hiệu cặp h300 − rand [95 %]"],
        _e5_rows(td, "iter"),
    )  # fmt: skip
    return lines


def _e5_win(r: dict[str, str] | None) -> str:
    return "—" if r is None else f"{vn(r['win_rate'])} {ci(r['win_lo'], r['win_hi'])}"


def _e5_rows(td: Path, bt: str) -> list[list[str]]:
    """Hàng bảng E5 theo một trục ngân sách: đối đầu, Greedy, mref (+ AB2 ở trục iteration)."""
    pr = _t(td, "e5_paired.csv")
    out: list[list[str]] = []
    names = {"h2h": "đối đầu (h300 vs rand)", "greedy": "Greedy", "mref": "mref", "ab2": "AB2"}
    for part in ("h2h", "greedy", "mref", "ab2"):
        rows = [r for r in _t(td, f"e5_{part}.csv")
                if r["split"] == "all" and r["budget_type"] == bt]  # fmt: skip
        for b in sorted({float(r["budget"]) for r in rows}):
            ro = {r["rollout"]: r for r in rows if float(r["budget"]) == b}
            bud = f"{vn(b, 1)} s" if bt == "time" else vn(b, 0)
            if part == "h2h":
                r = ro["h300"]
                its = (f"{vn(r['b_search_iterations_per_move'], 0)} / "
                       f"{vn(r['a_search_iterations_per_move'], 0)}")  # fmt: skip
                mid = its if bt == "time" else f"— / {r['n']}"
                out.append([names[part], bud, "—", _e5_win(r), mid, "—"])
                continue
            pd = [x for x in pr if x["part"] == part and x["budget_type"] == bt
                  and float(x["budget"]) == b]  # fmt: skip
            diff = (f"{vn(pd[0]['diff'])} {ci(pd[0]['paired_lo'], pd[0]['paired_hi'])}"
                    if pd else "—")  # fmt: skip
            if bt == "time":
                mid = " / ".join(
                    vn(ro[k]["a_search_iterations_per_move"], 0) for k in ("rand", "h300")
                )
            else:
                mid = " / ".join(ro[k]["n"] if k in ro else "—" for k in ("rand", "h300"))
            out.append(
                [names[part], bud, _e5_win(ro.get("rand")), _e5_win(ro.get("h300")), mid, diff]
            )
    return out


def section_e6(td: Path) -> list[str]:
    ch = [r for r in _t(td, "e6_choice.csv") if r["stratum"] == "all"]
    pr = _t(td, "e6_paired.csv")

    def rate(roll: str, it: int) -> str:
        return vn(_one(ch, type="block", rollout=roll, iter=it)["correct_rate"])

    def pd(part: str, it: int) -> str:
        r = _one(pr, part=part, iters=it)
        return (f"{vn(r['mean_off'])} → {vn(r['mean_on'])}, hiệu {vn(r['diff'])} "
                f"{ci(r['paired_lo'], r['paired_hi'])}")  # fmt: skip

    its = e6.CHECKPOINTS
    lines = [
        "- Tắt tactics, chọn đúng ô chặn (trọng số pool) "
        f"{'/'.join(map(str, its))} iter: rand "
        + " → ".join(rate("rand", it) for it in its)
        + "; h300 "
        + " → ".join(rate("h300", it) for it in its)
        + "; bật tactics 1,00.",
        f"- Win rate tắt → bật (so cặp): h300 vs Greedy 1000 iter {pd('greedy', 1000)}; 5000 iter "
        f"{pd('greedy', 5000)}; rand vs mref {pd('mref', 1000)}.",
    ]
    mpath = td / "e6_mechanism.csv"
    if mpath.exists():
        mt = read_rows(mpath)

        def g(roll: str, it: int, grp: str, k: str) -> str:
            return vn(_one(mt, rollout=roll, iter=it, group=grp)[k])

        lines.append(
            "- Cơ chế (block, chạy lại cây): tỷ lệ con sai có W = 0 ở 100 iter h300 "
            f"{g('h300', 100, 'all', 'frac_wrong_zero')} vs rand "
            f"{g('rand', 100, 'all', 'frac_wrong_zero')}; nhóm chọn sai h300: W/N nước được chọn "
            f"{g('h300', 100, 'correct=0', 'wn_chosen')} / "
            f"{g('h300', 1000, 'correct=0', 'wn_chosen')} / "
            f"{g('h300', 5000, 'correct=0', 'wn_chosen')} (100 / 1000 / 5000 iter), ô thắng của "
            f"đối thủ đã mở dưới nước đó {g('h300', 1000, 'correct=0', 'refute_rate')} (1000) → "
            f"{g('h300', 5000, 'correct=0', 'refute_rate')} (5000). "
            "Kết luận: `e6_tactics.md`, D-21."
        )
    return lines + _e6_tables(td, ch, pr)


def _e6_tables(td: Path, ch: list[dict[str, str]], pr: list[dict[str, str]]) -> list[str]:
    """Bảng E6: tỷ lệ chọn đúng khi tắt tactics, win rate tắt → bật (cặp), chi phí."""

    def cell(typ: str, roll: str, it: str) -> str:
        r = _one(ch, type=typ, rollout=roll, iter=it)
        return f"{vn(r['correct_rate'])} {ci(r['boot_lo'], r['boot_hi'])}"

    its = [str(i) for i in e6.CHECKPOINTS]
    rows = [[it] + [cell(t, ro, it) for t in ("block", "win") for ro in ("rand", "h300")]
            for it in its]  # fmt: skip
    on = [vn(_one(ch, type=t, rollout="on", iter="")["correct_rate"]) for t in ("block", "win")]
    rows.append(["bật tactics", on[0], on[0], on[1], on[1]])
    r0 = _one(ch, type="block", rollout="rand", iter=its[0])
    seeds = int(r0["n_runs"]) // int(r0["n_pos"])
    out = _table(
        f"Bảng E6 — tỷ lệ chọn đúng khi TẮT check_tactics ({r0['n_pos']} thế/loại × {seeds} seed; "
        "trọng số pool, bootstrap 95 %; `e6_choice.csv`)",
        ["iter", "chặn four — rand", "chặn four — h300", "thắng ngay — rand", "thắng ngay — h300"],
        rows,
    )  # fmt: skip
    names = {"greedy": "h300 vs Greedy", "mref": "rand vs mref"}
    rows = [[names[r["part"]], r["iters"], r["n"], vn(r["mean_off"]), vn(r["mean_on"]),
             f"{vn(r['diff'])} {ci(r['paired_lo'], r['paired_hi'])}"] for r in pr]  # fmt: skip
    out += _table(
        "Bảng E6 — tỷ lệ thắng tắt → bật check_tactics, so cặp (`e6_paired.csv`)",
        ["cấu hình", "iter", "ván", "tắt", "bật", "hiệu bật − tắt [95 %]"],
        rows,
    )  # fmt: skip
    cost = _t(td, "e6_cost_check.csv")
    rows = []
    for typ, name in (("block", "đối thủ có four (chặn)"), ("win", "mình thắng ngay"),
                      ("quiet", "yên tĩnh (không tactic)")):  # fmt: skip
        rs = [r for r in cost if r["type"] == typ]
        ms = [float(r["check_ms"]) for r in rs]
        ovr = [float(r["overhead_rand"]) * 100 for r in rs if r["overhead_rand"]]
        ovh = [float(r["overhead_h300"]) * 100 for r in rs if r["overhead_h300"]]
        rows.append([name, str(len(rs)), vn(statistics.median(ms)), vn(max(ms)),
                     vn(statistics.median(ovr), 1) + " %" if ovr else "—",
                     vn(statistics.median(ovh), 1) + " %" if ovh else "—"])  # fmt: skip
    out += _table(
        "Bảng E6 — chi phí một lần check_tactics, đơn luồng (`e6_cost_check.csv`; overhead so với "
        "MCTS 1000 iter tắt tactics trên cùng thế)",
        ["loại thế", "số thế", "ms trung vị", "ms tối đa", "overhead trung vị — rand",
         "overhead trung vị — h300"],
        rows,
    )  # fmt: skip
    tr = [r for r in _t(td, "e6_tactic_rate.csv") if r["tactics"] == "on"]
    tm = _t(td, "e6_time.csv")
    rows = []
    for r in tr:
        off = [x for x in tm if x["part"] == r["part"] and x["iters"] == r["iters"]
               and x["tactics"] == "off"]  # fmt: skip
        onr = _one(tm, part=r["part"], iters=r["iters"], tactics="on")
        pct = vn(float(r["pct_direct"]) * 100, 1) + " %"
        vs = {"mref": "mref", "self": "h300 tắt (đối đầu)", "greedy": "Greedy"}[r["part"]]
        rows.append([r["label"], vs, r["n_moves"], pct,
                     vn(off[0]["mean_agent_time"]) if off else "—",
                     vn(onr["mean_agent_time"]), onr["source"].upper()])  # fmt: skip
    out += _table(
        "Bảng E6 — nước đi thẳng nhờ check_tactics và thời gian/nước trong ván "
        "(`e6_tactic_rate.csv`, "
        "`e6_time.csv`)",
        ["cấu hình (bật)", "ván với", "nước", "đi thẳng (không search)", "s/nước tắt",
         "s/nước bật", "ván bật lấy từ"],
        rows,
    )  # fmt: skip
    return out


SECTIONS: dict[str, Callable[[Path], list[str]]] = {
    "E1": section_e1, "E2": section_e2, "E3": section_e3, "E4": section_e4, "E5": section_e5,
    "E6": section_e6,
}  # fmt: skip


def write_summary_md(table_dir: Path = TABLE_DIR, fig_dir: Path = FIG_DIR) -> Path:
    """`summary_kinrow.md`: bản đồ hình/bảng → mục 5 báo cáo + số chính mỗi E; mọi số đọc từ CSV."""
    out = [
        "# Tổng hợp kết quả k-in-row (E1–E6) — nguồn cho mục 5 báo cáo",
        "",
        "> **Sinh tự động** bởi `python -m gameai.experiments.plots` từ `results/tables/*.csv` — "
        "không sửa tay. Số kiểu VN (dấu phẩy thập phân). Khoảng [ ] là 95 %: Wilson cho tỷ lệ một "
        "điểm, khoảng cặp cho hiệu, xấp xỉ chuẩn cho score E4, bootstrap cụm thế cho E6.",
        "",
        "## Bản đồ hình / bảng → mục 5 báo cáo",
        "",
        *_md_table(
            ["Mục", "Nội dung", "E", "Hình (`results/figures/`)", "Bảng (`results/tables/`)"],
            [
                [
                    sec,
                    what,
                    e,
                    ", ".join(f"`{f}`" for f in figs) or "—",
                    ", ".join(f"`{t}`" for t in tabs),
                ]
                for sec, what, e, figs, tabs in REPORT_MAP
            ],
        ),  # fmt: skip
        "",
    ]
    for sec, what, e, figs, tabs in REPORT_MAP:
        out += [f"## {e} — {what} (mục {sec})", ""]
        out += SECTIONS[e](table_dir)
        files = [f"`results/figures/{f}`" for f in figs if (fig_dir / f).exists()]
        files += [f"`results/tables/{t}`" for t in tabs if (table_dir / t).exists()]
        out += ["", "Nguồn: " + ", ".join(files), ""]
    path = table_dir / "summary_kinrow.md"
    with path.open("w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out))
    return path


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="sinh vào thư mục tạm và so byte")
    args = ap.parse_args(argv)
    missing = [n for n in MEASURED if not (TABLE_DIR / n).exists()]
    if missing:
        print(f"thiếu bảng đo trực tiếp: {missing}")
        return 1
    if args.check:
        with tempfile.TemporaryDirectory() as tmp:
            tdir, fdir = Path(tmp) / "tables", Path(tmp) / "figures"
            tdir.mkdir(parents=True)
            for n in MEASURED:
                if (TABLE_DIR / n).exists():
                    shutil.copy2(TABLE_DIR / n, tdir / n)
            tables, figs = regenerate(RAW_DIR, tdir, fdir)
            names = [p.name for p in tables]
            bad = compare(tdir, TABLE_DIR, names)
            measured = ", ".join(n for n in MEASURED if n not in names)
            print(f"[check] {len(tables)} bảng, {len(figs)} hình sinh lại; "
                  f"bảng đo trực tiếp (không sinh lại): {measured}")  # fmt: skip
            for n, why in bad:
                print(f"  ≠ {n}: {why}")
            changed = [n for n, why in bad if not why.startswith("mới")]
            print(f"[check] {len(tables) - len(bad)} giống byte, {len(changed)} khác, "
                  f"{len(bad) - len(changed)} mới")  # fmt: skip
            write_summary_md(tdir, fdir)  # kiểm sinh được (file tổng hợp, không so)
            return 1 if changed else 0
    tables, figs = regenerate(RAW_DIR, TABLE_DIR, FIG_DIR)
    for p in tables + figs:
        print(f"[plots] {p.relative_to(ROOT)}")
    print(f"[plots] {write_summary_md(TABLE_DIR, FIG_DIR).relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
