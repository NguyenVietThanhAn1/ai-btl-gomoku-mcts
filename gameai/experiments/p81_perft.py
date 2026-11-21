"""P8.1: perft cờ tướng so với số chuẩn của chessprogramming.org + đo tốc độ luật.

Chạy: `python -m gameai.experiments.p81_perft [--max-depth 4] [--out results/tables/p81_perft.csv]`
Độ sâu mặc định 4 (~12 s tổng, 11 thế). Thoát với mã 1 nếu có số lệch.
"""

from __future__ import annotations

import argparse
import csv
import random
import sys
import time
from pathlib import Path

from gameai.games.xiangqi import Xiangqi, perft

SOURCE = "https://www.chessprogramming.org/Chinese_Chess_Perft_Results"

# (tên, FEN, nút ở độ sâu 1..4). Nguồn: trang trên, truy cập 2026-11-21.
POSITIONS: tuple[tuple[str, str, tuple[int, int, int, int]], ...] = (
    (
        "start",
        "rheakaehr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RHEAKAEHR w - - 0 1",
        (44, 1920, 79666, 3290240),
    ),
    (
        "pos2",
        "r1ea1a3/4kh3/2h1e4/pHp1p1p1p/4c4/6P2/P1P2R2P/1CcC5/9/2EAKAE2 w - - 0 1",
        (38, 1128, 43929, 1339047),
    ),
    (
        "pos3",
        "1ceak4/9/h2a5/2p1p3p/5cp2/2h2H3/6PCP/3AE4/2C6/3A1K1H1 w - - 0 1",
        (7, 281, 8620, 326201),
    ),
    (
        "pos4",
        "5a3/3k5/3aR4/9/5r3/5h3/9/3A1A3/5K3/2EC2E2 w - - 0 1",
        (25, 424, 9850, 202884),
    ),
    (
        "pos5",
        "CRH1k1e2/3ca4/4ea3/9/2hr5/9/9/4E4/4A4/4KA3 w - - 0 1",
        (28, 516, 14808, 395483),
    ),
    (
        "pos6",
        "R1H1k1e2/9/3aea3/9/2hr5/2E6/9/4E4/4A4/4KA3 w - - 0 1",
        (21, 364, 7626, 162837),
    ),
    (
        "pos7",
        "C1hHk4/9/9/9/9/9/h1pp5/E3C4/9/3A1K3 w - - 0 1",
        (28, 222, 6241, 64971),
    ),
    (
        "pos8",
        "4ka3/4a4/9/9/4H4/p8/9/4C3c/7h1/2EK5 w - - 0 1",
        (23, 345, 8124, 149272),
    ),
    (
        "pos9",
        "2e1ka3/9/e3H4/4h4/9/9/9/4C4/2p6/2EK5 w - - 0 1",
        (21, 195, 3883, 48060),
    ),
    (
        "pos10",
        "1C2ka3/9/C1Hae1h2/p3p3p/6p2/9/P3P3P/3AE4/3p2c2/c1EAK4 w - - 0 1",
        (30, 830, 22787, 649866),
    ),
    (
        "pos11",
        "ChH1k1e2/c3a4/4ea3/9/2hr5/9/9/4C4/4A4/4KA3 w - - 0 1",
        (19, 583, 11714, 376467),
    ),
)

FIELDS = ["position", "depth", "nodes", "expected", "ok", "seconds", "nodes_per_sec"]


def run_perft(max_depth: int) -> list[dict]:
    rows = []
    for name, fen, expected in POSITIONS:
        for depth in range(1, max_depth + 1):
            g = Xiangqi(fen)
            t0 = time.perf_counter()
            nodes = perft(g, depth)
            dt = time.perf_counter() - t0
            exp = expected[depth - 1]
            rows.append(
                {
                    "position": name,
                    "depth": depth,
                    "nodes": nodes,
                    "expected": exp,
                    "ok": int(nodes == exp),
                    "seconds": round(dt, 4),
                    "nodes_per_sec": round(nodes / dt) if dt > 0 else 0,
                }
            )
    return rows


def measure_speed(games: int = 20, seed: int = 0) -> dict[str, float]:
    """Thời gian trung bình của `legal_moves()` / `winner()` trên thế ngẫu nhiên giữa ván."""
    rng = random.Random(seed)
    positions = []
    for _ in range(games):
        g = Xiangqi()
        for _ in range(rng.randint(10, 60)):
            moves = g.legal_moves()
            if not moves:
                break
            g.play(rng.choice(moves))
        positions.append(g)
    reps = 20

    def per_call(fn_name: str) -> float:
        t0 = time.perf_counter()
        for g in positions:
            for _ in range(reps):
                g._legal = None
                g._win = False
                getattr(g, fn_name)()
        return (time.perf_counter() - t0) / (len(positions) * reps)

    return {"legal_moves_s": per_call("legal_moves"), "winner_s": per_call("winner")}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--max-depth", type=int, default=4)
    ap.add_argument("--out", type=Path, default=Path("results/tables/p81_perft.csv"))
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):  # console Windows cp1252 không in được tiếng Việt
        sys.stdout.reconfigure(encoding="utf-8")

    rows = run_perft(args.max_depth)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    bad = [r for r in rows if not r["ok"]]
    for r in rows:
        mark = "OK " if r["ok"] else "LỆCH"
        print(
            f"{mark} {r['position']:<6} d{r['depth']} nodes={r['nodes']:>10} "
            f"expected={r['expected']:>10} {r['seconds']:>8.3f}s {r['nodes_per_sec']:>9} n/s"
        )
    speed = measure_speed()
    print(
        f"legal_moves(): {speed['legal_moves_s'] * 1e6:.0f} us/call; "
        f"winner() (không cache, có nước): {speed['winner_s'] * 1e6:.0f} us/call"
    )
    print(f"{len(rows) - len(bad)}/{len(rows)} khớp -> {args.out}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
