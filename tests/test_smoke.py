"""Smoke test: các gói của skeleton import được."""

import importlib

import pytest

PACKAGES = [
    "gameai",
    "gameai.core",
    "gameai.games",
    "gameai.heuristics",
    "gameai.agents",
    "gameai.gui",
    "gameai.experiments",
]


@pytest.mark.parametrize("name", PACKAGES)
def test_package_imports(name: str) -> None:
    assert importlib.import_module(name) is not None
