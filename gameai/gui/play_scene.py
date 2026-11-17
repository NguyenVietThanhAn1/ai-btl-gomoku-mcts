"""Màn ván đấu (P6.3): bàn + panel kiểu chess.com, modal kết thúc, xem lại; giữ phím tắt P6.1."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import pygame

from gameai.core.game import DRAW, P1, P2, Game
from gameai.gui.controller import SIDE_TAG, GameController, MoveInfo
from gameai.gui.game_config import AI_NAMES, GameConfig
from gameai.gui.presets import (
    LEVEL_NAMES,
    PRESET_ORDER,
    PRESETS,
    Preset,
    find_level,
    mcts_iterations,
    side_label,
    swap_sides,
    with_iterations,
)
from gameai.gui.scene import Scene
from gameai.gui.view import GameView, OverlayOpts, make_view
from gameai.gui.widgets import (
    ACCENT,
    BORDER,
    CARD,
    CARD_ACTIVE,
    DANGER,
    INK,
    MUTED,
    PANEL,
    Button,
    Modal,
    ScrollList,
    Toggle,
    draw_text,
    is_click,
)

BOARD_RECT = pygame.Rect(16, 16, 688, 688)  # gồm lề nhãn tọa độ (view tự chừa)
PANEL_X, PANEL_W = 730, 530
CARD_TOP = pygame.Rect(PANEL_X, 16, PANEL_W, 70)  # bên đi sau (O)
CARD_BOTTOM = pygame.Rect(PANEL_X, 634, PANEL_W, 70)  # bên đi trước (X)
STATUS_Y = 96
HISTORY_RECT = pygame.Rect(PANEL_X, 132, PANEL_W, 208)
BUTTON_Y, BUTTON_H, BUTTON_W, GAP = 348, 40, 126, 8
TOGGLE_Y = 398
ANALYSIS_RECT = pygame.Rect(PANEL_X, 432, PANEL_W, 164)
FOOTER_Y = 604
MODAL_RECT = pygame.Rect(390, 210, 500, 290)
HISTORY_COLUMNS = (0, 48, 84, 150, 250)  # số nước, bên, nước, thời gian, ghi chú
DELAY_STEP = 0.25
TOP_K = 5
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
        self.ctrl = GameController(
            self.state.preset(), seed=self.state.seed, delay=self.state.delay
        )
        self.view: GameView = make_view(self.ctrl.preset.game, BOARD_RECT)
        self.mouse = (-1, -1)
        self.modal = Modal(MODAL_RECT)
        self.history = ScrollList(HISTORY_RECT, row_h=26, on_click=self.on_history_click,
                                  columns=HISTORY_COLUMNS)  # fmt: skip
        x = [PANEL_X + i * (BUTTON_W + GAP) for i in range(4)]
        self.b_undo = Button((x[0], BUTTON_Y, BUTTON_W, BUTTON_H), "Đi lại", self.on_undo)
        self.b_new = Button((x[1], BUTTON_Y, BUTTON_W, BUTTON_H), "Ván mới", self.restart)
        self.b_resign = Button((x[2], BUTTON_Y, BUTTON_W, BUTTON_H), "Đầu hàng", self.on_resign,
                               danger=True)  # fmt: skip
        self.b_menu = Button((x[3], BUTTON_Y, BUTTON_W, BUTTON_H), "Menu", self.on_menu)
        self.b_prev = Button((x[0], BUTTON_Y, BUTTON_W, BUTTON_H), "‹ Trước", lambda: self.step(-1))
        self.b_next = Button((x[1], BUTTON_Y, BUTTON_W, BUTTON_H), "Sau ›", lambda: self.step(1))
        self.b_exit_review = Button((x[3] - BUTTON_W - GAP, BUTTON_Y, 2 * BUTTON_W + GAP, BUTTON_H),
                                    "Thoát xem lại", self.exit_review)  # fmt: skip
        self.t_analysis = Toggle((PANEL_X, TOGGLE_Y, 170, 28), "Phân tích", self.state.overlay.show,
                                 self._set_overlay)  # fmt: skip
        self.t_wn = Toggle((PANEL_X + 180, TOGGLE_Y, 120, 28), "W/N", self.state.overlay.show_wn,
                           self._set_wn)  # fmt: skip
        self.widgets = [
            self.history, self.b_undo, self.b_new, self.b_resign, self.b_menu,
            self.b_prev, self.b_next, self.b_exit_review, self.t_analysis, self.t_wn,
        ]  # fmt: skip
        self._reset_ui()

    # ------------------------------------------------------------ trạng thái ván
    def _reset_ui(self) -> None:
        self.review: int | None = None
        self._review_game: Game | None = None
        self._was_over = False
        self.modal.close()
        self.view.reset_input()
        self.history.set_rows([])
        self.history.offset = 0

    def restart(self) -> None:
        """Ván mới với lựa chọn hiện tại (kết quả AI cũ bị bỏ theo game_id)."""
        preset = self.state.preset()
        self.ctrl.new_game(preset, self.state.seed)
        self.ctrl.delay = preset.delay if self.state.delay is None else self.state.delay
        self.view = make_view(preset.game, BOARD_RECT)
        self._reset_ui()

    @property
    def board_n(self) -> int:
        return int(self.ctrl.preset.game.params.get("n", 15))

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
        """(tiêu đề, dòng phụ, màu) của modal theo góc nhìn: 'Bạn thắng' khi người vs AI."""
        c = self.ctrl
        detail = [c.result_text() or "", f"{c.ply} nước · seed {c.seed}"]
        if c.error is not None:
            return "Lỗi", detail, DANGER
        out = c.outcome
        human = self.single_human
        if out == DRAW:
            return "Hòa", detail, INK
        if human is not None:
            if out == human:
                return "Bạn thắng!", detail, ACCENT
            return ("Bạn đã đầu hàng" if c.resigned == human else "Bạn thua"), detail, DANGER
        if c.resigned is not None:
            return f"{SIDE_TAG[c.resigned]} đầu hàng", detail, INK
        return f"{SIDE_TAG[out]} thắng", detail, ACCENT

    def open_result(self) -> None:
        title, lines, color = self.result_view()
        r = MODAL_RECT
        y, w = r.bottom - 70, 140
        xs = [r.centerx - w - w // 2 - 10, r.centerx - w // 2, r.centerx + w // 2 + 10]
        buttons = [
            Button((xs[0], y, w, 46), "Chơi lại", self.restart, primary=True),
            Button((xs[1], y, w, 46), "Xem lại", lambda: self.enter_review(self.ctrl.ply)),
            Button((xs[2], y, w, 46), "Về menu", self.on_menu),
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
    def update(self) -> None:
        c = self.ctrl
        c.update()
        if not c.is_human_turn():
            self.view.reset_input()
        if c.over and not self._was_over:
            self.exit_review()
            self.open_result()
        self._was_over = c.over
        self.history.set_rows(self.history_rows(), follow=self.review is None)
        if self.review is None:
            self.history.selected = c.ply - 1 if c.ply else None
        self._sync_buttons()

    def history_rows(self) -> list[tuple[str, ...]]:
        """Mỗi nước một dòng: (số, bên, nước, thời gian, ghi chú)."""
        rows = []
        for i, m in enumerate(self.ctrl.history):
            note = "tactic" if m.by_ai and m.is_tactic else ("AI" if m.by_ai else "")
            rows.append((f"{i + 1}.", SIDE_TAG[m.player], self.view.move_label(m.move),
                         fmt_s(m.time), note))  # fmt: skip
        return rows

    def _sync_buttons(self) -> None:
        c = self.ctrl
        reviewing = self.review is not None
        for b in (self.b_prev, self.b_next, self.b_exit_review):
            b.visible = reviewing
        for b in (self.b_undo, self.b_new, self.b_resign, self.b_menu):
            b.visible = not reviewing
        if reviewing:
            self.b_prev.enabled = self.review > 0
            self.b_next.enabled = self.review < c.ply
            return
        if c.ai_vs_ai:
            self.b_undo.text = "Tiếp tục" if c.paused else "Tạm dừng"
            self.b_undo.on_click = self._toggle_pause
            self.b_undo.enabled = not c.over
        else:
            self.b_undo.text, self.b_undo.on_click = "Đi lại", self.on_undo
            self.b_undo.enabled = c.can_undo
        if c.over:
            self.b_resign.visible, self.b_resign.text, self.b_resign.danger = True, "Kết quả", False
            self.b_resign.enabled = True
        else:
            side = c.resign_side()
            self.b_resign.visible = not c.ai_vs_ai
            self.b_resign.danger = True
            self.b_resign.enabled = side is not None
            two_players = len(c.human_sides) == 2
            self.b_resign.text = (
                f"{SIDE_TAG[side]} đầu hàng" if two_players and side else "Đầu hàng"
            )
        self.t_analysis.value, self.t_wn.value = self.state.overlay.show, self.state.overlay.show_wn
        self.t_analysis.enabled = self.t_wn.enabled = self.has_mcts

    def _toggle_pause(self) -> None:
        self.ctrl.paused = not self.ctrl.paused

    # ------------------------------------------------------------ vẽ
    def displayed(self) -> tuple[Game, MoveInfo | None]:
        """Thế đang vẽ: thế xem lại (bản dựng lại) hoặc ván thật."""
        if self.review is not None and self._review_game is not None:
            last = self.ctrl.history[self.review - 1] if self.review else None
            return self._review_game, last
        return self.ctrl.game, self.ctrl.last

    def draw(self, surf: pygame.Surface) -> None:
        super().draw(surf)  # nền + widget panel
        game, last = self.displayed()
        overlay_info = last if (last is not None and last.by_ai) else None
        self.view.draw(surf, game, last, overlay_info, self.state.overlay)
        c = self.ctrl
        if (self.review is None and not self.modal.open and c.is_human_turn() and not c.thinking
                and self.view.rect.collidepoint(self.mouse)):  # fmt: skip
            move = self.view.preview(self.mouse, game)
            if move is not None:
                self.view.draw_ghost(surf, move, game.current_player())
        self._draw_card(surf, P2, CARD_TOP)
        self._draw_card(surf, P1, CARD_BOTTOM)
        self._draw_status(surf)
        self._draw_analysis(surf, overlay_info, last)
        self._draw_footer(surf)
        self.modal.draw(surf)

    def player_name(self, side: int) -> tuple[str, str]:
        """(tên, dòng cấu hình) cho thẻ người chơi."""
        spec = self.ctrl.specs[side]
        if spec is None:
            if self.single_human is not None:
                return "Bạn", "Người chơi"
            return f"Người chơi {SIDE_TAG[side]}", "2 người cùng máy"
        found = find_level(spec, self.board_n)
        detail = side_label(spec)
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

    def _draw_badge(self, surf: pygame.Surface, side: int, center: tuple[int, int]) -> None:
        r = pygame.Rect(0, 0, 44, 44)
        r.center = center
        if self.board_n > 5:  # quân đen / trắng như trên bàn 15×15
            fill, ink = (
                ((20, 20, 20), (240, 240, 240)) if side == P1 else ((240, 240, 240), (20, 20, 20))
            )
            pygame.draw.circle(surf, fill, center, 20)
            pygame.draw.circle(surf, BORDER, center, 20, 2)
        else:
            fill = (200, 60, 55) if side == P1 else (50, 105, 205)
            ink = (255, 255, 255)
            pygame.draw.rect(surf, fill, r, border_radius=8)
        draw_text(surf, SIDE_TAG[side], center, 22, ink, bold=True, anchor="center")

    def _draw_card(self, surf: pygame.Surface, side: int, rect: pygame.Rect) -> None:
        c = self.ctrl
        to_move = not c.over and c.game.current_player() == side and self.review is None
        pygame.draw.rect(surf, CARD_ACTIVE if to_move else CARD, rect, border_radius=8)
        if to_move:
            pygame.draw.rect(surf, ACCENT, (rect.x, rect.y, 5, rect.h), border_radius=3)
        self._draw_badge(surf, side, (rect.x + 34, rect.centery))
        name, detail = self.player_name(side)
        draw_text(surf, name, (rect.x + 66, rect.y + 10), 20, INK, bold=True, max_width=250)
        right = rect.right - 12
        moves = [m for m in c.history if m.player == side]
        time_w = 0
        if moves:
            text = f"nước cuối {fmt_s(moves[-1].time)} · tổng {fmt_s(c.side_time(side))}"
            time_w = draw_text(surf, text, (right, rect.y + 40), 14, MUTED, anchor="topright").w
        draw_text(surf, detail, (rect.x + 66, rect.y + 40), 14, MUTED,
                  max_width=rect.w - 76 - time_w - 16)  # fmt: skip
        if to_move and c.thinking:
            dots = "." * (1 + int(time.monotonic() * 3) % 3)
            draw_text(surf, f"đang nghĩ{dots}", (right - 22, rect.y + 10), 18, ACCENT, bold=True,
                      anchor="topright")  # fmt: skip
        elif to_move and c.is_human_turn():
            draw_text(surf, "đến lượt", (right, rect.y + 10), 18, ACCENT, bold=True,
                      anchor="topright")  # fmt: skip

    def _draw_status(self, surf: pygame.Surface) -> None:
        c = self.ctrl
        if self.review is not None:
            text, color = f"Xem lại: nước {self.review} / {c.ply}   (← →)", INK
        elif c.over:
            text, color = c.result_text() or "", ACCENT
        else:
            who = SIDE_TAG[c.game.current_player()]
            if c.thinking:
                text = f"Lượt {who}: AI đang nghĩ…"
            elif c.paused and c.is_ai_turn():
                text = f"Lượt {who}: tạm dừng (Space)"
            elif c.is_human_turn():
                text = f"Lượt {who}: mời {'bạn' if self.single_human else who} đi"
            else:
                text = f"Lượt {who}"
            color = INK
        draw_text(surf, text, (PANEL_X, STATUS_Y), 20, color, bold=True, max_width=PANEL_W - 110)
        draw_text(surf, f"Số nước: {c.ply}", (PANEL_X + PANEL_W, STATUS_Y + 2), 16, MUTED,
                  anchor="topright")  # fmt: skip

    def _draw_analysis(self, surf: pygame.Surface, overlay_info: MoveInfo | None,
                       last: MoveInfo | None) -> None:  # fmt: skip
        r = ANALYSIS_RECT
        pygame.draw.rect(surf, PANEL, r, border_radius=8)
        x, y = r.x + 12, r.y + 8
        if last is not None:
            text = f"Nước cuối: {SIDE_TAG[last.player]} {self.view.move_label(last.move)}"
            if last.by_ai:
                if last.is_tactic:
                    kind = "thắng ngay" if last.tactic == 1 else "chặn ngay"
                    text += f" — tactic ({kind}), {fmt_s(last.time)}"
                else:
                    text += f" — {fmt_s(last.time)}"
                    if last.iterations is not None:
                        text += f", {last.iterations} iter"
                    if last.nodes is not None:
                        text += f", {last.nodes} nút"
            draw_text(surf, text, (x, y), 16, INK, max_width=r.w - 24)
        y += 26
        if not self.has_mcts:
            draw_text(surf, "Ván này không có AI MCTS → không có thống kê gốc (N, W/N).", (x, y),
                      15, MUTED)  # fmt: skip
            return
        if not self.state.overlay.show:
            draw_text(surf, "Bật Phân tích để xem N, W/N ở gốc MCTS trên bàn.", (x, y), 15, MUTED)
            return
        if overlay_info is None or not overlay_info.root_stats:
            note = "Gốc MCTS: chưa có (nước cuối không phải nước MCTS có cây)."
            if last is not None and last.by_ai and self.ctrl.specs[last.player] is not None:
                if self.ctrl.specs[last.player].kind == "alphabeta":
                    note = "Alpha-Beta: không có thống kê gốc."
            draw_text(surf, note, (x, y), 15, MUTED, max_width=r.w - 24)
            return
        draw_text(surf, "Gốc MCTS (N lớn nhất):", (x, y), 15, MUTED)
        y += 22
        for move, _w, n, wn in overlay_info.root_stats[:TOP_K]:
            chosen = move == overlay_info.move
            mark = "›" if chosen else " "
            line = f"{mark} {self.view.move_label(move):<4}  N = {n:<6}  W/N = {wn:.3f}"
            draw_text(surf, line, (x, y), 16, ACCENT if chosen else INK, bold=chosen)
            y += 21

    def _draw_footer(self, surf: pygame.Surface) -> None:
        c = self.ctrl
        parts = [f"Seed {c.seed}"]
        if c.agents[P1] is not None or c.agents[P2] is not None:
            parts.append(f"độ trễ AI {fmt_s(c.delay)}")
        if self.state.experiment:
            parts.append(EXPERIMENT_LABEL)
        parts.append("Esc thoát · phím tắt: Hướng dẫn")
        draw_text(surf, "  ·  ".join(parts), (PANEL_X, FOOTER_Y), 14, MUTED, max_width=PANEL_W)
