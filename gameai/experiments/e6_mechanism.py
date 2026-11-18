"""E6 — kiểm chứng cơ chế "block h300 không đơn điệu" (P7.1, D-21 mục kiểm chứng cơ chế).

Chạy lại **đúng các cây** của phần (a) E6 (thế block, rand + h300, 10 seed/thế, cùng seed) — không
chơi ván mới — để ghi thêm W/N của nước được chọn và trạng thái cây con của nút sai.
Tại mỗi checkpoint, `move, n_correct, wn_correct, n_chosen` phải khớp `e6_choice.csv`; lệch → dừng.

    python -m gameai.experiments.e6_mechanism run [--workers 4] [--limit N]
    python -m gameai.experiments.e6_mechanism tables     # bảng + hình từ raw
"""

from __future__ import annotations

import argparse
import math
import os
import statistics
import subprocess
import sys
import time
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from datetime import datetime
from pathlib import Path
from typing import Any

from gameai.agents.mcts import MCTSAgent, Node
from gameai.agents.registry import make_agent
from gameai.arena import derive_seed
from gameai.experiments.common import git_info, read_rows
from gameai.experiments.e5_rollout import (
    CODE_PATHS,
    INK,
    INK2,
    SURFACE,
    _append_csv,
    _style,
    _write,
    cpu_name,
    fnum,
)
from gameai.experiments.e6_tactics import (
    CHECKPOINTS,
    COLORS,
    MARKERS,
    ROLLOUTS,
    _boot_ci,
    checkpoint_moves,
    choice_path,
    correct_set,
    load_positions,
    position_game,
    power_status,
    spec_off,
)
from gameai.experiments.figfmt import ratio_axis, vn_figure

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "results" / "raw"
TABLE_DIR = ROOT / "results" / "tables"
FIG_DIR = ROOT / "results" / "figures"
TAG = "kinrow-final"
TYPE = "block"
N_SEEDS = 10

RAW_COLUMNS = ["pos_id", "rollout", "seed", "iter", "move", "matches_raw", "correct",
               "n_chosen", "wn_chosen", "n_correct", "wn_correct", "n_children", "n_wrong",
               "frac_wrong_zero", "max_n_wrong", "n_wrong_top", "wn_wrong_top",
               "children_wrong_top", "refute_expanded", "n_refute", "wn_refute",
               "git_commit", "git_dirty"]  # fmt: skip
RUNINFO_COLUMNS = ["step", "n_tasks", "workers", "cpu", "logical_cpus", "power", "battery_pct",
                   "started", "finished", "wall_s", "git_commit", "git_dirty", "note"]  # fmt: skip
CHECK_KEYS = ("move", "n_correct", "wn_correct", "n_chosen")


def raw_path(raw_dir: Path = RAW_DIR) -> Path:
    return raw_dir / "e6_mechanism.csv"


def code_unchanged(tag: str = TAG, paths: tuple[str, ...] = CODE_PATHS) -> bool:
    """`git diff --quiet <tag> -- paths` trên **cây làm việc** (gồm thay đổi chưa commit)."""
    r = subprocess.run(["git", "diff", "--quiet", tag, "--", *paths], cwd=ROOT,
                       capture_output=True)  # fmt: skip
    return r.returncode == 0


# ---------------------------------------------------------------- một gốc


def _wn(node: Node) -> float:
    return node.W / node.N


def root_row(root: Node, chosen: Node, correct: set[int]) -> dict[str, Any]:
    """Thống kê gốc tại một checkpoint. `correct` = ô chặn = ô thắng của đối thủ (thế block)."""
    good = [ch for ch in root.children if ch.move in correct]
    wrong = [ch for ch in root.children if ch.move not in correct]
    top = max(good, key=lambda ch: (ch.N, ch.W)) if good else None
    wtop = max(wrong, key=lambda ch: (ch.N, ch.W)) if wrong else None
    refute = [g for g in wtop.children if g.move in correct] if wtop else []
    rf = max(refute, key=lambda g: g.N) if refute else None
    return {
        "move": chosen.move,
        "correct": int(chosen.move in correct),
        "n_chosen": chosen.N,
        "wn_chosen": round(_wn(chosen), 4),
        "n_correct": top.N if top else 0,
        "wn_correct": round(_wn(top), 4) if top else "",
        "n_children": len(root.children),
        "n_wrong": len(wrong),
        "frac_wrong_zero": round(sum(ch.W == 0 for ch in wrong) / len(wrong), 4) if wrong else "",
        "max_n_wrong": wtop.N if wtop else 0,
        "n_wrong_top": wtop.N if wtop else "",
        "wn_wrong_top": round(_wn(wtop), 4) if wtop else "",
        "children_wrong_top": len(wtop.children) if wtop else "",
        "refute_expanded": int(rf is not None) if wtop else "",
        "n_refute": rf.N if rf else 0,
        "wn_refute": round(_wn(rf), 4) if rf else "",
    }


def matches(row: dict[str, Any], ref: dict[str, str]) -> bool:
    """So với dòng `e6_choice.csv` cùng (thế, rollout, seed, iter)."""
    for k in CHECK_KEYS:
        a, b = row[k], ref[k]
        if k == "wn_correct":
            if (a == "") != (b == ""):
                return False
            if a != "" and abs(float(a) - float(b)) > 1e-9:
                return False
        elif int(a) != int(b):
            return False
    return True


def mechanism_task(
    pos: dict[str, str],
    rollout: str,
    seed: int,
    refs: dict[int, dict[str, str]],
    checkpoints: tuple[int, ...] = CHECKPOINTS,
) -> list[dict[str, Any]]:
    """Dựng lại cây như `e6_tactics.choice_task` (cùng spec, seed, checkpoint) và ghi thống kê.
    `refs[iter]` = dòng raw cũ; thiếu → `matches_raw` = 0."""
    game = position_game(pos)
    correct = correct_set(pos)
    agent = make_agent(spec_off(rollout, checkpoints[-1]), derive_seed(seed, pos["pos_id"]))
    assert isinstance(agent, MCTSAgent)
    rows = []
    for k, root, _ in checkpoint_moves(game, agent, checkpoints):
        row = root_row(root, agent._final_child(root), correct)
        ref = refs.get(k)
        rows.append({"pos_id": pos["pos_id"], "rollout": rollout, "seed": seed, "iter": k,
                     "matches_raw": int(ref is not None and matches(row, ref)), **row})  # fmt: skip
    return rows


# ---------------------------------------------------------------- chạy


def _ref_index(raw_dir: Path) -> dict[tuple[str, str, int], dict[int, dict[str, str]]]:
    idx: dict[tuple[str, str, int], dict[int, dict[str, str]]] = {}
    for r in read_rows(choice_path(False, raw_dir)):
        if r["type"] == TYPE:
            idx.setdefault((r["pos_id"], r["rollout"], int(r["seed"])), {})[int(r["iter"])] = r
    return idx


def _log(step: str, n_tasks: int, workers: int, started: str, t0: float, raw_dir: Path,
         note: str = "") -> None:  # fmt: skip
    commit, dirty = git_info()
    power, pct = power_status()
    _append_csv(raw_dir / "e6_mechanism_runinfo.csv", RUNINFO_COLUMNS, {
        "step": step, "n_tasks": n_tasks, "workers": workers, "cpu": cpu_name(),
        "logical_cpus": os.cpu_count(), "power": power, "battery_pct": pct, "started": started,
        "finished": datetime.now().isoformat(timespec="seconds"),
        "wall_s": round(time.perf_counter() - t0, 1), "git_commit": commit,
        "git_dirty": int(dirty), "note": note})  # fmt: skip


def run(workers: int, limit: int | None = None, raw_dir: Path = RAW_DIR) -> int:
    """Chạy các task còn thiếu. Trả số dòng lệch raw (0 = ok). Lệch → dừng ngay, không ghi
    task lệch."""
    if not code_unchanged():
        sys.exit(f"git diff {TAG} -- {' '.join(CODE_PATHS)} không rỗng → cây có thể khác, dừng.")
    path = raw_path(raw_dir)
    done: dict[tuple[str, str, str], int] = {}
    if path.exists():
        for r in read_rows(path):
            if r["matches_raw"] != "1":
                sys.exit(f"{path.name} đã có dòng lệch raw → không dùng được, báo An.")
            key = (r["pos_id"], r["rollout"], r["seed"])
            done[key] = done.get(key, 0) + 1
    refs = _ref_index(raw_dir)
    tasks = [
        (p, roll, s, refs.get((p["pos_id"], roll, s), {}))
        for p in load_positions(False, raw_dir)
        if p["type"] == TYPE
        for roll in ROLLOUTS
        for s in range(N_SEEDS)
        if done.get((p["pos_id"], roll, str(s)), 0) < len(CHECKPOINTS)
    ]
    if limit is not None:
        tasks = tasks[:limit]
    commit, dirty = git_info()
    meta = {"git_commit": commit, "git_dirty": int(dirty)}
    started, t0 = datetime.now().isoformat(timespec="seconds"), time.perf_counter()
    print(f"[mechanism] {len(tasks)} task ({len(done)} đã có), {workers} worker")
    bad: list[dict[str, Any]] = []

    def handle(rows: list[dict[str, Any]]) -> None:
        miss = [r for r in rows if not r["matches_raw"]]
        if miss:
            bad.extend(miss)
            return
        for row in rows:
            _append_csv(path, RAW_COLUMNS, {**row, **meta})

    if workers <= 1:
        for t in tasks:
            handle(mechanism_task(*t))
            if bad:
                break
    else:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            pending = {ex.submit(mechanism_task, *t) for t in tasks}
            n_done = 0
            while pending and not bad:
                fin, pending = wait(pending, return_when=FIRST_COMPLETED)
                for f in fin:
                    handle(f.result())
                    n_done += 1
                if n_done % 50 == 0 or not pending:
                    print(f"  {n_done}/{len(tasks)} ({time.perf_counter() - t0:.0f} s)")
            for f in pending:
                f.cancel()
    note = f"LỆCH {len(bad)} dòng" if bad else "khớp 100 %"
    _log("run", len(tasks), workers, started, t0, raw_dir, note)
    if bad:
        for r in bad[:10]:
            print("  LỆCH:", {k: r[k] for k in ("pos_id", "rollout", "seed", "iter", *CHECK_KEYS)})
        print(f"[mechanism] DỪNG: {len(bad)} dòng lệch e6_choice.csv — cây không tất định, "
              "không dùng dữ liệu.")  # fmt: skip
    else:
        print(f"[mechanism] xong {time.perf_counter() - t0:.1f} s, khớp raw 100 %")
    return len(bad)


# ---------------------------------------------------------------- bảng

GROUPS = (("all", None), ("correct=1", "1"), ("correct=0", "0"))
TABLE_COLUMNS = ["rollout", "iter", "group", "n_pos", "n_runs", "correct_rate",
                 "frac_wrong_zero", "fwz_lo", "fwz_hi",
                 "wn_chosen", "wn_chosen_lo", "wn_chosen_hi", "wn_chosen_gt0",
                 "wn_correct", "wn_correct_lo", "wn_correct_hi", "chosen_ge_correct",
                 "median_n_correct", "median_n_chosen", "ncorr_gt_maxwrong",
                 "wn_wrong_top", "wn_wrong_top_lo", "wn_wrong_top_hi", "median_n_wrong_top",
                 "refute_rate", "refute_lo", "refute_hi", "median_n_refute", "wn_refute_mean",
                 "wn_wrong_top_refuted", "wn_wrong_top_unrefuted"]  # fmt: skip


def _mean_ci(rows: list[dict[str, str]], key: str) -> tuple[float, float, float]:
    """Trung bình `key` (bỏ ô trống) + bootstrap theo cụm thế (`_boot_ci` với (tổng, số))."""
    by: dict[str, list[float]] = {}
    for r in rows:
        if r[key] != "":
            v = by.setdefault(r["pos_id"], [0.0, 0])
            v[0] += float(r[key])
            v[1] += 1
    if not by:
        return math.nan, math.nan, math.nan
    s = sum(v[0] for v in by.values())
    n = sum(v[1] for v in by.values())
    lo, hi = _boot_ci({p: (v[0], v[1]) for p, v in by.items()})
    return s / n, lo, hi


def _frac(rows: list[dict[str, str]], pred: Any) -> float:
    return sum(1 for r in rows if pred(r)) / len(rows) if rows else math.nan


def _median(xs: list[float]) -> float:
    return statistics.median(xs) if xs else math.nan


def build_table(raw_dir: Path = RAW_DIR, table_dir: Path = TABLE_DIR) -> list[dict[str, Any]]:
    path = raw_path(raw_dir)
    if not path.exists():
        return []
    raw = read_rows(path)
    out = []
    for roll in ROLLOUTS:
        for it in CHECKPOINTS:
            base = [r for r in raw if r["rollout"] == roll and int(r["iter"]) == it]
            for name, val in GROUPS:
                rs = [r for r in base if val is None or r["correct"] == val]
                if not rs:
                    continue
                fwz = _mean_ci(rs, "frac_wrong_zero")
                wch = _mean_ci(rs, "wn_chosen")
                wco = _mean_ci(rs, "wn_correct")
                wwt = _mean_ci(rs, "wn_wrong_top")
                ref = _mean_ci(rs, "refute_expanded")
                refuted = [float(r["wn_wrong_top"]) for r in rs if r["refute_expanded"] == "1"]
                unref = [float(r["wn_wrong_top"]) for r in rs if r["refute_expanded"] == "0"]
                wnr = [float(r["wn_refute"]) for r in rs if r["wn_refute"] != ""]
                out.append({
                    "rollout": roll, "iter": it, "group": name,
                    "n_pos": len({r["pos_id"] for r in rs}), "n_runs": len(rs),
                    "correct_rate": _frac(rs, lambda r: r["correct"] == "1"),
                    "frac_wrong_zero": fwz[0], "fwz_lo": fwz[1], "fwz_hi": fwz[2],
                    "wn_chosen": wch[0], "wn_chosen_lo": wch[1], "wn_chosen_hi": wch[2],
                    "wn_chosen_gt0": _frac(rs, lambda r: float(r["wn_chosen"]) > 0),
                    "wn_correct": wco[0], "wn_correct_lo": wco[1], "wn_correct_hi": wco[2],
                    "chosen_ge_correct": _frac(
                        [r for r in rs if r["wn_correct"] != ""],
                        lambda r: float(r["wn_chosen"]) >= float(r["wn_correct"])),
                    "median_n_correct": _median([int(r["n_correct"]) for r in rs]),
                    "median_n_chosen": _median([int(r["n_chosen"]) for r in rs]),
                    "ncorr_gt_maxwrong": _frac(
                        rs, lambda r: int(r["n_correct"]) > int(r["max_n_wrong"])),
                    "wn_wrong_top": wwt[0], "wn_wrong_top_lo": wwt[1], "wn_wrong_top_hi": wwt[2],
                    "median_n_wrong_top": _median(
                        [int(r["n_wrong_top"]) for r in rs if r["n_wrong_top"] != ""]),
                    "refute_rate": ref[0], "refute_lo": ref[1], "refute_hi": ref[2],
                    "median_n_refute": _median(
                        [int(r["n_refute"]) for r in rs if r["refute_expanded"] == "1"]),
                    "wn_refute_mean": statistics.fmean(wnr) if wnr else math.nan,
                    "wn_wrong_top_refuted": statistics.fmean(refuted) if refuted else math.nan,
                    "wn_wrong_top_unrefuted": statistics.fmean(unref) if unref else math.nan,
                })  # fmt: skip
    _write(table_dir / "e6_mechanism.csv", TABLE_COLUMNS, out)
    return out


# ---------------------------------------------------------------- hình


def make_figure(table_dir: Path = TABLE_DIR, fig_dir: Path = FIG_DIR) -> Path | None:
    tpath = table_dir / "e6_mechanism.csv"
    if not tpath.exists():
        return None
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    rows = read_rows(tpath)

    def series(roll: str, group: str, key: str) -> list[tuple[float, float, float, float]]:
        pts = []
        for r in rows:
            if r["rollout"] != roll or r["group"] != group:
                continue
            lo_k, hi_k = {"frac_wrong_zero": ("fwz_lo", "fwz_hi"),
                          "refute_rate": ("refute_lo", "refute_hi")}.get(
                key, (f"{key}_lo", f"{key}_hi"))  # fmt: skip
            y = fnum(r[key])
            if y == y:
                pts.append((int(r["iter"]), y, fnum(r[lo_k]), fnum(r[hi_k])))
        return sorted(pts)

    def line(ax: Any, roll: str, pts: list, i: int, dashed: bool = False) -> None:
        if not pts:
            return
        shift = 10 ** (0.02 * (i - 0.5))
        xs = [p[0] * shift for p in pts]
        err = [[max(0.0, p[1] - p[2]) for p in pts], [max(0.0, p[3] - p[1]) for p in pts]]
        ax.errorbar(xs, [p[1] for p in pts], yerr=err, color=COLORS[roll], marker=MARKERS[roll],
                    markersize=6, linewidth=2 if not dashed else 1.5,
                    linestyle="--" if dashed else "-", elinewidth=1.1, capsize=0,
                    markeredgecolor=SURFACE if not dashed else COLORS[roll],
                    markerfacecolor=COLORS[roll] if not dashed else SURFACE,
                    markeredgewidth=1)  # fmt: skip

    fig, axes = plt.subplots(1, 3, figsize=(13, 4.6), facecolor=SURFACE, sharey=True)
    panels = (
        ("(1) Mọi lần chạy: tỷ lệ con sai có W = 0", [("all", "frac_wrong_zero", False)]),
        ("(2) Lần chọn SAI: W/N nước được chọn (liền)\nvà W/N ô chặn (đứt)",
         [("correct=0", "wn_chosen", False), ("correct=0", "wn_correct", True)]),
        ("(3) Lần chọn SAI: ô thắng của đối thủ đã mở\ndưới nước sai được chọn",
         [("correct=0", "refute_rate", False)]),
    )  # fmt: skip
    for ax, (title, specs) in zip(axes, panels, strict=True):
        for i, roll in enumerate(ROLLOUTS):
            for group, key, dashed in specs:
                line(ax, roll, series(roll, group, key), i, dashed)
        ax.set_xscale("log")
        ax.set_xticks(CHECKPOINTS)
        ax.set_xticklabels([str(c) for c in CHECKPOINTS])
        ax.minorticks_off()
        ax.set_ylim(0.0, 1.03)
        ratio_axis(ax)
        ax.set_xlabel("iteration / nước", color=INK2)
        ax.set_title(title, color=INK, fontsize=9.5, loc="left")
        _style(ax)
    handles = [Line2D([], [], color=COLORS[r], marker=MARKERS[r], linewidth=2,
                      markeredgecolor=SURFACE) for r in ROLLOUTS]  # fmt: skip
    fig.legend(handles, ["rollout random", "rollout h300"], loc="upper right", ncol=2,
               frameon=False, fontsize=9, labelcolor=INK, bbox_to_anchor=(0.99, 0.99))  # fmt: skip
    fig.suptitle("E6 — cơ chế: thế phải chặn four, MCTS tắt check_tactics", color=INK,
                 fontsize=12, x=0.01, ha="left")  # fmt: skip
    fig.text(0.01, 0.005, "Chạy lại đúng cây của e6_choice (khớp 100 %). Thanh lỗi: bootstrap 95 % "
             "theo cụm thế. Số đầy đủ (gồm nhóm chọn đúng): e6_mechanism.csv.",
             color=INK2, fontsize=8, ha="left", va="bottom")  # fmt: skip
    vn_figure(fig)  # tick/nhãn số kiểu VN (P7.2)
    fig.tight_layout(rect=(0, 0.04, 1, 0.93))
    path = fig_dir / "e6_mechanism.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150, facecolor=SURFACE)
    plt.close(fig)
    return path


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("step", choices=("run", "tables"))
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--limit", type=int, default=None, help="chỉ chạy N task đầu (thử)")
    args = ap.parse_args()
    if args.step == "run" and run(args.workers, args.limit):
        sys.exit(1)
    build_table()
    print(f"[plot] {make_figure()}")


if __name__ == "__main__":
    main()
