"""P6.4 B5: sức mạnh AB Khó mới (15×15, chế độ chơi GUI) — số minh họa, **không vào report**.

AB Khó mới (`presets.AB15_HARD` với `top_k` thử) đấu AB Vừa mới (= Khó cũ, E1) và MCTS Khó (E3,
5000 iter). Agent theo thời gian (`time_limit`) gần tất định, AB Vừa tất định → mỗi ván bắt đầu từ
**khai cuộc ngẫu nhiên có seed** (2–4 nước quanh tâm, loại thế có thắng ngay, không trùng nhau),
mỗi khai cuộc 2 ván đổi bên. Ghi ngoài `results/` (mặc định `local_out/p64/`, gitignore); không
đụng `results/raw`.

    python -m gameai.experiments.p64_strength --quick            # 4 khai cuộc (8 ván) / ô
    python -m gameai.experiments.p64_strength                    # 20 khai cuộc (40 ván) / ô
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import random
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any

from gameai.agents.registry import AgentSpec, GameSpec, make_agent, make_game
from gameai.arena import derive_seed, play_game
from gameai.core.game import P1, P2, Move, result_for
from gameai.experiments.common import git_info
from gameai.experiments.e1_nodes import variants_15
from gameai.experiments.e3_c_sweep import GAME15
from gameai.experiments.e3_c_sweep import mcts_spec as e3_mcts_spec
from gameai.gui.presets import AB15_HARD

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "local_out" / "p64"
AB_VUA = variants_15(3)["ab_order"]  # Khó cũ = Vừa mới (D-36)
MCTS_KHO = e3_mcts_spec(15, 1.4, 5000)
TOP_KS: dict[str, tuple[int, ...]] = {"k16_12_8": (16, 12, 8), "k12_8_6": (12, 8, 6)}
OPPONENTS: dict[str, AgentSpec] = {"ab_vua": AB_VUA, "mcts_kho": MCTS_KHO}
N_PAIRS, QUICK_PAIRS, DEFAULT_WORKERS = 20, 4, 3
OPENING_LEN = (2, 4)
COLUMNS = [
    "cell",
    "game_id",
    "pair_seed",
    "a_is_x",
    "opening",
    "winner",
    "result_a",
    "termination",
    "n_moves",
    "moves",
    "a_mean_s",
    "a_max_s",
    "b_mean_s",
    "b_max_s",
    "a_depth_mean",
    "spec_a",
    "spec_b",
    "git_commit",
    "git_dirty",
    "finished_at",
]


def hard_spec(top_k: tuple[int, ...]) -> AgentSpec:
    """AB Khó mới với `top_k` thử (mọi tham số khác như `AB15_HARD`)."""
    name = "k" + "_".join(map(str, top_k))
    return replace(
        AB15_HARD, params={**AB15_HARD.params, "top_k": list(top_k)}, label=f"ab_hard_{name}"
    )


# ---------------------------------------------------------------- khai cuộc
def has_immediate_win(game: Any) -> bool:
    """Người sắp đi có nước thắng ngay không (play/undo trong candidate_moves)."""
    me = game.current_player()
    for m in game.candidate_moves():
        game.play(m)
        won = game.winner() == me
        game.undo()
        if won:
            return True
    return False


def make_opening(
    pair_seed: int,
    taken: set[tuple[Move, ...]] | None = None,
    spec: GameSpec = GAME15,
    max_tries: int = 200,
) -> tuple[Move, ...]:
    """Khai cuộc tất định theo `pair_seed`: 2–4 nước luân phiên trong `candidate_moves` (quanh tâm),
    ván chưa kết thúc, người sắp đi không có nước thắng ngay, và (nếu có `taken`) chưa dùng."""
    for attempt in range(max_tries):
        rng = random.Random(derive_seed(pair_seed, f"p64-opening-{attempt}"))
        n = rng.randint(*OPENING_LEN)
        game = make_game(spec)
        placed: list[Move] = []
        for _ in range(n):
            cands = list(game.candidate_moves())
            m = rng.choice(cands)
            game.play(m)
            placed.append(m)
            if game.is_terminal():
                break
        else:
            op = tuple(placed)
            if has_immediate_win(game) or (taken is not None and op in taken):
                continue
            return op
    raise RuntimeError(f"không dựng được khai cuộc cho seed {pair_seed}")


def make_openings(n_pairs: int, base_seed: int = 0) -> list[tuple[int, tuple[Move, ...]]]:
    """[(pair_seed, khai cuộc)] — khai cuộc đôi một khác nhau."""
    taken: set[tuple[Move, ...]] = set()
    out = []
    for i in range(n_pairs):
        op = make_opening(base_seed + i, taken)
        taken.add(op)
        out.append((base_seed + i, op))
    return out


# ---------------------------------------------------------------- chơi
def play_one(task: tuple[str, AgentSpec, AgentSpec, int, tuple[Move, ...], bool]) -> dict[str, Any]:
    """Một ván A vs B từ `opening`; A cầm X nếu `a_is_x`. Agent mới + seed suy từ pair_seed."""
    cell, spec_a, spec_b, pair_seed, opening, a_is_x = task
    game = make_game(GAME15)
    for m in opening:
        game.play(m)
    agent_a = make_agent(spec_a, derive_seed(pair_seed, "A"))
    agent_b = make_agent(spec_b, derive_seed(pair_seed, "B"))
    ax, ox = (agent_a, agent_b) if a_is_x else (agent_b, agent_a)
    rec = play_game(game, ax, ox, opening=opening)
    a_player = P1 if a_is_x else P2
    ta = [m.time for m in rec.moves if m.player == a_player]
    tb = [m.time for m in rec.moves if m.player != a_player]
    depths = [
        m.stats["depth_reached"]
        for m in rec.moves
        if m.player == a_player and "depth_reached" in m.stats
    ]
    commit, dirty = git_info()
    return {
        "cell": cell,
        "game_id": f"{pair_seed}-{'AX' if a_is_x else 'BX'}",
        "pair_seed": pair_seed,
        "a_is_x": int(a_is_x),
        "opening": " ".join(map(str, opening)),
        "winner": rec.winner,
        "result_a": result_for(rec.winner, a_player),
        "termination": rec.termination,
        "n_moves": rec.n_moves,
        "moves": " ".join(str(m.move) for m in rec.moves),
        "a_mean_s": round(sum(ta) / len(ta), 3) if ta else "",
        "a_max_s": round(max(ta, default=0), 3),
        "b_mean_s": round(sum(tb) / len(tb), 3) if tb else "",
        "b_max_s": round(max(tb, default=0), 3),
        "a_depth_mean": round(sum(depths) / len(depths), 2) if depths else "",
        "spec_a": json.dumps(spec_a.to_dict(), sort_keys=True),
        "spec_b": json.dumps(spec_b.to_dict(), sort_keys=True),
        "git_commit": commit,
        "git_dirty": int(dirty),
        "finished_at": datetime.now().isoformat(timespec="seconds"),
    }


def wilson(score: float, n: int, z: float = 1.96) -> tuple[float, float]:
    """Khoảng Wilson cho tỷ lệ điểm (hòa = 0,5; xấp xỉ) — chỉ để minh họa."""
    if n == 0:
        return 0.0, 1.0
    d = 1 + z * z / n
    c = score + z * z / (2 * n)
    h = z * math.sqrt(score * (1 - score) / n + z * z / (4 * n * n))
    return (c - h) / d, (c + h) / d


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Điểm A (thắng 1, hòa 0,5), W/D/L, khai cuộc phân biệt, số ván trùng chuỗi nước, thời gian."""
    n = len(rows)
    res = [float(r["result_a"]) for r in rows]
    score = sum(res) / n if n else 0.0
    lo, hi = wilson(score, n)
    seqs = [f"{r['opening']}|{r['moves']}" for r in rows]
    by_side = {s: [float(r["result_a"]) for r in rows if int(r["a_is_x"]) == s] for s in (1, 0)}
    return {
        "n": n,
        "wins": sum(x == 1 for x in res),
        "draws": sum(x == 0.5 for x in res),
        "losses": sum(x == 0 for x in res),
        "score": round(score, 3),
        "lo": round(lo, 3),
        "hi": round(hi, 3),
        "distinct_openings": len({r["opening"] for r in rows}),
        "duplicate_games": n - len(set(seqs)),
        "score_as_x": round(sum(by_side[1]) / len(by_side[1]), 3) if by_side[1] else "",
        "score_as_o": round(sum(by_side[0]) / len(by_side[0]), 3) if by_side[0] else "",
        "errors": sum(r["termination"] not in ("normal",) for r in rows),
        "a_mean_s": round(sum(float(r["a_mean_s"]) for r in rows if r["a_mean_s"] != "") / n, 3)
        if n
        else "",
        "a_max_s": max((float(r["a_max_s"]) for r in rows), default=0),
        "wall_game_mean_s": "",
    }


def read_cell(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def run_cell(
    cell: str, spec_a: AgentSpec, spec_b: AgentSpec, openings, workers: int, out_path: Path
) -> list[dict[str, Any]]:
    """Chơi mọi ván của một ô (resume: bỏ ván đã có trong `out_path`); ghi từng ván khi xong."""
    done = {r["game_id"]: r for r in read_cell(out_path)}
    for r in done.values():
        if r["spec_a"] != json.dumps(spec_a.to_dict(), sort_keys=True) or r["spec_b"] != json.dumps(
            spec_b.to_dict(), sort_keys=True
        ):
            raise SystemExit(f"{out_path}: spec khác file đã có — xóa file hoặc đổi --out")
    tasks = [
        (cell, spec_a, spec_b, ps, op, a_x)
        for ps, op in openings
        for a_x in (True, False)
        if f"{ps}-{'AX' if a_x else 'BX'}" not in done
    ]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    new = not out_path.exists()
    with out_path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, COLUMNS)
        if new:
            w.writeheader()
        with ProcessPoolExecutor(max_workers=workers) as ex:
            for row in ex.map(play_one, tasks):
                w.writerow(row)
                f.flush()
                done[row["game_id"]] = {k: str(v) for k, v in row.items()}
                print(
                    f"  [{cell}] {row['game_id']} → {row['result_a']} "
                    f"({row['n_moves']} nước, A {row['a_mean_s']} s/nước)",
                    flush=True,
                )
    return [done[k] for k in sorted(done)]


def main(argv: list[str] | None = None) -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument(
        "--quick", action="store_true", help=f"{QUICK_PAIRS} khai cuộc / ô (file *quick*)"
    )
    ap.add_argument(
        "--pairs", type=int, help=f"số khai cuộc / ô (mặc định {N_PAIRS}; quick {QUICK_PAIRS})"
    )
    ap.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        help="ít worker: agent theo thời gian nhạy tải CPU",
    )
    ap.add_argument("--topk", nargs="+", choices=sorted(TOP_KS), default=sorted(TOP_KS))
    ap.add_argument("--opponents", nargs="+", choices=sorted(OPPONENTS), default=sorted(OPPONENTS))
    ap.add_argument("--out", type=Path, default=OUT_DIR)
    ap.add_argument("--base-seed", type=int, default=0)
    args = ap.parse_args(argv)
    if ROOT / "results" in (args.out.resolve(), *args.out.resolve().parents):
        raise SystemExit("--out không được nằm trong results/ (D-36: số này không vào báo cáo).")
    n_pairs = args.pairs or (QUICK_PAIRS if args.quick else N_PAIRS)
    tag = "p64strength_quick" if args.quick else "p64strength"
    openings = make_openings(n_pairs, args.base_seed)
    print(
        f"[openings] {len(openings)} khai cuộc phân biệt: "
        f"{len({op for _, op in openings})} (độ dài {OPENING_LEN[0]}–{OPENING_LEN[1]})"
    )
    t0 = time.perf_counter()
    summary = []
    for kname in args.topk:
        spec_a = hard_spec(TOP_KS[kname])
        for oname in args.opponents:
            cell = f"{kname}_vs_{oname}"
            print(f"[{cell}] {2 * n_pairs} ván, {args.workers} worker", flush=True)
            c0 = time.perf_counter()
            rows = run_cell(
                cell,
                spec_a,
                OPPONENTS[oname],
                openings,
                args.workers,
                args.out / f"{tag}_{cell}.csv",
            )
            s = summarize(rows) | {
                "cell": cell,
                "top_k": kname,
                "opponent": oname,
                "cell_wall_s": round(time.perf_counter() - c0, 1),
            }
            summary.append(s)
            print(
                f"[{cell}] điểm A {s['score']} [{s['lo']}; {s['hi']}] W/D/L "
                f"{s['wins']}/{s['draws']}/{s['losses']}, khai cuộc phân biệt "
                f"{s['distinct_openings']}, ván trùng chuỗi nước {s['duplicate_games']}",
                flush=True,
            )
    path = args.out / f"{tag}_summary.csv"
    cols = [
        "cell",
        "top_k",
        "opponent",
        "n",
        "wins",
        "draws",
        "losses",
        "score",
        "lo",
        "hi",
        "score_as_x",
        "score_as_o",
        "distinct_openings",
        "duplicate_games",
        "errors",
        "a_mean_s",
        "a_max_s",
        "cell_wall_s",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(summary)
    print(
        f"[done] {round(time.perf_counter() - t0, 1)} s wall, {os.cpu_count()} CPU logic, "
        f"workers {args.workers} → {path}"
    )


if __name__ == "__main__":
    main()
