"""Chuyển động GUI (P6.3, D-29): tween theo `dt`, cờ tắt toàn cục (test / ảnh tất định)."""

from __future__ import annotations

import math
from collections.abc import Callable

ENABLED = True
Value = float | tuple[float, ...]

# thời lượng (giây) — thứ tự ưu tiên trong D-29
PLACE = 0.15  # đặt quân: scale 0,6 → 1 + fade-in
HOVER = 0.10  # đổi màu nút khi hover
MODAL = 0.20  # modal fade + slide
SCENE = 0.15  # chuyển scene crossfade
WIN_LINE = 0.30  # đường thắng vẽ dần
PULSE_PERIOD = 1.2  # chỉ báo "đang nghĩ"


def set_enabled(on: bool) -> None:
    """Tắt → mọi tween ở trạng thái cuối ngay (test headless, `--no-anim`)."""
    global ENABLED
    ENABLED = on


def ease_out_cubic(t: float) -> float:
    t = min(1.0, max(0.0, t))
    return 1 - (1 - t) ** 3


def lerp(a: Value, b: Value, t: float) -> Value:
    if isinstance(a, tuple):
        return tuple(x + (y - x) * t for x, y in zip(a, b, strict=True))
    return a + (b - a) * t


class Tween:
    """Giá trị đi từ `start` tới `end` trong `duration` giây (ease-out). `update(dt)` mỗi frame."""

    def __init__(self, start: Value, end: Value, duration: float,
                 ease: Callable[[float], float] = ease_out_cubic) -> None:  # fmt: skip
        self.start, self.end, self.duration, self.ease = start, end, duration, ease
        self.elapsed = 0.0 if (ENABLED and duration > 0) else duration

    @property
    def progress(self) -> float:
        return 1.0 if self.duration <= 0 else min(1.0, self.elapsed / self.duration)

    @property
    def done(self) -> bool:
        return self.progress >= 1.0

    @property
    def value(self) -> Value:
        return self.end if self.done else lerp(self.start, self.end, self.ease(self.progress))

    def update(self, dt: float) -> None:
        self.elapsed = self.duration if not ENABLED else self.elapsed + max(0.0, dt)

    def retarget(self, end: Value, duration: float | None = None) -> None:
        """Đổi đích, bắt đầu từ giá trị hiện tại (hover vào/ra giữa chừng không giật)."""
        if end == self.end:
            return
        self.start, self.end = self.value, end
        if duration is not None:
            self.duration = duration
        self.elapsed = 0.0 if (ENABLED and self.duration > 0) else self.duration


def pulse(t: float, period: float = PULSE_PERIOD) -> float:
    """0 → 1 → 0 theo sin; tắt animation → 1 (tĩnh)."""
    if not ENABLED:
        return 1.0
    return 0.5 - 0.5 * math.cos(2 * math.pi * (t % period) / period)
