"""E2: MCTS 3×3 có bao giờ thua? (đề ý 2) — `check_tactics=False`, rollout random, c = √2.

(a) `play`: MCTS(iter) vs Minimax hoàn hảo có seed (chọn ngẫu nhiên trong các nước tốt nhất),
    vs Random,
    vs MCTS cùng iter; iter ∈ {100, 250, 1000, 5000}; mỗi cặp 2·N_PAIRS ván đổi lượt.
(b) `exhaustive`: duyệt mọi chuỗi nước của đối thủ; MCTS đi 1 nhánh tất định, seed mỗi nút
    = derive_seed(base_seed, game.key()); 10 base_seed × 2 vai.

    python -m gameai.experiments.e2_never_lose all --quick
    python -m gameai.experiments.e2_never_lose all [--workers 4]
"""

from __future__ import annotations

import argparse
import csv
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from gameai.agents.registry import AgentSpec, GameSpec, make_agent, make_game
from gameai.arena import derive_seed
from gameai.core.game import DRAW, P1, P2, Game
from gameai.experiments.common import (
    add_runner_args,
    moves_path_for,
    read_rows,
    run_match,
    summarize,
    write_summary,
)

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "results" / "raw"
TABLE_DIR = ROOT / "results" / "tables"

GAME = GameSpec("kinrow", {"n": 3, "k": 3})
ITERATIONS = (100, 250, 1000, 5000)
N_PAIRS = 50  # 100 ván/cặp (PLAN: ≥ 100)
QUICK_PAIRS = 5
BASE_SEEDS = tuple(range(10))
QUICK_BASE_SEEDS = (0, 1)
OPPONENTS = ("minimax", "random", "mcts")

EXH_COLUMNS = ["iterations", "base_seed", "mcts_player", "branches", "losses", "draws", "wins",
               "mcts_decisions", "time", "loss_example"]  # fmt: skip
EXH_SUMMARY_COLUMNS = ["iterations", "n_runs", "branches", "losses", "draws", "wins",
                       "runs_with_loss", "loss_example"]  # fmt: skip


def mcts_spec(iterations: int, label: str | None = None) -> AgentSpec:
    return AgentSpec(
        "mcts",
        {"iterations": iterations, "check_tactics": False},
        label=label or f"mcts{iterations}",
    )


def opponent_spec(name: str, iterations: int) -> AgentSpec:
    if name == "minimax":  # seeded=True mặc định: chọn ngẫu nhiên trong các nước tốt nhất
        return AgentSpec("minimax", {"depth": None}, label="minimax")
    if name == "random":
        return AgentSpec("random", label="random")
    return mcts_spec(iterations, label=f"mcts{iterations}_opp")


# ---------------------------------------------------------------- (b) vét cạn

EXT_ITERATIONS = (10000, 20000)  # D-16: chỉ chạy nếu 5000 còn nhánh thua, cho đúng các seed đó
MISTAKE_COLUMNS = ["iterations", "base_seed", "mcts_player", "ply", "prefix", "move", "move_type",
                   "opp_last_move", "opp_last_type", "losing_leaves"]  # fmt: skip
BY_ROLE_COLUMNS = ["iterations", "mcts_player", "n_seeds", "seeds_zero_loss", "branches", "losses"]
MISTAKE_SUMMARY_COLUMNS = ["iterations", "mcts_player", "ply", "move_type", "opp_last_type",
                           "mistakes", "losing_leaves"]  # fmt: skip
_CORNERS, _EDGES = {0, 2, 6, 8}, {1, 3, 5, 7}


def move_type(m: int | None) -> str:
    """Loại ô 3×3: center (4) / corner (0,2,6,8) / edge (1,3,5,7) / none (chưa có nước)."""
    if m is None:
        return "none"
    return "center" if m == 4 else "corner" if m in _CORNERS else "edge"


def solve(g: Game, cache: dict[object, int]) -> int:
    """Giá trị minimax (1 thắng / 0 hòa / −1 thua) cho người đang đi ở `g` (chơi hoàn hảo)."""
    if g.is_terminal():
        return (
            0 if g.winner() in (None, DRAW) else -1
        )  # người vừa đi thắng → người đi hiện tại thua
    key = g.key()
    if key not in cache:
        best = -1
        for m in g.legal_moves():
            g.play(m)
            best = max(best, -solve(g, cache))
            g.undo()
            if best == 1:
                break
        cache[key] = best
    return cache[key]


def exhaustive_check(
    game: Game, spec: AgentSpec, base_seed: int, mcts_player: int
) -> dict[str, object]:
    """Duyệt mọi nước của đối thủ; MCTS đi đúng 1 nước/thế (seed = derive_seed(base_seed, key)).

    Nước của MCTS chỉ phụ thuộc `game.key()` (agent dựng mới, seed theo key) nên nhớ theo key.
    Trả về số nhánh (ván kết thúc), thắng/hòa/thua của MCTS, một chuỗi nước thua đầu tiên và
    `mistakes`: {(prefix, move): số nhánh thua} với `move` là **nước sai đầu tiên** của MCTS trên
    nhánh thua (nước làm giá trị minimax của MCTS giảm xuống; prefix = các nước trước đó).
    """
    memo: dict[object, int] = {}
    cache: dict[object, int] = {}
    counts = {"branches": 0, "wins": 0, "draws": 0, "losses": 0}
    example: list[str] = []
    mistakes: dict[tuple[tuple[int, ...], int], int] = {}
    path: list[int] = []

    def mcts_move(g: Game) -> int:
        key = g.key()
        if key not in memo:
            agent = make_agent(spec, derive_seed(base_seed, repr(key)))
            memo[key] = agent.select_move(g)
        return memo[key]

    def walk(g: Game, first_mistake: tuple[tuple[int, ...], int] | None) -> None:
        if g.is_terminal():
            counts["branches"] += 1
            w = g.winner()
            if w == mcts_player:
                counts["wins"] += 1
            elif w == -mcts_player:
                counts["losses"] += 1
                if not example:
                    example.append(" ".join(map(str, path)))
                assert first_mistake is not None  # bắt đầu từ hòa (0) → thua phải có nước sai
                mistakes[first_mistake] = mistakes.get(first_mistake, 0) + 1
            else:
                counts["draws"] += 1
            return
        mine = g.current_player() == mcts_player
        moves = [mcts_move(g)] if mine else g.legal_moves()
        before = solve(g, cache) if mine and first_mistake is None else 0
        for m in moves:
            nxt = first_mistake
            g.play(m)
            if mine and first_mistake is None and -solve(g, cache) < before:
                nxt = (tuple(path), m)
            path.append(m)
            walk(g, nxt)
            path.pop()
            g.undo()

    walk(game, None)
    return {
        **counts,
        "mcts_decisions": len(memo),
        "loss_example": example[0] if example else "",
        "mistakes": mistakes,
    }


def _exh_task(args: tuple[int, int, int]) -> dict[str, object]:
    iterations, base_seed, mcts_player = args
    t0 = time.perf_counter()
    res = exhaustive_check(make_game(GAME), mcts_spec(iterations), base_seed, mcts_player)
    return {"iterations": iterations, "base_seed": base_seed, "mcts_player": mcts_player,
            **res, "time": round(time.perf_counter() - t0, 3)}  # fmt: skip


def summarize_exhaustive(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    out = []
    for it in sorted({int(r["iterations"]) for r in rows}):
        rs = [r for r in rows if int(r["iterations"]) == it]
        lost = [r for r in rs if int(r["losses"]) > 0]
        out.append({
            "iterations": it, "n_runs": len(rs),
            "branches": sum(int(r["branches"]) for r in rs),
            "losses": sum(int(r["losses"]) for r in rs),
            "draws": sum(int(r["draws"]) for r in rs),
            "wins": sum(int(r["wins"]) for r in rs),
            "runs_with_loss": len(lost),
            "loss_example": lost[0]["loss_example"] if lost else "",
        })  # fmt: skip
    return out


def summarize_by_role(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    """Theo (iter, vai): số seed có 0 nhánh thua (trên số seed đã chạy)."""
    out = []
    for it in sorted({int(r["iterations"]) for r in rows}):
        for role in (P1, P2):
            rs = [r for r in rows if int(r["iterations"]) == it and int(r["mcts_player"]) == role]
            if rs:
                out.append({
                    "iterations": it, "mcts_player": role, "n_seeds": len(rs),
                    "seeds_zero_loss": sum(1 for r in rs if int(r["losses"]) == 0),
                    "branches": sum(int(r["branches"]) for r in rs),
                    "losses": sum(int(r["losses"]) for r in rs),
                })  # fmt: skip
    return out


def mistake_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    out = []
    for r in rows:
        for (prefix, m), n in sorted(r["mistakes"].items()):  # type: ignore[attr-defined]
            opp = prefix[-1] if prefix else None
            out.append({
                "iterations": r["iterations"], "base_seed": r["base_seed"],
                "mcts_player": r["mcts_player"], "ply": len(prefix),
                "prefix": " ".join(map(str, prefix)), "move": m, "move_type": move_type(m),
                "opp_last_move": "" if opp is None else opp, "opp_last_type": move_type(opp),
                "losing_leaves": n,
            })  # fmt: skip
    return out


def summarize_mistakes(mrows: list[dict[str, object]]) -> list[dict[str, object]]:
    """Gom theo (iter, vai, ply, loại ô MCTS đi, loại ô đối thủ vừa đi): số quyết định sai và
    số nhánh thua tương ứng."""
    agg: dict[tuple, list[int]] = {}
    for r in mrows:
        k = (r["iterations"], r["mcts_player"], r["ply"], r["move_type"], r["opp_last_type"])
        a = agg.setdefault(k, [0, 0])
        a[0] += 1
        a[1] += int(r["losing_leaves"])  # type: ignore[call-overload]
    return [
        dict(zip(MISTAKE_SUMMARY_COLUMNS, (*k, v[0], v[1]), strict=True))
        for k, v in sorted(agg.items(), key=lambda kv: (kv[0][0], kv[0][1], -kv[1][1]))
    ]


def _write(path: Path, columns: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def _run_tasks(
    tasks: list[tuple[int, int, int]], stem: str, workers: int
) -> list[dict[str, object]]:
    t0 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=workers) as pool:
        rows = list(pool.map(_exh_task, tasks))
    mrows = mistake_rows(rows)
    _write(RAW_DIR / f"{stem}.csv", EXH_COLUMNS, rows)
    _write(RAW_DIR / f"{stem}_mistakes.csv", MISTAKE_COLUMNS, mrows)
    _write(TABLE_DIR / f"{stem}.csv", EXH_SUMMARY_COLUMNS, summarize_exhaustive(rows))
    _write(TABLE_DIR / f"{stem}_by_role.csv", BY_ROLE_COLUMNS, summarize_by_role(rows))
    _write(TABLE_DIR / f"{stem}_mistakes.csv", MISTAKE_SUMMARY_COLUMNS, summarize_mistakes(mrows))
    print(f"[b] {stem}: {len(tasks)} runs, {time.perf_counter() - t0:.1f} s")
    for s in summarize_exhaustive(rows):
        print(f"    iter={s['iterations']}: {s['branches']} nhánh, thua {s['losses']} "
              f"({s['runs_with_loss']}/{s['n_runs']} run có thua) {s['loss_example']}")  # fmt: skip
    for s in summarize_by_role(rows):
        print(f"    iter={s['iterations']} role={s['mcts_player']:+d}: "
              f"{s['seeds_zero_loss']}/{s['n_seeds']} seed 0 thua "
              f"({s['losses']}/{s['branches']})")  # fmt: skip
    return rows


def run_exhaustive(quick: bool, workers: int) -> list[dict[str, object]]:
    seeds = QUICK_BASE_SEEDS if quick else BASE_SEEDS
    stem = "e2quick_exhaustive" if quick else "e2_exhaustive"
    tasks = [(it, s, p) for it in ITERATIONS for s in seeds for p in (P1, P2)]
    return _run_tasks(tasks, stem, workers)


def run_extension(
    rows: list[dict[str, object]], quick: bool, workers: int
) -> list[dict[str, object]]:
    """Luật D-16: 5000 iter còn nhánh thua ở seed nào → chạy 10000 và 20000 cho đúng các seed đó
    (cả hai vai). Không có seed nào → không làm gì."""
    top = max(ITERATIONS)
    seeds = sorted({int(r["base_seed"]) for r in rows
                    if int(r["iterations"]) == top and int(r["losses"]) > 0})  # fmt: skip
    if not seeds:
        print(f"[b] {top} iter: 0 nhánh thua ở mọi seed → không chạy mở rộng")
        return []
    stem = "e2quick_exhaustive_ext" if quick else "e2_exhaustive_ext"
    print(f"[b] {top} iter còn nhánh thua ở seed {seeds} → chạy {EXT_ITERATIONS}")
    tasks = [(it, s, p) for it in EXT_ITERATIONS for s in seeds for p in (P1, P2)]
    return _run_tasks(tasks, stem, workers)


# ---------------------------------------------------------------- (a) ván đấu


def run_play(quick: bool, workers: int, allow_code_change: bool) -> list[dict]:
    n_pairs = QUICK_PAIRS if quick else N_PAIRS
    prefix = "e2quick_" if quick else "e2_"
    summary: list[dict] = []
    t0 = time.perf_counter()
    for it in ITERATIONS:
        for opp in OPPONENTS:
            t1 = time.perf_counter()
            raw = RAW_DIR / f"{prefix}{it}_vs_{opp}.csv"
            rows = run_match(raw, GAME, mcts_spec(it), opponent_spec(opp, it), n_pairs,
                             workers=workers, allow_code_change=allow_code_change)  # fmt: skip
            summary += summarize(rows, read_rows(moves_path_for(raw)))
            print(f"[a] iter={it} vs {opp}: {time.perf_counter() - t1:.1f} s")
    write_summary(summary, TABLE_DIR / f"{prefix}play.csv")
    print(f"[a] tổng {time.perf_counter() - t0:.1f} s")
    for r in summary:
        if r["split"] == "all":
            print(f"    {r['label_a']} vs {r['label_b']}: W/D/L = {r['wins']}/{r['draws']}/"
                  f"{r['losses']}, distinct_games = {r['distinct_games']}/{r['n']}")  # fmt: skip
    return summary


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]  # console cp1252
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("step", choices=("play", "exhaustive", "all"))
    add_runner_args(ap)
    args = ap.parse_args()
    if args.step in ("play", "all"):
        run_play(args.quick, args.workers, args.allow_code_change)
    if args.step in ("exhaustive", "all"):
        run_extension(run_exhaustive(args.quick, args.workers), args.quick, args.workers)


if __name__ == "__main__":
    main()
