"""Sprite khử răng cưa cho GUI (P6.3, D-29): vẽ ở 4× rồi `smoothscale`, cache có giới hạn.

Quy ước cache (chỉnh của An): mọi `lru_cache` có `maxsize`; khóa chỉ gồm kích thước chuẩn + màu
token (hữu hạn). Tween kích thước → `scaled()` từ sprite chuẩn (không cache); tween màu →
`tint()` mặt nạ đã cache (không cache).
Mọi cache bị xóa khi `pygame.quit()` (Surface cũ không dùng được sau quit).
"""

from __future__ import annotations

import math
from collections.abc import Callable
from functools import lru_cache

import numpy as np
import pygame

SS = 4  # hệ số siêu lấy mẫu
Color = tuple[int, ...]

_CACHES: list[Callable[[], None]] = []
_hooked = False


def _cached(maxsize: int):
    """`lru_cache(maxsize)` + đăng ký để xóa khi pygame.quit."""

    def deco(fn):
        wrapped = lru_cache(maxsize=maxsize)(fn)
        _CACHES.append(wrapped.cache_clear)
        return wrapped

    return deco


def clear_caches() -> None:
    global _hooked
    for clear in _CACHES:
        clear()
    _hooked = False


def _ensure_hook() -> None:
    """pygame bỏ danh sách `register_quit` sau mỗi lần quit → đăng ký lại mỗi chu kỳ init."""
    global _hooked
    if not _hooked:
        pygame.register_quit(clear_caches)
        _hooked = True


def cache_sizes() -> dict[str, int]:
    """Số entry của từng cache (test: không tăng theo số frame)."""
    out = {}
    for name, obj in list(globals().items()):
        if hasattr(obj, "cache_info") and callable(obj):
            out[name] = obj.cache_info().currsize
    return out


def _down(big: pygame.Surface, size: tuple[int, int]) -> pygame.Surface:
    return pygame.transform.smoothscale(big, (max(1, size[0]), max(1, size[1])))


# ---------------------------------------------------------------- mặt nạ (trắng + alpha)
@_cached(256)
def rounded_mask(w: int, h: int, r: int) -> pygame.Surface:
    _ensure_hook()
    big = pygame.Surface((w * SS, h * SS), pygame.SRCALPHA)
    pygame.draw.rect(big, (255, 255, 255, 255), big.get_rect(), border_radius=r * SS)
    return _down(big, (w, h))


@_cached(128)
def circle_mask(d: int) -> pygame.Surface:
    _ensure_hook()
    big = pygame.Surface((d * SS, d * SS), pygame.SRCALPHA)
    pygame.draw.circle(big, (255, 255, 255, 255), (d * SS // 2, d * SS // 2), d * SS // 2)
    return _down(big, (d, d))


@_cached(128)
def ring_mask(d: int, width: int) -> pygame.Surface:
    _ensure_hook()
    big = pygame.Surface((d * SS, d * SS), pygame.SRCALPHA)
    pygame.draw.circle(big, (255, 255, 255, 255), (d * SS // 2, d * SS // 2), d * SS // 2,
                       width * SS)  # fmt: skip
    return _down(big, (d, d))


def tint(mask: pygame.Surface, color: Color) -> pygame.Surface:
    """Mặt nạ trắng × màu (RGB hoặc RGBA). Không cache — dùng cho màu đang tween."""
    out = mask.copy()
    rgba = (*color[:3], color[3] if len(color) > 3 else 255)
    out.fill(rgba, special_flags=pygame.BLEND_RGBA_MULT)
    return out


@_cached(512)
def rounded_rect(w: int, h: int, r: int, color: Color) -> pygame.Surface:
    """Hình chữ nhật bo góc màu token (cache; màu tween → `tint(rounded_mask(...), c)`)."""
    _ensure_hook()
    return tint(rounded_mask(w, h, r), color)


@_cached(64)
def rounded_outline(w: int, h: int, r: int, width: int, color: Color) -> pygame.Surface:
    """Viền bo góc (khung nước cuối 3×3)."""
    _ensure_hook()
    big = pygame.Surface((w * SS, h * SS), pygame.SRCALPHA)
    pygame.draw.rect(big, (*color[:3], color[3] if len(color) > 3 else 255), big.get_rect(),
                     width=width * SS, border_radius=r * SS)  # fmt: skip
    return _down(big, (w, h))


@_cached(128)
def circle(d: int, color: Color) -> pygame.Surface:
    _ensure_hook()
    return tint(circle_mask(d), color)


@_cached(64)
def ring(d: int, width: int, color: Color) -> pygame.Surface:
    _ensure_hook()
    return tint(ring_mask(d, width), color)


@_cached(16)
def solid(w: int, h: int, color: Color) -> pygame.Surface:
    """Hình chữ nhật phẳng (RGBA) — nền mờ sau modal."""
    _ensure_hook()
    out = pygame.Surface((w, h), pygame.SRCALPHA)
    out.fill((*color[:3], color[3] if len(color) > 3 else 255))
    return out


def scaled(sprite: pygame.Surface, factor: float) -> pygame.Surface:
    """Tween kích thước: scale sprite chuẩn đã cache (không thêm entry)."""
    w, h = sprite.get_size()
    return pygame.transform.smoothscale(
        sprite, (max(1, round(w * factor)), max(1, round(h * factor)))
    )


def faded(sprite: pygame.Surface, alpha: int) -> pygame.Surface:
    """Bản sao mờ (alpha 0–255) — không cache."""
    out = sprite.copy()
    out.fill((255, 255, 255, max(0, min(255, alpha))), special_flags=pygame.BLEND_RGBA_MULT)
    return out


# ---------------------------------------------------------------- bóng đổ
@_cached(128)
def shadow(w: int, h: int, r: int, blur: int, alpha: int) -> pygame.Surface:
    """Bóng mờ của hình bo góc w×h: Surface (w + 2·blur) × (h + 2·blur), đặt lệch (−blur, −blur)."""
    _ensure_hook()
    pad = blur
    W, H = w + 2 * pad, h + 2 * pad
    base = pygame.Surface((W, H), pygame.SRCALPHA)
    base.blit(tint(rounded_mask(w, h, r), (0, 0, 0, alpha)), (pad, pad))
    k = max(2, blur // 2)  # mờ: thu nhỏ rồi phóng to (2 lần cho mềm)
    small = pygame.transform.smoothscale(base, (max(1, W // k), max(1, H // k)))
    small = pygame.transform.smoothscale(
        small, (max(1, W // (2 * k)) or 1, max(1, H // (2 * k)) or 1)
    )
    return pygame.transform.smoothscale(small, (W, H))


# ---------------------------------------------------------------- quân cờ
@_cached(64)
def stone(d: int, base: Color, light: Color, rim: Color) -> pygame.Surface:
    """Quân tròn có gradient tỏa (sáng ở trên-trái), viền tối nhẹ; khử răng cưa."""
    _ensure_hook()
    n = d * SS
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    c = (n - 1) / 2
    rad = n / 2
    dist = np.hypot(xx - c, yy - c) / rad  # 0 tâm → 1 mép
    hx, hy = c - 0.35 * rad, c - 0.4 * rad
    hl = np.clip(1 - np.hypot(xx - hx, yy - hy) / (1.1 * rad), 0, 1) ** 1.6
    edge = np.clip((dist - 0.78) / 0.22, 0, 1) ** 1.5
    rgb = np.empty((n, n, 3), np.float32)
    for i in range(3):
        v = base[i] + (light[i] - base[i]) * hl
        rgb[..., i] = v + (rim[i] - v) * edge * 0.6
    big = pygame.Surface((n, n), pygame.SRCALPHA)
    pygame.surfarray.blit_array(big, np.clip(rgb, 0, 255).astype(np.uint8).transpose(1, 0, 2))
    alpha = pygame.surfarray.pixels_alpha(big)
    alpha[...] = (dist <= 1.0).T.astype(np.uint8) * 255
    del alpha
    return _down(big, (d, d))


@_cached(32)
def stone_shadow(d: int, alpha: int) -> pygame.Surface:
    return shadow(d, d, d // 2, max(3, d // 7), alpha)


@_cached(32)
def x_mark(d: int, color: Color, thickness: float = 0.13) -> pygame.Surface:
    """Chữ X nét bo tròn (thân đa giác dày + đầu tròn)."""
    _ensure_hook()
    n = d * SS
    big = pygame.Surface((n, n), pygame.SRCALPHA)
    t = max(2.0, n * thickness)
    pad = n * 0.2
    for p0, p1 in (((pad, pad), (n - pad, n - pad)), ((n - pad, pad), (pad, n - pad))):
        _thick_segment(big, p0, p1, t, (*color[:3], 255))
    return _down(big, (d, d))


@_cached(32)
def o_mark(d: int, color: Color, thickness: float = 0.13) -> pygame.Surface:
    _ensure_hook()
    n = d * SS
    big = pygame.Surface((n, n), pygame.SRCALPHA)
    r = n / 2 - n * 0.2 + n * thickness / 2
    pygame.draw.circle(big, (*color[:3], 255), (n // 2, n // 2), int(r), int(n * thickness))
    return _down(big, (d, d))


def _thick_segment(surf: pygame.Surface, p0, p1, width: float, color) -> None:
    """Đoạn thẳng dày đầu tròn (vẽ ở độ phân giải đã phóng to)."""
    (x0, y0), (x1, y1) = p0, p1
    ang = math.atan2(y1 - y0, x1 - x0)
    dx, dy = math.sin(ang) * width / 2, -math.cos(ang) * width / 2
    pygame.draw.polygon(surf, color, [(x0 + dx, y0 + dy), (x1 + dx, y1 + dy),
                                      (x1 - dx, y1 - dy), (x0 - dx, y0 - dy)])  # fmt: skip
    for x, y in (p0, p1):
        pygame.draw.circle(surf, color, (round(x), round(y)), round(width / 2))


@_cached(16)
def line(dx: int, dy: int, thickness: int, color: Color) -> pygame.Surface:
    """Vạch dày đầu tròn từ (0,0) tới (dx,dy) trong Surface bao quanh (lề thickness)."""
    _ensure_hook()
    pad = thickness
    w, h = abs(dx) + 2 * pad, abs(dy) + 2 * pad
    big = pygame.Surface((w * SS, h * SS), pygame.SRCALPHA)
    x0 = pad if dx >= 0 else pad + abs(dx)
    y0 = pad if dy >= 0 else pad + abs(dy)
    _thick_segment(big, (x0 * SS, y0 * SS), ((x0 + dx) * SS, (y0 + dy) * SS), thickness * SS,
                   (*color[:3], color[3] if len(color) > 3 else 255))  # fmt: skip
    return _down(big, (w, h))


# ---------------------------------------------------------------- chữ
@_cached(1024)
def text(s: str, size: int, weight: str, color: Color) -> pygame.Surface:
    """Ảnh chữ (cache; khóa hữu hạn: chuỗi hiển thị × cỡ × độ đậm × màu token)."""
    from gameai.gui.view import get_font

    _ensure_hook()
    return get_font(size, weight=weight).render(s, True, color[:3])


# ---------------------------------------------------------------- vân gỗ
@_cached(8)
def wood(w: int, h: int, light: Color, dark: Color, grain: Color, seed: int = 7) -> pygame.Surface:
    """Vân gỗ sinh bằng code (sin theo hàng + nhiễu tần số thấp, seed cố định → tất định)."""
    _ensure_hook()
    rng = np.random.default_rng(seed)
    y = np.arange(h, dtype=np.float32)[:, None]
    x = np.arange(w, dtype=np.float32)[None, :]
    knots = rng.normal(0, 1, 8).astype(np.float32)
    warp = sum(0.9 * np.sin(x * (0.004 + 0.002 * i) + knots[i]) for i in range(4))
    rings = 0.5 + 0.5 * np.sin(y * 0.16 + 2.2 * warp + 0.6 * np.sin(y * 0.021 + knots[5]))
    fine = (
        rng.normal(0, 1, (h, 1)).astype(np.float32) * 0.15
        + rng.normal(0, 1, (h, w)).astype(np.float32) * 0.04
    )
    t = np.clip(rings**3 * 0.55 + 0.25 * (0.5 + 0.5 * np.sin(x * 0.011 + knots[6])) + fine, 0, 1)
    rgb = np.empty((h, w, 3), np.float32)
    for i in range(3):
        base = light[i] + (dark[i] - light[i]) * (0.35 * t)
        rgb[..., i] = base + (grain[i] - base) * (t**2) * 0.35
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.surfarray.blit_array(surf, np.clip(rgb, 0, 255).astype(np.uint8).transpose(1, 0, 2))
    alpha = pygame.surfarray.pixels_alpha(surf)
    alpha[...] = 255
    del alpha
    return surf
