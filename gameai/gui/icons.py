"""Icon vẽ bằng code (P6.3, D-29): cache (tên, cỡ), tô màu khi vẽ."""

from __future__ import annotations

import math
from collections.abc import Callable

import pygame

from gameai.gui import render
from gameai.gui.render import SS, Color, _cached, _ensure_hook, _thick_segment

W = (255, 255, 255, 255)
Painter = Callable[[pygame.Surface, float], None]


def _arc_arrow(s: pygame.Surface, n: float) -> None:  # đi lại: cung + mũi tên ở đầu trái
    t = n * 0.11
    rect = pygame.Rect(n * 0.2, n * 0.24, n * 0.62, n * 0.6)
    pygame.draw.arc(s, W, rect, math.radians(-60), math.radians(160), round(t))
    tip = (n * 0.2, n * 0.42)
    pygame.draw.polygon(
        s,
        W,
        [
            (tip[0] - t * 1.4, tip[1] - t * 0.2),
            (tip[0] + t * 1.5, tip[1] - t * 0.4),
            (tip[0] + t * 0.1, tip[1] + t * 1.7),
        ],
    )


def _plus(s: pygame.Surface, n: float) -> None:  # ván mới
    t = n * 0.11
    _thick_segment(s, (n * 0.5, n * 0.22), (n * 0.5, n * 0.78), t, W)
    _thick_segment(s, (n * 0.22, n * 0.5), (n * 0.78, n * 0.5), t, W)


def _flag(s: pygame.Surface, n: float) -> None:  # đầu hàng: cờ trắng
    t = n * 0.09
    _thick_segment(s, (n * 0.26, n * 0.16), (n * 0.26, n * 0.86), t, W)
    pts = [(n * 0.28, n * 0.18)]
    for i in range(9):  # mép trên lượn sóng
        x = n * (0.28 + 0.5 * i / 8)
        pts.append((x, n * (0.18 + 0.04 * math.sin(i / 8 * math.pi * 2))))
    for i in range(8, -1, -1):
        x = n * (0.28 + 0.5 * i / 8)
        pts.append((x, n * (0.52 + 0.04 * math.sin(i / 8 * math.pi * 2))))
    pygame.draw.polygon(s, W, pts)


def _home(s: pygame.Surface, n: float) -> None:
    t = n * 0.1
    roof = [(n * 0.14, n * 0.5), (n * 0.5, n * 0.16), (n * 0.86, n * 0.5)]
    _thick_segment(s, roof[0], roof[1], t, W)
    _thick_segment(s, roof[1], roof[2], t, W)
    pygame.draw.rect(
        s, W, pygame.Rect(n * 0.26, n * 0.48, n * 0.48, n * 0.36), border_radius=round(n * 0.04)
    )
    pygame.draw.rect(s, (0, 0, 0, 0), pygame.Rect(n * 0.43, n * 0.62, n * 0.14, n * 0.22))


def _play(s: pygame.Surface, n: float) -> None:
    pygame.draw.polygon(s, W, [(n * 0.3, n * 0.2), (n * 0.8, n * 0.5), (n * 0.3, n * 0.8)])


def _pause(s: pygame.Surface, n: float) -> None:
    for x in (0.28, 0.58):
        pygame.draw.rect(
            s, W, pygame.Rect(n * x, n * 0.2, n * 0.15, n * 0.6), border_radius=round(n * 0.04)
        )


def _chevron(direction: int) -> Painter:
    def paint(s: pygame.Surface, n: float) -> None:
        t = n * 0.12
        x0, x1 = (0.62, 0.36) if direction < 0 else (0.38, 0.64)
        _thick_segment(s, (n * x0, n * 0.22), (n * x1, n * 0.5), t, W)
        _thick_segment(s, (n * x1, n * 0.5), (n * x0, n * 0.78), t, W)

    return paint


def _info(s: pygame.Surface, n: float) -> None:  # ⓘ
    pygame.draw.circle(s, W, (n / 2, n / 2), n * 0.44, round(n * 0.08))
    pygame.draw.circle(s, W, (n / 2, n * 0.3), n * 0.065)
    _thick_segment(s, (n / 2, n * 0.45), (n / 2, n * 0.72), n * 0.11, W)


def _chart(s: pygame.Surface, n: float) -> None:  # phân tích
    for i, h in enumerate((0.35, 0.6, 0.45)):
        x = n * (0.18 + 0.24 * i)
        pygame.draw.rect(
            s, W, pygame.Rect(x, n * (0.82 - h), n * 0.17, n * h), border_radius=round(n * 0.03)
        )


def _close(s: pygame.Surface, n: float) -> None:  # thoát
    t = n * 0.11
    _thick_segment(s, (n * 0.26, n * 0.26), (n * 0.74, n * 0.74), t, W)
    _thick_segment(s, (n * 0.74, n * 0.26), (n * 0.26, n * 0.74), t, W)


def _book(s: pygame.Surface, n: float) -> None:  # hướng dẫn
    t = n * 0.08
    for x0, x1 in ((0.14, 0.48), (0.52, 0.86)):
        pygame.draw.polygon(
            s,
            W,
            [(n * x0, n * 0.24), (n * x1, n * 0.3), (n * x1, n * 0.8), (n * x0, n * 0.74)],
            round(t),
        )


def _flask(s: pygame.Surface, n: float) -> None:  # demo thí nghiệm
    t = n * 0.08
    _thick_segment(s, (n * 0.4, n * 0.16), (n * 0.6, n * 0.16), t, W)
    pygame.draw.polygon(
        s,
        W,
        [
            (n * 0.42, n * 0.18),
            (n * 0.58, n * 0.18),
            (n * 0.58, n * 0.4),
            (n * 0.82, n * 0.82),
            (n * 0.18, n * 0.82),
            (n * 0.42, n * 0.4),
        ],
    )


PAINTERS: dict[str, Painter] = {
    "undo": _arc_arrow, "new_game": _plus, "flag": _flag, "home": _home, "play": _play,
    "pause": _pause, "chevron_left": _chevron(-1), "chevron_right": _chevron(1), "info": _info,
    "chart": _chart, "close": _close, "book": _book, "flask": _flask,
}  # fmt: skip


@_cached(128)
def icon_mask(name: str, size: int) -> pygame.Surface:
    """Mặt nạ trắng + alpha của icon `name` cỡ `size` px."""
    _ensure_hook()
    n = size * SS
    big = pygame.Surface((n, n), pygame.SRCALPHA)
    PAINTERS[name](big, float(n))
    return pygame.transform.smoothscale(big, (size, size))


def icon(name: str, size: int, color: Color) -> pygame.Surface:
    """Icon tô màu (không cache — màu có thể đang tween)."""
    return render.tint(icon_mask(name, size), color)
