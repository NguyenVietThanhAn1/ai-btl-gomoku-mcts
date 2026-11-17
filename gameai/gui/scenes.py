"""Các màn ngoài ván (P6.3): Home, Setup (chọn chế độ), Demo thí nghiệm, Hướng dẫn."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import pygame

from gameai.gui import brand, render
from gameai.gui.game_config import (
    AI_NAMES,
    GAMES,
    MODES,
    SIDES,
    AIChoice,
    GameConfig,
    build_preset,
)
from gameai.gui.play_scene import AppState
from gameai.gui.presets import LEVEL_NAMES, LEVELS, PRESET_ORDER, PRESETS, side_label
from gameai.gui.scene import Scene
from gameai.gui.view import OverlayOpts
from gameai.gui.widgets import (
    BODY,
    TITLE,
    WORDMARK,
    Button,
    SegmentedControl,
    Stepper,
    draw_text,
    panel,
    space,
)
from gameai.gui.widgets import current_theme as T

W, H = 1280, 720
BACK_RECT = (60, 640, 180, 50)


def level_line(cfg: GameConfig, choice: AIChoice) -> str:
    """'Khó = MCTS h300 5000 iter, c=1.4, tactics — cấu hình E3'."""
    lv = cfg.level(choice)
    return f"{LEVEL_NAMES[choice.level]} = {side_label(lv.spec)} — {lv.source_text}"


class HomeScene(Scene):
    """Màn chào: wordmark + 4 nút bên trái, bàn minh họa bên phải (không chữ kỹ thuật, D-29)."""

    name = "home"
    COL_X, COL_W, BTN_H = 120, 380, 56
    HERO = pygame.Rect(676, 132, 456, 456)

    def on_enter(self, **_: Any) -> None:
        x, w, h = self.COL_X, self.COL_W, self.BTN_H
        m = self.manager
        y0, gap = 330, space(2)
        self.buttons = {
            "play": Button((x, y0, w, h), "Chơi", lambda: m.switch("setup"), primary=True,
                           size=TITLE, icon="play"),
            "demo": Button((x, y0 + (h + gap), w, h), "Demo thí nghiệm", lambda: m.switch("demo"),
                           size=BODY + 1, icon="flask"),
            "help": Button((x, y0 + 2 * (h + gap), w, h), "Hướng dẫn", lambda: m.switch("help"),
                           size=BODY + 1, icon="book"),
            "quit": Button((x, y0 + 3 * (h + gap), w, h), "Thoát", m.quit, size=BODY + 1,
                           icon="close", ghost=True),
        }  # fmt: skip
        self.widgets = list(self.buttons.values())

    def handle_key(self, key: int) -> None:
        if key == pygame.K_ESCAPE:
            self.manager.quit()

    def draw(self, surf: pygame.Surface) -> None:
        super().draw(surf)
        t = T()
        wm = brand.draw_wordmark(surf, (0, 0), WORDMARK, t)  # đo kích thước rồi vẽ lại đúng chỗ
        surf.fill(t.bg, wm)
        brand.draw_wordmark(surf, (self.COL_X + wm.w // 2, 230), WORDMARK, t)
        surf.blit(hero_board(self.HERO.w, t.name), self.HERO)


HERO_STONES = (  # (hàng, cột, quân) trên bàn 9×9
    (2, 2, 1), (3, 3, 1), (4, 4, 1), (5, 5, 1), (6, 6, 1), (3, 5, 2), (4, 3, 2),
               (5, 4, 2), (2, 6, 2), (6, 2, 2), (4, 6, 1), (5, 3, 2))  # fmt: skip


@render._cached(4)
def hero_board(size: int, theme_name: str) -> pygame.Surface:
    """Bàn 9×9 minh họa (gỗ, quân, đường thắng chéo) cho màn Home; cache theo theme."""
    from gameai.gui.widgets import THEMES

    t = THEMES[theme_name]
    out = pygame.Surface((size, size), pygame.SRCALPHA)
    pad, blur = 24, 18
    frame = pygame.Rect(pad, pad, size - 2 * pad, size - 2 * pad)
    out.blit(
        render.shadow(frame.w, frame.h, 18, blur, t.shadow_alpha),
        (frame.x - blur, frame.y - blur + 8),
    )
    out.blit(render.rounded_rect(frame.w, frame.h, 18, t.board_frame), frame)
    inner = frame.inflate(-12, -12)
    wood = render.wood(inner.w, inner.h, t.board_light, t.board_dark, t.board_grain, seed=11).copy()
    n = 9
    cell = inner.w // n
    off = (inner.w - cell * n) // 2
    lines = pygame.Surface(inner.size, pygame.SRCALPHA)
    for i in range(n + 1):
        p = off + i * cell
        pygame.draw.line(lines, (*t.grid, 130), (off, p), (off + cell * n, p))
        pygame.draw.line(lines, (*t.grid, 130), (p, off), (p, off + cell * n))
    wood.blit(lines, (0, 0))
    wood.blit(
        render.rounded_mask(inner.w, inner.h, 14), (0, 0), special_flags=pygame.BLEND_RGBA_MULT
    )
    out.blit(wood, inner)
    d = cell - 6
    dark = render.stone(d, t.stone_dark, t.stone_dark_hi, (0, 0, 0))
    light = render.stone(d, t.stone_light, t.stone_light_hi, (150, 146, 140))
    sh = render.stone_shadow(d, max(30, t.shadow_alpha))

    def center(r: int, c: int) -> tuple[int, int]:
        return inner.x + off + c * cell + cell // 2, inner.y + off + r * cell + cell // 2

    for r, c, v in HERO_STONES:
        cx, cy = center(r, c)
        out.blit(sh, sh.get_rect(center=(cx + 1, cy + 3)))
        sprite = dark if v == 1 else light
        out.blit(sprite, sprite.get_rect(center=(cx, cy)))
    (x0, y0), (x1, y1) = center(2, 2), center(6, 6)
    thick = max(6, cell // 6)
    line = render.line(x1 - x0, y1 - y0, thick, (*t.win, 235))
    out.blit(line, (x0 - thick, y0 - thick))
    return out


class SetupScene(Scene):
    """Chọn trò, chế độ, bên, loại AI + độ khó (theo bảng D-29), seed, độ trễ (AI vs AI)."""

    name = "setup"
    LABEL_X, CTRL_X, CTRL_W = 80, 300, 900

    def __init__(self, manager) -> None:
        super().__init__(manager)
        self.cfg = GameConfig()

    def on_enter(self, **_: Any) -> None:
        self._build()

    def set(self, **changes: Any) -> None:
        self.cfg = replace(self.cfg, **changes)
        self._build()

    def _row(self, label: str, height: int = 44) -> int:
        """Cấp một hàng: ghi nhãn, trả y của control, dời con trỏ."""
        y = self._y
        self.rows.append((label, y + height // 2))
        self._y += height + 16
        return y

    def _build(self) -> None:
        cfg, x, w = self.cfg, self.CTRL_X, self.CTRL_W
        self.rows: list[tuple[str, int]] = []  # (nhãn, tâm y) để vẽ
        self.controls: dict[str, Any] = {}
        self._y = 100
        c = self.controls
        y = self._row("Trò chơi", 54)
        c["game"] = SegmentedControl((x, y, w, 54), [(k, v[1]) for k, v in GAMES.items()], cfg.game,
                                     lambda k: self.set(game=k), disabled=["xiangqi"],
                                     hints={"xiangqi": "sắp có — P6.2"})  # fmt: skip
        y = self._row("Chế độ")
        c["mode"] = SegmentedControl((x, y, w, 44), list(MODES.items()), cfg.mode,
                                     lambda k: self.set(mode=k))  # fmt: skip
        if cfg.mode == "human_ai":
            y = self._row("Bạn cầm")
            c["side"] = SegmentedControl((x, y, w, 44), list(SIDES.items()), cfg.side,
                                         lambda k: self.set(side=k))  # fmt: skip
            self._ai_row("AI", "ai")
        elif cfg.mode == "ai_ai":
            self._ai_row("AI cầm X", "ai")
            self._ai_row("AI cầm O", "ai_o")
            y = self._row("Độ trễ AI")
            c["delay"] = Stepper((x, y, 220, 44), cfg.delay, 0.25, 0.0, 5.0,
                                 lambda v: self.set(delay=v),
                                 lambda v: f"{v:.2f} s".replace(".", ","))  # fmt: skip
        y = self._row("Seed")
        c["seed"] = Stepper((x, y, 220, 44), cfg.seed, 1, 0, 9999,
                            lambda v: self.set(seed=int(v)), lambda v: str(int(v)))  # fmt: skip
        self.info_y = self._y
        m = self.manager
        self.back = Button(BACK_RECT, "Quay lại", lambda: m.switch("home"))
        self.start = Button((W - 240, 640, 180, 50), "Bắt đầu", self.on_start, primary=True,
                            size=22)  # fmt: skip
        self.widgets = [*c.values(), self.back, self.start]

    def _ai_row(self, label: str, field: str) -> None:
        """Hai control cạnh nhau: loại AI | độ khó, cho `cfg.ai` hoặc `cfg.ai_o`."""
        choice: AIChoice = getattr(self.cfg, field)
        x, half = self.CTRL_X, (self.CTRL_W - 20) // 2
        y = self._row(label)
        self.controls[f"{field}_kind"] = SegmentedControl(
            (x, y, half, 44), list(AI_NAMES.items()), choice.kind,
            lambda k: self.set(**{field: replace(choice, kind=k)}))  # fmt: skip
        self.controls[f"{field}_level"] = SegmentedControl(
            (x + half + 20, y, half, 44), [(lv, LEVEL_NAMES[lv]) for lv in LEVELS], choice.level,
            lambda k: self.set(**{field: replace(choice, level=k)}))  # fmt: skip

    def ai_lines(self) -> list[str]:
        """Dòng cấu hình thật của từng bên AI (hiện dưới các lựa chọn)."""
        cfg = self.cfg
        if cfg.game == "xiangqi" or cfg.mode == "two_players":
            return ["2 người cùng máy: không có AI."] if cfg.mode == "two_players" else []
        if cfg.mode == "human_ai":
            return [f"AI: {level_line(cfg, cfg.ai)}"]
        return [f"X: {level_line(cfg, cfg.ai)}", f"O: {level_line(cfg, cfg.ai_o)}"]

    def on_start(self) -> None:
        cfg = self.cfg
        preset = build_preset(cfg)
        state = AppState(None, cfg.seed, delay=cfg.delay if cfg.mode == "ai_ai" else None,
                         overlay=OverlayOpts(False, False), base=preset, config=cfg)  # fmt: skip
        self.manager.switch("play", state=state)

    def draw(self, surf: pygame.Surface) -> None:
        super().draw(surf)
        draw_text(surf, "Chọn chế độ chơi", (W // 2, 36), 34, T().ink, bold=True, anchor="midtop")
        for label, cy in self.rows:
            draw_text(surf, label, (self.LABEL_X, cy), 20, T().ink, bold=True, anchor="midleft")
        lines = self.ai_lines()
        if lines:
            box = pygame.Rect(self.CTRL_X, self.info_y, self.CTRL_W, 18 + 26 * len(lines))
            panel(surf, box)
            for i, line in enumerate(lines):
                draw_text(surf, line, (box.x + 14, box.y + 10 + 26 * i), 17, T().accent,
                          max_width=box.w - 28)  # fmt: skip


class DemoScene(Scene):
    """3 preset P6.1 giữ nguyên spec thí nghiệm (D-28)."""

    name = "demo"

    def on_enter(self, **_: Any) -> None:
        m = self.manager
        self.buttons: dict[str, Button] = {}
        for i, key in enumerate(PRESET_ORDER):
            p = PRESETS[key]
            hint = f"X: {side_label(p.x)}   ·   O: {side_label(p.o)}"
            self.buttons[key] = Button((190, 160 + i * 130, 900, 100), p.title,
                                       lambda k=key: m.switch("play", state=AppState(k)),
                                       size=24, hint=hint)  # fmt: skip
        self.widgets = [
            *self.buttons.values(),
            Button(BACK_RECT, "Quay lại", lambda: m.switch("home")),
        ]

    def draw(self, surf: pygame.Surface) -> None:
        super().draw(surf)
        draw_text(surf, "Demo thí nghiệm", (W // 2, 40), 34, T().ink, bold=True, anchor="midtop")
        draw_text(surf, "Cấu hình thí nghiệm: spec giống hệt E2 / E3 (phím 1 / 2 / 3 trong ván).",
                  (W // 2, 92), 18, T().muted, anchor="midtop")  # fmt: skip


HELP_LINES = [
    ("Luật", True),
    (
        "Hai bên lần lượt đặt quân X (đi trước) và O. 3×3: 3 quân thẳng hàng thắng; 15×15: 5 quân.",
        False,
    ),
    ("Thẳng hàng theo hàng ngang, dọc hoặc chéo. Bàn đầy mà không ai thắng → hòa.", False),
    ("Trong ván", True),
    ("Click ô trống để đi. Đi lại: lùi về lượt trước của bạn (khóa khi AI đang nghĩ).", False),
    (
        "Phân tích: tô các nước ở gốc cây MCTS theo N (số lần thăm), W/N = tỉ lệ thắng ước lượng.",
        False,
    ),
    ("Hết ván: Xem lại bằng ‹ › hoặc phím ← →, hoặc click dòng trong lịch sử.", False),
    ("Phím tắt (giữ từ bản demo P6.1)", True),
    ("1 / 2 / 3: preset thí nghiệm    N: ván mới    S: đổi bên    [ ]: seed −/+", False),
    ("I / K: iteration MCTS ×2 / ÷2    − / =: độ trễ AI    O: Phân tích    W: thêm W/N", False),
    ("Space: tạm dừng AI    Esc: đóng hộp thoại / thoát (trong ván), về menu (màn khác)", False),
]


class HelpScene(Scene):
    name = "help"

    def on_enter(self, **_: Any) -> None:
        self.widgets = [Button(BACK_RECT, "Quay lại", lambda: self.manager.switch("home"))]

    def draw(self, surf: pygame.Surface) -> None:
        super().draw(surf)
        draw_text(surf, "Hướng dẫn", (W // 2, 40), 34, T().ink, bold=True, anchor="midtop")
        y = 110
        for text, header in HELP_LINES:
            if header:
                y += 10
                draw_text(surf, text, (120, y), 22, T().accent, bold=True)
                y += 34
            else:
                draw_text(surf, text, (140, y), 18, T().ink, max_width=W - 260)
                y += 30
