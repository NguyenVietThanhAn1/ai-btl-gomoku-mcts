"""Test P7.2 p72_env: bảng môi trường."""

import csv
import sys
from pathlib import Path

from gameai.experiments import p72_env


def test_collect_and_write(tmp_path: Path):
    rows = {r["key"]: r["value"] for r in p72_env.collect()}
    assert rows["python"].startswith(f"{sys.version_info.major}.{sys.version_info.minor}.")
    for pkg in p72_env.PACKAGES:
        assert pkg in rows
    path = p72_env.write(tmp_path / "env.csv")
    with path.open(encoding="utf-8") as f:
        back = {r["key"]: r["value"] for r in csv.DictReader(f)}
    assert back == rows
