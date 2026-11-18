"""E6: tác dụng `check_tactics` của MCTS (D-21). Chỉ 15×15, ngân sách iteration.

(a) Bộ thế cờ trích từ ván E3/E5: loại 1 (block) = đối thủ có four đúng 1 ô chặn,
    loại 2 (win) = mình có thắng ngay. Tactics tắt: tỷ lệ chọn đúng theo iter
    {100, 500, 1000, 2500, 5000} (rand, h300, 10 seed/thế); tactics bật: sanity 100 %.
(b) Win rate tắt vs bật: `randoff_i1000` vs mref; h300 tắt vs h300 bật; h300 tắt vs Greedy
    (bản bật từ E3).
(c) Chi phí: thời gian một lần `check_tactics`, % nước đi thẳng, thời gian/nước bật vs tắt.

    python -m gameai.experiments.e6_tactics all --quick
    python -m gameai.experiments.e6_tactics <step>
    # step: positions | sanity | choice | match | cost | tables
"""

from __future__ import annotations

import argparse
import hashlib
import math
import os
import random
import statistics
import sys
import time
from collections.abc import Iterable
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from dataclasses import dataclass
from datetime import datetime
from functools import cache
from pathlib import Path
from typing import Any

from gameai.agents.mcts import TACTIC_BLOCK, TACTIC_WIN, MCTSAgent, Node
from gameai.agents.registry import AgentSpec, make_agent
from gameai.arena import derive_seed
from gameai.core.game import P1, P2
from gameai.experiments.common import (
    SUMMARY_COLUMNS,
    add_runner_args,
    git_info,
    moves_path_for,
    read_rows,
    run_match,
    summarize,
    wilson,
)
from gameai.experiments.e3_c_sweep import GAME15, GREEDY
from gameai.experiments.e5_rollout import (
    INK,
    INK2,
    MREF,
    SURFACE,
    _append_csv,
    _keep_pairs,
    _style,
    _write,
    cpu_name,
    e3_reusable,
    fnum,
    mcts_spec,
    paired_diff,
    phase_of,
)
from gameai.experiments.figfmt import ratio_axis, vn_figure
from gameai.games.kinrow import KInRow, cell_of

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "results" / "raw"
TABLE_DIR = ROOT / "results" / "tables"
FIG_DIR = ROOT / "results" / "figures"

N, K = 15, 5
CHECKPOINTS = (100, 500, 1000, 2500, 5000)
ROLLOUTS = ("rand", "h300")
TYPES = ("block", "win")
N_PER_STRATUM = 15  # D-21 (sửa sau quick): 15 thế/tầng/loại → 45/loại
QUICK_PER_STRATUM = 2
N_SEEDS = 10
QUICK_SEEDS = 2
QUIET_PER_PHASE = 14
QUICK_QUIET = 2
QUIET_MIN_PLY = 4  # thế yên tĩnh: bỏ vài nước đầu (bàn gần trống, ít candidate)
STRATA = (("<60", 0, 59), ("60-100", 60, 100), (">100", 101, None))
BOOT_N = 2000
BOOT_SEED = 21
SELF_ITERS = (1000,)  # D-21: bỏ đối đầu 5000
GREEDY_ITERS = (1000, 5000)
MREF_ITER = 1000
N_PAIRS = 25  # 50 ván/điểm
QUICK_PAIRS = 1
CHECK_REPS = 3
SPEEDUP_4W = 3.5  # như E3/E5
POOL_OVERHEAD_S = 2.0
SOURCE_PATTERNS = (
    "e3_greedy_c*_i*.csv",
    "e3_ab2_c*_i*.csv",
    "e5_h2h_*.csv",
    "e5_greedy_*.csv",
    "e5_mref_*.csv",
    "e5_ab2_*.csv",
)
STEPS = ("bench", "positions", "sanity", "choice", "match", "cost", "tables", "all")
BENCH_PLIES = (8, 16, 24)  # bench ngắn, so với cùng thế trong e5_bench.csv
BENCH_SEEDS = (0,)


def prefix(quick: bool) -> str:
    return "e6quick_" if quick else "e6_"


# ---------------------------------------------------------------- ô thắng ngay

DIRS = ((0, 1), (1, 0), (1, 1), (1, -1))


def is_win_cell(board: bytearray, n: int, k: int, cell: int, stone: int) -> bool:
    """Đặt `stone` vào ô trống `cell` có tạo ≥ k quân liên tiếp không (khớp `KInRow._wins_at`)."""
    r, c = divmod(cell, n)
    for dr, dc in DIRS:
        cnt = 1
        for s in (1, -1):
            rr, cc = r + dr * s, c + dc * s
            while 0 <= rr < n and 0 <= cc < n and board[rr * n + cc] == stone:
                cnt += 1
                rr += dr * s
                cc += dc * s
        if cnt >= k:
            return True
    return False


def win_cells(game: KInRow, player: int) -> set[int]:
    """Các ô mà `player` đặt vào thì thắng ngay (không phụ thuộc ai đang tới lượt).
    Ô thắng luôn kề quân của `player` nên nằm trong `candidate_moves()`."""
    if game.is_terminal():
        return set()
    stone = cell_of(player)
    b = game.board
    return {m for m in game.candidate_moves() if is_win_cell(b, game.n, game.k, m, stone)}


@cache
def _line_cells(n: int, k: int, move: int) -> tuple[int, ...]:
    """Các ô trên 4 đường qua `move`, cách ≤ k − 1 (không gồm `move`)."""
    r, c = divmod(move, n)
    out = []
    for dr, dc in DIRS:
        for s in (1, -1):
            for d in range(1, k):
                rr, cc = r + dr * s * d, c + dc * s * d
                if 0 <= rr < n and 0 <= cc < n:
                    out.append(rr * n + cc)
    return tuple(out)


class WinTracker:
    """Giữ tập ô thắng ngay của cả hai bên khi replay; sau mỗi nước chỉ xét lại các ô trên 4 đường
    qua nước vừa đi (trạng thái "ô thắng" của y chỉ đổi khi có quân đặt trên đường qua y,
    cách ≤ k−1)."""

    def __init__(self, game: KInRow) -> None:
        self.game = game
        self.cells = {P1: win_cells(game, P1), P2: win_cells(game, P2)}

    def play(self, move: int) -> None:
        g = self.game
        g.play(move)
        for s in self.cells.values():
            s.discard(move)
        if g.is_terminal():
            return
        b, n, k = g.board, g.n, g.k
        for y in _line_cells(n, k, move):
            if b[y]:
                continue
            for p, s in self.cells.items():
                if is_win_cell(b, n, k, y, cell_of(p)):
                    s.add(y)
                else:
                    s.discard(y)


def classify(mine: set[int], opp: set[int]) -> str:
    """'win' | 'block' | 'open4' (đối thủ ≥ 2 ô thắng, ta không thắng ngay) | 'quiet'."""
    if mine:
        return "win"
    if len(opp) == 1:
        return "block"
    if len(opp) >= 2:
        return "open4"
    return "quiet"


def keeps_win(game: KInRow, move: int) -> bool:
    """Nước `move` (không thắng ngay) giữ được thắng chắc: sau đó đối thủ không có ô thắng ngay và
    người vừa đi còn ≥ 2 ô thắng ngay (đối thủ chỉ chặn được một). Điều kiện đủ, không cần."""
    me = game.current_player()
    g = game.clone()
    g.play(move)
    if g.is_terminal():
        return False
    return not win_cells(g, -me) and len(win_cells(g, me)) >= 2


# ---------------------------------------------------------------- trích thế

POS_COLUMNS = ["pos_id", "type", "source", "game_id", "ply", "mover", "n_candidates", "n_mine",
               "n_opp", "correct_cells", "phase", "stratum", "moves"]  # fmt: skip


def stratum_of(n_cand: int) -> str:
    for name, lo, hi in STRATA:
        if n_cand >= lo and (hi is None or n_cand <= hi):
            return name
    raise ValueError(n_cand)


def source_files(raw_dir: Path = RAW_DIR) -> list[Path]:
    files: set[Path] = set()
    for pat in SOURCE_PATTERNS:
        files |= {p for p in raw_dir.glob(pat) if not p.name.endswith("_moves.csv")}
    return sorted(files)


def game_from_moves(moves: Iterable[int]) -> KInRow:
    g = KInRow(N, K)
    for m in moves:
        g.play(m)
    return g


def _key_hash(game: KInRow) -> str:
    return hashlib.sha256(bytes(game.board) + str(game.current_player()).encode()).hexdigest()


def scan_game(moves: list[int]) -> list[dict[str, Any]]:
    """Mọi thế chưa kết thúc của một ván kèm phân loại (theo thứ tự ply)."""
    g = KInRow(N, K)
    tr = WinTracker(g)
    out = []
    for ply, m in enumerate(moves):
        if g.is_terminal():
            break
        me = g.current_player()
        mine, opp = tr.cells[me], tr.cells[-me]
        t = classify(mine, opp)
        out.append(
            {
                "type": t,
                "ply": ply,
                "mover": me,
                "n_candidates": len(g.candidate_moves()),
                "n_mine": len(mine),
                "n_opp": len(opp),
                "correct": sorted(mine) if t == "win" else sorted(opp) if t == "block" else [],
                "hash": _key_hash(g),
                "moves": moves[:ply],
            }
        )
        tr.play(m)
    return out


def extract_positions(
    raw_dir: Path = RAW_DIR,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, dict[str, int]]]:
    """Trả (ứng viên đã khử trùng + sắp theo sha256(key) cho từng loại, bảng đếm).

    Loại 'block'/'win': mỗi ván lần xuất hiện đầu. Loại 'quiet:<phase>': mỗi ván thế yên tĩnh
    đầu tiên
    (ply ≥ QUIET_MIN_PLY) trong mỗi nhóm giai đoạn. Chọn N đầu danh sách → quick ⊂ full."""
    counts: dict[str, dict[str, int]] = {}
    seen: dict[str, dict[str, dict[str, Any]]] = {}

    def cnt(t: str, k: str, d: int = 1) -> None:
        counts.setdefault(t, {"occurrences": 0, "games": 0, "distinct": 0})[k] += d

    n_games = 0
    for f in source_files(raw_dir):
        for r in sorted(read_rows(f), key=lambda x: x["game_id"]):
            if not r["moves"]:
                continue
            n_games += 1
            moves = [int(x) for x in r["moves"].split(";")]
            first: dict[str, dict[str, Any]] = {}
            for p in scan_game(moves):
                t = p["type"]
                if t == "quiet":
                    if p["ply"] < QUIET_MIN_PLY:
                        continue
                    t = f"quiet:{phase_of(p['ply'])}"
                cnt(t, "occurrences")
                if t not in first:
                    first[t] = p
            for t, p in first.items():
                cnt(t, "games")
                bucket = seen.setdefault(t, {})
                if p["hash"] not in bucket:
                    bucket[p["hash"]] = {**p, "type": t, "source": f.name, "game_id": r["game_id"]}
    out: dict[str, list[dict[str, Any]]] = {}
    for t, bucket in seen.items():
        cnt(t, "distinct", len(bucket))
        out[t] = [bucket[h] for h in sorted(bucket)]
    counts["_meta"] = {"occurrences": n_games, "games": n_games, "distinct": 0}
    return out, counts


def select_positions(cands: dict[str, list[dict[str, Any]]], quick: bool) -> list[dict[str, Any]]:
    """Loại 1/2: lấy mẫu phân tầng theo `n_candidates`, mỗi tầng N đầu danh sách (sắp theo sha256)
    → tất định, quick ⊂ full. Thế yên tĩnh: N đầu mỗi nhóm giai đoạn."""
    n_str = QUICK_PER_STRATUM if quick else N_PER_STRATUM
    n_quiet = QUICK_QUIET if quick else QUIET_PER_PHASE
    sel = []
    for t in sorted(cands):
        if t in TYPES:
            chosen = [
                p
                for name, _, _ in STRATA
                for p in [c for c in cands[t] if stratum_of(c["n_candidates"]) == name][:n_str]
            ]
        elif t.startswith("quiet:"):
            chosen = cands[t][:n_quiet]
        else:
            chosen = []
        for p in chosen:
            sel.append(
                {
                    "pos_id": f"{t.split(':')[0]}-{p['hash'][:10]}",
                    "type": t.split(":")[0],
                    "source": p["source"],
                    "game_id": p["game_id"],
                    "ply": p["ply"],
                    "mover": p["mover"],
                    "n_candidates": p["n_candidates"],
                    "n_mine": p["n_mine"],
                    "n_opp": p["n_opp"],
                    "correct_cells": ";".join(map(str, p["correct"])),
                    "phase": phase_of(p["ply"]),
                    "stratum": stratum_of(p["n_candidates"]),
                    "moves": ";".join(map(str, p["moves"])),
                }
            )
    return sel


def positions_path(quick: bool, raw_dir: Path = RAW_DIR) -> Path:
    return raw_dir / f"{prefix(quick)}positions.csv"


def run_positions(quick: bool, raw_dir: Path = RAW_DIR, table_dir: Path = TABLE_DIR) -> float:
    t0 = time.perf_counter()
    cands, counts = extract_positions(raw_dir)
    sel = select_positions(cands, quick)
    _write(positions_path(quick, raw_dir), POS_COLUMNS, sel)
    rows = []
    for t in ("block", "win", "open4", *sorted(x for x in counts if x.startswith("quiet:"))):
        c = counts.get(t, {"occurrences": 0, "games": 0, "distinct": 0})
        chosen = [p for p in sel if p["type"] == t.split(":")[0]]
        if t.startswith("quiet:"):
            chosen = [p for p in chosen if p["phase"] == t.split(":")[1]]
        row = {"type": t, **c, "selected": len(chosen)}
        pool = cands.get(t, [])
        for name, _, _ in STRATA:
            row[f"sel_{name}"] = sum(p["stratum"] == name for p in chosen)
            row[f"pool_{name}"] = sum(stratum_of(x["n_candidates"]) == name for x in pool)
        if chosen:
            ncs = [int(p["n_candidates"]) for p in chosen]
            row.update(cand_min=min(ncs), cand_median=statistics.median(ncs), cand_max=max(ncs))
        rows.append(row)
    cols = ["type", "occurrences", "games", "distinct", "selected",
            *[f"sel_{s[0]}" for s in STRATA], *[f"pool_{s[0]}" for s in STRATA],
            "cand_min", "cand_median", "cand_max"]  # fmt: skip
    _write(table_dir / f"{prefix(quick)}positions_summary.csv", cols, rows)
    dt = time.perf_counter() - t0
    print(f"[positions] {counts['_meta']['games']} ván nguồn, {dt:.1f} s")
    for r in rows:
        strata = ", ".join(f"{s[0]}: {r[f'sel_{s[0]}']}/{r[f'pool_{s[0]}']}" for s in STRATA)
        print(
            f"  {r['type']}: {r['occurrences']} lần, {r['games']} ván, "
            f"{r['distinct']} thế khác nhau, "
            f"chọn {r['selected']} ({strata})"
        )
    return dt


def load_positions(quick: bool, raw_dir: Path = RAW_DIR) -> list[dict[str, str]]:
    return read_rows(positions_path(quick, raw_dir))


def pool_weights(quick: bool, table_dir: Path = TABLE_DIR) -> dict[str, dict[str, float]]:
    """Trọng số tự nhiên của tầng = tỷ lệ thế trong pool đầy đủ (sau khử trùng) của từng loại."""
    path = table_dir / f"{prefix(quick)}positions_summary.csv"
    out: dict[str, dict[str, float]] = {}
    if not path.exists():
        return out
    for r in read_rows(path):
        if r["type"] in TYPES:
            tot = sum(int(r[f"pool_{s[0]}"]) for s in STRATA)
            out[r["type"]] = {s[0]: int(r[f"pool_{s[0]}"]) / tot for s in STRATA}
    return out


def position_game(p: dict[str, str]) -> KInRow:
    return game_from_moves(int(x) for x in p["moves"].split(";") if x)


def correct_set(p: dict[str, str]) -> set[int]:
    return {int(x) for x in p["correct_cells"].split(";") if x}


# ---------------------------------------------------------------- spec


def spec_off(rollout: str, iterations: int) -> AgentSpec:
    """Như `e5_rollout.mcts_spec` (bản bật, trùng E3/E5) nhưng `check_tactics = False`."""
    on = mcts_spec(rollout, iterations=iterations)
    params = {**on.params, "check_tactics": False}
    return AgentSpec("mcts", params, label=f"{rollout}off_i{iterations}")


# ---------------------------------------------------------------- (a) sanity tactics bật

SANITY_COLUMNS = ["pos_id", "type", "n_candidates", "stratum", "tactic", "move", "correct", "ok"]


def run_sanity(quick: bool, raw_dir: Path = RAW_DIR, table_dir: Path = TABLE_DIR) -> bool:
    rows = []
    for p in load_positions(quick, raw_dir):
        if p["type"] not in TYPES:
            continue
        g = position_game(p)
        agent = MCTSAgent(iterations=1, check_tactics=True, seed=0)
        m = agent.select_move(g)
        want = TACTIC_BLOCK if p["type"] == "block" else TACTIC_WIN
        correct = m in correct_set(p)
        rows.append(
            {
                "pos_id": p["pos_id"],
                "type": p["type"],
                "n_candidates": p["n_candidates"],
                "stratum": p["stratum"],
                "tactic": agent.stats["tactic"],
                "move": m,
                "correct": int(correct),
                "ok": int(correct and agent.stats["tactic"] == want),
            }
        )
    _write(table_dir / f"{prefix(quick)}sanity.csv", SANITY_COLUMNS, rows)
    ok = all(r["ok"] for r in rows) and bool(rows)
    print(f"[sanity] tactics bật: {sum(r['ok'] for r in rows)}/{len(rows)} đúng")
    return ok


# ---------------------------------------------------------------- (a) tactics tắt, checkpoint

CHOICE_COLUMNS = ["pos_id", "type", "rollout", "seed", "iter", "move", "correct", "keeps_win",
                  "correct_expanded", "n_correct", "wn_correct", "n_chosen", "root_children",
                  "time_s", "git_commit", "git_dirty"]  # fmt: skip


def checkpoint_moves(
    game: KInRow, agent: MCTSAgent, checkpoints: tuple[int, ...] = CHECKPOINTS
) -> Iterable[tuple[int, Node, float]]:
    """Chạy MCTS (tắt tactics) tới checkpoint cuối, yield (k, root, giây) tại mỗi checkpoint k.

    Gọi `_search` nối tiếp trên cùng gốc với `iterations` = phần tăng thêm: vòng lặp chỉ phụ
    thuộc gốc, rng và c → cây tại k giống hệt `MCTSAgent(iterations=k)` cùng seed (có test).
    Root bị sửa sau mỗi
    yield → người gọi phải đọc ngay."""
    assert not agent.check_tactics
    root = Node(None, None, -game.current_player(), list(game.candidate_moves()))
    agent.root = root
    t0 = time.perf_counter()
    done = 0
    for k in checkpoints:
        agent.iterations = k - done
        agent._search(game, root, t0)
        done = k
        yield k, root, time.perf_counter() - t0


def choice_task(
    pos: dict[str, str], rollout: str, seed: int, checkpoints: tuple[int, ...] = CHECKPOINTS
) -> list[dict[str, Any]]:
    game = position_game(pos)
    correct = correct_set(pos)
    agent = make_agent(spec_off(rollout, checkpoints[-1]), derive_seed(seed, pos["pos_id"]))
    assert isinstance(agent, MCTSAgent)
    rows = []
    for k, root, dt in checkpoint_moves(game, agent, checkpoints):
        best = agent._final_child(root)
        good = [ch for ch in root.children if ch.move in correct]
        top = max(good, key=lambda ch: (ch.N, ch.W)) if good else None
        is_correct = best.move in correct
        kw: Any = ""
        if pos["type"] == "win":
            kw = int(not is_correct and keeps_win(game, best.move))
        rows.append(
            {
                "pos_id": pos["pos_id"],
                "type": pos["type"],
                "rollout": rollout,
                "seed": seed,
                "iter": k,
                "move": best.move,
                "correct": int(is_correct),
                "keeps_win": kw,
                "correct_expanded": int(top is not None),
                "n_correct": top.N if top else 0,
                "wn_correct": round(top.W / top.N, 4) if top else "",
                "n_chosen": best.N,
                "root_children": len(root.children),
                "time_s": round(dt, 4),
            }
        )
    return rows


def choice_path(quick: bool, raw_dir: Path = RAW_DIR) -> Path:
    return raw_dir / f"{prefix(quick)}choice.csv"


def run_choice(quick: bool, workers: int, raw_dir: Path = RAW_DIR) -> None:
    """Mỗi (thế, rollout, seed) một task; ghi khi xong; chạy lại bỏ qua task đã đủ checkpoint."""
    path = choice_path(quick, raw_dir)
    done: dict[tuple[str, str, str], int] = {}
    if path.exists():
        for r in read_rows(path):
            key = (r["pos_id"], r["rollout"], r["seed"])
            done[key] = done.get(key, 0) + 1
    seeds = range(QUICK_SEEDS if quick else N_SEEDS)
    tasks = [
        (p, r, s)
        for p in load_positions(quick, raw_dir)
        if p["type"] in TYPES
        for r in ROLLOUTS
        for s in seeds
        if done.get((p["pos_id"], r, str(s)), 0) < len(CHECKPOINTS)
    ]
    commit, dirty = git_info()
    meta = {"git_commit": commit, "git_dirty": int(dirty)}
    t0 = time.perf_counter()
    print(f"[choice] {len(tasks)} task ({len(done)} đã có), {workers} worker")

    def write(rows: list[dict[str, Any]]) -> None:
        for row in rows:
            _append_csv(path, CHOICE_COLUMNS, {**row, **meta})

    if workers <= 1:
        for t in tasks:
            write(choice_task(*t))
    else:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            pending = {ex.submit(choice_task, *t) for t in tasks}
            n_done = 0
            while pending:
                fin, pending = wait(pending, return_when=FIRST_COMPLETED)
                for f in fin:
                    write(f.result())
                    n_done += 1
                if n_done % 50 == 0 or not pending:
                    print(f"  {n_done}/{len(tasks)} ({time.perf_counter() - t0:.0f} s)")
    print(f"[choice] xong {time.perf_counter() - t0:.1f} s")


# ---------------------------------------------------------------- (b) win rate


@dataclass(frozen=True)
class MatchPoint:
    part: str  # mref | self | greedy
    iters: int
    spec_a: AgentSpec  # bản tắt
    spec_b: AgentSpec
    on_a: AgentSpec | None  # bản bật cùng đối thủ (so cặp); None với self
    on_path: str | None  # file E3/E5 có thể tái dùng cho bản bật


def match_points() -> list[MatchPoint]:
    out = [
        MatchPoint(
            "mref",
            MREF_ITER,
            spec_off("rand", MREF_ITER),
            MREF,
            mcts_spec("rand", iterations=MREF_ITER),
            str(RAW_DIR / f"e5_mref_rand_i{MREF_ITER}.csv"),
        )
    ]
    for it in SELF_ITERS:
        out.append(
            MatchPoint(
                "self", it, spec_off("h300", it), mcts_spec("h300", iterations=it), None, None
            )
        )
    for it in GREEDY_ITERS:
        out.append(
            MatchPoint(
                "greedy",
                it,
                spec_off("h300", it),
                GREEDY,
                mcts_spec("h300", iterations=it),
                str(RAW_DIR / f"e3_greedy_c1.4_i{it}.csv"),
            )
        )
    return out


def match_raw(part: str, label_a: str, quick: bool, raw_dir: Path = RAW_DIR) -> Path:
    return raw_dir / f"{prefix(quick)}{part}_{label_a}.csv"


def on_source(pt: MatchPoint, quick: bool, raw_dir: Path = RAW_DIR) -> tuple[str, Path, str]:
    """(source, file, lý do) của bản bật: 'e3'/'e5' nếu tái dùng được, ngược lại 'e6'."""
    assert pt.on_a is not None
    if pt.on_path is not None:
        ok, reason = e3_reusable(pt.on_path, pt.on_a, pt.spec_b, N_PAIRS)
        if ok:
            return Path(pt.on_path).name[:2], Path(pt.on_path), reason
    else:
        reason = "không có file tái dùng"
    return "e6", match_raw(pt.part, pt.on_a.name, quick, raw_dir), reason


RUNINFO_COLUMNS = ["step", "part", "iters", "label_a", "label_b", "role", "source", "workers",
                   "n_pairs", "cpu", "logical_cpus", "power", "battery_pct", "started", "finished",
                   "wall_s", "git_commit", "git_dirty", "note"]  # fmt: skip


def power_status() -> tuple[str, int | str]:
    """('AC' | 'battery' | 'unknown', % pin) qua `GetSystemPowerStatus` (Windows)."""
    try:
        import ctypes

        class _S(ctypes.Structure):
            _fields_ = [("ac", ctypes.c_byte), ("flag", ctypes.c_byte), ("pct", ctypes.c_byte),
                        ("saver", ctypes.c_byte), ("life", ctypes.c_ulong),
                        ("full", ctypes.c_ulong)]  # fmt: skip

        st = _S()
        if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(st)):  # type: ignore[attr-defined]
            return "unknown", ""
        pct = st.pct if 0 <= st.pct <= 100 else ""
        return {1: "AC", 0: "battery"}.get(st.ac, "unknown"), pct
    except Exception:  # noqa: BLE001 — không phải Windows
        return "unknown", ""


def log_run(step: str, quick: bool, started: str, t0: float, raw_dir: Path = RAW_DIR,
            **fields: Any) -> None:  # fmt: skip
    """Ghi 1 dòng `e6_runinfo.csv` cho mọi bước (D-21: kèm trạng thái nguồn điện)."""
    commit, dirty = git_info()
    power, pct = power_status()
    _append_csv(
        raw_dir / f"{prefix(quick)}runinfo.csv",
        RUNINFO_COLUMNS,
        {
            "step": step,
            "cpu": cpu_name(),
            "logical_cpus": os.cpu_count(),
            "power": power,
            "battery_pct": pct,
            "started": started,
            "finished": datetime.now().isoformat(timespec="seconds"),
            "wall_s": round(time.perf_counter() - t0, 1),
            "git_commit": commit,
            "git_dirty": int(dirty),
            **fields,
        },
    )


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _run_one(
    path: Path,
    spec_a: AgentSpec,
    spec_b: AgentSpec,
    pt: MatchPoint,
    role: str,
    quick: bool,
    workers: int,
    allow: bool,
    raw_dir: Path,
) -> None:
    started = datetime.now().isoformat(timespec="seconds")
    t0 = time.perf_counter()
    n_pairs = QUICK_PAIRS if quick else N_PAIRS
    rows = run_match(
        path, GAME15, spec_a, spec_b, n_pairs, workers=workers, allow_code_change=allow
    )
    s = next(x for x in summarize(rows) if x["split"] == "all")
    log_run(
        "match", quick, started, t0, raw_dir,
        part=pt.part, iters=pt.iters, label_a=spec_a.name, label_b=spec_b.name, role=role,
        source="e6", workers=workers, n_pairs=n_pairs,
    )  # fmt: skip
    print(
        f"[match] {spec_a.name} vs {spec_b.name}: W/D/L {s['wins']}/{s['draws']}/{s['losses']} "
        f"(n={s['n']}, distinct={s['distinct_games']}), {time.perf_counter() - t0:.1f} s"
    )


def run_matches(quick: bool, workers: int, allow: bool, raw_dir: Path = RAW_DIR) -> None:
    for pt in match_points():
        _run_one(
            match_raw(pt.part, pt.spec_a.name, quick, raw_dir),
            pt.spec_a, pt.spec_b, pt, "off", quick, workers, allow, raw_dir,
        )  # fmt: skip
        if pt.on_a is None:
            continue
        src, path, reason = on_source(pt, quick, raw_dir)
        if src == "e6":
            print(f"[match] bản bật {pt.on_a.name} không tái dùng được ({reason}) → chạy")
            _run_one(path, pt.on_a, pt.spec_b, pt, "on", quick, workers, allow, raw_dir)
        else:
            print(f"[match] bản bật {pt.on_a.name}: tái dùng {src} — {reason}")


# ---------------------------------------------------------------- bench tốc độ (D-21)

BENCH_COLUMNS = ["rollout", "plies", "seed", "iterations", "agent_time", "iter_per_s",
                 "e5_iter_per_s", "speed_vs_e5", "power"]  # fmt: skip


def run_bench(quick: bool, table_dir: Path = TABLE_DIR) -> float:
    """Bench ngắn đơn luồng (1 s/thế, thế 8/16/24 quân, seed 0, rand + h300) bằng
    `e5_rollout.bench`; so với cùng (rollout, thế, seed) trong `e5_bench.csv` → `speed_vs_e5`.
    Trả trung vị tỷ lệ."""
    from gameai.experiments.e5_rollout import bench

    power, _ = power_status()
    rows = bench(seconds=1.0, plies=BENCH_PLIES, seeds=BENCH_SEEDS, path=None)
    ref_path = table_dir / "e5_bench.csv"
    ref = {}
    if ref_path.exists():
        for r in read_rows(ref_path):
            ref[(r["rollout"], r["plies"], r["seed"])] = float(r["iter_per_s"])
    ratios = []
    for r in rows:
        e5 = ref.get((r["rollout"], str(r["plies"]), str(r["seed"])))
        r["e5_iter_per_s"] = e5 if e5 is not None else ""
        r["speed_vs_e5"] = round(r["iter_per_s"] / e5, 3) if e5 else ""
        r["power"] = power
        if e5:
            ratios.append(r["iter_per_s"] / e5)
    _write(table_dir / f"{prefix(quick)}bench.csv", BENCH_COLUMNS, rows)
    med = statistics.median(ratios) if ratios else math.nan
    detail = ", ".join(f"{x:.2f}" for x in ratios)
    print(f"[bench] nguồn {power}; tốc độ / e5_bench: trung vị {med:.2f} ({detail})")
    return med


# ---------------------------------------------------------------- (c) chi phí: microbench

COST_COLUMNS = ["pos_id", "type", "phase", "n_candidates", "tactic", "check_ms", "rand1000_ms",
                "h300_1000_ms", "overhead_rand", "overhead_h300"]  # fmt: skip


def run_cost(quick: bool, raw_dir: Path = RAW_DIR, table_dir: Path = TABLE_DIR) -> float:
    """Đơn luồng: thời gian `_tactics` (trung vị CHECK_REPS lần) mọi thế; thế yên tĩnh đo thêm MCTS
    1000 iter tắt tactics (rand, h300; 1 lần, seed 0) → overhead = check / search."""
    power, _ = power_status()
    if power != "AC":
        print(f"[cost] BỎ QUA: nguồn = {power}; D-21 chỉ đo phần (c) khi cắm sạc")
        return math.nan
    t_all = time.perf_counter()
    reps = 1 if quick else CHECK_REPS
    rows = []
    for p in load_positions(quick, raw_dir):
        g = position_game(p)
        agent = MCTSAgent(iterations=1, check_tactics=True)
        ts = []
        tactic = 0
        for _ in range(reps):
            t0 = time.perf_counter()
            _, tactic, _ = agent._tactics(g)
            ts.append(time.perf_counter() - t0)
        row: dict[str, Any] = {
            "pos_id": p["pos_id"],
            "type": p["type"],
            "phase": p["phase"],
            "n_candidates": p["n_candidates"],
            "tactic": tactic,
            "check_ms": round(1000 * statistics.median(ts), 3),
        }
        if p["type"] == "quiet":
            for r, col in (("rand", "rand1000_ms"), ("h300", "h300_1000_ms")):
                a = make_agent(spec_off(r, 1000), 0)
                t0 = time.perf_counter()
                a.select_move(g)
                row[col] = round(1000 * (time.perf_counter() - t0), 2)
            row["overhead_rand"] = round(row["check_ms"] / row["rand1000_ms"], 4)
            row["overhead_h300"] = round(row["check_ms"] / row["h300_1000_ms"], 4)
        rows.append(row)
    _write(table_dir / f"{prefix(quick)}cost_check.csv", COST_COLUMNS, rows)
    dt = time.perf_counter() - t_all
    print(f"[cost] {len(rows)} thế, {dt:.1f} s")
    return dt


# ---------------------------------------------------------------- bảng


def _boot_ci(
    by_pos: dict[str, tuple[int, int]], n_boot: int = BOOT_N, seed: int = BOOT_SEED
) -> tuple[float, float]:
    """Bootstrap theo cụm thế: lấy lại thế có hoàn lại, tỷ lệ = Σ đúng / Σ lần;
    percentile 2,5–97,5."""
    ids = sorted(by_pos)
    if not ids:
        return math.nan, math.nan
    rng = random.Random(seed)
    stats = []
    for _ in range(n_boot):
        k = n = 0
        for _ in ids:
            a, b = by_pos[ids[rng.randrange(len(ids))]]
            k += a
            n += b
        stats.append(k / n)
    stats.sort()
    return stats[int(0.025 * n_boot)], stats[min(n_boot - 1, int(0.975 * n_boot))]


CHOICE_TABLE_COLUMNS = ["type", "rollout", "iter", "stratum", "weighting", "n_pos", "n_runs",
                        "correct", "correct_rate", "wilson_lo", "wilson_hi", "boot_lo", "boot_hi",
                        "pos_all_correct", "pos_none_correct", "nolose_rate", "nolose_wilson_lo",
                        "nolose_wilson_hi", "nolose_boot_lo", "nolose_boot_hi",
                        "expanded_rate", "median_n_correct"]  # fmt: skip
MINE_STRATA = (("mine=1", 1, 1), ("mine>=2", 2, None))  # loại 2, phân tầng offline theo n_mine


def _by_pos(rows: list[dict[str, Any]], key: str) -> dict[str, tuple[int, int]]:
    acc: dict[str, list[int]] = {}
    for r in rows:
        v = acc.setdefault(r["pos_id"], [0, 0])
        v[0] += int(r[key])
        v[1] += 1
    return {p: (v[0], v[1]) for p, v in acc.items()}


def _rate_block(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    by_pos = _by_pos(rows, key)
    k = sum(v[0] for v in by_pos.values())
    n = sum(v[1] for v in by_pos.values())
    lo, hi = wilson(k, n)
    blo, bhi = _boot_ci(by_pos)
    return {
        "k": k,
        "n": n,
        "rate": k / n if n else math.nan,
        "wlo": lo,
        "whi": hi,
        "blo": blo,
        "bhi": bhi,
        "all": sum(v[0] == v[1] for v in by_pos.values()),
        "none": sum(v[0] == 0 for v in by_pos.values()),
    }


def _weighted_block(
    rows: list[dict[str, Any]],
    strat: dict[str, str],
    weights: dict[str, float],
    key: str,
    n_boot: int = BOOT_N,
    seed: int = BOOT_SEED,
) -> dict[str, Any]:
    """Tỷ lệ chung = Σ w_s · tỷ lệ tầng s (w = trọng số tự nhiên trong pool, chuẩn hóa lại trên các
    tầng có dữ liệu). Khoảng: bootstrap phân tầng (lấy lại thế trong từng tầng, kết hợp cùng w)."""
    groups: dict[str, dict[str, tuple[int, int]]] = {}
    for name, _, _ in STRATA:
        bp = _by_pos([r for r in rows if strat.get(r["pos_id"]) == name], key)
        if bp:
            groups[name] = bp
    wsum = sum(weights.get(n, 0.0) for n in groups)
    if not groups or wsum <= 0:
        return {"rate": math.nan, "blo": math.nan, "bhi": math.nan}
    w = {n: weights.get(n, 0.0) / wsum for n in groups}

    def rate(g: dict[str, tuple[int, int]]) -> float:
        return sum(v[0] for v in g.values()) / sum(v[1] for v in g.values())

    est = sum(w[n] * rate(g) for n, g in groups.items())
    rng = random.Random(seed)
    stats = []
    for _ in range(n_boot):
        tot = 0.0
        for n in sorted(groups):
            ids = sorted(groups[n])
            k = m = 0
            for _ in ids:
                a, b = groups[n][ids[rng.randrange(len(ids))]]
                k += a
                m += b
            tot += w[n] * k / m
        stats.append(tot)
    stats.sort()
    return {
        "rate": est,
        "blo": stats[int(0.025 * n_boot)],
        "bhi": stats[min(n_boot - 1, int(0.975 * n_boot))],
    }


def _choice_base(
    choice_rows: list[dict[str, str]], sanity_rows: list[dict[str, str]], t: str, roll: str, it: Any
) -> list[dict[str, Any]]:
    if roll == "on":
        return [
            {"pos_id": r["pos_id"], "correct": r["ok"], "nolose": r["ok"]}
            for r in sanity_rows
            if r["type"] == t
        ]
    return [
        {**r, "nolose": int(r["correct"] == "1" or r["keeps_win"] == "1")}
        for r in choice_rows
        if r["type"] == t and r["rollout"] == roll and int(r["iter"]) == it
    ]


def choice_table(
    choice_rows: list[dict[str, str]],
    positions: list[dict[str, str]],
    sanity_rows: list[dict[str, str]],
    weights: dict[str, dict[str, float]] | None = None,
) -> list[dict[str, Any]]:
    """Mỗi (loại, rollout, iter): dòng `all` (trọng số tự nhiên của tầng trong pool; không có
    `weights` → gộp mẫu), `sample` (gộp mẫu, không trọng số), từng tầng `n_candidates`, và (loại 2)
    tầng `n_mine`. `rollout = on` lấy từ sanity."""
    weights = weights or {}
    strat = {p["pos_id"]: p["stratum"] for p in positions}
    mine = {p["pos_id"]: int(p["n_mine"]) for p in positions if p.get("n_mine")}
    out = []
    for t in TYPES:
        for roll in (*ROLLOUTS, "on"):
            iters: tuple[Any, ...] = CHECKPOINTS if roll != "on" else ("",)
            for it in iters:
                base = _choice_base(choice_rows, sanity_rows, t, roll, it)
                groups: list[tuple[str, list[dict[str, Any]]]] = [("all", base), ("sample", base)]
                for n, _, _ in STRATA:
                    groups.append((n, [r for r in base if strat.get(r["pos_id"]) == n]))
                if t == "win":
                    for n, lo, hi in MINE_STRATA:
                        sel = [
                            r
                            for r in base
                            if mine.get(r["pos_id"], 0) >= lo
                            and (hi is None or mine.get(r["pos_id"], 0) <= hi)
                        ]
                        groups.append((n, sel))
                for s, rows in groups:
                    if rows:
                        out.append(_choice_row(t, roll, it, s, rows, strat, weights))
    return out


def _choice_row(
    t: str,
    roll: str,
    it: Any,
    s: str,
    rows: list[dict[str, Any]],
    strat: dict[str, str],
    weights: dict[str, dict[str, float]],
) -> dict[str, Any]:
    c = _rate_block(rows, "correct")
    weighted = s == "all" and t in weights
    row: dict[str, Any] = {
        "type": t,
        "rollout": roll,
        "iter": it,
        "stratum": s,
        "weighting": "pool" if weighted else "sample",
        "n_pos": len({r["pos_id"] for r in rows}),
        "n_runs": c["n"],
        "correct": c["k"],
        "correct_rate": c["rate"],
        "wilson_lo": c["wlo"],
        "wilson_hi": c["whi"],
        "boot_lo": c["blo"],
        "boot_hi": c["bhi"],
        "pos_all_correct": c["all"],
        "pos_none_correct": c["none"],
    }
    if weighted:  # Wilson không áp dụng cho tỷ lệ có trọng số
        wb = _weighted_block(rows, strat, weights[t], "correct")
        row.update(
            correct_rate=wb["rate"],
            boot_lo=wb["blo"],
            boot_hi=wb["bhi"],
            wilson_lo="",
            wilson_hi="",
        )
    if t == "win":
        nl = _rate_block(rows, "nolose")
        row.update(
            nolose_rate=nl["rate"],
            nolose_wilson_lo=nl["wlo"],
            nolose_wilson_hi=nl["whi"],
            nolose_boot_lo=nl["blo"],
            nolose_boot_hi=nl["bhi"],
        )
        if weighted:
            wb = _weighted_block(rows, strat, weights[t], "nolose")
            row.update(
                nolose_rate=wb["rate"],
                nolose_boot_lo=wb["blo"],
                nolose_boot_hi=wb["bhi"],
                nolose_wilson_lo="",
                nolose_wilson_hi="",
            )
    if roll != "on":
        row["expanded_rate"] = sum(r["correct_expanded"] == "1" for r in rows) / len(rows)
        row["median_n_correct"] = statistics.median(int(r["n_correct"]) for r in rows)
    return row


MATCH_COLUMNS = ["part", "iters", "tactics", "source", "raw", *SUMMARY_COLUMNS]
PAIRED_COLUMNS = ["part", "iters", "n", "mean_on", "mean_off", "diff", "paired_lo", "paired_hi",
                  "indep_lo", "indep_hi", "sd_diff"]  # fmt: skip
RATE_COLUMNS = ["part", "iters", "label", "tactics", "side", "source", "n_moves", "n_ply0",
                "t0", "t1", "t2", "t3", "pct_t1", "pct_t2", "pct_direct"]  # fmt: skip
TIME_COLUMNS = ["part", "iters", "label", "tactics", "side", "source", "n_moves",
                "mean_agent_time", "n_search", "mean_search_time", "n_direct",
                "mean_direct_time"]  # fmt: skip


def _load_match(path: Path, n_pairs: int) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    if not path.exists():
        return [], []
    rows = _keep_pairs(read_rows(path), n_pairs)
    ids = {r["game_id"] for r in rows}
    mp = moves_path_for(path)
    moves = [m for m in read_rows(mp) if m["game_id"] in ids] if mp.exists() else []
    return rows, moves


def _side_rows(
    pt: MatchPoint, label: str, tactics: str, side: str, src: str, moves: list[dict[str, str]]
) -> tuple[dict[str, Any], dict[str, Any]]:
    ms = [m for m in moves if m["side"] == side]
    ply0 = [m for m in ms if m["ply"] == "0"]  # bàn trống: 1 candidate → tactic 2 "giả"
    ms = [m for m in ms if m["ply"] != "0"]
    cnt = {t: sum(m["tactic"] == str(t) for m in ms) for t in range(4)}
    n = len(ms)
    rate = {
        "part": pt.part,
        "iters": pt.iters,
        "label": label,
        "tactics": tactics,
        "side": side,
        "source": src,
        "n_moves": n,
        "n_ply0": len(ply0),
        **{f"t{t}": cnt[t] for t in range(4)},
        "pct_t1": cnt[1] / n if n else math.nan,
        "pct_t2": cnt[2] / n if n else math.nan,
        "pct_direct": (cnt[1] + cnt[2]) / n if n else math.nan,
    }
    search = [float(m["agent_time"]) for m in ms if m["tactic"] not in ("1", "2")]
    direct = [float(m["agent_time"]) for m in ms if m["tactic"] in ("1", "2")]
    allt = [float(m["agent_time"]) for m in ms]
    tm = {
        "part": pt.part,
        "iters": pt.iters,
        "label": label,
        "tactics": tactics,
        "side": side,
        "source": src,
        "n_moves": n,
        "mean_agent_time": statistics.fmean(allt) if allt else math.nan,
        "n_search": len(search),
        "mean_search_time": statistics.fmean(search) if search else math.nan,
        "n_direct": len(direct),
        "mean_direct_time": statistics.fmean(direct) if direct else math.nan,
    }
    return rate, tm


def build_tables(
    quick: bool, raw_dir: Path = RAW_DIR, table_dir: Path = TABLE_DIR
) -> dict[str, list[dict[str, Any]]]:
    p = prefix(quick)
    out: dict[str, list[dict[str, Any]]] = {}
    pos = load_positions(quick, raw_dir) if positions_path(quick, raw_dir).exists() else []
    cp = choice_path(quick, raw_dir)
    sp = table_dir / f"{p}sanity.csv"
    if cp.exists():
        out["choice"] = choice_table(
            read_rows(cp),
            pos,
            read_rows(sp) if sp.exists() else [],
            pool_weights(quick, table_dir),
        )
        _write(table_dir / f"{p}choice.csv", CHOICE_TABLE_COLUMNS, out["choice"])
    n_pairs = QUICK_PAIRS if quick else N_PAIRS
    match, paired, rates, times = [], [], [], []
    for pt in match_points():
        off_path = match_raw(pt.part, pt.spec_a.name, quick, raw_dir)
        off_rows, off_moves = _load_match(off_path, n_pairs)
        if not off_rows:
            continue
        for s in summarize(off_rows, off_moves):
            match.append({"part": pt.part, "iters": pt.iters, "tactics": "off", "source": "e6",
                          "raw": off_path.name, **s})  # fmt: skip
        r, t = _side_rows(pt, pt.spec_a.name, "off", "A", "e6", off_moves)
        rates.append(r)
        times.append(t)
        if pt.on_a is None:  # self: B = bản bật trong cùng file
            r, t = _side_rows(pt, pt.spec_b.name, "on", "B", "e6", off_moves)
            rates.append(r)
            times.append(t)
            continue
        src, on_path, _ = on_source(pt, quick, raw_dir)
        on_rows, on_moves = _load_match(on_path, n_pairs)
        if not on_rows:
            continue
        for s in summarize(on_rows, on_moves):
            match.append({"part": pt.part, "iters": pt.iters, "tactics": "on", "source": src,
                          "raw": on_path.name, **s})  # fmt: skip
        r, t = _side_rows(pt, pt.on_a.name, "on", "A", src, on_moves)
        rates.append(r)
        times.append(t)
        d = paired_diff(on_rows, off_rows)
        paired.append(
            {
                "part": pt.part,
                "iters": pt.iters,
                "n": d["n"],
                "mean_on": d["mean_h300"],
                "mean_off": d["mean_rand"],
                **{
                    k: d[k]
                    for k in ("diff", "paired_lo", "paired_hi", "indep_lo", "indep_hi", "sd_diff")
                },
            }  # fmt: skip
        )
    if match:
        _write(table_dir / f"{p}match.csv", MATCH_COLUMNS, match)
        _write(table_dir / f"{p}paired.csv", PAIRED_COLUMNS, paired)
        _write(table_dir / f"{p}tactic_rate.csv", RATE_COLUMNS, rates)
        _write(table_dir / f"{p}time.csv", TIME_COLUMNS, times)
    out.update(match=match, paired=paired, tactic_rate=rates, time=times)
    return out


# ---------------------------------------------------------------- ước tính full

ESTIMATE_COLUMNS = ["part", "units", "sec_per_unit", "seq_minutes", "est_wall_minutes", "note"]


def estimate_full(
    positions_s: float,
    cost_s: float,
    raw_dir: Path = RAW_DIR,
    table_dir: Path = TABLE_DIR,
    workers: int = 4,
) -> list[dict[str, Any]]:
    """Ngoại suy từ quick. choice: giây/task (tới 5000 iter) theo rollout × số task full;
    match: giây/ván đo (a_time_sum + b_time_sum) × 50; cost: theo số thế."""
    sp = SPEEDUP_4W if workers >= 4 else max(1.0, 0.9 * workers)
    out = [{"part": "positions", "units": 1, "sec_per_unit": round(positions_s, 1),
            "seq_minutes": round(positions_s / 60, 1),
            "est_wall_minutes": round(positions_s / 60, 1), "note": "đơn luồng"}]  # fmt: skip
    rows = read_rows(choice_path(True, raw_dir)) if choice_path(True, raw_dir).exists() else []
    n_full = N_PER_STRATUM * len(STRATA) * len(TYPES) * N_SEEDS
    for roll in ROLLOUTS:
        ts = [
            float(r["time_s"])
            for r in rows
            if r["rollout"] == roll and int(r["iter"]) == CHECKPOINTS[-1]
        ]
        sec = statistics.fmean(ts) if ts else math.nan
        seq = n_full * sec
        out.append({"part": f"choice {roll}", "units": n_full, "sec_per_unit": round(sec, 2),
                    "seq_minutes": round(seq / 60, 1),
                    "est_wall_minutes": round(seq / sp / 60, 1),
                    "note": f"{len(ts)} task quick"})  # fmt: skip
    for pt in match_points():
        for role, spec in (("off", pt.spec_a), ("on", pt.on_a)):
            if spec is None:
                continue
            path = match_raw(pt.part, spec.name, True, raw_dir)
            if role == "on":
                src, _, reason = on_source(pt, True, raw_dir)
                if src != "e6":
                    out.append({"part": f"match {pt.part} {spec.name}", "units": 0,
                                "seq_minutes": 0, "est_wall_minutes": 0,
                                "note": f"tái dùng {src}"})  # fmt: skip
                    continue
            mr = read_rows(path) if path.exists() else []
            sec = (
                statistics.fmean(
                    sum(float(r[k]) for k in ("a_time_sum", "b_time_sum") if r.get(k)) for r in mr
                )
                if mr
                else math.nan
            )
            games = 2 * N_PAIRS
            seq = games * sec
            out.append({"part": f"match {pt.part} {spec.name}", "units": games,
                        "sec_per_unit": round(sec, 2), "seq_minutes": round(seq / 60, 1),
                        "est_wall_minutes": round((seq / sp + POOL_OVERHEAD_S) / 60, 1),
                        "note": f"{len(mr)} ván quick"})  # fmt: skip
    qp = load_positions(True, raw_dir)
    n_cost = len(TYPES) * len(STRATA) * N_PER_STRATUM + 3 * QUIET_PER_PHASE
    scale = n_cost / max(1, len(qp))
    seq = cost_s * scale * CHECK_REPS  # quick đo 1 lần; full 3 lần check (search chỉ 1 lần → trên)
    out.append({"part": "cost", "units": n_cost,
                "sec_per_unit": round(cost_s / max(1, len(qp)), 2),
                "seq_minutes": round(seq / 60, 1), "est_wall_minutes": round(seq / 60, 1),
                "note": "đơn luồng, cận trên"})  # fmt: skip
    tot = sum(
        fnum(r["est_wall_minutes"])
        for r in out
        if fnum(r["est_wall_minutes"]) == fnum(r["est_wall_minutes"])
    )
    out.append({"part": "total", "est_wall_minutes": round(tot, 1)})
    _write(table_dir / "e6quick_estimate.csv", ESTIMATE_COLUMNS, out)
    for r in out:
        print(f"[estimate] {r['part']}: ~{r['est_wall_minutes']} phút  {r.get('note', '')}")
    return out


# ---------------------------------------------------------------- hình

COLORS = {"rand": "#2a78d6", "h300": "#eb6834"}  # như E5 (đã kiểm ở E3)
MARKERS = {"rand": "o", "h300": "s"}
NAMES = {"rand": "rollout random, tắt tactics", "h300": "rollout h300, tắt tactics"}


def make_figures(quick: bool, table_dir: Path = TABLE_DIR, fig_dir: Path = FIG_DIR) -> list[Path]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    p = prefix(quick)
    out: list[Path] = []
    cpath = table_dir / f"{p}choice.csv"
    if cpath.exists():
        rows = [r for r in read_rows(cpath) if r["stratum"] == "all"]
        fig, axes = plt.subplots(1, 2, figsize=(11, 5.8), facecolor=SURFACE, sharey=True)
        titles = {"block": "Loại 1 — phải chặn four (1 ô chặn)", "win": "Loại 2 — có thắng ngay"}
        for ax, t in zip(axes, TYPES, strict=True):
            for i, roll in enumerate(ROLLOUTS):
                pts = sorted(
                    (int(r["iter"]), fnum(r["correct_rate"]), fnum(r["boot_lo"]),
                     fnum(r["boot_hi"]),
                     fnum(r["nolose_rate"]))
                    for r in rows
                    if r["type"] == t and r["rollout"] == roll
                )  # fmt: skip
                if not pts:
                    continue
                shift = 10 ** (0.02 * (i - 0.5))
                xs = [q[0] * shift for q in pts]
                err = [[max(0.0, q[1] - q[2]) for q in pts], [max(0.0, q[3] - q[1]) for q in pts]]
                ax.errorbar(xs, [q[1] for q in pts], yerr=err, color=COLORS[roll],
                            marker=MARKERS[roll], markersize=6, linewidth=2, elinewidth=1.2,
                            capsize=0, markeredgecolor=SURFACE, markeredgewidth=1,
                            label=NAMES[roll] + " — chọn đúng (chặn / thắng ngay)")  # fmt: skip
                if t == "win":
                    ax.plot(xs, [q[4] for q in pts], color=COLORS[roll], linestyle="--",
                            linewidth=1.5, marker=MARKERS[roll], markersize=5,
                            markerfacecolor=SURFACE,
                            label=NAMES[roll] + " — không mất thắng")  # fmt: skip
            ax.axhline(1.0, color=INK, linestyle=":", linewidth=1.2, label="bật tactics (sanity)")
            ax.set_xscale("log")
            ax.set_xticks(CHECKPOINTS)
            ax.set_xticklabels([str(c) for c in CHECKPOINTS])
            ax.set_ylim(0.0, 1.05)
            ratio_axis(ax)
            ax.set_xlabel("iteration / nước", color=INK2)
            ax.set_title(titles[t], color=INK, fontsize=10, loc="left")
            _style(ax)
        axes[0].set_ylabel("tỷ lệ chọn đúng", color=INK2)
        # legend chung dưới hình, 2 cột theo rollout (trái random, phải h300): tiêu đề cột rồi
        # "chọn đúng", "không mất thắng" (chỉ panel loại 2 có); "bật tactics" riêng ở cuối
        h1, l1 = axes[1].get_legend_handles_labels()
        by = dict(zip(l1, h1, strict=True))
        col: list[tuple[Any, str]] = []
        for roll in ROLLOUTS:
            col.append((Line2D([], [], linestyle="none"), NAMES[roll]))
            for key, text in (("chọn đúng (chặn / thắng ngay)", "chọn đúng (chặn / thắng ngay)"),
                              ("không mất thắng", "không mất thắng")):  # fmt: skip
                col.append((by[f"{NAMES[roll]} — {key}"], text))
        fig.legend(*zip(*col, strict=True), loc="lower left", bbox_to_anchor=(0.01, 0.085),
                   ncol=len(ROLLOUTS), frameon=False, fontsize=8, labelcolor=INK)  # fmt: skip
        fig.legend([by["bật tactics (sanity)"]], ["bật tactics (sanity)"], loc="lower left",
                   bbox_to_anchor=(0.01, 0.04), frameon=False, fontsize=8,
                   labelcolor=INK)  # fmt: skip
        fig.suptitle("E6 — MCTS tắt check_tactics trên bộ thế cờ thật 15×15", color=INK,
                     fontsize=12, x=0.01, ha="left")  # fmt: skip
        fig.text(0.01, 0.005, "Tỷ lệ chung có trọng số tầng n_candidates theo pool (D-21). Thanh "
                 "lỗi: bootstrap phân tầng 95 % theo cụm thế. Từng tầng: e6_choice.csv.",
                 color=INK2, fontsize=8, ha="left", va="bottom")  # fmt: skip
        vn_figure(fig)  # tick/nhãn số kiểu VN (P7.2)
        fig.tight_layout(rect=(0, 0.24, 1, 0.95))
        path = fig_dir / f"{p}choice.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=150, facecolor=SURFACE)
        plt.close(fig)
        out.append(path)
    mpath = table_dir / f"{p}match.csv"
    if mpath.exists():
        rows = [r for r in read_rows(mpath) if r["split"] == "all"]
        fig, axes = plt.subplots(1, 2, figsize=(11, 4.0), facecolor=SURFACE,
                                 gridspec_kw={"width_ratios": [3, 1.3]})  # fmt: skip
        ax = axes[0]
        cats = [("mref", MREF_ITER), *(("greedy", it) for it in GREEDY_ITERS)]
        for j, (tac, col, mk) in enumerate((("off", "#2a78d6", "o"), ("on", "#eb6834", "s"))):
            xs, ys, lo, hi = [], [], [], []
            for i, (part, it) in enumerate(cats):
                r = next((x for x in rows if x["part"] == part and int(x["iters"]) == it
                          and x["tactics"] == tac), None)  # fmt: skip
                if r is None:
                    continue
                xs.append(i + (j - 0.5) * 0.18)
                ys.append(fnum(r["win_rate"]))
                lo.append(max(0.0, ys[-1] - fnum(r["win_lo"])))
                hi.append(max(0.0, fnum(r["win_hi"]) - ys[-1]))
            ax.errorbar(xs, ys, yerr=[lo, hi], color=col, marker=mk, linestyle="none",
                        markersize=7, elinewidth=1.2, markeredgecolor=SURFACE,
                        label=f"tactics {'tắt' if tac == 'off' else 'bật'}")  # fmt: skip
        ax.set_xticks(range(len(cats)))
        ax.set_xticklabels(["rand 1000 vs mref", "h300 1000 vs Greedy", "h300 5000 vs Greedy"])
        ax.set_ylim(0.0, 1.05)
        ratio_axis(ax)
        ax.set_ylabel("tỷ lệ thắng (của MCTS)", color=INK2)
        ax.set_title("Cùng đối thủ, cùng seed: tắt vs bật", color=INK, fontsize=10, loc="left")
        ax.legend(frameon=False, fontsize=8, labelcolor=INK)
        _style(ax)
        ax = axes[1]
        xs, ys, lo, hi = [], [], [], []
        for i, it in enumerate(SELF_ITERS):
            r = next((x for x in rows if x["part"] == "self" and int(x["iters"]) == it), None)
            if r is None:
                continue
            # tỷ lệ thắng của bản BẬT (B) = tỷ lệ thua của A
            n = int(r["n"])
            k = int(r["losses"])
            w_lo, w_hi = wilson(k, n)
            xs.append(i)
            ys.append(k / n)
            lo.append(max(0.0, ys[-1] - w_lo))
            hi.append(max(0.0, w_hi - ys[-1]))
        ax.errorbar(xs, ys, yerr=[lo, hi], color="#eb6834", marker="s", linestyle="none",
                    markersize=7, elinewidth=1.2, markeredgecolor=SURFACE,
                    label="h300 bật thắng h300 tắt")  # fmt: skip
        ax.axhline(0.5, color=INK2, linestyle=":", linewidth=1)
        ax.set_xticks(range(len(SELF_ITERS)))
        ax.set_xticklabels([f"{it} iter" for it in SELF_ITERS])
        ax.set_xlim(-0.5, len(SELF_ITERS) - 0.5)
        ax.set_ylim(0.0, 1.05)
        ratio_axis(ax)
        ax.set_title("Đối đầu trực tiếp h300 bật vs tắt", color=INK, fontsize=10, loc="left")
        ax.legend(frameon=False, fontsize=8, labelcolor=INK)
        _style(ax)
        fig.suptitle("E6 — tỷ lệ thắng khi tắt / bật check_tactics", color=INK, fontsize=12,
                     x=0.01, ha="left")  # fmt: skip
        fig.text(0.01, 0.005, "Thanh lỗi: Wilson 95 % (độc lập từng điểm); so cặp: e6_paired.csv.",
                 color=INK2, fontsize=8, ha="left", va="bottom")  # fmt: skip
        vn_figure(fig)  # tick/nhãn số kiểu VN (P7.2)
        fig.tight_layout(rect=(0, 0.03, 1, 0.95))
        path = fig_dir / f"{p}match.png"
        fig.savefig(path, dpi=150, facecolor=SURFACE)
        plt.close(fig)
        out.append(path)
    return out


# ---------------------------------------------------------------- main


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("step", choices=STEPS)
    add_runner_args(ap)
    args = ap.parse_args()
    q, w, allow = args.quick, args.workers, args.allow_code_change
    t0 = time.perf_counter()
    pos_s = cost_s = math.nan

    def step(name: str, fn: Any, *a: Any, **fields: Any) -> Any:
        started, ts = _now(), time.perf_counter()
        res = fn(*a)
        log_run(name, q, started, ts, workers=fields.get("workers", 1), note=fields.get("note", ""))
        return res

    if args.step in ("bench", "all"):
        step("bench", run_bench, q)
    if args.step in ("positions", "all"):
        pos_s = step("positions", run_positions, q)
    if args.step in ("sanity", "all"):
        if not step("sanity", run_sanity, q):
            sys.exit("sanity tactics bật < 100 % → dừng (D-21), báo An")
    if args.step in ("choice", "all"):
        step("choice", run_choice, q, w, workers=w)
    if args.step in ("match", "all"):
        run_matches(q, w, allow)
    if args.step in ("cost", "all"):
        cost_s = step("cost", run_cost, q)
    build_tables(q)
    make_figures(q)
    if q and args.step == "all":
        estimate_full(pos_s, cost_s, workers=w)
    print(f"tổng {time.perf_counter() - t0:.1f} s")


if __name__ == "__main__":
    main()
