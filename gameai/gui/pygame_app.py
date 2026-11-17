"""GUI pygame: vòng lặp, panel thông tin, phím tắt. Logic ván nằm ở `controller.py`.

Chạy: `python -m gameai.gui.pygame_app --preset 3x3_human_mcts --seed 0`
"""

from __future__ import annotations

import argparse
import random
import sys
import time
from dataclasses import dataclass, field

import pygame

from gameai.gui.controller import SIDE_TAG, GameController, MoveInfo
from gameai.gui.presets import (
    PRESET_ORDER,
    PRESETS,
    Preset,
    mcts_iterations,
    side_label,
    swap_sides,
    with_iterations,
)
from gameai.gui.view import GameView, OverlayOpts, get_font, make_view

WINDOW = (1280, 720)
BOARD_RECT = pygame.Rect(20, 20, 680, 680)
PANEL_X = 730
FPS = 30
BG = (245, 240, 230)
INK = (30, 30, 30)
MUTED = (110, 110, 110)
ACCENT = (200, 40, 40)
DELAY_STEP = 0.25
TOP_K = 6  # số dòng root stats trên panel

KEYS_HELP = [
    "1/2/3  chọn preset      N  ván mới",
    "S  đổi bên người/AI     [ ]  seed −/+",
    "I / K  iteration ×2 / ÷2   - / =  độ trễ",
    "O  overlay N     W  thêm W/N",
    "Space  tạm dừng AI     Esc  thoát",
]


def set_dpi_aware() -> None:
    """Windows: tắt scale DPI để cửa sổ không bị mờ khi quay video."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.user32.SetProcessDpiAware()
    except Exception:  # noqa: BLE001
        pass


@dataclass
class AppState:
    """Lựa chọn của người dùng; preset thực tế = base → đổi bên → iteration."""

    preset_key: str
    seed: int = 0
    swapped: bool = False
    iterations: int | None = None  # None = theo preset
    delay: float | None = None  # None = theo preset
    overlay: OverlayOpts = field(default_factory=OverlayOpts)

    def preset(self) -> Preset:
        p = PRESETS[self.preset_key]
        if self.swapped:
            p = swap_sides(p)
        if self.iterations is not None:
            p = with_iterations(p, self.iterations)
        return p


class App:
    """Ghép controller + view + panel. `surface` có thể là Surface headless (test)."""

    def __init__(self, state: AppState, surface: pygame.Surface | None = None) -> None:
        self.state = state
        self.screen = surface if surface is not None else pygame.display.set_mode(WINDOW)
        self.ctrl = GameController(state.preset(), seed=state.seed, delay=state.delay)
        self.view: GameView = make_view(self.ctrl.preset.game, BOARD_RECT)
        self.running = True

    # ------------------------------------------------------------ điều khiển
    def restart(self) -> None:
        """Ván mới với lựa chọn hiện tại (kết quả AI cũ bị bỏ theo game_id)."""
        preset = self.state.preset()
        self.ctrl.new_game(preset, self.state.seed)
        self.ctrl.delay = preset.delay if self.state.delay is None else self.state.delay
        self.view = make_view(preset.game, BOARD_RECT)
        self.view.reset_input()

    def handle_key(self, key: int) -> None:
        st = self.state
        if key == pygame.K_ESCAPE:
            self.running = False
        elif key in (pygame.K_1, pygame.K_2, pygame.K_3):
            idx = key - pygame.K_1
            if idx < len(PRESET_ORDER):
                st.preset_key, st.swapped, st.iterations, st.delay = (
                    PRESET_ORDER[idx],
                    False,
                    None,
                    None,
                )
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

    def handle_click(self, pos: tuple[int, int]) -> bool:
        """Click trái lên bàn → nước của người (nếu hợp lệ và đúng lượt)."""
        if not self.ctrl.is_human_turn() or self.ctrl.thinking:
            return False
        move = self.view.hit_test(pos, self.ctrl.game)
        return move is not None and self.ctrl.submit_human_move(move)

    def handle_event(self, ev: pygame.event.Event) -> None:
        if ev.type == pygame.QUIT:
            self.running = False
        elif ev.type == pygame.KEYDOWN:
            self.handle_key(ev.key)
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            self.handle_click(ev.pos)

    def tick(self) -> None:
        """Một frame: cập nhật controller rồi vẽ."""
        self.ctrl.update()
        if not self.ctrl.is_human_turn():
            self.view.reset_input()
        self.draw()

    # ------------------------------------------------------------ vẽ
    def draw(self) -> None:
        self.screen.fill(BG)
        last = self.ctrl.last
        overlay_info = last if (last is not None and last.by_ai) else None
        self.view.draw(self.screen, self.ctrl.game, last, overlay_info, self.state.overlay)
        self._draw_panel(overlay_info)

    def _text(self, text: str, y: int, size: int = 20, color=INK, bold: bool = False) -> int:
        img = get_font(size, bold).render(text, True, color)
        self.screen.blit(img, (PANEL_X, y))
        return y + img.get_height() + 4

    def _draw_panel(self, overlay_info: MoveInfo | None) -> None:
        c, p = self.ctrl, self.ctrl.preset
        y = self._text(PRESETS[self.state.preset_key].title, 20, 26, bold=True)
        y = self._text(f"X: {side_label(p.x)}", y)
        y = self._text(f"O: {side_label(p.o)}", y)
        y = self._text(f"Seed: {c.seed}    Độ trễ AI: {c.delay:.2f} s", y, color=MUTED)
        y += 8
        result = c.result_text()
        if result is not None:
            y = self._text(result, y, 30, ACCENT, bold=True)
        else:
            who = SIDE_TAG[c.game.current_player()]
            if c.thinking:
                status = f"Lượt {who}: AI đang nghĩ…"
            elif c.paused and c.is_ai_turn():
                status = f"Lượt {who}: tạm dừng (Space)"
            elif c.is_human_turn():
                status = f"Lượt {who}: mời bạn đi"
            else:
                status = f"Lượt {who}"
            y = self._text(status, y, 26, bold=True)
        y = self._text(f"Số nước: {c.ply}", y, color=MUTED)
        y += 8
        last = c.last
        if last is not None:
            who = SIDE_TAG[last.player]
            y = self._text(f"Nước cuối: {who} {self.view.move_label(last.move)}", y, bold=True)
            if last.by_ai:
                if last.is_tactic:
                    kind = "thắng ngay" if last.tactic == 1 else "chặn ngay"
                    y = self._text(f"  tactic ({kind}) — {last.time:.2f} s", y)
                else:
                    detail = f"  {last.time:.2f} s/nước"
                    if last.iterations is not None:
                        detail += f", {last.iterations} iter"
                    if last.nodes is not None:
                        detail += f", {last.nodes} nút"
                    y = self._text(detail, y)
        if overlay_info is not None and overlay_info.root_stats:
            y += 6
            y = self._text("Gốc MCTS (N lớn nhất):", y, 18, MUTED)
            for move, _w, n, wn in overlay_info.root_stats[:TOP_K]:
                mark = "▶ " if move == overlay_info.move else "   "
                line = f"{mark}{self.view.move_label(move):>4}   N={n:<6} W/N={wn:.3f}"
                y = self._text(line, y, 18)
        y = WINDOW[1] - 24 * len(KEYS_HELP) - 16
        overlay = "bật" if self.state.overlay.show else "tắt"
        y = self._text(f"Overlay: {overlay}" + (" + W/N" if self.state.overlay.show_wn else ""),
                       y - 26, 18, MUTED)  # fmt: skip
        for line in KEYS_HELP:
            y = self._text(line, y, 18, MUTED)


# ---------------------------------------------------------------- chạy
def autoplay_move(app: App, rng: random.Random) -> None:
    """Thay người: đi một nước ngẫu nhiên có seed trong candidate_moves (kiểm tra headless)."""
    if app.ctrl.is_human_turn() and not app.ctrl.thinking:
        app.ctrl.submit_human_move(rng.choice(app.ctrl.game.candidate_moves()))


def run(state: AppState, autoplay: bool = False, max_frames: int | None = None,
        timeout: float | None = None) -> App:  # fmt: skip
    """Vòng lặp chính, khóa 30 fps. `autoplay`: tự đánh thay người và thoát khi ván xong."""
    set_dpi_aware()
    pygame.init()
    pygame.display.set_caption("BTL AI — k-in-a-row: Minimax / Alpha-Beta / MCTS")
    app = App(state)
    clock = pygame.time.Clock()
    rng = random.Random(state.seed)
    frames, t0 = 0, time.monotonic()
    while app.running:
        for ev in pygame.event.get():
            app.handle_event(ev)
        if autoplay:
            autoplay_move(app, rng)
        app.tick()
        pygame.display.flip()
        clock.tick(FPS)
        frames += 1
        if autoplay and app.ctrl.over:
            app.running = False
        if max_frames is not None and frames >= max_frames:
            app.running = False
        if timeout is not None and time.monotonic() - t0 > timeout:
            app.running = False
    pygame.quit()
    return app


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="GUI k-in-a-row (pygame).")
    ap.add_argument("--preset", choices=PRESET_ORDER, default=PRESET_ORDER[0])
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--delay", type=float, default=None, help="giây chờ trước mỗi nước AI")
    ap.add_argument("--iterations", type=int, default=None, help="đổi iteration của MCTS")
    ap.add_argument("--swap", action="store_true", help="đổi bên (người cầm O)")
    ap.add_argument("--no-overlay", action="store_true")
    ap.add_argument("--wn", action="store_true", help="overlay hiện cả W/N")
    ap.add_argument("--autoplay", action="store_true", help="tự đánh thay người, thoát khi hết ván")
    ap.add_argument("--max-frames", type=int, default=None)
    ap.add_argument("--timeout", type=float, default=None)
    args = ap.parse_args(argv)
    state = AppState(args.preset, args.seed, args.swap, args.iterations, args.delay,
                     OverlayOpts(not args.no_overlay, args.wn))  # fmt: skip
    t0 = time.monotonic()
    app = run(state, args.autoplay, args.max_frames, args.timeout)
    c = app.ctrl
    ai_moves = [m for m in c.history if m.by_ai]
    print(f"preset={state.preset_key} swap={state.swapped} seed={c.seed} ply={c.ply} "
          f"winner={c.winner} error={c.error is not None} human_x={c.preset.x is None} "
          f"ai_moves={len(ai_moves)} wall={time.monotonic() - t0:.1f}s")  # fmt: skip
    if c.error:
        sys.exit(1)


if __name__ == "__main__":
    main()
