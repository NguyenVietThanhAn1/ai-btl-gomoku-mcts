"""E3: ảnh hưởng của hằng số khám phá c (đề ý 3) — D-18.

c ∈ {0.5, 1.0, 1.4, 2.0} × iter ∈ {100, 250, 500, 1000, 2500, 5000}, ngân sách iteration.
- 3×3 (rollout random, tactics tắt): vs Random (200 ván/điểm) và vs Minimax có seed, cache theo key
  (100 ván/điểm).
- 15×15 (h300, tactics bật): vs Greedy (50 ván/điểm).
- 15×15 vs AB depth 2: pilot (c tốt nhất vs Greedy ở 5000 iter, 20 ván) → cổng ≥ 2/20 thắng →
  iter {2500, 5000} × 4 c × 50 ván.

    python -m gameai.experiments.e3_c_sweep all --quick
    python -m gameai.experiments.e3_c_sweep 3x3 | greedy | ab2-pilot | ab2 [--force] | plot
"""

from __future__ import annotations

import argparse
import csv
import math
import random
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from gameai.agents.base import Agent
from gameai.agents.minimax import MinimaxAgent
from gameai.agents.registry import AgentSpec, GameSpec
from gameai.core.game import Game, Move
from gameai.experiments.common import (
    SUMMARY_COLUMNS,
    add_runner_args,
    moves_path_for,
    read_rows,
    run_match,
    summarize,
)

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "results" / "raw"
TABLE_DIR = ROOT / "results" / "tables"
FIG_DIR = ROOT / "results" / "figures"

C_VALUES = (0.5, 1.0, 1.4, 2.0)
ITERATIONS = (100, 250, 500, 1000, 2500, 5000)
AB2_ITERATIONS = (2500, 5000)
PILOT_ITER = 5000
PILOT_PAIRS = 10  # 20 ván
GATE_MIN_WINS = 2  # D-18: ≥ 2/20 thắng → chạy AB2
DEFAULT_C = 1.4
SPEEDUP_4_WORKERS = 3.5  # ước tính thô cho 4 worker (P3.3: không bị tải thêm ở 4 worker)

GAME3 = GameSpec("kinrow", {"n": 3, "k": 3})
GAME15 = GameSpec("kinrow", {"n": 15, "k": 5})
TABLE_COLUMNS = ["part", "c", "iterations", *SUMMARY_COLUMNS]
ESTIMATE_COLUMNS = ["part", "points", "games", "sec_per_game_fit_a", "sec_per_iter_fit_b",
                    "seq_minutes", "est_4w_minutes"]  # fmt: skip


# ---------------------------------------------------------------- đối thủ Minimax có cache

_MINIMAX_CACHE: dict[Any, list[Move]] = {}  # key → các nước tối ưu (mỗi tiến trình một bản)


class CachedMinimaxAgent(Agent):
    """Minimax hoàn hảo (`depth=None`) có seed: chọn ngẫu nhiên trong các nước bằng giá trị tốt
    nhất (như `MinimaxAgent(seed=s)`), danh sách nước tối ưu nhớ theo `game.key()` trong tiến trình.

    Dùng qua registry: `AgentSpec("gameai.experiments.e3_c_sweep:CachedMinimaxAgent")`.
    `stats`: `nodes` (0 khi trúng cache), `iterations` = 0, `time`, `cache_hit` (1/0).
    """

    def __init__(self, seed: int | None = None) -> None:
        super().__init__()
        self._rng = random.Random(seed)

    def _select_move(self, game: Game) -> Move:
        t0 = time.perf_counter()
        key = game.key()
        hit = key in _MINIMAX_CACHE
        nodes = 0
        if not hit:
            mm = MinimaxAgent(depth=None)
            values = mm.root_values(game)
            best = max(v for _, v in values)
            _MINIMAX_CACHE[key] = [m for m, v in values if v == best]
            nodes = int(mm.stats["nodes"])
        move = self._rng.choice(_MINIMAX_CACHE[key])
        self.stats = {"nodes": nodes, "iterations": 0, "time": time.perf_counter() - t0,
                      "cache_hit": int(hit)}  # fmt: skip
        return move


# ---------------------------------------------------------------- cấu hình


@dataclass(frozen=True)
class Part:
    name: str
    game: GameSpec
    opponent: AgentSpec
    n_pairs: int
    quick_pairs: int
    iterations: tuple[int, ...]
    quick_c: tuple[float, ...]
    quick_iterations: tuple[int, ...]


GREEDY = AgentSpec("greedy", label="greedy")
AB2 = AgentSpec("alphabeta", {"depth": 2, "eval": "evaluate", "delta": "delta_eval",
                              "order": "move_score"}, label="ab2")  # fmt: skip
PARTS: dict[str, Part] = {
    "3x3_random": Part("3x3_random", GAME3, AgentSpec("random", label="random"), 100, 2,
                       ITERATIONS, C_VALUES, ITERATIONS),
    "3x3_minimax": Part("3x3_minimax", GAME3,
                        AgentSpec("gameai.experiments.e3_c_sweep:CachedMinimaxAgent",
                                  label="minimax"),
                        50, 2, ITERATIONS, C_VALUES, ITERATIONS),
    "greedy": Part("greedy", GAME15, GREEDY, 25, 1, ITERATIONS, (0.5, 2.0), (100, 1000, 5000)),
    "ab2": Part("ab2", GAME15, AB2, 25, 1, AB2_ITERATIONS, (), ()),
}  # fmt: skip


def mcts_spec(board: int, c: float, iterations: int) -> AgentSpec:
    """3×3: rollout random, tactics tắt (D-16). 15×15: h300, tactics bật (D-14)."""
    params: dict[str, Any] = {"iterations": iterations, "c": c}
    if board == 3:
        params["check_tactics"] = False
    else:
        params.update({"rollout": "heavy_kinrow", "temperature": 300, "check_tactics": True})
    return AgentSpec("mcts", params, label=label_for(c, iterations))


def label_for(c: float, iterations: int) -> str:
    return f"c{c}_i{iterations}"


def points(part: Part, quick: bool) -> list[tuple[float, int]]:
    cs, its = (part.quick_c, part.quick_iterations) if quick else (C_VALUES, part.iterations)
    return [(c, it) for it in its for c in cs]  # iter thấp trước: dữ liệu dùng được sớm


def prefix(quick: bool) -> str:
    return "e3quick_" if quick else "e3_"


def raw_path(part: str, c: float, iterations: int, quick: bool, raw_dir: Path = RAW_DIR) -> Path:
    return raw_dir / f"{prefix(quick)}{part}_c{c}_i{iterations}.csv"


# ---------------------------------------------------------------- luật D-18


def choose_pilot_c(greedy_table: list[dict[str, Any]], iterations: int = PILOT_ITER) -> float:
    """c có win rate vs Greedy cao nhất ở `iterations` (dòng split "all"); hòa → 1.4 nếu trong
    nhóm hòa, không thì c gần 1.4 nhất (D-18)."""
    rows = [r for r in greedy_table
            if r["split"] == "all" and int(r["iterations"]) == iterations]  # fmt: skip
    if not rows:
        raise ValueError(f"bảng Greedy không có điểm iter={iterations}")
    best = max(float(r["win_rate"]) for r in rows)
    tied = sorted(float(r["c"]) for r in rows if math.isclose(float(r["win_rate"]), best))
    if DEFAULT_C in tied:
        return DEFAULT_C
    return min(tied, key=lambda c: (abs(c - DEFAULT_C), c))


def gate_passes(wins: int) -> bool:
    """D-18: pilot 20 ván, thắng ≥ 2 → chạy AB2; ≤ 1 → bỏ."""
    return wins >= GATE_MIN_WINS


# ---------------------------------------------------------------- chạy


def _fmt(v: Any) -> Any:
    return "" if v is None or (isinstance(v, float) and math.isnan(v)) else v


def write_table(rows: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, TABLE_COLUMNS, extrasaction="ignore")
        w.writeheader()
        w.writerows({k: _fmt(r.get(k)) for k in TABLE_COLUMNS} for r in rows)


def run_part(
    part_name: str,
    quick: bool,
    workers: int,
    allow_code_change: bool,
    pts: list[tuple[float, int]] | None = None,
    n_pairs: int | None = None,
    table_name: str | None = None,
    raw_dir: Path = RAW_DIR,
    table_dir: Path = TABLE_DIR,
) -> list[dict[str, Any]]:
    """Chạy các điểm (c, iter) của một phần; ghi raw mỗi điểm + bảng dạng dài; trả bảng."""
    part = PARTS[part_name]
    pts = points(part, quick) if pts is None else pts
    pairs = n_pairs if n_pairs is not None else (part.quick_pairs if quick else part.n_pairs)
    board = int(part.game.params["n"])
    table: list[dict[str, Any]] = []
    t0 = time.perf_counter()
    for c, it in pts:
        t1 = time.perf_counter()
        raw = raw_path(part.name, c, it, quick, raw_dir)
        rows = run_match(raw, part.game, mcts_spec(board, c, it), part.opponent, pairs,
                         workers=workers, allow_code_change=allow_code_change)  # fmt: skip
        summ = summarize(rows, read_rows(moves_path_for(raw)))
        table += [{"part": part.name, "c": c, "iterations": it, **s} for s in summ]
        a = next(s for s in summ if s["split"] == "all")
        wdl = f"{a['wins']}/{a['draws']}/{a['losses']}"
        print(f"[{part.name}] c={c} iter={it}: W/D/L {wdl} (n={a['n']}, "
              f"distinct={a['distinct_games']}), {time.perf_counter() - t1:.1f} s")  # fmt: skip
    write_table(table, table_dir / f"{prefix(quick)}{table_name or part.name}.csv")
    print(f"[{part.name}] tổng {time.perf_counter() - t0:.1f} s")
    return table


def run_3x3(quick: bool, workers: int, allow: bool) -> None:
    run_part("3x3_random", quick, workers, allow)
    run_part("3x3_minimax", quick, workers, allow)


def run_pilot(quick: bool, workers: int, allow: bool) -> list[dict[str, Any]]:
    greedy = read_rows(TABLE_DIR / f"{prefix(quick)}greedy.csv")
    c = choose_pilot_c(greedy)
    print(f"[ab2-pilot] c = {c} (win rate vs Greedy cao nhất ở {PILOT_ITER} iter, D-18)")
    pairs = PARTS["ab2"].quick_pairs if quick else PILOT_PAIRS
    table = run_part("ab2", quick, workers, allow, pts=[(c, PILOT_ITER)], n_pairs=pairs,
                     table_name="ab2_pilot")  # fmt: skip
    a = next(r for r in table if r["split"] == "all")
    verdict = "QUA cổng → chạy AB2" if gate_passes(int(a["wins"])) else "KHÔNG qua → bỏ AB2"
    if quick:
        verdict = "(quick: không áp luật cổng)"
    print(f"[ab2-pilot] thắng {a['wins']}/{a['n']} — {verdict}")
    return table


def run_ab2(quick: bool, workers: int, allow: bool, force: bool) -> None:
    pilot = read_rows(TABLE_DIR / f"{prefix(quick)}ab2_pilot.csv")
    a = next(r for r in pilot if r["split"] == "all")
    if not quick and int(a["n"]) != 2 * PILOT_PAIRS:
        sys.exit(f"pilot có {a['n']} ván, cần {2 * PILOT_PAIRS}")
    if not quick and not gate_passes(int(a["wins"])) and not force:
        sys.exit(
            f"pilot thắng {a['wins']}/{a['n']} < {GATE_MIN_WINS} → bỏ AB2 (D-18); --force để ép"
        )
    run_part("ab2", quick, workers, allow, pts=[(c, it) for it in AB2_ITERATIONS for c in C_VALUES])


# ---------------------------------------------------------------- ước tính chi phí từ quick


def fit_cost(raw_rows: list[tuple[int, float]]) -> tuple[float, float]:
    """Bình phương tối thiểu sec/ván = a + b·iter trên (iter, giây CPU/ván) của quick."""
    n = len(raw_rows)
    if n == 0:
        return math.nan, math.nan
    xs = [x for x, _ in raw_rows]
    ys = [y for _, y in raw_rows]
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0:
        return my, 0.0
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True)) / sxx
    return my - b * mx, b


def _game_seconds(r: dict[str, str]) -> float:
    return sum(float(r[k]) for k in ("a_time_sum", "b_time_sum") if r.get(k))


def estimate_full(raw_dir: Path = RAW_DIR, table_dir: Path = TABLE_DIR) -> list[dict[str, Any]]:
    """Đọc raw quick, fit sec/ván theo iter cho từng phần, ngoại suy thời gian full."""
    plans = {
        "3x3_random": (PARTS["3x3_random"], points(PARTS["3x3_random"], False), 100),
        "3x3_minimax": (PARTS["3x3_minimax"], points(PARTS["3x3_minimax"], False), 50),
        "greedy": (PARTS["greedy"], points(PARTS["greedy"], False), 25),
        "ab2_pilot": (PARTS["ab2"], [(DEFAULT_C, PILOT_ITER)], PILOT_PAIRS),
        "ab2_full": (PARTS["ab2"], [(c, it) for it in AB2_ITERATIONS for c in C_VALUES], 25),
    }
    out = []
    for name, (part, pts, pairs) in plans.items():
        data = []
        for f in raw_dir.glob(f"e3quick_{part.name}_c*_i*.csv"):
            if f.stem.endswith("_moves"):
                continue
            it = int(f.stem.rsplit("_i", 1)[1])
            data += [(it, _game_seconds(r)) for r in read_rows(f)]
        a, b = fit_cost(data)
        if name == "ab2_full":  # pilot đã chơi 20 ván của một điểm
            games_extra = -2 * PILOT_PAIRS
        else:
            games_extra = 0
        games = 2 * pairs * len(pts) + games_extra
        seq = sum(2 * pairs * (a + b * it) for _, it in pts) + games_extra * (a + b * PILOT_ITER)
        out.append({"part": name, "points": len(pts), "games": games,
                    "sec_per_game_fit_a": round(a, 4), "sec_per_iter_fit_b": round(b, 7),
                    "seq_minutes": round(seq / 60, 1),
                    "est_4w_minutes": round(seq / 60 / SPEEDUP_4_WORKERS, 1)})  # fmt: skip
    path = table_dir / "e3quick_estimate.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, ESTIMATE_COLUMNS)
        w.writeheader()
        w.writerows(out)
    for r in out:
        print(f"[estimate] {r['part']}: {r['games']} ván, ~{r['seq_minutes']} phút tuần tự, "
              f"~{r['est_4w_minutes']} phút 4 worker")  # fmt: skip
    return out


# ---------------------------------------------------------------- hình

# Bảng màu phân loại đã kiểm (dataviz validator, light): 4 slot đầu, thứ tự cố định theo c.
SERIES_COLORS = ("#2a78d6", "#eb6834", "#1baf7a", "#eda100")
MARKERS = ("o", "s", "^", "D")  # mã hóa phụ: không phụ thuộc màu
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
METRICS = {"win": ("win_rate", "win_lo", "win_hi"),
           "nonloss": ("nonloss_rate", "nonloss_lo", "nonloss_hi")}  # fmt: skip


def plot_panels(
    panels: list[tuple[list[dict[str, Any]], str, str]], path: Path, title: str
) -> Path:
    """Mỗi panel = (bảng E3, "win"|"nonloss", tiêu đề). Trục x log iteration, 1 đường/c,
    thanh lỗi Wilson 95 % (tính độc lập từng điểm), lệch x nhẹ giữa các c để không đè nhau."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, len(panels), figsize=(5.2 * len(panels), 4.2), squeeze=False,
                             facecolor=SURFACE)  # fmt: skip
    for ax, (rows, metric, sub) in zip(axes[0], panels, strict=True):
        key, lo_k, hi_k = METRICS[metric]
        rows = [r for r in rows if r["split"] == "all"]
        cs = sorted({float(r["c"]) for r in rows})
        lows = []
        for c in cs:
            i = C_VALUES.index(c)  # màu/marker theo c, không theo thứ hạng
            pts = sorted((int(r["iterations"]), float(r[key]), float(r[lo_k]), float(r[hi_k]))
                         for r in rows if float(r["c"]) == c)  # fmt: skip
            shift = 10 ** (0.025 * (i - 1.5))
            xs = [p[0] * shift for p in pts]
            ys = [p[1] for p in pts]
            err = [[p[1] - p[2] for p in pts], [p[3] - p[1] for p in pts]]
            lows += [p[2] for p in pts]
            ax.errorbar(xs, ys, yerr=err, color=SERIES_COLORS[i], marker=MARKERS[i],
                        markersize=6, linewidth=2, elinewidth=1.2, capsize=0,
                        markeredgecolor=SURFACE, markeredgewidth=1, label=f"c = {c}")  # fmt: skip
        its = sorted({int(r["iterations"]) for r in rows})
        ax.set_xscale("log")
        ax.set_xticks(its, [str(x) for x in its])
        ax.minorticks_off()
        floor = min(lows, default=0.0)
        ax.set_ylim(max(0.0, math.floor((floor - 0.02) * 10) / 10) if floor > 0.5 else 0.0, 1.03)
        ax.set_facecolor(SURFACE)
        ax.grid(True, axis="y", color=GRID, linewidth=0.8)
        ax.set_axisbelow(True)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        for s in ("left", "bottom"):
            ax.spines[s].set_color(INK2)
        ax.tick_params(colors=INK2)
        ax.set_xlabel("iteration / nước", color=INK2)
        ax.set_ylabel({"win": "tỉ lệ thắng", "nonloss": "tỉ lệ không thua"}[metric], color=INK2)
        ax.set_title(sub, color=INK, fontsize=11, loc="left")
    handles, labels = axes[0][0].get_legend_handles_labels()  # một legend chung, không đè dữ liệu
    fig.legend(handles, labels, loc="upper right", ncol=len(labels), frameon=False,
               labelcolor=INK, fontsize=9)  # fmt: skip
    fig.suptitle(title, color=INK, fontsize=12, x=0.01, ha="left")
    fig.text(0.01, 0.005, "Thanh lỗi: Wilson 95 %, tính độc lập từng điểm (các c dùng chung seed).",
             color=INK2, fontsize=8, ha="left", va="bottom")  # fmt: skip
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150, facecolor=SURFACE)
    plt.close(fig)
    return path


def make_figures(quick: bool, table_dir: Path = TABLE_DIR, fig_dir: Path = FIG_DIR) -> list[Path]:
    p = prefix(quick)
    out = []

    def table(name: str) -> list[dict[str, str]] | None:
        f = table_dir / f"{p}{name}.csv"
        return read_rows(f) if f.exists() else None

    r3, m3 = table("3x3_random"), table("3x3_minimax")
    if r3 and m3:
        out.append(plot_panels([(r3, "win", "Thắng vs Random"),
                                (r3, "nonloss", "Không thua vs Random"),
                                (m3, "nonloss", "Không thua vs Minimax")],
                               fig_dir / f"{p}3x3.png", "E3 — 3×3, rollout random"))  # fmt: skip
    for name, sub in (("greedy", "vs Greedy"), ("ab2", "vs Alpha-Beta depth 2")):
        t = table(name)
        if t:
            out.append(plot_panels([(t, "win", f"Thắng {sub}")], fig_dir / f"{p}{name}.png",
                                   "E3 — 15×15, MCTS h300 + tactics"))  # fmt: skip
    for f in out:
        print(f"[plot] {f}")
    return out


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]  # console cp1252
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("step", choices=("3x3", "greedy", "ab2-pilot", "ab2", "plot", "all"))
    ap.add_argument("--force", action="store_true", help="ab2: chạy dù pilot không qua cổng")
    add_runner_args(ap)
    args = ap.parse_args()
    q, w, allow = args.quick, args.workers, args.allow_code_change
    t0 = time.perf_counter()
    if args.step in ("3x3", "all"):
        run_3x3(q, w, allow)
    if args.step in ("greedy", "all"):
        run_part("greedy", q, w, allow)
    if args.step in ("ab2-pilot", "all"):
        run_pilot(q, w, allow)
    if args.step == "ab2":
        run_ab2(q, w, allow, args.force)
    make_figures(q)  # mọi bước: vẽ lại từ các bảng đang có
    if q and args.step == "all":
        estimate_full()
    print(f"tổng {time.perf_counter() - t0:.1f} s")


if __name__ == "__main__":
    main()
