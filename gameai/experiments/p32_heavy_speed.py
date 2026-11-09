"""P3.2: đo tốc độ rollout 15×15 — random, HeavyRollout (bản chuẩn), KInRowHeavyRollout (tăng dần).

Mỗi (T, độ dài khai cuộc, seed): bản chuẩn và bản nhanh chạy từ cùng thế cờ với cùng seed rng,
ghi thời gian và kiểm chuỗi nước có giống hệt không. Số liệu đo phát triển (không phải E5).

    python -m gameai.experiments.p32_heavy_speed [--quick]
"""

from __future__ import annotations

import argparse
import csv
import platform
import random
import statistics
import time
from collections.abc import Callable
from pathlib import Path

from gameai.agents.mcts import MCTSAgent
from gameai.agents.rollout import HeavyRollout, RandomRollout
from gameai.games.kinrow import KInRow
from gameai.heuristics.kinrow_eval import move_score
from gameai.heuristics.kinrow_rollout import KInRowHeavyRollout

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "results" / "raw" / "p32_heavy_speed.csv"
TABLE = ROOT / "results" / "tables" / "p32_heavy_speed.csv"
MCTS_TABLE = ROOT / "results" / "tables" / "p32_mcts_iterations.csv"
TIME_LIMIT = 0.5  # giây/nước, như bước quét tham số (D-12)

TEMPERATURES = (100.0, 300.0, 1000.0)
OPENINGS = (6, 20)  # số nước ngẫu nhiên (trên candidate) trước khi rollout
OPENING_SEED0 = 0  # thế cờ thứ i dùng seed OPENING_SEED0 + i
RNG_SEED0 = 1000  # rng của rollout thứ i dùng seed RNG_SEED0 + i


def opening(n_moves: int, seed: int) -> KInRow:
    g = KInRow(15, 5)
    r = random.Random(seed)
    for _ in range(n_moves):
        g.play(r.choice(g.candidate_moves()))
    return g


def timed_rollout(policy: Callable, g: KInRow, seed: int) -> tuple[list[int], float]:
    rng = random.Random(seed)
    seq = []
    t0 = time.perf_counter()
    while not g.is_terminal():
        m = policy(g, rng)
        seq.append(m)
        g.play(m)
    return seq, time.perf_counter() - t0


def run(n_rollouts: int) -> list[dict]:
    rows = []
    rand = RandomRollout()
    for n_open in OPENINGS:
        starts = [opening(n_open, OPENING_SEED0 + i) for i in range(n_rollouts)]
        for i, s in enumerate(starts):
            seq, dt = timed_rollout(rand, s.clone(), RNG_SEED0 + i)
            rows.append(_row("random", "", n_open, i, len(seq), dt, ""))
        for t in TEMPERATURES:
            ref, fast = HeavyRollout(move_score, t), KInRowHeavyRollout(t)  # dùng lại qua các ván
            for i, s in enumerate(starts):
                seq_r, dt_r = timed_rollout(ref, s.clone(), RNG_SEED0 + i)
                seq_f, dt_f = timed_rollout(fast, s.clone(), RNG_SEED0 + i)
                same = int(seq_r == seq_f)
                rows.append(_row("heavy_ref", t, n_open, i, len(seq_r), dt_r, ""))
                rows.append(_row("heavy_kinrow", t, n_open, i, len(seq_f), dt_f, same))
    return rows


def mcts_iterations(time_limit: float, n_seeds: int) -> list[dict]:
    """Số iteration MCTS trong cùng `time_limit` với từng rollout policy (rollout tới hết ván)."""
    policies: list[tuple[str, object, Callable]] = [("random", "", RandomRollout)]
    for t in TEMPERATURES:
        policies.append(("heavy_ref", t, lambda t=t: HeavyRollout(move_score, t)))
        policies.append(("heavy_kinrow", t, lambda t=t: KInRowHeavyRollout(t)))
    out = []
    for n_open in OPENINGS:
        for name, t, make in policies:
            its, plies = [], []
            for i in range(n_seeds):
                g = opening(n_open, OPENING_SEED0 + i)
                agent = MCTSAgent(time_limit=time_limit, rollout_policy=make(), seed=RNG_SEED0 + i)
                agent.select_move(g)
                its.append(agent.stats["iterations"])
                plies.append(agent.stats["rollout_plies"] / agent.stats["iterations"])
            out.append(
                {
                    "policy": name,
                    "temperature": t,
                    "opening_moves": n_open,
                    "time_limit": time_limit,
                    "n_positions": n_seeds,
                    "mean_iterations": round(statistics.mean(its), 1),
                    "plies_per_iter": round(statistics.mean(plies), 1),
                    "python": platform.python_version(),
                    "machine": platform.processor() or platform.machine(),
                }
            )
    return out


def _row(policy, t, n_open, i, plies, dt, same) -> dict:
    return {
        "policy": policy,
        "temperature": t,
        "opening_moves": n_open,
        "opening_seed": OPENING_SEED0 + i,
        "rng_seed": RNG_SEED0 + i,
        "plies": plies,
        "seconds": f"{dt:.6f}",
        "identical_to_ref": same,
    }


def summarize(rows: list[dict]) -> list[dict]:
    groups: dict[tuple, list[dict]] = {}
    for r in rows:
        groups.setdefault((r["policy"], r["temperature"], r["opening_moves"]), []).append(r)
    ref_ms = {}
    out = []
    for (pol, t, n_open), rs in groups.items():
        secs = sum(float(r["seconds"]) for r in rs)
        plies = sum(r["plies"] for r in rs)
        ms = secs / len(rs) * 1e3
        if pol == "heavy_ref":
            ref_ms[(t, n_open)] = ms
        out.append(
            {
                "policy": pol,
                "temperature": t,
                "opening_moves": n_open,
                "n_rollouts": len(rs),
                "mean_plies": round(statistics.mean(r["plies"] for r in rs), 1),
                "us_per_ply": round(secs / max(plies, 1) * 1e6, 1),
                "ms_per_rollout": round(ms, 3),
                "speedup_vs_ref": "",
                "identical_to_ref": (
                    f"{sum(r['identical_to_ref'] for r in rs)}/{len(rs)}"
                    if pol == "heavy_kinrow"
                    else ""
                ),
                "python": platform.python_version(),
                "machine": platform.processor() or platform.machine(),
            }
        )
    for r in out:
        if r["policy"] == "heavy_kinrow":
            r["speedup_vs_ref"] = round(
                ref_ms[(r["temperature"], r["opening_moves"])] / r["ms_per_rollout"], 1
            )
    return out


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--quick", action="store_true", help="5 rollout/ô, không ghi file results/")
    ap.add_argument("--n", type=int, default=50, help="số rollout mỗi (policy, T, khai cuộc)")
    args = ap.parse_args()
    n = 5 if args.quick else args.n
    t0 = time.perf_counter()
    rows = run(n)
    table = summarize(rows)
    if not args.quick:
        write_csv(RAW, rows)
        write_csv(TABLE, table)
    for r in table:
        print(
            f"{r['policy']:13s} T={r['temperature']!s:7s} open={r['opening_moves']:2d} "
            f"plies={r['mean_plies']:5.1f} {r['us_per_ply']:7.1f} us/ply "
            f"{r['ms_per_rollout']:7.3f} ms/rollout x{r['speedup_vs_ref']!s:5s} "
            f"same={r['identical_to_ref']}"
        )
    iters = mcts_iterations(0.2 if args.quick else TIME_LIMIT, 1 if args.quick else 3)
    if not args.quick:
        write_csv(MCTS_TABLE, iters)
    for r in iters:
        print(
            f"mcts {r['policy']:13s} T={r['temperature']!s:7s} open={r['opening_moves']:2d} "
            f"iters/move={r['mean_iterations']:7.1f} rollout_plies/iter={r['plies_per_iter']:5.1f}"
        )
    print(f"total {time.perf_counter() - t0:.1f} s")  # ASCII: console Windows cp1252


if __name__ == "__main__":
    main()
