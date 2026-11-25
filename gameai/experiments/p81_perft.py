"""P8.1: perft cờ tướng so với số chuẩn của chessprogramming.org + đo tốc độ luật.

Chạy: `python -m gameai.experiments.p81_perft [--max-depth 4] [--out results/tables/p81_perft.csv]`
Độ sâu mặc định 4 (~12 s tổng, 11 thế). Ghi thêm `--speed-out` (p81_speed.csv: tốc độ trên máy này).
Thoát với mã 1 nếu có số lệch.
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


SPEED_FIELDS = ["metric", "value", "unit", "n_samples", "note"]


def measure_speed(
    rows: list[dict], games: int = 20, playouts: int = 150, seed: int = 0
) -> list[dict]:
    """Đo tốc độ luật trên máy này (phụ thuộc máy): các dòng cho `p81_speed.csv`."""
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

    def per_call_us(fn_name: str) -> float:
        t0 = time.perf_counter()
        for g in positions:
            for _ in range(reps):
                g._legal = None  # bỏ cache để đo đúng chi phí sinh nước
                g._win = False
                getattr(g, fn_name)()
        return (time.perf_counter() - t0) / (len(positions) * reps) * 1e6

    n_calls = len(positions) * reps
    out = [
        {
            "metric": "legal_moves",
            "value": round(per_call_us("legal_moves"), 1),
            "unit": "us/call",
            "n_samples": n_calls,
            "note": "không cache; thế giữa ván ngẫu nhiên (10-60 ply từ thế khởi đầu)",
        },
        {
            "metric": "winner",
            "value": round(per_call_us("winner"), 1),
            "unit": "us/call",
            "n_samples": n_calls,
            "note": "không cache, bên đi còn nước (dừng ở nước hợp lệ đầu tiên)",
        },
    ]
    start_d4 = [r for r in rows if r["position"] == "start" and r["depth"] == 4]
    if start_d4:
        out.append(
            {
                "metric": "perft_start_depth4",
                "value": start_d4[0]["nodes_per_sec"],
                "unit": "leaf_nodes/s",
                "n_samples": 1,
                "note": "có bulk counting ở lá (độ sâu 1 chỉ đếm len(nước), không play/undo lá)",
            }
        )
    out.append(
        {
            "metric": "perft_all_positions",
            "value": round(sum(r["nodes"] for r in rows) / sum(r["seconds"] for r in rows)),
            "unit": "leaf_nodes/s",
            "n_samples": len(rows),
            "note": "tổng nút / tổng giây của mọi dòng p81_perft.csv; có bulk counting ở lá",
        }
    )
    # rollout ngẫu nhiên đến hết ván (play + winner mỗi ply), hoàn tác sau mỗi ván
    rng = random.Random(seed + 1)
    g = Xiangqi()
    total_plies = draws = 0
    t0 = time.perf_counter()
    for _ in range(playouts):
        n = 0
        while (w := g.winner()) is None:
            g.play(rng.choice(g.legal_moves()))
            n += 1
        total_plies += n
        draws += w == 0
        for _ in range(n):
            g.undo()
    dt = time.perf_counter() - t0
    note = "play + winner mỗi ply, tới hết ván (max_plies=300), seed cố định"
    out += [
        {
            "metric": "random_rollout_games",
            "value": round(playouts / dt, 1),
            "unit": "games/s",
            "n_samples": playouts,
            "note": note,
        },
        {
            "metric": "random_rollout_plies",
            "value": round(total_plies / dt),
            "unit": "plies/s",
            "n_samples": total_plies,
            "note": note,
        },
        {
            "metric": "random_rollout_mean_length",
            "value": round(total_plies / playouts, 1),
            "unit": "plies/game",
            "n_samples": playouts,
            "note": f"{draws}/{playouts} ván hòa (chạm max_plies hoặc lặp thế)",
        },
    ]
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--max-depth", type=int, default=4)
    ap.add_argument("--out", type=Path, default=Path("results/tables/p81_perft.csv"))
    ap.add_argument("--speed-out", type=Path, default=Path("results/tables/p81_speed.csv"))
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
    speed = measure_speed(rows)
    with args.speed_out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=SPEED_FIELDS)
        w.writeheader()
        w.writerows(speed)
    for r in speed:
        print(f"{r['metric']:<28} {r['value']:>10} {r['unit']:<13} (n={r['n_samples']})")
    print(f"{len(rows) - len(bad)}/{len(rows)} khớp -> {args.out}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
