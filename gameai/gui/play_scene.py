"""Màn ván đấu (P6.3): bàn + panel kiểu chess.com, modal kết thúc, xem lại; giữ phím tắt P6.1."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import pygame

from gameai.core.game import DRAW, P1, P2, Game
from gameai.gui import anim, render
from gameai.gui.controller import GameController, MoveInfo
from gameai.gui.game_config import AI_NAMES, GameConfig
from gameai.gui.icons import icon
from gameai.gui.presets import (
    LEVEL_NAMES,
    PRESET_ORDER,
    PRESETS,
    BoardKey,
    Preset,
    board_key,
    experiment_source,
    find_level,
    mcts_iterations,
    side_label,
    swap_sides,
    with_iterations,
)
from gameai.gui.scene import Scene
from gameai.gui.view import GameView, OverlayOpts, make_view
from gameai.gui.widgets import (
    BODY,
    CAPTION,
    TITLE,
    Button,
    IconButton,
    Modal,
    ScrollList,
    Toggle,
    Tooltip,
    draw_text,
    is_click,
    panel,
    space,
)
from gameai.gui.widgets import current_theme as T

BOARD_RECT = pygame.Rect(24, 24, 672, 672)  # gồm khung + lề nhãn tọa độ (view tự chừa)
PANEL_X, PANEL_W = 728, 528
PANEL_AREA = pygame.Rect(PANEL_X - 16, 0, PANEL_W + 40, 720)
CARD_TOP = pygame.Rect(PANEL_X, 24, PANEL_W, 72)  # bên đi sau (O)
CARD_BOTTOM = pygame.Rect(PANEL_X, 624, PANEL_W, 72)  # bên đi trước (X)
STATUS_Y = 112
HISTORY_CARD = pygame.Rect(PANEL_X, 144, PANEL_W, 200)
HISTORY_RECT = HISTORY_CARD.inflate(0, -16)
BUTTON_Y, BUTTON_H, BUTTON_W, GAP = 352, 48, 126, 8
ANALYSIS_CARD = pygame.Rect(PANEL_X, 412, PANEL_W, 200)
MODAL_RECT = pygame.Rect(PANEL_X + 16, 232, PANEL_W - 32, 200)  # trên panel, không che bàn
HISTORY_COLUMNS = (0, 48, 84, 160, 260)  # số nước, bên, nước, thời gian, ghi chú
DELAY_STEP = 0.25
TOP_K = 5  # dòng trong card Phân tích (bàn hiện top-8)
EXPERIMENT_LABEL = "cấu hình thí nghiệm"


def fmt_s(seconds: float) -> str:
    """Giây kiểu Việt: 2,10 s."""
    return f"{seconds:.2f}".replace(".", ",") + " s"


@dataclass
class AppState:
    """Lựa chọn của ván. Preset thực tế = (base hoặc PRESETS[preset_key]) → đổi bên → iteration.

    `preset_key` khác None = vào từ Demo / `--preset` (cấu hình thí nghiệm P6.1);
    `config` = từ Setup.
    """

    preset_key: str | None = None
    seed: int = 0
    swapped: bool = False
    iterations: int | None = None  # None = theo preset
    delay: float | None = None  # None = theo preset
    overlay: OverlayOpts = field(default_factory=OverlayOpts)
    base: Preset | None = None
    config: GameConfig | None = None

    def preset(self) -> Preset:
        p = self.base if self.preset_key is None else PRESETS[self.preset_key]
        if p is None:
            raise ValueError("AppState cần preset_key hoặc base")
        if self.swapped:
            p = swap_sides(p)
        if self.iterations is not None:
            p = with_iterations(p, self.iterations)
        return p

    @property
    def experiment(self) -> bool:
        return self.preset_key is not None


class PlayScene(Scene):
    """Ván đấu: `ctrl` (GameController), `view` (GameView), `review` = ply đang xem lại / None."""

    name = "play"

    def on_enter(self, state: AppState | None = None, **_: object) -> None:
        self.state = state if state is not None else AppState(PRESET_ORDER[0])
        st = self.state
        self.ctrl = GameController(st.preset(), seed=st.seed, delay=st.delay)
        self.view: GameView = self._make_view()
        self.mouse = (-1, -1)
        self.modal = Modal(MODAL_RECT, dim_rect=PANEL_AREA)
        self.history = ScrollList(HISTORY_RECT, row_h=23, on_click=self.on_history_click,
                                  columns=HISTORY_COLUMNS)  # fmt: skip
        self.history.muted_cols = {0, 3, 4}
        self.history.symbols = {
            "●": lambda: self.symbol_sprite(P1),
            "○": lambda: self.symbol_sprite(P2),
        }
        x = [PANEL_X + i * (BUTTON_W + GAP) for i in range(4)]
        bh = (BUTTON_W, BUTTON_H)
        self.b_undo = Button((x[0], BUTTON_Y, *bh), "Đi lại", self.on_undo, icon="undo")
        self.b_new = Button((x[1], BUTTON_Y, *bh), "Ván mới", self.restart, icon="new_game")
        self.b_resign = Button((x[2], BUTTON_Y, *bh), "Đầu hàng", self.on_resign, danger=True,
                               icon="flag")  # fmt: skip
        self.b_menu = Button((x[3], BUTTON_Y, *bh), "Menu", self.on_menu, icon="home")
        self.b_prev = Button(
            (x[0], BUTTON_Y, *bh), "Trước", lambda: self.step(-1), icon="chevron_left"
        )
        self.b_next = Button(
            (x[1], BUTTON_Y, *bh), "Sau", lambda: self.step(1), icon="chevron_right"
        )
        self.b_exit_review = Button((x[2], BUTTON_Y, 2 * BUTTON_W + GAP, BUTTON_H), "Thoát xem lại",
                                    self.exit_review, icon="close")  # fmt: skip
        ay = ANALYSIS_CARD.y + space(1)
        self.t_analysis = Toggle((ANALYSIS_CARD.x + space(2), ay, 180, 32), "Phân tích",
                                 st.overlay.show, self._set_overlay)  # fmt: skip
        self.t_wn = Toggle((ANALYSIS_CARD.right - 112, ay, 100, 32), "W/N", st.overlay.show_wn,
                           self._set_wn)  # fmt: skip
        self.info = {
            side: IconButton((0, 0, 28, 28), "info", size=CAPTION + 2) for side in (P1, P2)
        }
        self.tips = {side: Tooltip(self.info[side].rect, lambda s=side: self.info_lines(s))
                     for side in (P1, P2)}  # fmt: skip
        self.widgets = [
            self.history, self.b_undo, self.b_new, self.b_resign, self.b_menu,
            self.b_prev, self.b_next, self.b_exit_review, self.t_analysis, self.t_wn,
            *self.info.values(), *self.tips.values(),
        ]  # fmt: skip
        self._reset_ui()

    # ------------------------------------------------------------ trạng thái ván
    def _reset_ui(self) -> None:
        self.review: int | None = None
        self._review_game: Game | None = None
        self._was_over = False
        self._seen_ply = self.ctrl.ply
        self._place: tuple[int, anim.Tween] | None = None  # (ô, tween 0→1) quân vừa đặt
        self._win: anim.Tween | None = None  # đường thắng vẽ dần
        self.modal.close()
        self.view.reset_input()
        self.history.set_rows([])
        self.history.offset = 0

    def restart(self) -> None:
        """Ván mới với lựa chọn hiện tại (kết quả AI cũ bị bỏ theo game_id)."""
        preset = self.state.preset()
        self.ctrl.new_game(preset, self.state.seed)
        self.ctrl.delay = preset.delay if self.state.delay is None else self.state.delay
        self.view = self._make_view()
        self._reset_ui()

    def _make_view(self) -> GameView:
        """View của trò hiện tại; cờ tướng xoay bàn (Đen ở dưới) khi người duy nhất cầm Đen."""
        view = make_view(self.ctrl.preset.game, BOARD_RECT)
        if hasattr(view, "flipped"):
            view.flipped = self.single_human == P2
        return view

    @property
    def board_n(self) -> int:
        """Cạnh bàn k-in-row (15 nếu không có `n`, vd. cờ tướng — chỉ để chọn kiểu quân)."""
        return int(self.ctrl.preset.game.params.get("n", 15))

    @property
    def board_key(self) -> BoardKey:
        """Khóa trò trong bảng độ khó: 3 / 15 / "xiangqi"."""
        return board_key(self.ctrl.preset.game)

    def card_layout(self) -> list[tuple[int, pygame.Rect]]:
        """(bên, thẻ): bên đi sau ở trên, đi trước ở dưới; đảo khi bàn xoay (thẻ khớp phía bàn)."""
        if getattr(self.view, "flipped", False):
            return [(P1, CARD_TOP), (P2, CARD_BOTTOM)]
        return [(P2, CARD_TOP), (P1, CARD_BOTTOM)]

    @property
    def has_mcts(self) -> bool:
        return any(s is not None and s.kind == "mcts" for s in self.ctrl.specs.values())

    @property
    def single_human(self) -> int | None:
        humans = self.ctrl.human_sides
        return humans[0] if len(humans) == 1 else None

    # ------------------------------------------------------------ nút
    def on_undo(self) -> None:
        if self.ctrl.undo():
            self.view.reset_input()

    def on_resign(self) -> None:
        if self.ctrl.over:  # sau khi hết ván, nút này mở lại modal kết quả
            self.open_result()
        else:
            self.ctrl.resign()

    def on_menu(self) -> None:
        self.ctrl.paused = True  # ván bị bỏ; thread cũ (nếu có) chạy nốt rồi bị bỏ
        self.manager.switch("home")

    def on_history_click(self, index: int) -> None:
        if self.ctrl.over and not self.modal.open:  # xem lại chỉ sau khi hết ván (✂ khi đang chơi)
            self.enter_review(index + 1)

    def _set_overlay(self, value: bool) -> None:
        self.state.overlay.show = value

    def _set_wn(self, value: bool) -> None:
        self.state.overlay.show_wn = value

    # ------------------------------------------------------------ kết thúc + xem lại
    def result_view(self) -> tuple[str, list[str], tuple[int, int, int]]:
        """(tiêu đề, dòng phụ, màu) của modal theo góc nhìn: 'Bạn thắng' khi người vs AI.

        Dòng phụ = kết quả (nếu khác tiêu đề) + "N nước · seed S"."""
        c, t = self.ctrl, T()
        moves = f"{c.ply} nước · seed {c.seed}"
        res = self.result_text()
        human = self.single_human
        out = c.outcome
        if c.error is not None:
            title, color = "Lỗi", t.lose
        elif out == DRAW:
            title, color = "Hòa", t.ink
        elif human is not None:
            won = out == human
            title = (
                "Bạn thắng!" if won else ("Bạn đã đầu hàng" if c.resigned == human else "Bạn thua")
            )
            color = t.win if won else t.lose
        elif c.resigned is not None:
            title, color = f"{self.side(c.resigned)} đầu hàng", t.ink
        else:
            title, color = f"{self.side(out)} thắng", t.win
        if res.startswith(f"{title} — "):  # "Đen thắng — Chiếu bí" dưới tiêu đề "Đen thắng"
            res = res[len(title) + 3 :]
            res = res[:1].upper() + res[1:]
        detail = ([res] if res and res != title else []) + [moves]
        return title, detail, color

    def side(self, player: int) -> str:
        """Tên bên trong lời văn: 15×15 "Đen"/"Trắng", 3×3 "X"/"O" (theo view)."""
        return self.view.side_name(player)

    def result_text(self) -> str:
        """Như `ctrl.result_text()` nhưng dùng tên bên của view."""
        c = self.ctrl
        if c.error is not None:
            return c.error
        if c.resigned is not None:
            return f"{self.side(c.resigned)} đầu hàng — {self.side(-c.resigned)} thắng"
        w = c.game.winner()
        if w is None:
            return ""
        reason = self.view.end_reason(c.game)  # cờ tướng: "Chiếu bí", "Hòa — lặp thế 3 lần"…
        if w == DRAW:
            return reason or "Hòa"
        return f"{self.side(w)} thắng" + (f" — {reason}" if reason else "")

    def symbol_sprite(self, player: int) -> pygame.Surface:
        """Chấm Đen/Trắng trong lịch sử 15×15 (sprite cache theo theme); cờ tướng: đĩa Đỏ/Đen."""
        if hasattr(self.view, "side_dot"):
            return self.view.side_dot(player, 14)
        t = T()
        if player == P1:
            return render.stone(14, t.stone_dark, t.stone_dark_hi, (0, 0, 0))
        return render.stone(14, t.stone_light, t.stone_light_hi, (150, 146, 140))

    def open_result(self) -> None:
        title, lines, color = self.result_view()
        r = MODAL_RECT
        w, h = (r.w - space(4) - 2 * GAP) // 3, 48
        y = r.bottom - space(3) - h
        xs = [r.x + space(2) + i * (w + GAP) for i in range(3)]
        buttons = [
            Button((xs[0], y, w, h), "Chơi lại", self.restart, primary=True),
            Button((xs[1], y, w, h), "Xem lại", lambda: self.enter_review(self.ctrl.ply)),
            Button((xs[2], y, w, h), "Về menu", self.on_menu),
        ]
        self.modal.show(title, lines, buttons, color)

    def enter_review(self, ply: int) -> None:
        self.modal.close()
        self.review = max(0, min(self.ctrl.ply, ply))
        self._review_game = self.ctrl.position_at(self.review)
        self.history.selected = self.review - 1 if self.review else None
        if self.review:
            self.history.ensure_visible(self.review - 1)

    def step(self, delta: int) -> None:
        if self.review is not None:
            self.enter_review(self.review + delta)

    def exit_review(self) -> None:
        self.review = None
        self._review_game = None

    # ------------------------------------------------------------ input
    def handle_click(self, pos: tuple[int, int]) -> bool:
        """Click lên bàn → nước của người (nếu đúng lượt, AI không nghĩ, không modal / xem lại)."""
        if self.modal.open or self.review is not None:
            return False
        if not self.ctrl.is_human_turn() or self.ctrl.thinking:
            return False
        move = self.view.hit_test(pos, self.ctrl.game)
        return move is not None and self.ctrl.submit_human_move(move)

    def handle_event(self, ev: pygame.event.Event) -> bool:
        if ev.type == pygame.MOUSEMOTION:
            self.mouse = ev.pos
        if self.modal.open:
            return self.modal.handle_event(ev)
        if super().handle_event(ev):
            return True
        if is_click(ev) and self.view.rect.collidepoint(ev.pos):
            return self.handle_click(ev.pos)
        return False

    def handle_key(self, key: int) -> None:
        st = self.state
        if key == pygame.K_ESCAPE:
            if self.modal.open:
                self.modal.close()
            else:
                self.manager.quit()
        elif key in (pygame.K_LEFT, pygame.K_RIGHT):
            delta = -1 if key == pygame.K_LEFT else 1
            if self.review is not None:
                self.step(delta)
            elif self.ctrl.over and not self.modal.open:
                self.enter_review(self.ctrl.ply + min(0, delta))
        elif key in (pygame.K_1, pygame.K_2, pygame.K_3):
            idx = key - pygame.K_1
            if idx < len(PRESET_ORDER):
                st.preset_key, st.base, st.config = PRESET_ORDER[idx], None, None
                st.swapped, st.iterations, st.delay = False, None, None
                self.restart()
        elif key == pygame.K_n:
            self.restart()
        elif key == pygame.K_s:
            st.swapped = not st.swapped
            self.restart()
        elif key in (pygame.K_LEFTBRACKET, pygame.K_RIGHTBRACKET):
            st.seed = max(0, st.seed + (1 if key == pygame.K_RIGHTBRACKET else -1))
            self.restart()
        elif key in (pygame.K_i, pygame.K_k):
            cur = mcts_iterations(st.preset())
            if cur is not None:
                st.iterations = max(1, cur * 2 if key == pygame.K_i else cur // 2)
                self.restart()
        elif key in (pygame.K_MINUS, pygame.K_EQUALS):
            step = DELAY_STEP if key == pygame.K_EQUALS else -DELAY_STEP
            st.delay = max(0.0, self.ctrl.delay + step)
            self.ctrl.delay = st.delay
        elif key == pygame.K_o:
            st.overlay.show = not st.overlay.show
        elif key == pygame.K_w:
            st.overlay.show_wn = not st.overlay.show_wn
        elif key == pygame.K_SPACE:
            self.ctrl.paused = not self.ctrl.paused

    # ------------------------------------------------------------ frame
    def update(self, dt: float = 0.0) -> None:
        c = self.ctrl
        c.update()
        if not c.is_human_turn():
            self.view.reset_input()
        if c.ply > self._seen_ply and c.last is not None:  # quân mới → scale + fade-in
            self._place = (int(c.last.move), anim.Tween(0.0, 1.0, anim.PLACE))
        self._seen_ply = c.ply
        if c.over and not self._was_over:
            self.exit_review()
            self.open_result()
            self._win = anim.Tween(0.0, 1.0, anim.WIN_LINE)
        self._was_over = c.over
        self._step_animations(dt)
        super().update(dt)
        self.modal.update(dt)
        self.history.set_rows(self.history_rows(), follow=self.review is None)
        if self.review is None:
            self.history.selected = c.ply - 1 if c.ply else None
        self._sync_buttons()

    def _step_animations(self, dt: float) -> None:
        view = self.view
        if self._place is not None:
            move, tw = self._place
            tw.update(dt)
            p = float(tw.value)
            if tw.done or self.review is not None:
                self._place = None
            elif hasattr(view, "anim_move"):
                view.anim_move = (move, 0.6 + 0.4 * p, int(255 * p))
        if self._place is None and hasattr(view, "anim_move"):
            view.anim_move = None
        if hasattr(view, "win_progress"):
            if self._win is not None and self.review is None:
                self._win.update(dt)
                view.win_progress = float(self._win.value)
            else:
                view.win_progress = 1.0

    def history_rows(self) -> list[tuple[str, ...]]:
        """Mỗi nước một dòng: (số, bên, nước, thời gian, ghi chú)."""
        rows = []
        for i, m in enumerate(self.ctrl.history):
            note = "tactic" if m.by_ai and m.is_tactic else ("AI" if m.by_ai else "")
            rows.append((f"{i + 1}.", self.view.side_symbol(m.player), self.view.move_label(m.move),
                         fmt_s(m.time), note))  # fmt: skip
        return rows

    def _sync_buttons(self) -> None:
        c = self.ctrl
        reviewing = self.review is not None
        for b in (self.b_prev, self.b_next, self.b_exit_review):
            b.visible = reviewing
        for b in (self.b_undo, self.b_new, self.b_resign, self.b_menu):
            b.visible = not reviewing
        for side, rect in self.card_layout():  # ⓘ cạnh tên AI
            btn = self.info[side]
            btn.visible = self.tips[side].visible = c.specs[side] is not None
            name_w = render.text(self.player_name(side)[0], TITLE, "semibold", T().ink).get_width()
            btn.rect.topleft = (rect.x + 72 + name_w + 4, rect.y + 12)
            self.tips[side].rect = btn.rect
        if reviewing:
            self.b_prev.enabled = self.review > 0
            self.b_next.enabled = self.review < c.ply
            return
        if c.ai_vs_ai:
            self.b_undo.text = "Tiếp tục" if c.paused else "Tạm dừng"
            self.b_undo.icon = "play" if c.paused else "pause"
            self.b_undo.on_click = self._toggle_pause
            self.b_undo.enabled = not c.over
        else:
            self.b_undo.text, self.b_undo.icon, self.b_undo.on_click = (
                "Đi lại",
                "undo",
                self.on_undo,
            )
            self.b_undo.enabled = c.can_undo
        if c.over:
            self.b_resign.visible, self.b_resign.text, self.b_resign.danger = True, "Kết quả", False
            self.b_resign.icon = "chart"
            self.b_resign.enabled = True
        else:
            side = c.resign_side()
            self.b_resign.visible = not c.ai_vs_ai
            self.b_resign.danger, self.b_resign.icon = True, "flag"
            self.b_resign.enabled = side is not None
            named = len(c.human_sides) == 2 and side is not None
            text = f"{self.side(side)} đầu hàng" if named else "Đầu hàng"
            # Không vừa nút (đo bằng font thật, kèm icon) → chữ ngắn, không để bị cắt "Đỏ đầu …".
            self.b_resign.text = text if self.b_resign.fits(text) else "Đầu hàng"
        self.t_analysis.value, self.t_wn.value = self.state.overlay.show, self.state.overlay.show_wn
        self.t_analysis.enabled = self.t_wn.enabled = self.has_mcts

    def _toggle_pause(self) -> None:
        self.ctrl.paused = not self.ctrl.paused

    # ------------------------------------------------------------ nội dung thẻ
    def player_name(self, side: int) -> tuple[str, str]:
        """(tên hiển thị, chi tiết cấu hình + nguồn) — chi tiết hiện trong tooltip ⓘ."""
        spec = self.ctrl.specs[side]
        if spec is None:
            if self.single_human is not None:
                return "Bạn", "Người chơi"
            return f"Người chơi {self.side(side)}", "2 người cùng máy"
        found = find_level(spec, self.board_key)
        detail = side_label(spec)
        exp_source = experiment_source(spec, self.board_key)
        if found is None and exp_source is not None:  # spec thí nghiệm của Demo, không phải mức
            name = AI_NAMES.get(spec.kind, spec.name)
            source = f"cấu hình {exp_source}"
            if self.state.experiment:
                source = EXPERIMENT_LABEL + f" ({exp_source})"
            return name, f"{detail} — {source}"
        if found is not None:
            level, lv = found
            name = f"{AI_NAMES.get(spec.kind, spec.kind)} · {LEVEL_NAMES[level]}"
            source = lv.source_text
            if self.state.experiment and lv.source is not None:
                source = EXPERIMENT_LABEL + f" ({lv.source})"
            return name, f"{detail} — {source}"
        name = AI_NAMES.get(spec.kind, spec.name)
        if self.state.experiment and self.state.iterations is None:
            return name, f"{detail} — {EXPERIMENT_LABEL}"
        return name, detail

    def subtitle(self, side: int) -> tuple[str, bool]:
        """Dòng dưới tên: (chữ, có tô màu nhấn). Demo thí nghiệm hiện rõ nguồn."""
        spec = self.ctrl.specs[side]
        if spec is None:
            return ("Người chơi" if self.single_human is not None else "2 người cùng máy"), False
        if self.state.experiment:
            found = find_level(spec, self.board_key)
            tag = found[1].source if found is not None else experiment_source(spec, self.board_key)
            src = f" · {tag}" if tag else ""
            if self.state.iterations is None:
                return f"Cấu hình thí nghiệm{src}", True
        return "AI", False

    def info_lines(self, side: int) -> list[str]:
        """Tooltip ⓘ: cấu hình thật + nguồn, seed, độ trễ."""
        if self.ctrl.specs[side] is None:
            return []
        detail = self.player_name(side)[1]
        spec_text, _, source = detail.partition(" — ")
        lines = [spec_text]
        if source:
            lines.append(source[:1].upper() + source[1:])
        lines.append(f"Seed {self.ctrl.seed} · độ trễ {fmt_s(self.ctrl.delay)}")
        return lines

    # ------------------------------------------------------------ vẽ
    def displayed(self) -> tuple[Game, MoveInfo | None]:
        """Thế đang vẽ: thế xem lại (bản dựng lại) hoặc ván thật."""
        if self.review is not None and self._review_game is not None:
            last = self.ctrl.history[self.review - 1] if self.review else None
            return self._review_game, last
        return self.ctrl.game, self.ctrl.last

    def draw(self, surf: pygame.Surface) -> None:
        t = T()
        surf.fill(t.bg)
        game, last = self.displayed()
        overlay_info = last if (last is not None and last.by_ai) else None
        c = self.ctrl
        ghost = None
        if (self.review is None and not self.modal.open and c.is_human_turn() and not c.thinking
                and self.view.rect.collidepoint(self.mouse)):  # fmt: skip
            ghost = self.view.preview(self.mouse, game)
        if hasattr(self.view, "hover_move"):
            self.view.hover_move = ghost  # ô đang hover: ẩn nhãn overlay để thấy quân mờ
        self.view.draw(surf, game, last, overlay_info, self.state.overlay)
        if ghost is not None:
            self.view.draw_ghost(surf, ghost, game.current_player())
        for side, rect in self.card_layout():
            self._draw_card(surf, side, rect)
        self._draw_status(surf)
        panel(surf, HISTORY_CARD, t.surface1)
        panel(surf, ANALYSIS_CARD, t.surface1)
        for w in self.widgets:
            if not isinstance(w, Tooltip):
                w.draw(surf)
        self._draw_analysis(surf, overlay_info, last)
        if not self.modal.open:
            for tip in self.tips.values():
                tip.draw(surf)
        self.modal.draw(surf)

    def _draw_avatar(self, surf: pygame.Surface, side: int, center: tuple[int, int]) -> None:
        t = T()
        surf.blit(render.rounded_rect(48, 48, 12, t.surface2), (center[0] - 24, center[1] - 24))
        cell = 1 if side == P1 else 2
        if hasattr(self.view, "avatar"):  # cờ tướng: quân tướng Đỏ / Đen
            sprite = self.view.avatar(side, 38)
        elif self.board_n > 5:
            sprite = render.stone(
                34,
                *(
                    (t.stone_dark, t.stone_dark_hi, (0, 0, 0))
                    if cell == 1
                    else (t.stone_light, t.stone_light_hi, (150, 146, 140))
                ),
            )
        else:
            sprite = render.x_mark(36, t.x_color) if cell == 1 else render.o_mark(36, t.o_color)
        surf.blit(sprite, sprite.get_rect(center=center))

    def _draw_card(self, surf: pygame.Surface, side: int, rect: pygame.Rect) -> None:
        c, t = self.ctrl, T()
        to_move = not c.over and c.game.current_player() == side and self.review is None
        panel(surf, rect, t.surface2 if to_move else t.surface1)
        if to_move:
            surf.blit(render.rounded_rect(4, rect.h - 24, 2, t.accent), (rect.x + 6, rect.y + 12))
        self._draw_avatar(surf, side, (rect.x + 40, rect.centery))
        name = self.player_name(side)[0]
        draw_text(
            surf, name, (rect.x + 72, rect.y + 12), TITLE, t.ink, weight="semibold", max_width=260
        )
        sub, accent = self.subtitle(side)
        draw_text(surf, sub, (rect.x + 72, rect.y + 42), CAPTION, t.accent if accent else t.muted,
                  weight="medium" if accent else "regular", max_width=240)  # fmt: skip
        right = rect.right - space(2)
        moves = [m for m in c.history if m.player == side]
        total = c.side_time(side)
        draw_text(
            surf,
            fmt_s(total),
            (right, rect.y + 12),
            TITLE,
            t.ink,
            weight="semibold",
            anchor="topright",
        )
        if moves:
            draw_text(
                surf,
                f"nước cuối {fmt_s(moves[-1].time)}",
                (right, rect.y + 42),
                CAPTION,
                t.muted,
                anchor="topright",
            )
        if to_move and (c.thinking or c.is_human_turn()):
            label = "Đang nghĩ…" if c.thinking else "Đến lượt"
            pill = pygame.Rect(0, 0, 112, 28)
            pill.midright = (right - 96, rect.y + 24)
            if c.thinking:  # pulse: độ đậm dao động (tint mặt nạ, không thêm cache)
                a = int(150 + 105 * anim.pulse(time.monotonic()))
                surf.blit(
                    render.tint(render.rounded_mask(pill.w, pill.h, 14), (*t.accent, a)), pill
                )
            else:
                surf.blit(render.rounded_rect(pill.w, pill.h, 14, t.accent), pill)
            draw_text(
                surf,
                label,
                (pill.x + 14, pill.centery),
                CAPTION,
                t.accent_ink,
                weight="semibold",
                anchor="midleft",
            )

    def status_line(self) -> tuple[str, tuple[int, int, int]]:
        """(chữ, màu) của dòng trạng thái trên lịch sử; cờ tướng bị chiếu → chữ đỏ (`t.lose`)."""
        c, t = self.ctrl, T()
        if self.review is not None:
            return f"Xem lại · nước {self.review} / {c.ply}", t.ink
        if c.over:
            return self.result_text(), t.accent
        who = self.side(c.game.current_player())
        status = self.view.status_text(c.game)  # cờ tướng: "Đỏ đang bị chiếu"
        head = status or f"Lượt {who}"
        if c.thinking:
            text = f"{head} · AI đang nghĩ…"
        elif c.paused and c.is_ai_turn():
            text = f"{head} · tạm dừng (Space)"
        elif c.is_human_turn():
            text = f"{head} · mời {'bạn' if self.single_human else who} đi"
        else:
            text = head
        return text, (t.lose if status else t.ink)

    def _draw_status(self, surf: pygame.Surface) -> None:
        c, t = self.ctrl, T()
        text, color = self.status_line()
        draw_text(surf, text, (PANEL_X + 4, STATUS_Y), BODY + 1, color, weight="semibold",
                  max_width=PANEL_W - 140)  # fmt: skip
        draw_text(
            surf,
            f"Nước {c.ply} · seed {c.seed}",
            (PANEL_X + PANEL_W - 4, STATUS_Y + 2),
            CAPTION,
            t.muted,
            anchor="topright",
        )

    def last_move_text(self, last: MoveInfo) -> str:
        """Dòng "Nước cuối: …" (card Phân tích): bên + nước; nước AI thêm thời gian, iter, nút."""
        text = f"Nước cuối: {self.side(last.player)} {self.view.move_label(last.move)}"
        if last.by_ai:
            if last.is_tactic:
                kind = "thắng ngay" if last.tactic == 1 else "chặn ngay"
                text += f" · tactic ({kind}) · {fmt_s(last.time)}"
            else:
                text += f" · {fmt_s(last.time)}"
                if last.iterations:  # chỉ khi > 0: AB báo 0 iteration → không hiện "0 iter"
                    text += f" · {last.iterations} iter"
                if last.nodes is not None:
                    text += f" · {last.nodes} nút"
        return text

    def _draw_analysis(self, surf: pygame.Surface, overlay_info: MoveInfo | None,
                       last: MoveInfo | None) -> None:  # fmt: skip
        t = T()
        r = ANALYSIS_CARD
        x, y = r.x + space(2), r.y + 52
        surf.blit(render.rounded_rect(r.w - space(4), 1, 0, t.border), (x, r.y + 44))
        if last is not None:
            draw_text(surf, self.last_move_text(last), (x, y), CAPTION, t.muted,
                      max_width=r.w - space(4))  # fmt: skip
        y += 22
        if not self.has_mcts:
            draw_text(surf, "Ván này không có AI MCTS — không có thống kê gốc (N, W/N).", (x, y),
                      CAPTION, t.faint)  # fmt: skip
            return
        if not self.state.overlay.show:
            img = icon("chart", 18, t.faint)
            surf.blit(img, (x, y))
            draw_text(surf, "Bật Phân tích để xem số lần thăm N (và W/N) của các nước ở gốc MCTS.",
                      (x + 26, y), CAPTION, t.faint, max_width=r.w - space(4) - 26)  # fmt: skip
            return
        if overlay_info is None or not overlay_info.root_stats:
            note = "Gốc MCTS: chưa có (nước cuối không phải nước MCTS có cây)."
            if last is not None and last.by_ai and self.ctrl.specs[last.player] is not None:
                if self.ctrl.specs[last.player].kind == "alphabeta":
                    note = "Alpha-Beta: không có thống kê gốc."
            draw_text(surf, note, (x, y), CAPTION, t.faint, max_width=r.w - space(4))
            return
        cols = (0, 44, 120, 220)
        for j, head in enumerate(("#", "Nước", "N", "W/N")):
            draw_text(surf, head, (x + cols[j], y), CAPTION, t.faint, weight="semibold")
        y += 18
        ranked = sorted(overlay_info.root_stats, key=lambda s: -s[2])[:TOP_K]
        for rank, (move, _w, n, wn) in enumerate(ranked, start=1):
            chosen = move == overlay_info.move
            color = t.accent if chosen else t.ink
            weight = "semibold" if chosen else "regular"
            cells = (str(rank), self.view.move_label(move), str(n), f"{wn:.3f}")
            for j, cell in enumerate(cells):
                draw_text(surf, cell, (x + cols[j], y), CAPTION, color, weight=weight)
            y += 19
