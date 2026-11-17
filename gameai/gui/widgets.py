"""Widget pygame tự viết (P6.3): Button, Toggle, SegmentedControl, Stepper, Modal, ScrollList."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

import pygame

from gameai.gui.view import get_font

# ---------------------------------------------------------------- theme (tông tối kiểu chess.com)
BG = (49, 46, 43)
PANEL = (38, 36, 33)
CARD = (60, 57, 53)
CARD_ACTIVE = (75, 72, 66)
INK = (235, 235, 230)
MUTED = (160, 156, 150)
ACCENT = (129, 182, 76)  # xanh lá nút chính
ACCENT_HOVER = (149, 200, 94)
BUTTON = (75, 72, 66)
BUTTON_HOVER = (95, 92, 86)
DISABLED_BG = (58, 56, 52)
DISABLED_INK = (110, 107, 102)
DANGER = (200, 70, 60)
BORDER = (90, 87, 82)
SELECT = (100, 96, 60)
OVERLAY_DIM = (0, 0, 0, 150)
RADIUS = 6


def ellipsize(text: str, font: pygame.font.Font, width: int) -> str:
    """Cắt `text` (thêm …) cho vừa `width` px."""
    if font.size(text)[0] <= width:
        return text
    while text and font.size(text + "…")[0] > width:
        text = text[:-1]
    return text + "…"


def draw_text(surf: pygame.Surface, text: str, pos: tuple[int, int], size: int = 18,
              color=INK, bold: bool = False, anchor: str = "topleft",
              max_width: int | None = None) -> pygame.Rect:  # fmt: skip
    """Vẽ một dòng chữ; trả rect đã vẽ."""
    font = get_font(size, bold)
    if max_width is not None:
        text = ellipsize(text, font, max_width)
    img = font.render(text, True, color)
    rect = img.get_rect(**{anchor: pos})
    surf.blit(img, rect)
    return rect


def is_click(ev: pygame.event.Event) -> bool:
    return ev.type == pygame.MOUSEBUTTONDOWN and getattr(ev, "button", 0) == 1


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

    def draw(self, surf: pygame.Surface) -> None:  # pragma: no cover — lớp con vẽ
        pass


class Button(Widget):
    """Nút bấm. Disabled → không gọi `on_click`, vẫn tiêu thụ click trong rect."""

    def __init__(self, rect, text: str, on_click: Callable[[], Any] | None = None, *,
                 primary: bool = False, danger: bool = False, size: int = 20,
                 enabled: bool = True, hint: str | None = None) -> None:  # fmt: skip
        super().__init__(rect)
        self.text, self.on_click = text, on_click
        self.primary, self.danger, self.size = primary, danger, size
        self.enabled = enabled
        self.hint = hint  # dòng chữ nhỏ dưới nhãn (vd. "sắp có — P6.2")

    def handle_event(self, ev: pygame.event.Event) -> bool:
        super().handle_event(ev)
        if not self.visible or not is_click(ev) or not self.rect.collidepoint(ev.pos):
            return False
        if self.enabled and self.on_click is not None:
            self.on_click()
        return True

    def draw(self, surf: pygame.Surface) -> None:
        if not self.visible:
            return
        if not self.enabled:
            bg, ink = DISABLED_BG, DISABLED_INK
        elif self.primary:
            bg, ink = (ACCENT_HOVER if self.hover else ACCENT), (255, 255, 255)
        elif self.danger:
            bg, ink = (BUTTON_HOVER if self.hover else BUTTON), (240, 140, 130)
        else:
            bg, ink = (BUTTON_HOVER if self.hover else BUTTON), INK
        pygame.draw.rect(surf, bg, self.rect, border_radius=RADIUS)
        cy = self.rect.centery - (8 if self.hint else 0)
        draw_text(surf, self.text, (self.rect.centerx, cy), self.size, ink, bold=True,
                  anchor="center", max_width=self.rect.w - 10)  # fmt: skip
        if self.hint:
            draw_text(surf, self.hint, (self.rect.centerx, cy + self.size // 2 + 10), 14,
                      DISABLED_INK if not self.enabled else MUTED, anchor="center",
                      max_width=self.rect.w - 10)  # fmt: skip


class Toggle(Widget):
    """Công tắc bật/tắt có nhãn bên phải."""

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
        track = pygame.Rect(self.rect.x, self.rect.centery - 11, 40, 22)
        on = self.value and self.enabled
        pygame.draw.rect(surf, ACCENT if on else BORDER, track, border_radius=11)
        knob_x = track.right - 11 if self.value else track.x + 11
        pygame.draw.circle(surf, (245, 245, 240), (knob_x, track.centery), 9)
        draw_text(surf, self.label, (track.right + 8, self.rect.centery), 17,
                  INK if self.enabled else DISABLED_INK, anchor="midleft")  # fmt: skip


class SegmentedControl(Widget):
    """Một hàng lựa chọn loại trừ nhau; mục trong `disabled` không chọn được (có thể có `hints`)."""

    def __init__(self, rect, options: Sequence[tuple[str, str]], selected: str,
                 on_change: Callable[[str], Any] | None = None, *,
                 disabled: Sequence[str] = (), hints: dict[str, str] | None = None,
                 size: int = 17) -> None:  # fmt: skip
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
        pygame.draw.rect(surf, CARD, self.rect, border_radius=RADIUS)
        labels = dict(self.options)
        for key, r in self.segment_rects():
            dis = key in self.disabled or not self.enabled
            if key == self.selected and not dis:
                pygame.draw.rect(surf, ACCENT, r.inflate(-4, -4), border_radius=RADIUS)
            elif key == self._hover_key and not dis:
                pygame.draw.rect(surf, BUTTON_HOVER, r.inflate(-4, -4), border_radius=RADIUS)
            ink = DISABLED_INK if dis else ((255, 255, 255) if key == self.selected else INK)
            hint = self.hints.get(key)
            cy = r.centery - (7 if hint else 0)
            draw_text(surf, labels[key], (r.centerx, cy), self.size, ink, bold=key == self.selected,
                      anchor="center", max_width=r.w - 8)  # fmt: skip
            if hint:
                draw_text(surf, hint, (r.centerx, cy + 17), 13, DISABLED_INK if dis else MUTED,
                          anchor="center", max_width=r.w - 8)  # fmt: skip


class Stepper(Widget):
    """Số có nút − / +: `value` trong [lo, hi], bước `step`; `fmt` định dạng hiển thị."""

    def __init__(self, rect, value: float, step: float, lo: float, hi: float,
                 on_change: Callable[[float], Any] | None = None,
                 fmt: Callable[[float], str] = str) -> None:  # fmt: skip
        super().__init__(rect)
        self.value, self.step, self.lo, self.hi = value, step, lo, hi
        self.on_change, self.fmt = on_change, fmt
        h = self.rect.h
        self.minus = Button((self.rect.x, self.rect.y, h, h), "−", lambda: self._bump(-1))
        self.plus = Button((self.rect.right - h, self.rect.y, h, h), "+", lambda: self._bump(1))

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
        pygame.draw.rect(surf, CARD, self.rect, border_radius=RADIUS)
        self.minus.draw(surf)
        self.plus.draw(surf)
        draw_text(surf, self.fmt(self.value), self.rect.center, 18, INK, bold=True, anchor="center")


class Modal(Widget):
    """Hộp thoại giữa màn hình; khi `open`, mọi sự kiện chuột bị chặn (chỉ nút trong modal nhận)."""

    def __init__(self, rect, title: str = "", lines: Sequence[str] = (),
                 buttons: Sequence[Button] = (), title_color=INK) -> None:  # fmt: skip
        super().__init__(rect)
        self.title, self.lines = title, list(lines)
        self.buttons = list(buttons)
        self.title_color = title_color
        self.open = False

    def show(self, title: str, lines: Sequence[str], buttons: Sequence[Button],
             title_color=INK) -> None:  # fmt: skip
        self.title, self.lines, self.buttons, self.title_color = (
            title,
            list(lines),
            list(buttons),
            title_color,
        )
        self.open = True

    def close(self) -> None:
        self.open = False

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
        dim = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        dim.fill(OVERLAY_DIM)
        surf.blit(dim, (0, 0))
        pygame.draw.rect(surf, PANEL, self.rect, border_radius=12)
        pygame.draw.rect(surf, BORDER, self.rect, width=2, border_radius=12)
        y = self.rect.y + 28
        r = draw_text(surf, self.title, (self.rect.centerx, y), 34, self.title_color, bold=True,
                      anchor="midtop", max_width=self.rect.w - 30)  # fmt: skip
        y = r.bottom + 12
        for line in self.lines:
            r = draw_text(surf, line, (self.rect.centerx, y), 18, MUTED, anchor="midtop",
                          max_width=self.rect.w - 30)  # fmt: skip
            y = r.bottom + 4
        for b in self.buttons:
            b.draw(surf)


class ScrollList(Widget):
    """Danh sách dòng cuộn bằng bánh xe; click dòng → `on_click(index)`; dòng `selected` tô đậm.

    Dòng là chuỗi, hoặc tuple ô vẽ theo cột tại `columns` (px tính từ mép trái + 10).
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
        pygame.draw.rect(surf, CARD, self.rect, border_radius=RADIUS)
        clip = surf.get_clip()
        surf.set_clip(self.rect)
        for i in range(self.offset, min(len(self.rows), self.offset + self.visible_rows + 1)):
            r = self.row_rect(i)
            if i == self.selected:
                pygame.draw.rect(surf, SELECT, r)
            elif i % 2:
                pygame.draw.rect(surf, (55, 52, 48), r)
            row = self.rows[i]
            cells = row if isinstance(row, tuple) else (row,)
            xs = self.columns or [0]
            for j, cell in enumerate(cells):
                x0 = xs[min(j, len(xs) - 1)]
                x1 = xs[j + 1] if j + 1 < len(xs) else r.w - 20
                draw_text(surf, cell, (r.x + 10 + x0, r.centery), 17,
                          INK if i == self.selected else (215, 212, 205), bold=i == self.selected,
                          anchor="midleft", max_width=max(10, x1 - x0 - 4))  # fmt: skip
        surf.set_clip(clip)
        if self.max_offset:  # thanh cuộn
            h = self.rect.h * self.visible_rows / len(self.rows)
            y = self.rect.y + (self.rect.h - h) * self.offset / self.max_offset
            pygame.draw.rect(surf, BORDER, (self.rect.right - 5, y, 4, h), border_radius=2)
