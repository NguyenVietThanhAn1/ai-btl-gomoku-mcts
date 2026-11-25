"""Design tokens (`Theme`) + widget pygame tự viết (P6.3, D-29).

Button, IconButton, Toggle, SegmentedControl, Stepper, Modal, ScrollList, Tooltip. Mọi hình bo
góc / tròn vẽ qua `render` (khử răng cưa, cache)."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

import pygame

from gameai.gui import anim, render
from gameai.gui.icons import icon
from gameai.gui.view import get_font

Color = tuple[int, int, int]


# ---------------------------------------------------------------- design tokens
@dataclass(frozen=True)
class Theme:
    """Bảng màu + hình khối dùng chung. Mọi widget đọc `current_theme()` lúc vẽ."""

    name: str
    bg: Color  # nền cửa sổ
    surface1: Color  # card
    surface2: Color  # control trong card, nút phụ
    surface3: Color  # hover / tooltip
    border: Color
    ink: Color  # chữ chính
    muted: Color  # chữ phụ
    faint: Color  # chữ mờ / disabled
    accent: Color  # màu nhấn duy nhất
    accent_hover: Color
    accent_ink: Color  # chữ trên nền nhấn
    win: Color
    lose: Color
    last_move: Color  # đánh dấu nước cuối (mọi bàn)
    select: Color  # dòng đang chọn
    heat: Color  # overlay Phân tích
    board_light: Color
    board_dark: Color
    board_grain: Color
    board_frame: Color
    grid: Color
    label: Color  # nhãn tọa độ
    stone_dark: Color
    stone_dark_hi: Color
    stone_light: Color
    stone_light_hi: Color
    x_color: Color  # 3×3
    o_color: Color
    shadow_alpha: int = 110
    dim_alpha: int = 140  # nền mờ sau modal
    radius: int = 10
    radius_small: int = 6


DARK = Theme(
    name="dark",
    bg=(36, 34, 31), surface1=(48, 46, 42), surface2=(62, 59, 55), surface3=(78, 75, 70),
    border=(92, 88, 82), ink=(242, 240, 235), muted=(170, 166, 159), faint=(118, 114, 108),
    accent=(129, 182, 76), accent_hover=(148, 199, 94), accent_ink=(255, 255, 255),
    win=(129, 182, 76), lose=(226, 98, 86), last_move=(246, 214, 92), select=(84, 80, 58),
    heat=(255, 146, 48),
    board_light=(226, 190, 140), board_dark=(204, 160, 106), board_grain=(170, 122, 72),
    board_frame=(74, 52, 34), grid=(92, 62, 34), label=(150, 146, 139),
    stone_dark=(28, 28, 32), stone_dark_hi=(96, 96, 104), stone_light=(226, 224, 218),
    stone_light_hi=(255, 255, 255), x_color=(232, 96, 82), o_color=(88, 152, 232),
    shadow_alpha=150,
)  # fmt: skip

WARM = Theme(
    name="warm",
    bg=(245, 239, 229), surface1=(255, 252, 247), surface2=(240, 232, 219),
    surface3=(229, 218, 201),
    border=(219, 205, 186), ink=(48, 39, 31), muted=(124, 110, 95), faint=(176, 164, 148),
    accent=(194, 96, 44), accent_hover=(212, 114, 60), accent_ink=(255, 255, 255),
    win=(64, 146, 86), lose=(196, 72, 60), last_move=(18, 150, 136), select=(244, 226, 205),
    heat=(214, 92, 40),
    board_light=(238, 208, 160), board_dark=(222, 182, 126), board_grain=(186, 136, 84),
    board_frame=(150, 104, 62), grid=(118, 80, 44), label=(140, 124, 106),
    stone_dark=(40, 34, 30), stone_dark_hi=(112, 100, 92), stone_light=(244, 240, 232),
    stone_light_hi=(255, 255, 255), x_color=(204, 78, 52), o_color=(52, 112, 182),
    shadow_alpha=70, dim_alpha=110,
)  # fmt: skip

THEMES = {t.name: t for t in (DARK, WARM)}
DEFAULT_THEME = "dark"
_current = THEMES[DEFAULT_THEME]

# cỡ chữ (4 cấp + wordmark) và lưới 8 px
CAPTION, BODY, TITLE, DISPLAY, WORDMARK = 14, 16, 20, 30, 52


def space(n: float) -> int:
    """Khoảng cách theo lưới 8 px."""
    return int(round(8 * n))


def current_theme() -> Theme:
    return _current


T = current_theme  # viết tắt trong code vẽ


def set_theme(name: str) -> Theme:
    """Đổi theme toàn cục (`dark` / `warm`)."""
    global _current
    _current = THEMES[name]
    return _current


# ---------------------------------------------------------------- vẽ cơ bản
def ellipsize(text: str, font: pygame.font.Font, width: int) -> str:
    """Cắt `text` (thêm …) cho vừa `width` px."""
    if font.size(text)[0] <= width:
        return text
    while text and font.size(text + "…")[0] > width:
        text = text[:-1]
    return text + "…"


def draw_text(surf: pygame.Surface, text: str, pos: tuple[int, int], size: int = BODY,
              color: Color | None = None, bold: bool = False, anchor: str = "topleft",
              max_width: int | None = None, weight: str | None = None) -> pygame.Rect:  # fmt: skip
    """Vẽ một dòng chữ (ảnh chữ cache trong `render.text`); trả rect đã vẽ."""
    w = weight or ("semibold" if bold else "regular")
    if max_width is not None:
        text = ellipsize(text, get_font(size, weight=w), max_width)
    img = render.text(text, size, w, color or T().ink)
    rect = img.get_rect(**{anchor: pos})
    surf.blit(img, rect)
    return rect


def wrap_text(text: str, size: int, width: int, weight: str = "regular") -> list[str]:
    """Gói `text` thành các dòng rộng ≤ `width` px (theo từ)."""
    font = get_font(size, weight=weight)
    lines: list[str] = []
    cur = ""
    for word in text.split():
        cand = f"{cur} {word}".strip()
        if cur and font.size(cand)[0] > width:
            lines.append(cur)
            cur = word
        else:
            cur = cand
    if cur:
        lines.append(cur)
    return lines


def panel(surf: pygame.Surface, rect: pygame.Rect, color: Color | None = None,
          radius: int | None = None, shadow: bool = False) -> None:  # fmt: skip
    """Card bo góc (+ bóng đổ mềm)."""
    t = T()
    r = t.radius if radius is None else radius
    rect = pygame.Rect(rect)
    if shadow:
        blur = 14
        sh = render.shadow(rect.w, rect.h, r, blur, t.shadow_alpha)
        surf.blit(sh, (rect.x - blur, rect.y - blur + 4))
    surf.blit(render.rounded_rect(rect.w, rect.h, r, color or t.surface1), rect)


def is_click(ev: pygame.event.Event) -> bool:
    return ev.type == pygame.MOUSEBUTTONDOWN and getattr(ev, "button", 0) == 1


# ---------------------------------------------------------------- widget
class Widget:
    """Cơ sở: `rect`, `visible`, `enabled`; `handle_event` trả True nếu đã tiêu thụ sự kiện."""

    def __init__(self, rect: pygame.Rect | tuple[int, int, int, int]) -> None:
        self.rect = pygame.Rect(rect)
        self.visible = True
        self.enabled = True
        self.hover = False

    def handle_event(self, ev: pygame.event.Event) -> bool:
        if not self.visible:
            return False
        if ev.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(ev.pos)
        return False

    def update(self, dt: float) -> None:  # noqa: B027 — mặc định không có tween
        """Cập nhật tween (gọi mỗi frame)."""

    def draw(self, surf: pygame.Surface) -> None:  # pragma: no cover — lớp con vẽ
        pass


class Button(Widget):
    """Nút bấm (tùy chọn icon bên trái). Disabled → không gọi `on_click`, vẫn tiêu thụ click."""

    def __init__(self, rect, text: str, on_click: Callable[[], Any] | None = None, *,
                 primary: bool = False, danger: bool = False, size: int = BODY,
                 enabled: bool = True, hint: str | None = None, icon: str | None = None,
                 ghost: bool = False) -> None:  # fmt: skip
        super().__init__(rect)
        self.text, self.on_click = text, on_click
        self.primary, self.danger, self.ghost, self.size = primary, danger, ghost, size
        self.enabled = enabled
        self.hint = hint  # dòng chữ nhỏ dưới nhãn
        self.icon = icon
        self._bg_tween: anim.Tween | None = None  # màu nền hover (RGBA)

    def handle_event(self, ev: pygame.event.Event) -> bool:
        super().handle_event(ev)
        if not self.visible or not is_click(ev) or not self.rect.collidepoint(ev.pos):
            return False
        if self.enabled and self.on_click is not None:
            self.on_click()
        return True

    def _target_rgba(self) -> tuple[float, ...]:
        bg = self.colors()[0]
        return (*T().surface3, 0.0) if bg is None else (*bg, 255.0)

    def update(self, dt: float) -> None:
        target = self._target_rgba()
        if self._bg_tween is None:
            self._bg_tween = anim.Tween(target, target, 0.0)
        self._bg_tween.retarget(target, anim.HOVER)
        self._bg_tween.update(dt)

    def colors(self) -> tuple[Color | None, Color]:
        t = T()
        if not self.enabled:
            return (None if self.ghost else t.surface2), t.faint
        if self.primary:
            return (t.accent_hover if self.hover else t.accent), t.accent_ink
        bg = t.surface3 if self.hover else (None if self.ghost else t.surface2)
        return bg, (t.lose if self.danger else t.ink)

    def content_width(self, text: str) -> int:
        """Bề rộng (px, font thật) của icon + khoảng cách + `text` khi vẽ trên nút này."""
        label_w = get_font(self.size, weight="semibold").size(text)[0] if text else 0
        gap = 8 if text else 0
        return (self.size + 4 + gap if self.icon else 0) + label_w

    def fits(self, text: str) -> bool:
        """`text` (kèm icon) vừa nút mà không bị cắt (lề 8 px mỗi bên)."""
        return self.content_width(text) <= self.rect.w - 16

    def draw(self, surf: pygame.Surface) -> None:
        if not self.visible:
            return
        bg, ink = self.colors()
        r = T().radius
        tw = self._bg_tween
        if tw is not None and not tw.done:  # đang chuyển màu hover: tint mặt nạ (không thêm cache)
            rgba = tuple(int(round(c)) for c in tw.value)
            if rgba[3] > 0:
                surf.blit(
                    render.tint(render.rounded_mask(self.rect.w, self.rect.h, r), rgba), self.rect
                )
        elif bg is not None:
            if self.primary and self.enabled:
                panel(surf, self.rect, bg, shadow=True)
            else:
                surf.blit(render.rounded_rect(self.rect.w, self.rect.h, r, bg), self.rect)
        cy = self.rect.centery - (9 if self.hint else 0)
        icon_size = self.size + 4
        gap = 8 if self.text else 0
        total = self.content_width(self.text)
        x = self.rect.centerx - min(total, self.rect.w - 16) // 2
        if self.icon:
            img = icon(self.icon, icon_size, ink)
            surf.blit(img, img.get_rect(midleft=(x, cy)))
            x += icon_size + gap
        if self.text:
            draw_text(surf, self.text, (x, cy), self.size, ink, weight="semibold", anchor="midleft",
                      max_width=self.rect.right - 8 - x)  # fmt: skip
        if self.hint:
            draw_text(surf, self.hint, (self.rect.centerx, cy + self.size // 2 + 12), CAPTION,
                      T().faint if not self.enabled else T().muted, anchor="center",
                      max_width=self.rect.w - 16)  # fmt: skip


class IconButton(Button):
    """Nút chỉ có icon (vd. ⓘ); `tooltip` gắn ngoài nếu cần."""

    def __init__(self, rect, icon_name: str, on_click: Callable[[], Any] | None = None, *,
                 ghost: bool = True, size: int = BODY) -> None:  # fmt: skip
        super().__init__(rect, "", on_click, icon=icon_name, ghost=ghost, size=size)

    def colors(self) -> tuple[Color | None, Color]:
        t = T()
        bg = t.surface3 if self.hover else (None if self.ghost else t.surface2)
        return bg, (t.ink if self.hover else t.muted)


class Toggle(Widget):
    """Công tắc bật/tắt có nhãn bên phải."""

    TRACK = (40, 22)

    def __init__(self, rect, label: str, value: bool = False,
                 on_change: Callable[[bool], Any] | None = None) -> None:  # fmt: skip
        super().__init__(rect)
        self.label, self.value, self.on_change = label, value, on_change

    def handle_event(self, ev: pygame.event.Event) -> bool:
        super().handle_event(ev)
        if not self.visible or not is_click(ev) or not self.rect.collidepoint(ev.pos):
            return False
        if self.enabled:
            self.value = not self.value
            if self.on_change is not None:
                self.on_change(self.value)
        return True

    def draw(self, surf: pygame.Surface) -> None:
        if not self.visible:
            return
        t = T()
        tw, th = self.TRACK
        track = pygame.Rect(self.rect.x, self.rect.centery - th // 2, tw, th)
        on = self.value and self.enabled
        surf.blit(render.rounded_rect(tw, th, th // 2, t.accent if on else t.border), track)
        d = th - 6
        knob_x = track.right - 3 - d if self.value else track.x + 3
        surf.blit(
            render.circle(d, (255, 255, 255) if self.enabled else t.faint), (knob_x, track.y + 3)
        )
        draw_text(surf, self.label, (track.right + 10, self.rect.centery), BODY,
                  t.ink if self.enabled else t.faint, anchor="midleft")  # fmt: skip


class SegmentedControl(Widget):
    """Một hàng lựa chọn loại trừ nhau; mục trong `disabled` không chọn được (có thể có `hints`)."""

    def __init__(self, rect, options: Sequence[tuple[str, str]], selected: str,
                 on_change: Callable[[str], Any] | None = None, *,
                 disabled: Sequence[str] = (), hints: dict[str, str] | None = None,
                 size: int = BODY) -> None:  # fmt: skip
        super().__init__(rect)
        self.options = list(options)
        self.selected, self.on_change = selected, on_change
        self.disabled = set(disabled)
        self.hints = hints or {}
        self.size = size
        self._hover_key: str | None = None

    def segment_rects(self) -> list[tuple[str, pygame.Rect]]:
        n = len(self.options)
        w = self.rect.w // n
        return [(key, pygame.Rect(self.rect.x + i * w, self.rect.y, w if i < n - 1 else
                                  self.rect.w - w * (n - 1), self.rect.h))
                for i, (key, _) in enumerate(self.options)]  # fmt: skip

    def rect_of(self, key: str) -> pygame.Rect:
        return dict(self.segment_rects())[key]

    def handle_event(self, ev: pygame.event.Event) -> bool:
        super().handle_event(ev)
        if not self.visible:
            return False
        if ev.type == pygame.MOUSEMOTION:
            self._hover_key = next((k for k, r in self.segment_rects() if r.collidepoint(ev.pos)),
                                   None)  # fmt: skip
        if not is_click(ev) or not self.rect.collidepoint(ev.pos):
            return False
        for key, r in self.segment_rects():
            if r.collidepoint(ev.pos) and self.enabled and key not in self.disabled:
                if key != self.selected:
                    self.selected = key
                    if self.on_change is not None:
                        self.on_change(key)
        return True

    def draw(self, surf: pygame.Surface) -> None:
        if not self.visible:
            return
        t = T()
        surf.blit(render.rounded_rect(self.rect.w, self.rect.h, t.radius, t.surface2), self.rect)
        labels = dict(self.options)
        for key, r in self.segment_rects():
            dis = key in self.disabled or not self.enabled
            pill = r.inflate(-6, -6)
            if key == self.selected and not dis:
                surf.blit(render.rounded_rect(pill.w, pill.h, t.radius_small, t.accent), pill)
            elif key == self._hover_key and not dis:
                surf.blit(render.rounded_rect(pill.w, pill.h, t.radius_small, t.surface3), pill)
            sel = key == self.selected and not dis
            ink = t.faint if dis else (t.accent_ink if sel else t.ink)
            hint = self.hints.get(key)
            cy = r.centery - (8 if hint else 0)
            draw_text(
                surf,
                labels[key],
                (r.centerx, cy),
                self.size,
                ink,
                weight="semibold" if sel else "medium",
                anchor="center",
                max_width=r.w - 12,
            )
            if hint:
                draw_text(surf, hint, (r.centerx, cy + 18), CAPTION, t.faint if dis else t.muted,
                          anchor="center", max_width=r.w - 12)  # fmt: skip


class Stepper(Widget):
    """Số có nút − / +: `value` trong [lo, hi], bước `step`; `fmt` định dạng hiển thị."""

    def __init__(self, rect, value: float, step: float, lo: float, hi: float,
                 on_change: Callable[[float], Any] | None = None,
                 fmt: Callable[[float], str] = str) -> None:  # fmt: skip
        super().__init__(rect)
        self.value, self.step, self.lo, self.hi = value, step, lo, hi
        self.on_change, self.fmt = on_change, fmt
        h = self.rect.h
        self.minus = Button(
            (self.rect.x, self.rect.y, h, h), "−", lambda: self._bump(-1), ghost=True
        )
        self.plus = Button(
            (self.rect.right - h, self.rect.y, h, h), "+", lambda: self._bump(1), ghost=True
        )

    def _bump(self, sign: int) -> None:
        new = min(self.hi, max(self.lo, round(self.value + sign * self.step, 6)))
        if new != self.value:
            self.value = new
            if self.on_change is not None:
                self.on_change(new)

    def handle_event(self, ev: pygame.event.Event) -> bool:
        if not self.visible:
            return False
        return self.minus.handle_event(ev) or self.plus.handle_event(ev)

    def draw(self, surf: pygame.Surface) -> None:
        if not self.visible:
            return
        surf.blit(
            render.rounded_rect(self.rect.w, self.rect.h, T().radius, T().surface2), self.rect
        )
        self.minus.draw(surf)
        self.plus.draw(surf)
        draw_text(
            surf, self.fmt(self.value), self.rect.center, BODY, weight="semibold", anchor="center"
        )


class Modal(Widget):
    """Hộp thoại; khi `open`, mọi sự kiện chuột bị chặn (chỉ nút trong modal nhận).

    `dim_rect` = vùng làm mờ phía sau (mặc định cả màn hình)."""

    def __init__(self, rect, title: str = "", lines: Sequence[str] = (),
                 buttons: Sequence[Button] = (), title_color: Color | None = None,
                 dim_rect: pygame.Rect | None = None) -> None:  # fmt: skip
        super().__init__(rect)
        self.title, self.lines = title, list(lines)
        self.buttons = list(buttons)
        self.title_color = title_color
        self.dim_rect = dim_rect
        self.open = False

    SLIDE = 24  # px trượt lên khi mở

    def show(self, title: str, lines: Sequence[str], buttons: Sequence[Button],
             title_color: Color | None = None) -> None:  # fmt: skip
        self.title, self.lines, self.title_color = title, list(lines), title_color
        self.buttons = list(buttons)
        self.open = True
        self._tween = anim.Tween(0.0, 1.0, anim.MODAL)

    def close(self) -> None:
        self.open = False

    @property
    def progress(self) -> float:
        """0 → 1 khi đang mở (fade + slide); 1 khi animation tắt."""
        tw = getattr(self, "_tween", None)
        return 1.0 if tw is None else float(tw.value)

    def update(self, dt: float) -> None:
        if not self.open:
            return
        tw = getattr(self, "_tween", None)
        if tw is not None:
            tw.update(dt)
        for b in self.buttons:
            b.update(dt)

    def handle_event(self, ev: pygame.event.Event) -> bool:
        if not self.open:
            return False
        for b in self.buttons:
            if b.handle_event(ev):
                return True
        return ev.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEWHEEL)

    def draw(self, surf: pygame.Surface) -> None:
        if not self.open:
            return
        t = T()
        p = self.progress
        dim = self.dim_rect or surf.get_rect()
        surf.blit(render.solid(dim.w, dim.h, (*t.bg, int(t.dim_alpha * p))), dim)
        if p >= 0.999:
            self._draw_card(surf, 0)
            return
        layer = pygame.Surface(surf.get_size(), pygame.SRCALPHA)  # chỉ trong ~0,2 s khi mở
        self._draw_card(layer, int(round((1 - p) * self.SLIDE)))
        layer.set_alpha(int(255 * p))
        surf.blit(layer, (0, 0))

    def _draw_card(self, surf: pygame.Surface, dy: int) -> None:
        t = T()
        card = self.rect.move(0, dy)
        panel(surf, card, t.surface1, radius=14, shadow=True)
        accent = self.title_color or t.accent
        surf.blit(render.rounded_rect(card.w - 48, 4, 2, accent), (card.x + 24, card.y + 12))
        y = card.y + space(4)
        r = draw_text(surf, self.title, (card.centerx, y), DISPLAY, self.title_color or t.ink,
                      weight="bold", anchor="midtop", max_width=card.w - 32)  # fmt: skip
        y = r.bottom + space(1.5)
        for line in self.lines:
            r = draw_text(surf, line, (card.centerx, y), BODY, t.muted, anchor="midtop",
                          max_width=card.w - 32)  # fmt: skip
            y = r.bottom + 4
        for b in self.buttons:
            b.rect.move_ip(0, dy)
            b.draw(surf)
            b.rect.move_ip(0, -dy)


class ScrollList(Widget):
    """Danh sách dòng cuộn bằng bánh xe; click dòng → `on_click(index)`; dòng `selected` tô đậm.

    Dòng là chuỗi, hoặc tuple ô vẽ theo cột tại `columns` (px tính từ mép trái + 12).
    """

    def __init__(self, rect, row_h: int = 26,
                 on_click: Callable[[int], Any] | None = None,
                 columns: Sequence[int] = ()) -> None:  # fmt: skip
        super().__init__(rect)
        self.rows: list[str | tuple[str, ...]] = []
        self.columns = list(columns)
        self.row_h = row_h
        self.on_click = on_click
        self.offset = 0  # chỉ số dòng đầu đang hiện
        self.selected: int | None = None
        self.muted_cols: set[int] = set()  # cột vẽ màu phụ
        self.symbols: dict[str, Callable[[], pygame.Surface]] = {}  # ô = ký hiệu → vẽ sprite

    @property
    def visible_rows(self) -> int:
        return max(1, self.rect.h // self.row_h)

    @property
    def max_offset(self) -> int:
        return max(0, len(self.rows) - self.visible_rows)

    def set_rows(self, rows: Sequence[str | tuple[str, ...]], follow: bool = False) -> None:
        """Đổi nội dung; `follow` → cuộn xuống cuối nếu có dòng mới."""
        grew = len(rows) > len(self.rows)
        self.rows = list(rows)
        if follow and grew:
            self.offset = self.max_offset
        self.offset = min(self.offset, self.max_offset)

    def scroll(self, delta_rows: int) -> None:
        self.offset = min(self.max_offset, max(0, self.offset + delta_rows))

    def ensure_visible(self, index: int) -> None:
        if index < self.offset:
            self.offset = index
        elif index >= self.offset + self.visible_rows:
            self.offset = index - self.visible_rows + 1
        self.offset = min(self.max_offset, max(0, self.offset))

    def row_rect(self, index: int) -> pygame.Rect:
        return pygame.Rect(self.rect.x, self.rect.y + (index - self.offset) * self.row_h,
                           self.rect.w, self.row_h)  # fmt: skip

    def handle_event(self, ev: pygame.event.Event) -> bool:
        super().handle_event(ev)
        if not self.visible:
            return False
        if ev.type == pygame.MOUSEWHEEL:
            if self.hover:
                self.scroll(-ev.y)
                return True
            return False
        if not is_click(ev) or not self.rect.collidepoint(ev.pos):
            return False
        index = self.offset + (ev.pos[1] - self.rect.y) // self.row_h
        if 0 <= index < len(self.rows) and self.enabled and self.on_click is not None:
            self.on_click(index)
        return True

    def draw(self, surf: pygame.Surface) -> None:
        if not self.visible:
            return
        t = T()
        clip = surf.get_clip()
        surf.set_clip(self.rect)
        for i in range(self.offset, min(len(self.rows), self.offset + self.visible_rows + 1)):
            r = self.row_rect(i)
            sel = i == self.selected
            if sel:
                pill = r.inflate(-8, -2)
                surf.blit(render.rounded_rect(pill.w, pill.h, t.radius_small, t.select), pill)
            row = self.rows[i]
            cells = row if isinstance(row, tuple) else (row,)
            xs = self.columns or [0]
            for j, cell in enumerate(cells):
                x0 = xs[min(j, len(xs) - 1)]
                x1 = xs[j + 1] if j + 1 < len(xs) else r.w - 24
                if cell in self.symbols:
                    sprite = self.symbols[cell]()
                    surf.blit(sprite, sprite.get_rect(midleft=(r.x + 12 + x0, r.centery)))
                    continue
                color = t.muted if (j in self.muted_cols and not sel) else t.ink
                draw_text(surf, cell, (r.x + 12 + x0, r.centery), BODY, color,
                          weight="semibold" if sel else "regular", anchor="midleft",
                          max_width=max(10, x1 - x0 - 4))  # fmt: skip
        surf.set_clip(clip)
        if self.max_offset:  # thanh cuộn
            h = max(16, int(self.rect.h * self.visible_rows / len(self.rows)))
            y = self.rect.y + int((self.rect.h - h) * self.offset / self.max_offset)
            surf.blit(render.rounded_rect(4, h, 2, t.border), (self.rect.right - 6, y))


class Disclosure(Widget):
    """Dòng tiêu đề thu gọn / mở rộng (vd. "Tùy chọn nâng cao"): chevron › / ⌄ + nhãn."""

    def __init__(self, rect, label: str, open_: bool = False,
                 on_toggle: Callable[[bool], Any] | None = None) -> None:  # fmt: skip
        super().__init__(rect)
        self.label, self.open, self.on_toggle = label, open_, on_toggle

    def handle_event(self, ev: pygame.event.Event) -> bool:
        super().handle_event(ev)
        if not self.visible or not is_click(ev) or not self.rect.collidepoint(ev.pos):
            return False
        self.open = not self.open
        if self.on_toggle is not None:
            self.on_toggle(self.open)
        return True

    def draw(self, surf: pygame.Surface) -> None:
        if not self.visible:
            return
        t = T()
        color = t.ink if self.hover else t.muted
        img = icon("chevron_right", 18, color)
        if self.open:
            img = pygame.transform.rotate(img, -90)
        surf.blit(img, img.get_rect(midleft=(self.rect.x, self.rect.centery)))
        draw_text(surf, self.label, (self.rect.x + 26, self.rect.centery), BODY, color,
                  weight="medium", anchor="midleft")  # fmt: skip


class Tooltip(Widget):
    """Hiện hộp chữ khi chuột ở trên `rect` (vd. icon ⓘ). `lines` có thể là hàm (nội dung động)."""

    def __init__(self, rect, lines: Sequence[str] | Callable[[], Sequence[str]],
                 width: int = 340) -> None:  # fmt: skip
        super().__init__(rect)
        self._lines = lines
        self.width = width

    @property
    def lines(self) -> list[str]:
        return list(self._lines() if callable(self._lines) else self._lines)

    def box_rect(self, screen: pygame.Rect) -> pygame.Rect:
        h = space(2) + 22 * len(self.lines)
        box = pygame.Rect(0, 0, self.width, h)
        box.topright = (self.rect.right, self.rect.bottom + 6)
        if box.bottom > screen.bottom - 8:
            box.bottomright = (self.rect.right, self.rect.top - 6)
        box.clamp_ip(screen.inflate(-16, -16))
        return box

    def draw(self, surf: pygame.Surface) -> None:
        if not (self.visible and self.hover and self.lines):
            return
        t = T()
        box = self.box_rect(surf.get_rect())
        panel(surf, box, t.surface3, radius=t.radius_small, shadow=True)
        for i, line in enumerate(self.lines):
            draw_text(surf, line, (box.x + space(1.5), box.y + space(1) + 22 * i), CAPTION, t.ink,
                      max_width=box.w - space(3))  # fmt: skip
