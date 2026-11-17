"""Các màn ngoài ván (P6.3): Home, Setup (chọn chế độ), Demo thí nghiệm, Hướng dẫn."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import pygame

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
    ACCENT,
    INK,
    MUTED,
    PANEL,
    Button,
    SegmentedControl,
    Stepper,
    draw_text,
)

W, H = 1280, 720
BACK_RECT = (60, 640, 180, 50)


def level_line(cfg: GameConfig, choice: AIChoice) -> str:
    """'Khó = MCTS h300 5000 iter, c=1.4, tactics — cấu hình E3'."""
    lv = cfg.level(choice)
    return f"{LEVEL_NAMES[choice.level]} = {side_label(lv.spec)} — {lv.source_text}"


class HomeScene(Scene):
    name = "home"

    def on_enter(self, **_: Any) -> None:
        x, w, h = W // 2 - 160, 320, 58
        m = self.manager
        self.buttons = {
            "play": Button(
                (x, 290, w, h), "Chơi", lambda: m.switch("setup"), primary=True, size=24
            ),
            "demo": Button((x, 360, w, h), "Demo thí nghiệm", lambda: m.switch("demo"), size=22),
            "help": Button((x, 430, w, h), "Hướng dẫn", lambda: m.switch("help"), size=22),
            "quit": Button((x, 500, w, h), "Thoát", m.quit, size=22),
        }
        self.widgets = list(self.buttons.values())

    def handle_key(self, key: int) -> None:
        if key == pygame.K_ESCAPE:
            self.manager.quit()

    def draw(self, surf: pygame.Surface) -> None:
        super().draw(surf)
        draw_text(surf, "Caro AI", (W // 2, 110), 72, INK, bold=True, anchor="midtop")
        draw_text(surf, "Minimax · Alpha-Beta · MCTS-UCT", (W // 2, 200), 24, ACCENT,
                  anchor="midtop")  # fmt: skip
        draw_text(surf, "BTL Trí tuệ nhân tạo — k-in-a-row (3×3, 15×15)", (W // 2, 236), 18, MUTED,
                  anchor="midtop")  # fmt: skip


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
        draw_text(surf, "Chọn chế độ chơi", (W // 2, 36), 34, INK, bold=True, anchor="midtop")
        for label, cy in self.rows:
            draw_text(surf, label, (self.LABEL_X, cy), 20, INK, bold=True, anchor="midleft")
        lines = self.ai_lines()
        if lines:
            box = pygame.Rect(self.CTRL_X, self.info_y, self.CTRL_W, 18 + 26 * len(lines))
            pygame.draw.rect(surf, PANEL, box, border_radius=8)
            for i, line in enumerate(lines):
                draw_text(surf, line, (box.x + 14, box.y + 10 + 26 * i), 17, ACCENT,
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
        draw_text(surf, "Demo thí nghiệm", (W // 2, 40), 34, INK, bold=True, anchor="midtop")
        draw_text(surf, "Cấu hình thí nghiệm: spec giống hệt E2 / E3 (phím 1 / 2 / 3 trong ván).",
                  (W // 2, 92), 18, MUTED, anchor="midtop")  # fmt: skip


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
        draw_text(surf, "Hướng dẫn", (W // 2, 40), 34, INK, bold=True, anchor="midtop")
        y = 110
        for text, header in HELP_LINES:
            if header:
                y += 10
                draw_text(surf, text, (120, y), 22, ACCENT, bold=True)
                y += 34
            else:
                draw_text(surf, text, (140, y), 18, INK, max_width=W - 260)
                y += 30
