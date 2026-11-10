"""Runner thí nghiệm: chạy match song song, ghi CSV từng ván, resume, bảng tổng hợp (P4.1, D-13).

Script thí nghiệm phải gọi `run_match` bên trong `if __name__ == "__main__":` (Windows dùng spawn).
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import os
import subprocess
from collections.abc import Iterable, Sequence
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from pathlib import Path
from typing import Any

from gameai.agents.registry import AgentSpec, GameSpec, make_agent, make_game
from gameai.arena import ERROR_TERMINATIONS, MatchGame, game_id_for, match_tasks, play_seeded_game

DEFAULT_WORKERS = 4
_REPO_ROOT = Path(__file__).resolve().parents[2]

# Khóa stats được tổng hợp mỗi bên: (khóa, có mean không)
_SUM_KEYS = ("nodes", "iterations", "rollout_plies")
_SIDE_COLUMNS = (
    ["moves", "time_sum", "time_mean", "time_max"]
    + [f"{k}_{agg}" for k in _SUM_KEYS for agg in ("sum", "mean")]
    + ["max_depth_max", "cutoffs_sum", "tt_hits_sum", "tactic_moves"]
)
GAME_COLUMNS: list[str] = (
    [
        "game_id", "pair_seed", "a_is_x", "label_a", "label_b", "winner", "result_a",
        "termination", "error_side", "error", "n_moves", "opening", "moves",
    ]
    + [f"{s}_{c}" for s in ("a", "b") for c in _SIDE_COLUMNS]
    + [
        "seed_a", "seed_b", "spec_a", "spec_b", "game_spec", "max_moves", "random_opening",
        "base_seed", "config_hash", "git_commit", "git_dirty", "workers", "finished_at",
    ]
)  # fmt: skip
_MOVE_STATS = ("nodes", "iterations", "value", "cutoffs", "tt_hits", "max_depth",
               "rollout_plies", "tactic")  # fmt: skip
MOVE_COLUMNS: list[str] = ["game_id", "ply", "side", "player", "move", "time", "agent_time",
                           *_MOVE_STATS]  # fmt: skip
SUMMARY_COLUMNS: list[str] = [
    "label_a", "label_b", "split", "n", "wins", "draws", "losses",
    "win_rate", "win_lo", "win_hi", "nonloss_rate", "nonloss_lo", "nonloss_hi", "score",
    "distinct_games", "mean_moves", "errors", "a_errors", "b_errors", "max_moves_draws",
    "a_time_per_move", "b_time_per_move", "a_nodes_per_move", "b_nodes_per_move",
    "a_iterations_per_move", "b_iterations_per_move",
    "a_search_moves", "b_search_moves",
    "a_search_iterations_per_move", "b_search_iterations_per_move",
]  # fmt: skip


class ResumeError(ValueError):
    """File kết quả có sẵn không khớp với lần chạy hiện tại (header / config / commit)."""


# ---------------------------------------------------------------- tiện ích


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Khoảng tin cậy Wilson cho tỉ lệ k/n (mặc định 95%). n = 0 → (nan, nan)."""
    if n == 0:
        return math.nan, math.nan
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, center - half), min(1.0, center + half)


def git_info() -> tuple[str, bool]:
    """(commit HEAD, dirty). dirty = file đã track ngoài `results/` có thay đổi.

    Không gọi được git → ("unknown", False).
    """
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        diff = subprocess.run(
            ["git", "diff", "--quiet", "HEAD", "--", ".", ":(exclude)results"],
            cwd=_REPO_ROOT,
            capture_output=True,
        )
        return commit, diff.returncode != 0
    except (OSError, subprocess.CalledProcessError):
        return "unknown", False


def config_hash(
    game_spec: GameSpec,
    spec_a: AgentSpec,
    spec_b: AgentSpec,
    max_moves: int | None,
    random_opening: int,
    base_seed: int,
) -> str:
    """Băm cấu hình match (không gồm số ván → chạy thêm ván được)."""
    blob = json.dumps(
        {
            "game": game_spec.to_dict(),
            "a": spec_a.to_dict(),
            "b": spec_b.to_dict(),
            "max_moves": max_moves,
            "random_opening": random_opening,
            "base_seed": base_seed,
        },
        sort_keys=True,
    )
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def moves_path_for(out_path: str | Path) -> Path:
    """File moves đi kèm: `<stem>_moves.csv` cùng thư mục."""
    p = Path(out_path)
    return p.with_name(f"{p.stem}_moves{p.suffix}")


def read_rows(path: str | Path) -> list[dict[str, str]]:
    """Đọc CSV thành list dict (giá trị là chuỗi)."""
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _fmt(x: Any) -> str:
    if x is None:
        return ""
    if isinstance(x, bool):
        return "1" if x else "0"
    return str(x)


def _seq(moves: Iterable[Any]) -> str:
    return ";".join(_fmt(m) for m in moves)


# ---------------------------------------------------------------- record → dòng CSV


def _side_aggregates(mg: MatchGame, side: str) -> dict[str, Any]:
    ms = [m for m in mg.record.moves if m.side == side]
    out: dict[str, Any] = {"moves": len(ms)}
    times = [m.time for m in ms]
    out["time_sum"] = sum(times)
    out["time_mean"] = sum(times) / len(times) if times else None
    out["time_max"] = max(times) if times else None
    for k in _SUM_KEYS:
        vals = [m.stats[k] for m in ms if k in m.stats]
        s = sum(vals) if vals else None
        if vals and all(isinstance(v, int) for v in vals):
            s = int(s)
        out[f"{k}_sum"] = s
        out[f"{k}_mean"] = s / len(vals) if vals else None
    depth = [m.stats["max_depth"] for m in ms if "max_depth" in m.stats]
    out["max_depth_max"] = max(depth) if depth else None
    for k in ("cutoffs", "tt_hits"):
        vals = [m.stats[k] for m in ms if k in m.stats]
        out[f"{k}_sum"] = sum(vals) if vals else None
    tac = [m.stats["tactic"] for m in ms if "tactic" in m.stats]
    out["tactic_moves"] = sum(1 for t in tac if t) if tac else None
    return out


def game_row(mg: MatchGame, meta: dict[str, Any]) -> dict[str, str]:
    rec = mg.record
    row: dict[str, Any] = {
        "game_id": mg.game_id, "pair_seed": mg.pair_seed, "a_is_x": mg.a_is_x,
        "label_a": meta["label_a"], "label_b": meta["label_b"], "winner": rec.winner,
        "result_a": float(mg.result_a), "termination": rec.termination,
        "error_side": "" if rec.error_player is None
        else ("A" if rec.error_player == mg.a_player else "B"),
        "error": rec.error, "n_moves": rec.n_moves, "opening": _seq(rec.opening),
        "moves": _seq(rec.move_sequence), "seed_a": mg.seed_a, "seed_b": mg.seed_b,
        "finished_at": dt.datetime.now().isoformat(timespec="seconds"),
    }  # fmt: skip
    for side in ("A", "B"):
        for k, v in _side_aggregates(mg, side).items():
            row[f"{side.lower()}_{k}"] = v
    for k in (
        "spec_a",
        "spec_b",
        "game_spec",
        "max_moves",
        "random_opening",
        "base_seed",
        "config_hash",
        "git_commit",
        "git_dirty",
        "workers",
    ):
        row[k] = meta[k]
    return {c: _fmt(row.get(c)) for c in GAME_COLUMNS}


def move_rows(mg: MatchGame) -> list[dict[str, str]]:
    rows = []
    for m in mg.record.moves:
        r: dict[str, Any] = {"game_id": mg.game_id, "ply": m.ply, "side": m.side,
                             "player": m.player, "move": m.move, "time": m.time,
                             "agent_time": m.stats.get("time")}  # fmt: skip
        for k in _MOVE_STATS:
            r[k] = m.stats.get(k)
        rows.append({c: _fmt(r.get(c)) for c in MOVE_COLUMNS})
    return rows


# ---------------------------------------------------------------- file / resume


def _drop_partial_tail(path: Path) -> None:
    """Bỏ phần sau dòng xuống cuối cùng (dòng bị cắt dở khi chạy bị ngắt)."""
    data = path.read_bytes()
    if data and not data.endswith(b"\n"):
        cut = data.rfind(b"\n") + 1
        with open(path, "r+b") as f:
            f.truncate(cut)


def _load_existing(path: Path, columns: list[str]) -> list[dict[str, str]] | None:
    """Rows đã có (sau khi bỏ dòng cắt dở); None nếu chưa có file / file rỗng."""
    if not path.exists():
        return None
    _drop_partial_tail(path)
    if path.stat().st_size == 0:
        return None
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if header != columns:
            raise ResumeError(f"header của {path} không khớp schema hiện tại")
        return [dict(zip(columns, r, strict=True)) for r in reader if r]


def _fsync(f: Any) -> None:
    f.flush()
    os.fsync(f.fileno())


# ---------------------------------------------------------------- run_match


def _play_task(args: tuple[Any, ...]) -> MatchGame:
    return play_seeded_game(*args)


def run_match(
    out_path: str | Path,
    game_spec: GameSpec,
    spec_a: AgentSpec,
    spec_b: AgentSpec,
    n_pairs: int,
    base_seed: int = 0,
    workers: int = DEFAULT_WORKERS,
    max_moves: int | None = None,
    random_opening: int = 0,
    record_moves: bool = True,
    allow_code_change: bool = False,
) -> list[dict[str, str]]:
    """Chơi `2 * n_pairs` ván A vs B (seed `base_seed + i`, mỗi seed 2 ván đổi lượt), ghi từng ván
    vào `out_path` ngay khi xong (+ `<stem>_moves.csv` nếu `record_moves`). Chạy lại cùng file →
    bỏ qua ván đã xong. Trả về mọi dòng trong file (kể cả của lần chạy trước).

    Lỗi dựng agent/game → ném ra trước khi chơi. File có sẵn khác header / config / commit →
    `ResumeError` (commit: trừ khi `allow_code_change`).
    """
    out_path = Path(out_path)
    if workers < 1:
        raise ValueError("workers phải ≥ 1")
    # kiểm config ở tiến trình chính: sai thì dừng trước khi ghi gì
    make_game(game_spec)
    make_agent(spec_a, 0)
    make_agent(spec_b, 0)
    chash = config_hash(game_spec, spec_a, spec_b, max_moves, random_opening, base_seed)
    commit, dirty = git_info()
    meta = {
        "label_a": spec_a.name, "label_b": spec_b.name,
        "spec_a": json.dumps(spec_a.to_dict(), sort_keys=True),
        "spec_b": json.dumps(spec_b.to_dict(), sort_keys=True),
        "game_spec": json.dumps(game_spec.to_dict(), sort_keys=True),
        "max_moves": max_moves, "random_opening": random_opening, "base_seed": base_seed,
        "config_hash": chash, "git_commit": commit, "git_dirty": dirty, "workers": workers,
    }  # fmt: skip

    existing = _load_existing(out_path, GAME_COLUMNS) or []
    for r in existing:
        if r["config_hash"] != chash:
            raise ResumeError(f"{out_path}: config_hash khác ({r['config_hash']} ≠ {chash})")
        if (r["git_commit"], r["git_dirty"]) != (commit, _fmt(dirty)) and not allow_code_change:
            raise ResumeError(
                f"{out_path}: git commit khác ({r['git_commit']} dirty={r['git_dirty']} → "
                f"{commit} dirty={_fmt(dirty)}); dùng allow_code_change / --allow-code-change"
            )
    done = {r["game_id"] for r in existing}

    mpath = moves_path_for(out_path)
    if record_moves:
        old_moves = _load_existing(mpath, MOVE_COLUMNS)
        if old_moves is not None:
            kept = [r for r in old_moves if r["game_id"] in done]
            if len(kept) != len(old_moves):  # bỏ moves mồ côi của ván chưa ghi xong
                tmp = mpath.with_suffix(mpath.suffix + ".tmp")
                with open(tmp, "w", newline="", encoding="utf-8") as f:
                    w = csv.DictWriter(f, MOVE_COLUMNS)
                    w.writeheader()
                    w.writerows(kept)
                    _fsync(f)
                os.replace(tmp, mpath)

    tasks = [
        (game_spec, spec_a, spec_b, s, a_is_x, max_moves, random_opening)
        for s, a_is_x in match_tasks(n_pairs, base_seed)
        if game_id_for(s, a_is_x) not in done
    ]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    new_games = not out_path.exists() or out_path.stat().st_size == 0
    new_moves = record_moves and (not mpath.exists() or mpath.stat().st_size == 0)
    gf = open(out_path, "a", newline="", encoding="utf-8")
    mf = open(mpath, "a", newline="", encoding="utf-8") if record_moves else None
    try:
        gw = csv.DictWriter(gf, GAME_COLUMNS)
        mw = csv.DictWriter(mf, MOVE_COLUMNS) if mf else None
        if new_games:
            gw.writeheader()
            _fsync(gf)
        if mw and new_moves:
            mw.writeheader()
            _fsync(mf)

        def write(mg: MatchGame) -> None:
            if mw is not None:  # moves trước, dòng ván sau: dòng ván là dấu "đã xong"
                mw.writerows(move_rows(mg))
                _fsync(mf)
            gw.writerow(game_row(mg, meta))
            _fsync(gf)

        if workers == 1 or len(tasks) <= 1:
            for t in tasks:
                write(_play_task(t))
        else:
            ex = ProcessPoolExecutor(max_workers=min(workers, len(tasks)))
            try:
                pending = {ex.submit(_play_task, t) for t in tasks}
                while pending:
                    finished, pending = wait(pending, return_when=FIRST_COMPLETED)
                    for fut in finished:
                        write(fut.result())  # lỗi ngoài ván (dựng agent, khai cuộc) → ném ra
            except BaseException:
                ex.shutdown(wait=False, cancel_futures=True)
                raise
            ex.shutdown(wait=True)
    finally:
        gf.close()
        if mf:
            mf.close()
    return read_rows(out_path)


def add_runner_args(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """Thêm `--quick`, `--workers` (mặc định 4), `--allow-code-change` cho script thí nghiệm."""
    parser.add_argument("--quick", action="store_true",
                        help="smoke test: ít ván, file *quick* riêng")  # fmt: skip
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS,
                        help=f"số tiến trình (mặc định {DEFAULT_WORKERS})")  # fmt: skip
    parser.add_argument("--allow-code-change", action="store_true",
                        help="cho phép chạy tiếp file kết quả của commit khác")  # fmt: skip
    return parser


# ---------------------------------------------------------------- summarize


def _per_move(rows: Sequence[dict[str, str]], side: str, key: str) -> float:
    total, moves = 0.0, 0
    for r in rows:
        v = r[f"{side}_{key}_sum"]
        if v != "":
            total += float(v)
            moves += int(r[f"{side}_moves"])
    return total / moves if moves else math.nan


# Nước đi thẳng nhờ tactics (MCTS: thắng ngay = 1, chặn ngay = 2) không search → 0 iteration.
# Mã 3 (restrict) vẫn search nên tính là nước có search.
_DIRECT_TACTICS = frozenset({"1", "2"})


def _search_stats(
    rows: list[dict[str, str]], moves: dict[str, list[dict[str, str]]] | None
) -> dict[str, float]:
    """Số nước có search và iteration/nước chỉ tính các nước đó (nan nếu không có `moves`)."""
    out: dict[str, float] = {}
    for side in ("a", "b"):
        n, its = 0, 0.0
        if moves is not None:
            for r in rows:
                for m in moves.get(r["game_id"], ()):
                    if m["side"] == side.upper() and m["tactic"] not in _DIRECT_TACTICS:
                        if m["iterations"] != "":
                            n += 1
                            its += float(m["iterations"])
        out[f"{side}_search_moves"] = n if moves is not None else math.nan
        out[f"{side}_search_iterations_per_move"] = its / n if n else math.nan
    return out


def _summary_row(
    label_a: str,
    label_b: str,
    split: str,
    rows: list[dict[str, str]],
    moves: dict[str, list[dict[str, str]]] | None = None,
) -> dict:
    n = len(rows)
    res = [float(r["result_a"]) for r in rows]
    wins, draws = res.count(1.0), res.count(0.5)
    losses = n - wins - draws
    win_lo, win_hi = wilson(wins, n)
    nl_lo, nl_hi = wilson(wins + draws, n)
    if split == "all":
        distinct = len({(r["a_is_x"], r["opening"], r["moves"]) for r in rows})
    else:
        distinct = len({(r["opening"], r["moves"]) for r in rows})
    errs = [r for r in rows if r["termination"] in ERROR_TERMINATIONS]
    nan = math.nan
    return {
        "label_a": label_a, "label_b": label_b, "split": split, "n": n,
        "wins": wins, "draws": draws, "losses": losses,
        "win_rate": wins / n if n else nan, "win_lo": win_lo, "win_hi": win_hi,
        "nonloss_rate": (wins + draws) / n if n else nan, "nonloss_lo": nl_lo, "nonloss_hi": nl_hi,
        "score": (wins + 0.5 * draws) / n if n else nan,
        "distinct_games": distinct,
        "mean_moves": sum(int(r["n_moves"]) for r in rows) / n if n else nan,
        "errors": len(errs),
        "a_errors": sum(1 for r in errs if r["error_side"] == "A"),
        "b_errors": sum(1 for r in errs if r["error_side"] == "B"),
        "max_moves_draws": sum(1 for r in rows if r["termination"] == "max_moves"),
        **{f"{s}_{k}_per_move": _per_move(rows, s, k)
           for k in ("time", "nodes", "iterations") for s in ("a", "b")},
        **_search_stats(rows, moves),
    }  # fmt: skip


def summarize(
    rows: Iterable[dict[str, str]], moves: Iterable[dict[str, str]] | None = None
) -> list[dict[str, Any]]:
    """Bảng tổng hợp theo cặp (label_a, label_b), mỗi cặp 3 dòng: all, A=X, A=O.

    Số chính: win rate W/n + Wilson 95%; thêm non-loss (W+D)/n + Wilson; score (W + 0.5D)/n không có
    CI. `distinct_games`: số chuỗi nước khác nhau (gồm khai cuộc; dòng "all" tính cả vai A/B).
    `moves` (dòng của `*_moves.csv`, xem `read_rows(moves_path_for(path))`) → tính thêm
    `{a,b}_search_moves` và `{a,b}_search_iterations_per_move` (bỏ nước đi thẳng nhờ tactics);
    không truyền → các cột này là nan. Cột `*_iterations_per_move` cũ giữ nguyên (tính mọi nước).
    """
    by_game: dict[str, list[dict[str, str]]] | None = None
    if moves is not None:
        by_game = {}
        for m in moves:
            by_game.setdefault(m["game_id"], []).append(m)
    groups: dict[tuple[str, str], list[dict[str, str]]] = {}
    for r in rows:
        groups.setdefault((r["label_a"], r["label_b"]), []).append(r)
    out = []
    for (la, lb), rs in groups.items():
        out.append(_summary_row(la, lb, "all", rs, by_game))
        out.append(_summary_row(la, lb, "A=X", [r for r in rs if r["a_is_x"] == "1"], by_game))
        out.append(_summary_row(la, lb, "A=O", [r for r in rs if r["a_is_x"] == "0"], by_game))
    return out


def write_summary(summary: Sequence[dict[str, Any]], path: str | Path) -> None:
    """Ghi bảng tổng hợp ra CSV (tạo thư mục nếu cần)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, SUMMARY_COLUMNS)
        w.writeheader()
        w.writerows({c: _fmt(s.get(c)) for c in SUMMARY_COLUMNS} for s in summary)
