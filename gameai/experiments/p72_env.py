"""P7.2: ghi môi trường phần mềm (Python, thư viện, OS) cho mục 4 báo cáo.

Thí nghiệm E1–E6 không ghi phiên bản Python/thư viện; bảng này đo lúc viết báo cáo, cùng venv.

    python -m gameai.experiments.p72_env      # → results/tables/p72_env.csv
"""

from __future__ import annotations

import csv
import platform
import sys
from datetime import date
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results" / "tables" / "p72_env.csv"
PACKAGES = ("numpy", "pandas", "matplotlib", "pygame", "pytest")


def collect() -> list[dict[str, str]]:
    """Danh sách (key, value): python, os, machine + phiên bản từng gói (`-` nếu không cài)."""
    rows = [
        {"key": "python", "value": platform.python_version()},
        {"key": "implementation", "value": platform.python_implementation()},
        {"key": "os", "value": f"{platform.system()} {platform.release()} ({platform.version()})"},
        {"key": "machine", "value": platform.machine()},
    ]
    for pkg in PACKAGES:
        try:
            v = metadata.version(pkg)
        except metadata.PackageNotFoundError:
            v = "-"
        rows.append({"key": pkg, "value": v})
    rows.append({"key": "recorded", "value": date.today().isoformat()})
    return rows


def write(path: Path = OUT) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["key", "value"], lineterminator="\n")
        w.writeheader()
        w.writerows(collect())
    return path


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    print(f"[p72_env] {write()}")
