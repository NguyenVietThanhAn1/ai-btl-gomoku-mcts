"""GUI pygame: cửa sổ + scene manager (Home / Setup / Demo / Hướng dẫn / ván).

Logic ván ở `controller.py`.

Chạy: `python -m gameai.gui.pygame_app` (menu)
  hoặc `--preset 3x3_human_mcts --seed 0` (vào thẳng ván).
"""

from __future__ import annotations

import argparse
import random
import sys
import time

import pygame

from gameai.gui import anim, brand
from gameai.gui.controller import GameController
from gameai.gui.play_scene import BOARD_RECT, AppState, PlayScene
from gameai.gui.presets import PRESET_ORDER
from gameai.gui.scene import SceneManager
from gameai.gui.scenes import DemoScene, HelpScene, HomeScene, SetupScene
from gameai.gui.view import GameView, OverlayOpts
from gameai.gui.widgets import DEFAULT_THEME, THEMES, set_theme

__all__ = ["WINDOW", "BOARD_RECT", "FPS", "App", "AppState", "autoplay_move", "run", "main"]

WINDOW = (1280, 720)
FPS = 30


def set_dpi_aware() -> None:
    """Windows: tắt scale DPI để cửa sổ không bị mờ khi quay video."""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.user32.SetProcessDpiAware()
    except Exception:  # noqa: BLE001
        pass


class App:
    """Cửa sổ + scene manager. `state` khác None → vào thẳng màn ván; None → Home.

    `surface` có thể là Surface headless (test). `ctrl` / `view` / `state` trỏ tới màn ván
    (tương thích P6.1).
    """

    def __init__(
        self, state: AppState | None = None, surface: pygame.Surface | None = None
    ) -> None:
        self.screen = surface if surface is not None else pygame.display.set_mode(WINDOW)
        self.manager = SceneManager(self.screen)
        for cls in (HomeScene, SetupScene, DemoScene, HelpScene, PlayScene):
            self.manager.add(cls(self.manager))
        if state is not None:
            self.manager.switch("play", state=state)
        else:
            self.manager.switch("home")

    # ------------------------------------------------------------ tương thích P6.1
    @property
    def play(self) -> PlayScene:
        scene = self.manager.scenes["play"]
        assert isinstance(scene, PlayScene)
        return scene

    @property
    def in_play(self) -> bool:
        return self.manager.current_name == "play"

    @property
    def ctrl(self) -> GameController:
        return self.play.ctrl

    @property
    def view(self) -> GameView:
        return self.play.view

    @property
    def state(self) -> AppState:
        return self.play.state

    @property
    def running(self) -> bool:
        return self.manager.running

    @running.setter
    def running(self, value: bool) -> None:
        self.manager.running = value

    def restart(self) -> None:
        self.play.restart()

    def handle_key(self, key: int) -> None:
        if self.manager.current is not None:
            self.manager.current.handle_key(key)

    def handle_click(self, pos: tuple[int, int]) -> bool:
        """Click lên bàn của màn ván (API P6.1)."""
        return self.in_play and self.play.handle_click(pos)

    def handle_event(self, ev: pygame.event.Event) -> None:
        self.manager.handle_event(ev)

    def tick(self, dt: float = 1 / FPS) -> None:
        """Một frame: update(dt) + vẽ màn hiện tại."""
        self.manager.tick(dt)


# ---------------------------------------------------------------- chạy
def autoplay_move(app: App, rng: random.Random) -> None:
    """Thay người: đi một nước ngẫu nhiên có seed trong candidate_moves (kiểm tra headless)."""
    if app.in_play and app.ctrl.is_human_turn() and not app.ctrl.thinking:
        app.ctrl.submit_human_move(rng.choice(app.ctrl.game.candidate_moves()))


def run(state: AppState | None, autoplay: bool = False, max_frames: int | None = None,
        timeout: float | None = None) -> App:  # fmt: skip
    """Vòng lặp chính, khóa 30 fps. `autoplay`: tự đánh thay người và thoát khi ván xong."""
    set_dpi_aware()
    pygame.init()
    pygame.display.set_caption(brand.APP_NAME)
    pygame.display.set_icon(brand.window_icon())
    app = App(state)
    clock = pygame.time.Clock()
    rng = random.Random(state.seed if state is not None else 0)
    frames, t0 = 0, time.monotonic()
    dt = 1 / FPS
    while app.running:
        for ev in pygame.event.get():
            app.handle_event(ev)
        if autoplay:
            autoplay_move(app, rng)
        app.tick(dt)
        pygame.display.flip()
        dt = min(0.1, clock.tick(FPS) / 1000)  # giây thật từ frame trước (kẹp khi máy khựng)
        frames += 1
        if autoplay and app.in_play and app.ctrl.over:
            app.running = False
        if max_frames is not None and frames >= max_frames:
            app.running = False
        if timeout is not None and time.monotonic() - t0 > timeout:
            app.running = False
    pygame.quit()
    return app


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=f"{brand.APP_NAME} — GUI caro (pygame).")
    ap.add_argument("--preset", choices=PRESET_ORDER, default=None,
                    help="vào thẳng ván với preset thí nghiệm (bỏ qua menu)")  # fmt: skip
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--delay", type=float, default=None, help="giây chờ trước mỗi nước AI")
    ap.add_argument("--iterations", type=int, default=None, help="đổi iteration của MCTS")
    ap.add_argument("--swap", action="store_true", help="đổi bên (người cầm O)")
    ap.add_argument("--no-overlay", action="store_true")
    ap.add_argument("--wn", action="store_true", help="overlay hiện cả W/N")
    ap.add_argument("--autoplay", action="store_true", help="tự đánh thay người, thoát khi hết ván")
    ap.add_argument("--max-frames", type=int, default=None)
    ap.add_argument("--timeout", type=float, default=None)
    ap.add_argument("--theme", choices=sorted(THEMES), default=DEFAULT_THEME, help="bảng màu")
    ap.add_argument("--no-anim", action="store_true", help="tắt chuyển động")
    args = ap.parse_args(argv)
    set_theme(args.theme)
    anim.set_enabled(not args.no_anim)
    preset = args.preset if args.preset is not None or not args.autoplay else PRESET_ORDER[0]
    state = None
    if preset is not None:
        state = AppState(preset, args.seed, args.swap, args.iterations, args.delay,
                         OverlayOpts(not args.no_overlay, args.wn))  # fmt: skip
    t0 = time.monotonic()
    app = run(state, args.autoplay, args.max_frames, args.timeout)
    if not hasattr(app.play, "ctrl"):  # chưa vào ván nào
        return
    c = app.ctrl
    ai_moves = [m for m in c.history if m.by_ai]
    print(f"preset={app.state.preset_key} swap={app.state.swapped} seed={c.seed} ply={c.ply} "
          f"winner={c.winner} error={c.error is not None} human_x={c.preset.x is None} "
          f"ai_moves={len(ai_moves)} wall={time.monotonic() - t0:.1f}s")  # fmt: skip
    if c.error:
        sys.exit(1)


if __name__ == "__main__":
    main()
