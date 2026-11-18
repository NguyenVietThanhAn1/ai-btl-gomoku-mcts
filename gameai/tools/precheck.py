"""Kiểm tra trước push (AGENTS.md): một lệnh, exit code thật (≠ 0 nếu bất kỳ bước nào lỗi)."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from collections.abc import Callable, Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PY = sys.executable

STEPS: list[tuple[str, list[str]]] = [
    ("pytest (gồm golden k-in-row)", [PY, "-m", "pytest", "-q"]),
    ("ruff check", [PY, "-m", "ruff", "check", "."]),
    ("ruff format --check", [PY, "-m", "ruff", "format", "--check", "."]),
    ("report_check", [PY, "-m", "gameai.experiments.report_check"]),
    ("plots --check", [PY, "-m", "gameai.experiments.plots", "--check"]),
]

Runner = Callable[[Sequence[str]], tuple[int, str]]


def run_command(cmd: Sequence[str]) -> tuple[int, str]:
    """Chạy `cmd` ở gốc repo, trả (exit code thật, output gộp). Không qua pipe/shell."""
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    r = subprocess.run(
        list(cmd), cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8",
        errors="replace",
    )  # fmt: skip
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def precheck(
    steps: Sequence[tuple[str, list[str]]] = STEPS,
    runner: Runner = run_command,
    tail: int = 15,
    out: Callable[[str], None] = print,
) -> int:
    """Chạy mọi bước (không dừng ở lỗi đầu tiên), in PASS/FAIL từng bước. 0 = tất cả PASS."""
    results: list[tuple[str, bool, float]] = []
    for name, cmd in steps:
        t0 = time.perf_counter()
        code, text = runner(cmd)
        dt = time.perf_counter() - t0
        ok = code == 0
        results.append((name, ok, dt))
        out(f"[{'PASS' if ok else 'FAIL'}] {name} ({dt:.1f} s, exit {code})")
        if not ok:
            lines = text.strip().splitlines()[-tail:]
            out("\n".join("    " + ln for ln in lines))
    failed = [n for n, ok, _ in results if not ok]
    out("-" * 60)
    for name, ok, _ in results:
        out(f"{'PASS' if ok else 'FAIL'}  {name}")
    out(f"precheck: {len(results) - len(failed)}/{len(results)} PASS" + (
        "" if not failed else f" — FAIL: {', '.join(failed)}"))  # fmt: skip
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(description=__doc__).parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]  # console cp1252
    return precheck()


if __name__ == "__main__":
    sys.exit(main())
