"""P8.4 — kiểm độc lập nhãn chiếu bí / bí nước của E7 (D-25).

    python -m gameai.experiments.e7_term_check

Lấy ngẫu nhiên (seed cố định) 5 ván `stalemate` + 5 ván `mate` từ raw E7 (c4, a1, d1), replay tới
thế cuối bằng game, rồi kiểm lại thế cuối bằng **bộ sinh nước viết riêng từ FEN** (không dùng
`xiangqi.py`): không còn nước hợp lệ, chiếu ⇔ nhãn `mate`, bên tới lượt thua = winner CSV
= `winner()`.
In FEN thế cuối + kết quả; ghi `results/tables/e7_term_check.csv`. Mã thoát 1 nếu có ván lệch.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from pathlib import Path

from gameai.agents.registry import GameSpec, make_game
from gameai.experiments.e7_xiangqi import RAW_DIR, TABLE_DIR, _write, classify_game

SEED = 20261126
POINTS = ("c4", "a1", "d1")
N_EACH = 5
COLUMNS = [
    "point",
    "game_id",
    "label",
    "ply",
    "fen",
    "side_to_move",
    "indep_legal",
    "indep_check",
    "game_legal",
    "game_in_check",
    "game_winner",
    "csv_winner",
    "ok",
]

Grid = list[list[str | None]]
Sq = tuple[int, int]

# ---------------------------------------------------------------- bộ sinh nước độc lập
# Lưới 10×9, hàng 0 = trên cùng (phía Đen) theo thứ tự FEN; chữ hoa = Đỏ.
ORTHO = ((1, 0), (-1, 0), (0, 1), (0, -1))
DIAG = ((1, 1), (1, -1), (-1, 1), (-1, -1))
HORSE = (
    ((1, 0), ((2, 1), (2, -1))),
    ((-1, 0), ((-2, 1), (-2, -1))),
    ((0, 1), ((1, 2), (-1, 2))),
    ((0, -1), ((1, -2), (-1, -2))),
)


def parse_fen(fen: str) -> tuple[Grid, str]:
    """(lưới, bên tới lượt "R"/"B")."""
    board, side = fen.split()[:2]
    g: Grid = [[None] * 9 for _ in range(10)]
    for r, row in enumerate(board.split("/")):
        c = 0
        for ch in row:
            if ch.isdigit():
                c += int(ch)
            else:
                g[r][c] = ch
                c += 1
    return g, ("R" if side in ("w", "r") else "B")


def _color(p: str) -> str:
    return "R" if p.isupper() else "B"


def _inb(r: int, c: int) -> bool:
    return 0 <= r < 10 and 0 <= c < 9


def _palace(r: int, c: int, s: str) -> bool:
    return 3 <= c <= 5 and ((7 <= r <= 9) if s == "R" else (0 <= r <= 2))


def _own_half(r: int, s: str) -> bool:
    return r >= 5 if s == "R" else r <= 4


def _targets(g: Grid, r: int, c: int, s: str) -> list[Sq]:
    t = (g[r][c] or "").upper()
    out: list[Sq] = []
    if t == "K" or t == "A":
        for dr, dc in ORTHO if t == "K" else DIAG:
            if _palace(r + dr, c + dc, s):
                out.append((r + dr, c + dc))
    elif t in "BE":
        for dr, dc in DIAG:
            nr, nc = r + 2 * dr, c + 2 * dc
            if _inb(nr, nc) and _own_half(nr, s) and g[r + dr][c + dc] is None:
                out.append((nr, nc))
    elif t in "NH":
        for (lr, lc), dests in HORSE:
            if _inb(r + lr, c + lc) and g[r + lr][c + lc] is None:
                out += [(r + dr, c + dc) for dr, dc in dests if _inb(r + dr, c + dc)]
    elif t in "RC":
        for dr, dc in ORTHO:
            nr, nc, screen = r + dr, c + dc, False
            while _inb(nr, nc):
                if not screen:
                    if g[nr][nc] is None:
                        out.append((nr, nc))
                    elif t == "R":
                        out.append((nr, nc))
                        break
                    else:
                        screen = True
                elif g[nr][nc] is not None:
                    out.append((nr, nc))
                    break
                nr, nc = nr + dr, nc + dc
    elif t == "P":
        out.append((r + (-1 if s == "R" else 1), c))
        if not _own_half(r, s):
            out += [(r, c + 1), (r, c - 1)]
    return out


def pseudo_moves(g: Grid, s: str) -> list[tuple[Sq, Sq]]:
    """Nước giả hợp lệ (chưa xét tự chiếu) của bên s."""
    out = []
    for r in range(10):
        for c in range(9):
            p = g[r][c]
            if p is None or _color(p) != s:
                continue
            for nr, nc in _targets(g, r, c, s):
                if not _inb(nr, nc):
                    continue
                q = g[nr][nc]
                if q is None or _color(q) != s:
                    out.append(((r, c), (nr, nc)))
    return out


def _king(g: Grid, s: str) -> Sq | None:
    k = "K" if s == "R" else "k"
    return next(((r, c) for r in range(10) for c in range(9) if g[r][c] == k), None)


def attacked(g: Grid, s: str) -> bool:
    """Tướng bên s bị tấn công (gồm luật lộ mặt tướng)."""
    k = _king(g, s)
    if k is None:
        return True
    o = "B" if s == "R" else "R"
    if any(dst == k for _, dst in pseudo_moves(g, o)):
        return True
    ok = _king(g, o)
    if ok and ok[1] == k[1]:
        lo, hi = sorted((ok[0], k[0]))
        return all(g[r][k[1]] is None for r in range(lo + 1, hi))
    return False


def legal_moves(g: Grid, s: str) -> list[tuple[Sq, Sq]]:
    out = []
    for (r, c), (nr, nc) in pseudo_moves(g, s):
        cap = g[nr][nc]
        g[nr][nc], g[r][c] = g[r][c], None
        if not attacked(g, s):
            out.append(((r, c), (nr, nc)))
        g[r][c], g[nr][nc] = g[nr][nc], cap
    return out


def perft(g: Grid, s: str, depth: int) -> int:
    if depth == 0:
        return 1
    o, n = ("B" if s == "R" else "R"), 0
    for (r, c), (nr, nc) in legal_moves(g, s):
        cap = g[nr][nc]
        g[nr][nc], g[r][c] = g[r][c], None
        n += perft(g, o, depth - 1)
        g[r][c], g[nr][nc] = g[nr][nc], cap
    return n


# ---------------------------------------------------------------- kiểm
def check_row(point: str, row: dict[str, str]) -> dict[str, object]:
    """Replay một ván tới thế cuối, kiểm bằng bộ sinh độc lập + API game."""
    label, ply = classify_game(row)
    gs = json.loads(row["game_spec"])
    game = make_game(GameSpec(gs["kind"], gs["params"]))
    for m in (int(x) for x in f"{row['opening']};{row['moves']}".split(";") if x):
        game.play(m)
    fen = game.to_fen()
    g, stm = parse_fen(fen)
    n_ind, chk = len(legal_moves(g, stm)), attacked(g, stm)
    w_game, w_csv = game.winner(), int(row["winner"])
    ok = (
        n_ind == 0
        and not game.legal_moves()
        and game.in_check() == chk
        and w_game == w_csv == (-1 if stm == "R" else 1)
        and label == ("mate" if chk else "stalemate")
    )
    return {
        "point": point,
        "game_id": row["game_id"],
        "label": label,
        "ply": ply,
        "fen": fen,
        "side_to_move": stm,
        "indep_legal": n_ind,
        "indep_check": int(chk),
        "game_legal": len(game.legal_moves()),
        "game_in_check": int(game.in_check()),
        "game_winner": w_game,
        "csv_winner": w_csv,
        "ok": int(ok),
    }


def sample_games(
    raw_dir: Path = RAW_DIR, seed: int = SEED, n_each: int = N_EACH
) -> list[tuple[str, dict[str, str]]]:
    """n_each ván stalemate + n_each ván mate, chọn ngẫu nhiên (seed) từ c4, a1, d1."""
    csv.field_size_limit(10**9)
    pool: dict[str, list[tuple[str, dict[str, str]]]] = {"mate": [], "stalemate": []}
    for pt in POINTS:
        with (raw_dir / f"e7_{pt}.csv").open(encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                term = classify_game(row)[0]
                if term in pool:
                    pool[term].append((pt, row))
    rng = random.Random(seed)
    print(f"pool: mate {len(pool['mate'])}, stalemate {len(pool['stalemate'])}")
    return rng.sample(pool["stalemate"], n_each) + rng.sample(pool["mate"], n_each)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    ap.add_argument("--out", type=Path, default=TABLE_DIR / "e7_term_check.csv")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    g0, s0 = parse_fen("rheakaehr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RHEAKAEHR w - - 0 1")
    p1, p2 = perft(g0, s0, 1), perft(g0, s0, 2)
    print(f"perft bộ sinh độc lập (thế đầu): {p1} / {p2} (chuẩn 44 / 1920)")
    if (p1, p2) != (44, 1920):
        print("LỖI: bộ sinh độc lập sai perft")
        return 1
    rows = [check_row(pt, row) for pt, row in sample_games(args.raw_dir)]
    for r in rows:
        print(
            f"{'OK ' if r['ok'] else 'LỆCH'} {r['point']} {r['game_id']} ply={r['ply']} "
            f"nhãn={r['label']} | độc lập: legal={r['indep_legal']} chiếu={r['indep_check']} | "
            f"game: legal={r['game_legal']} in_check={r['game_in_check']} "
            f"winner={r['game_winner']} csv={r['csv_winner']} tới lượt={r['side_to_move']}\n"
            f"    FEN {r['fen']}"
        )
    n_ok = sum(int(r["ok"]) for r in rows)  # type: ignore[call-overload]
    _write(args.out, COLUMNS, rows)
    print(f"khớp {n_ok}/{len(rows)} → {args.out}")
    return 0 if n_ok == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())
