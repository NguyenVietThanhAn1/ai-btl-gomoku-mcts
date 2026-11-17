"""Nhận diện sản phẩm (P6.3, D-29): tên app (đổi ở một chỗ), logo vẽ bằng code, wordmark."""

from __future__ import annotations

import pygame

from gameai.gui import render
from gameai.gui.render import SS, _cached, _ensure_hook
from gameai.gui.widgets import Theme, current_theme

APP_NAME = "MoveMind"
WORDMARK_SPLIT = 4  # "Move" | "Mind": phần sau tô màu nhấn


@_cached(16)
def logo_surface(size: int, accent: tuple[int, int, int], stone: tuple[int, int, int],
                 hollow: tuple[int, int, int]) -> pygame.Surface:  # fmt: skip
    """Logo: ô bo góc màu nhấn + 3 quân chéo (một "nước đi" thẳng hàng), quân giữa rỗng."""
    _ensure_hook()
    n = size * SS
    big = pygame.Surface((n, n), pygame.SRCALPHA)
    pygame.draw.rect(big, (*accent, 255), big.get_rect(), border_radius=int(n * 0.24))
    r = n * 0.12
    for i, f in enumerate((0.27, 0.5, 0.73)):
        center = (n * f, n * (1 - f))
        if i == 1:
            pygame.draw.circle(big, (*hollow, 255), center, r, max(2, int(r * 0.42)))
        else:
            pygame.draw.circle(big, (*stone, 255), center, r)
    return pygame.transform.smoothscale(big, (size, size))


def logo(size: int, theme: Theme | None = None) -> pygame.Surface:
    t = theme or current_theme()
    return logo_surface(size, t.accent, (255, 255, 255), (255, 255, 255))


def window_icon() -> pygame.Surface:
    """Icon cửa sổ (`pygame.display.set_icon`)."""
    return logo(64)


def draw_wordmark(surf: pygame.Surface, center: tuple[int, int], size: int,
                  theme: Theme | None = None, with_logo: bool = True) -> pygame.Rect:  # fmt: skip
    """Logo + "Move" (chữ chính) + "Mind" (màu nhấn), căn giữa tại `center`; trả rect bao."""
    t = theme or current_theme()
    head, tail = APP_NAME[:WORDMARK_SPLIT], APP_NAME[WORDMARK_SPLIT:]
    img_head = render.text(head, size, "bold", t.ink)
    img_tail = render.text(tail, size, "bold", t.accent)
    logo_size = int(size * 1.15) if with_logo else 0
    gap = int(size * 0.3) if with_logo else 0
    width = logo_size + gap + img_head.get_width() + img_tail.get_width()
    x = center[0] - width // 2
    if with_logo:
        surf.blit(logo(logo_size, t), (x, center[1] - logo_size // 2))
        x += logo_size + gap
    top = center[1] - img_head.get_height() // 2
    surf.blit(img_head, (x, top))
    surf.blit(img_tail, (x + img_head.get_width(), top))
    return pygame.Rect(
        center[0] - width // 2,
        center[1] - max(logo_size, img_head.get_height()) // 2,
        width,
        max(logo_size, img_head.get_height()),
    )


__all__ = ["APP_NAME", "logo", "logo_surface", "window_icon", "draw_wordmark"]
