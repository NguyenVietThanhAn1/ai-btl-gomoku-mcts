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
from gameai.gui.presets import (
    LEVEL_NAMES,
    LEVELS,
    PRESET_ORDER,
    PRESETS,
    experiment_source,
    find_level,
    side_label,
)
from gameai.gui.scene import Scene
from gameai.gui.view import OverlayOpts
from gameai.gui.widgets import (
    BODY,
    CAPTION,
    DISPLAY,
    TITLE,
    WORDMARK,
    Button,
    Disclosure,
    IconButton,
    SegmentedControl,
    Stepper,
    Tooltip,
    draw_text,
    panel,
    space,
    wrap_text,
)
from gameai.gui.widgets import current_theme as T

W, H = 1280, 720
BACK_RECT = (60, 640, 180, 50)


def level_line(cfg: GameConfig, choice: AIChoice) -> str:
    """'Khó = MCTS h300 5000 iter, c=1.4, tactics · cấu hình E3'."""
    lv = cfg.level(choice)
    return f"{LEVEL_NAMES[choice.level]} = {side_label(lv.spec)} · {lv.source_text}"


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
            "play": Button(
                (x, y0, w, h),
                "Chơi",
                lambda: m.switch("setup"),
                primary=True,
                size=TITLE,
                icon="play",
            ),
            "demo": Button(
                (x, y0 + (h + gap), w, h),
                "Demo thí nghiệm",
                lambda: m.switch("demo"),
                size=BODY + 1,
                icon="flask",
            ),
            "help": Button(
                (x, y0 + 2 * (h + gap), w, h),
                "Hướng dẫn",
                lambda: m.switch("help"),
                size=BODY + 1,
                icon="book",
            ),
            "quit": Button(
                (x, y0 + 3 * (h + gap), w, h),
                "Thoát",
                m.quit,
                size=BODY + 1,
                icon="close",
                ghost=True,
            ),
        }
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
    (2, 2, 1),
    (3, 3, 1),
    (4, 4, 1),
    (5, 5, 1),
    (6, 6, 1),
    (3, 5, 2),
    (4, 3, 2),
    (5, 4, 2),
    (2, 6, 2),
    (6, 2, 2),
    (4, 6, 1),
    (5, 3, 2),
)


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
    """Chọn trò, chế độ, bên, đối thủ (loại AI + độ khó, D-29), độ trễ AI, seed (nâng cao)."""

    name = "setup"
    CARD = pygame.Rect(80, 112, 1120, 0)  # cao theo số hàng
    LABEL_X, CTRL_X, CTRL_W = 112, 320, 848

    def __init__(self, manager) -> None:
        super().__init__(manager)
        self.cfg = GameConfig()
        self.advanced = False  # "Tùy chọn nâng cao" thu gọn mặc định

    def on_enter(self, **_: Any) -> None:
        self._build()

    def set(self, **changes: Any) -> None:
        self.cfg = replace(self.cfg, **changes)
        self._build()

    def _toggle_advanced(self, open_: bool) -> None:
        self.advanced = open_
        self._build()

    def side_name(self, side: str) -> str:
        """'X'/'O' → tên bên của trò (X/O, Đen/Trắng ở 15×15, Đỏ/Đen ở cờ tướng)."""
        return self.cfg.side_name(side)

    def _row(self, label: str, height: int = 44) -> int:
        """Cấp một hàng: ghi nhãn, trả y của control, dời con trỏ."""
        y = self._y
        self.rows.append((label, y + height // 2))
        self._y += height + space(2)
        return y

    def _build(self) -> None:
        cfg, x, w = self.cfg, self.CTRL_X, self.CTRL_W
        self.rows: list[tuple[str, int]] = []  # (nhãn, tâm y) để vẽ
        self.controls: dict[str, Any] = {}
        self.tips: list[Tooltip] = []
        self.summary: list[tuple[str, str, int]] = []  # (nhãn bên, "MCTS · Khó", y)
        self._y = self.CARD.y + space(3)
        c = self.controls
        y = self._row("Trò chơi", 56)
        c["game"] = SegmentedControl(
            (x, y, w, 56),
            [(k, v[1]) for k, v in GAMES.items()],
            cfg.game,
            lambda k: self.set(game=k),
        )
        y = self._row("Chế độ")
        c["mode"] = SegmentedControl(
            (x, y, w, 44), list(MODES.items()), cfg.mode, lambda k: self.set(mode=k)
        )
        if cfg.mode == "human_ai":
            y = self._row("Bạn cầm")
            sides = [
                ("X", f"{self.side_name('X')} · đi trước"),
                ("O", f"{self.side_name('O')} · đi sau"),
                ("random", SIDES["random"]),
            ]
            c["side"] = SegmentedControl((x, y, w, 44), sides, cfg.side, lambda k: self.set(side=k))
            self._ai_row("Đối thủ", "ai", "Đối thủ")
        elif cfg.mode == "ai_ai":
            self._ai_row(f"AI {self.side_name('X')}", "ai", self.side_name("X"))
            self._ai_row(f"AI {self.side_name('O')}", "ai_o", self.side_name("O"))
            y = self._row("Độ trễ AI")
            c["delay"] = Stepper(
                (x, y, 240, 44),
                cfg.delay,
                0.25,
                0.0,
                5.0,
                lambda v: self.set(delay=v),
                lambda v: f"{v:.2f} s".replace(".", ","),
            )
        y = self._y
        c["advanced"] = Disclosure(
            (x, y, 260, 32), "Tùy chọn nâng cao", self.advanced, self._toggle_advanced
        )
        self._y += 32 + space(1.5)
        if self.advanced:
            y = self._row("Seed")
            c["seed"] = Stepper(
                (x, y, 240, 44),
                cfg.seed,
                1,
                0,
                9999,
                lambda v: self.set(seed=int(v)),
                lambda v: str(int(v)),
            )
        self.card = pygame.Rect(
            self.CARD.x, self.CARD.y, self.CARD.w, self._y - self.CARD.y + space(1)
        )
        m = self.manager
        self.back = Button(
            (80, 632, 200, 52),
            "Quay lại",
            lambda: m.switch("home"),
            icon="chevron_left",
            ghost=True,
        )
        self.start = Button(
            (W - 300, 632, 220, 52), "Bắt đầu", self.on_start, primary=True, size=TITLE, icon="play"
        )
        self.widgets = [*c.values(), self.back, self.start, *self.tips]

    def _ai_row(self, label: str, field: str, who: str) -> None:
        """Loại AI | độ khó + dòng tóm tắt "MCTS · Khó" có ⓘ (chi tiết + nguồn trong tooltip)."""
        choice: AIChoice = getattr(self.cfg, field)
        x, half = self.CTRL_X, (self.CTRL_W - space(2)) // 2
        y = self._row(label)
        self.controls[f"{field}_kind"] = SegmentedControl(
            (x, y, half, 44),
            list(AI_NAMES.items()),
            choice.kind,
            lambda k: self.set(**{field: replace(choice, kind=k)}),
        )
        self.controls[f"{field}_level"] = SegmentedControl(
            (x + half + space(2), y, half, 44),
            [(lv, LEVEL_NAMES[lv]) for lv in LEVELS],
            choice.level,
            lambda k: self.set(**{field: replace(choice, level=k)}),
        )
        sy = self._y + 4  # tâm dòng tóm tắt dưới control
        name = choice.label()
        name_w = render.text(name, BODY, "semibold", T().ink).get_width()
        label_w = render.text(f"{who}:", BODY, "regular", T().muted).get_width()
        info = IconButton((x + label_w + 8 + name_w + 6, sy - 13, 26, 26), "info", size=CAPTION + 2)
        lv = self.cfg.level(choice)
        self.tips.append(
            Tooltip(
                info.rect,
                [side_label(lv.spec), lv.source_text[:1].upper() + lv.source_text[1:]],
                width=420,
            )
        )
        self.controls[f"{field}_info"] = info
        self.summary.append((who, name, sy))
        self._y += 30

    def ai_lines(self) -> list[str]:
        """Chi tiết cấu hình thật + nguồn của từng bên AI (nội dung tooltip ⓘ)."""
        cfg = self.cfg
        if cfg.mode == "two_players":
            return ["2 người cùng máy: không có AI."]
        if cfg.mode == "human_ai":
            return [f"AI: {level_line(cfg, cfg.ai)}"]
        return [
            f"{self.side_name('X')}: {level_line(cfg, cfg.ai)}",
            f"{self.side_name('O')}: {level_line(cfg, cfg.ai_o)}",
        ]

    def on_start(self) -> None:
        cfg = self.cfg
        preset = build_preset(cfg)
        state = AppState(
            None,
            cfg.seed,
            delay=cfg.delay if cfg.mode == "ai_ai" else None,
            overlay=OverlayOpts(False, False),
            base=preset,
            config=cfg,
        )
        self.manager.switch("play", state=state)

    def draw(self, surf: pygame.Surface) -> None:
        t = T()
        surf.fill(t.bg)
        draw_text(surf, "Ván mới", (80, 36), DISPLAY, t.ink, weight="bold")
        draw_text(surf, "Chọn trò chơi, đối thủ và độ khó.", (80, 78), BODY, t.muted)
        panel(surf, self.card, t.surface1, shadow=True)
        for label, cy in self.rows:
            draw_text(
                surf, label, (self.LABEL_X, cy), BODY, t.ink, weight="semibold", anchor="midleft"
            )
        for who, name, sy in self.summary:
            r = draw_text(surf, f"{who}:", (self.CTRL_X, sy), BODY, t.muted, anchor="midleft")
            draw_text(
                surf, name, (r.right + 8, sy), BODY, t.accent, weight="semibold", anchor="midleft"
            )
        for w in self.widgets:
            if not isinstance(w, Tooltip):
                w.draw(surf)
        for tip in self.tips:
            tip.draw(surf)


class DemoScene(Scene):
    """3 preset P6.1 giữ nguyên spec thí nghiệm (D-28); nhãn "Cấu hình thí nghiệm" hiện rõ."""

    name = "demo"

    @staticmethod
    def sources(key: str) -> str:
        """Nguồn thí nghiệm của các bên AI, tra ngược từ spec (không gõ tay): 'E2', 'E3 · E3/E5'."""
        p = PRESETS[key]
        n = int(p.game.params.get("n", 15))
        tags = []
        for spec in (p.x, p.o):
            if spec is None:
                continue
            found = find_level(spec, n)
            tag = found[1].source if found is not None else experiment_source(spec, n)
            if tag:
                tags.append(tag)
        return " · ".join(dict.fromkeys(tags))

    def on_enter(self, **_: Any) -> None:
        m = self.manager
        self.buttons: dict[str, Button] = {}
        for i, key in enumerate(PRESET_ORDER):
            rect = (80, 152 + i * 136, 1120, 112)
            self.buttons[key] = Button(rect, "", lambda k=key: m.switch("play", state=AppState(k)))
        self.back = Button(
            (80, 632, 200, 52),
            "Quay lại",
            lambda: m.switch("home"),
            icon="chevron_left",
            ghost=True,
        )
        self.widgets = [*self.buttons.values(), self.back]

    @staticmethod
    def _draw_thumb(surf: pygame.Surface, key: str, center: tuple[int, int], t) -> None:
        """Hình nhỏ: chữ X (3×3) hoặc quân Đen/Trắng (15×15)."""
        bg = pygame.Rect(0, 0, 56, 56)
        bg.center = center
        surf.blit(render.rounded_rect(56, 56, 12, t.surface2), bg)
        if PRESETS[key].game.params.get("n", 15) <= 5:
            img = render.x_mark(40, t.x_color)
            surf.blit(img, img.get_rect(center=center))
            return
        dark = render.stone(30, t.stone_dark, t.stone_dark_hi, (0, 0, 0))
        light = render.stone(30, t.stone_light, t.stone_light_hi, (150, 146, 140))
        surf.blit(light, light.get_rect(center=(center[0] + 7, center[1] + 6)))
        surf.blit(dark, dark.get_rect(center=(center[0] - 7, center[1] - 6)))

    @staticmethod
    def side_names(key: str) -> tuple[str, str]:
        return ("Đen", "Trắng") if PRESETS[key].game.params.get("n", 15) > 5 else ("X", "O")

    def draw(self, surf: pygame.Surface) -> None:
        t = T()
        surf.fill(t.bg)
        draw_text(surf, "Demo thí nghiệm", (80, 36), DISPLAY, t.ink, weight="bold")
        draw_text(
            surf,
            "Cấu hình giống hệt thí nghiệm trong báo cáo (E2, E3) - dùng để quay video.",
            (80, 78),
            BODY,
            t.muted,
        )
        for w in self.widgets:
            w.draw(surf)
        for i, key in enumerate(PRESET_ORDER):
            p, r = PRESETS[key], self.buttons[key].rect
            self._draw_thumb(surf, key, (r.x + space(3) + 24, r.centery), t)
            draw_text(
                surf, f"{i + 1}. {p.title}", (r.x + 96, r.y + 22), TITLE, t.ink, weight="semibold"
            )
            a, b = self.side_names(key)
            draw_text(
                surf,
                f"{a}: {side_label(p.x)}   ·   {b}: {side_label(p.o)}",
                (r.x + 96, r.y + 62),
                BODY,
                t.muted,
                max_width=r.w - 400,
            )
            badge = f"CẤU HÌNH THÍ NGHIỆM · {self.sources(key)}"
            img = render.text(badge, CAPTION, "bold", t.accent_ink)
            pill = pygame.Rect(0, 0, img.get_width() + 28, 30)
            pill.midright = (r.right - space(3), r.centery)
            surf.blit(render.rounded_rect(pill.w, pill.h, 15, t.accent), pill)
            surf.blit(img, img.get_rect(center=pill.center))


HELP_CARDS = [
    (
        "Luật chơi",
        [
            "Caro: lần lượt đặt quân, X (3×3) / Đen (15×15) đi trước; 3 (3×3) hoặc 5 (15×15) quân "
            "thẳng hàng ngang, dọc, chéo là thắng; bàn đầy là hòa.",
            "Cờ tướng: luật chuẩn, Đỏ đi trước. Chiếu bí hoặc hết nước đi là thua; lặp thế lần 3 "
            "hoặc quá 300 nước là hòa (không xét chiếu dai).",
        ],
    ),
    (
        "Trong ván",
        [
            "Click ô trống để đi; quân mờ cho biết nước sẽ đặt. Cờ tướng: click quân để chọn "
            "(chấm = nước đi, vòng = ăn quân), rồi click giao điểm đích.",
            "Đi lại: lùi về lượt trước của bạn (khóa khi AI đang nghĩ).",
            "Phân tích: tô nước ở gốc cây MCTS theo số lần thăm N; W/N là tỷ lệ thắng ước lượng.",
            "Hết ván: Xem lại bằng nút ‹ ›, phím mũi tên trái / phải, hoặc click một dòng lịch sử.",
        ],
    ),
]
HELP_KEYS = [
    ("1 2 3", "preset thí nghiệm"),
    ("N", "ván mới"),
    ("S", "đổi bên"),
    ("[ ]", "seed −/+"),
    ("I K", "iteration ×2 / ÷2"),
    ("− =", "độ trễ AI"),
    ("O", "Phân tích"),
    ("W", "thêm W/N"),
    ("Space", "tạm dừng AI"),
    ("‹ ›", "xem lại (mũi tên trái / phải)"),
    ("Esc", "đóng hộp thoại · thoát ván · về menu"),
]


class HelpScene(Scene):
    name = "help"

    def on_enter(self, **_: Any) -> None:
        self.widgets = [
            Button(
                (80, 632, 200, 52),
                "Quay lại",
                lambda: self.manager.switch("home"),
                icon="chevron_left",
                ghost=True,
            )
        ]

    def draw(self, surf: pygame.Surface) -> None:
        t = T()
        surf.fill(t.bg)
        draw_text(surf, "Hướng dẫn", (80, 36), DISPLAY, t.ink, weight="bold")
        draw_text(surf, f"Cách chơi {brand.APP_NAME} và các phím tắt.", (80, 78), BODY, t.muted)
        left = pygame.Rect(80, 120, 640, 488)
        panel(surf, left, t.surface1, shadow=True)
        y = left.y + space(3)
        for title, lines in HELP_CARDS:
            draw_text(surf, title, (left.x + space(3), y), TITLE, t.accent, weight="semibold")
            y += 36
            for line in lines:
                surf.blit(render.circle(6, t.muted), (left.x + space(3), y + 8))
                for k, part in enumerate(wrap_text(line, BODY, left.w - 72)):
                    draw_text(surf, part, (left.x + space(3) + 16, y), BODY, t.ink)
                    y += 24 if k == 0 else 22
                y += 6
            y += space(2)
        right = pygame.Rect(744, 120, 456, 488)
        panel(surf, right, t.surface1, shadow=True)
        draw_text(
            surf,
            "Phím tắt",
            (right.x + space(3), right.y + space(3)),
            TITLE,
            t.accent,
            weight="semibold",
        )
        y = right.y + space(3) + 40
        for keys, desc in HELP_KEYS:
            img = render.text(keys, CAPTION, "bold", t.ink)
            chip = pygame.Rect(right.x + space(3), y, max(44, img.get_width() + 20), 28)
            surf.blit(render.rounded_rect(chip.w, chip.h, 6, t.surface3), chip)
            surf.blit(img, img.get_rect(center=chip.center))
            draw_text(
                surf,
                desc,
                (right.x + 140, chip.centery),
                BODY,
                t.ink,
                anchor="midleft",
                max_width=right.w - 160,
            )
            y += 36
        for w in self.widgets:
            w.draw(surf)
