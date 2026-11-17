"""Cấu hình pytest chung: GUI chạy với animation tắt (trạng thái cuối ngay, D-29)."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _no_gui_animation():
    from gameai.gui import anim

    anim.set_enabled(False)
    yield
    anim.set_enabled(False)
