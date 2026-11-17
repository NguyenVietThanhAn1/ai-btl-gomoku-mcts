"""P6.3: đo thời gian/nước của từng mức độ khó GUI (D-29) qua vòng vẽ GUI thật.

App chạy trên Surface headless (`SDL_VIDEODRIVER=dummy`), khóa 30 fps như cửa sổ thật;
người = nước ngẫu nhiên có seed trong `candidate_moves`.
**Số minh họa GUI — không dùng cho báo cáo thí nghiệm.**
Điều kiện đo theo D-21: cắm sạc, máy rảnh; ghi nguồn điện, power plan,
bench ngắn so với `e5_bench.csv`.

    python -m gameai.experiments.p63_gui_timing [--boards 3 15] [--quick] [--allow-battery]
"""

from __future__ import annotations

import argparse
import os
import random
import statistics
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402

from gameai.core.game import P1, P2  # noqa: E402
from gameai.experiments.common import git_info, read_rows  # noqa: E402
from gameai.experiments.e5_rollout import _append_csv, _write, bench, cpu_name  # noqa: E402
from gameai.experiments.e6_tactics import power_status  # noqa: E402
from gameai.gui import anim  # noqa: E402
from gameai.gui.controller import MoveInfo  # noqa: E402
from gameai.gui.presets import AB2, DIFFICULTY, GAME3, GAME15, Level, Preset, side_label  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
TABLE_DIR = ROOT / "results" / "tables"
NOTE = "minh họa GUI — không dùng cho báo cáo thí nghiệm"
GAMES = {3: GAME3, 15: GAME15}
N_GAMES = {3: 5, 15: 3}  # ván vs người ngẫu nhiên / mức (đổi bên theo seed chẵn/lẻ)
QUICK_GAMES = {3: 1, 15: 1}
FPS = 30
GAME_TIMEOUT = 900.0  # giây/ván
BENCH_PLIES = (8, 16, 24)  # như bench E6 (D-21)
BENCH_SEEDS = (0,)

TIMING_COLUMNS = ["board", "kind", "level", "source", "config", "opponent", "games", "ai_moves",
                  "search_moves", "mean_s", "median_s", "max_s", "power", "animations",
                  "note"]  # fmt: skip
RUNINFO_COLUMNS = ["started", "finished", "wall_s", "boards", "quick", "cpu", "logical_cpus",
                   "power", "battery_pct", "power_plan", "bench_speed_vs_e5", "git_commit",
                   "git_dirty", "animations", "note"]  # fmt: skip
BENCH_COLUMNS = ["rollout", "plies", "seed", "iterations", "agent_time", "iter_per_s",
                 "e5_iter_per_s", "speed_vs_e5", "power"]  # fmt: skip


def prefix(quick: bool) -> str:
    """p63_ / p63quick_ (animation tắt, bảng gốc D-29); p63anim_ / p63animquick_ (animation bật)."""
    tag = "p63anim" if anim.ENABLED else "p63"
    return f"{tag}quick_" if quick else f"{tag}_"


def power_plan() -> str:
    """Tên power plan Windows đang bật (`powercfg /getactivescheme`), '' nếu không đọc được."""
    try:
        out = subprocess.run(["powercfg", "/getactivescheme"], capture_output=True, text=True,
                             timeout=10).stdout  # fmt: skip
    except Exception:  # noqa: BLE001 — không phải Windows
        return ""
    return out[out.find("(") + 1 : out.rfind(")")] if "(" in out else out.strip()


def run_bench(quick: bool, table_dir: Path = TABLE_DIR) -> float:
    """Bench ngắn đơn luồng (như E6: 1 s/thế, thế 8/16/24 quân, seed 0, rand + h300) → trung vị
    iter/s so với cùng (rollout, thế, seed) trong `e5_bench.csv`."""
    power, _ = power_status()
    rows = bench(seconds=1.0, plies=BENCH_PLIES, seeds=BENCH_SEEDS, path=None)
    ref_path = table_dir / "e5_bench.csv"
    ref = {}
    if ref_path.exists():
        ref = {(r["rollout"], r["plies"], r["seed"]): float(r["iter_per_s"])
               for r in read_rows(ref_path)}  # fmt: skip
    ratios = []
    for r in rows:
        e5 = ref.get((r["rollout"], str(r["plies"]), str(r["seed"])))
        r["e5_iter_per_s"] = e5 if e5 is not None else ""
        r["speed_vs_e5"] = round(r["iter_per_s"] / e5, 3) if e5 else ""
        r["power"] = power
        if e5:
            ratios.append(r["iter_per_s"] / e5)
    _write(table_dir / f"{prefix(quick)}bench.csv", BENCH_COLUMNS, rows)
    return round(statistics.median(ratios), 3) if ratios else float("nan")


def play_gui_game(preset: Preset, seed: int, surface: pygame.Surface) -> list[MoveInfo]:
    """Một ván qua `App` (vẽ mỗi frame, 30 fps); người = nước ngẫu nhiên có seed."""
    from gameai.gui.pygame_app import App, AppState, autoplay_move

    app = App(AppState(None, seed, delay=0.0, base=preset), surface=surface)
    rng = random.Random(seed)
    clock = pygame.time.Clock()
    dt = 1 / FPS
    t0 = time.monotonic()
    while not app.ctrl.over:
        if time.monotonic() - t0 > GAME_TIMEOUT:
            raise TimeoutError(f"ván quá {GAME_TIMEOUT} s")
        autoplay_move(app, rng)
        app.tick(dt)
        dt = min(0.1, clock.tick(FPS) / 1000)
    if app.ctrl.error:
        raise RuntimeError(app.ctrl.error)
    return app.ctrl.history


def measure_level(board: int, key: tuple[int, str, str], lv: Level, opponent: str, n_games: int,
                  surface: pygame.Surface, power: str) -> dict[str, Any]:  # fmt: skip
    """Đo một (mức, đối thủ): 'random_human' (đổi bên theo seed) hoặc 'ab2' (AI cầm X)."""
    times: list[float] = []
    search: list[float] = []
    seeds = range(n_games) if opponent == "random_human" else range(1)
    for s in seeds:
        if opponent == "ab2":
            preset, side = Preset("t", "t", GAMES[board], lv.spec, AB2), P1
        elif s % 2 == 0:
            preset, side = Preset("t", "t", GAMES[board], None, lv.spec), P2
        else:
            preset, side = Preset("t", "t", GAMES[board], lv.spec, None), P1
        ai = [m for m in play_gui_game(preset, s, surface) if m.by_ai and m.player == side]
        times += [m.time for m in ai]
        search += [m.time for m in ai if not m.is_tactic]
    st = search or [0.0]
    return {
        "board": board, "kind": key[1], "level": key[2], "source": lv.source or "riêng",
        "config": side_label(lv.spec), "opponent": opponent, "games": len(seeds),
        "ai_moves": len(times), "search_moves": len(search),
        "mean_s": round(statistics.mean(st), 3), "median_s": round(statistics.median(st), 3),
        "max_s": round(max(times, default=0.0), 3), "power": power,
        "animations": int(anim.ENABLED), "note": NOTE,
    }  # fmt: skip


def run(boards: list[int], quick: bool, table_dir: Path = TABLE_DIR) -> list[dict[str, Any]]:
    started, t0 = datetime.now().isoformat(timespec="seconds"), time.perf_counter()
    power, pct = power_status()
    speed = run_bench(quick, table_dir)
    print(f"[bench] nguồn {power}, plan {power_plan()!r}; tốc độ / e5_bench: trung vị {speed}")
    pygame.init()
    surface = pygame.Surface((1280, 720))
    rows = []
    for key, lv in DIFFICULTY.items():
        board = key[0]
        if board not in boards:
            continue
        opps = ("random_human", "ab2") if board == 15 else ("random_human",)
        for opp in opps:
            n = (QUICK_GAMES if quick else N_GAMES)[board]
            row = measure_level(board, key, lv, opp, n, surface, power)
            rows.append(row)
            print(f"[{board}] {key[1]} {key[2]} vs {opp}: mean {row['mean_s']} s, "
                  f"max {row['max_s']} s ({row['search_moves']} search)", flush=True)  # fmt: skip
    path = table_dir / f"{prefix(quick)}gui_timing.csv"
    keep = [r for r in read_rows(path) if int(r["board"]) not in boards] if path.exists() else []
    _write(path, TIMING_COLUMNS, sorted(keep + rows, key=lambda r: int(r["board"])))
    commit, dirty = git_info()
    _append_csv(table_dir / f"{prefix(quick)}gui_runinfo.csv", RUNINFO_COLUMNS, {
        "started": started, "finished": datetime.now().isoformat(timespec="seconds"),
        "wall_s": round(time.perf_counter() - t0, 1), "boards": " ".join(map(str, boards)),
        "quick": int(quick), "cpu": cpu_name(), "logical_cpus": os.cpu_count(), "power": power,
        "battery_pct": pct, "power_plan": power_plan(), "bench_speed_vs_e5": speed,
        "git_commit": commit, "git_dirty": int(dirty), "animations": int(anim.ENABLED),
        "note": NOTE,
    })  # fmt: skip
    return rows


def main(argv: list[str] | None = None) -> None:
    if hasattr(sys.stdout, "reconfigure"):  # console Windows cp1252 không in được tiếng Việt
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description="Đo thời gian/nước các mức độ khó GUI (P6.3).")
    ap.add_argument("--boards", type=int, nargs="+", choices=(3, 15), default=[3, 15])
    ap.add_argument("--quick", action="store_true", help="1 ván/mức, file p63quick_*")
    ap.add_argument("--allow-battery", action="store_true", help="cho chạy khi không cắm sạc")
    ap.add_argument("--no-anim", action="store_true", help="tắt animation (bảng gốc p63_*)")
    args = ap.parse_args(argv)
    power, _ = power_status()
    if power != "AC" and not args.allow_battery:
        raise SystemExit(f"Nguồn = {power}: D-21 yêu cầu cắm sạc (dùng --allow-battery để bỏ qua).")
    anim.set_enabled(not args.no_anim)
    run(args.boards, args.quick)
    pygame.quit()


if __name__ == "__main__":
    main()
