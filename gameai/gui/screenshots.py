"""Chụp ảnh headless các màn GUI (P6.3, D-29) → PNG cho báo cáo / duyệt giao diện.

Mặc định (theme mặc định → report/figures/gui/):
    python -m gameai.gui.screenshots
Ảnh so sánh theme (3a):
    python -m gameai.gui.screenshots --theme warm --only home play15 play3
        --out report/figures/gui/style/warm
"""

from __future__ import annotations

import argparse
import os
from collections.abc import Callable
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402

from gameai.gui.game_config import AIChoice, GameConfig, build_preset  # noqa: E402
from gameai.gui.play_scene import AppState  # noqa: E402
from gameai.gui.pygame_app import WINDOW, App  # noqa: E402
from gameai.gui.view import OverlayOpts  # noqa: E402
from gameai.gui.widgets import DEFAULT_THEME, THEMES, set_theme  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "report" / "figures" / "gui"


def _hover(app: App, pos: tuple[int, int]) -> None:
    app.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=pos, rel=(0, 0), buttons=(0, 0, 0)))


def _game_app(surf: pygame.Surface, cfg: GameConfig, overlay: OverlayOpts) -> App:
    return App(
        AppState(None, cfg.seed, overlay=overlay, base=build_preset(cfg), config=cfg), surface=surf
    )


def _play_moves(app: App, moves: list[int]) -> None:
    """Người đi lần lượt `moves` (bỏ ô đã có quân), AI trả lời giữa các nước."""
    for m in moves:
        app.ctrl.run_until_idle(120)
        if app.ctrl.over:
            return
        if app.ctrl.game.board[m] == 0:
            app.ctrl.submit_human_move(m)
    app.ctrl.run_until_idle(120)


def shot_home(surf: pygame.Surface) -> App:
    app = App(None, surface=surf)
    _hover(app, app.manager.current.buttons["play"].rect.center)
    return app


def shot_setup(surf: pygame.Surface) -> App:
    app = App(None, surface=surf)
    app.manager.switch("setup").set(game="15x15", mode="human_ai", ai=AIChoice("mcts", "hard"))
    return app


def shot_play15(surf: pygame.Surface) -> App:
    """15×15 người (X) vs MCTS Vừa, vài nước, Phân tích + W/N bật, chuột trên một ô trống."""
    app = _game_app(surf, GameConfig("15x15", "human_ai", "X", AIChoice("mcts", "medium")),
                    OverlayOpts(True, True))  # fmt: skip
    _play_moves(app, [112, 113, 97, 82])
    _hover(app, app.view.cell_rect(127).center)
    return app


def shot_play3(surf: pygame.Surface) -> App:
    """3×3 người (X) vs MCTS Khó, 2 nước, Phân tích bật."""
    app = _game_app(surf, GameConfig("3x3", "human_ai", "X", AIChoice("mcts", "hard")),
                    OverlayOpts(True, False))  # fmt: skip
    _play_moves(app, [4, 0])
    return app


def shot_modal(surf: pygame.Surface) -> App:
    """2 người 15×15, X thắng hàng ngang → modal kết thúc + đường thắng."""
    app = _game_app(surf, GameConfig("15x15", "two_players"), OverlayOpts(False, False))
    for m in (112, 128, 113, 129, 114, 130, 115, 131, 116):
        app.ctrl.submit_human_move(m)
    return app


def shot_review(surf: pygame.Surface) -> App:
    app = shot_modal(surf)
    app.tick()
    app.play.enter_review(5)
    return app


def shot_demo(surf: pygame.Surface) -> App:
    app = App(None, surface=surf)
    app.manager.switch("demo")
    return app


def shot_help(surf: pygame.Surface) -> App:
    app = App(None, surface=surf)
    app.manager.switch("help")
    return app


SHOTS: dict[str, Callable[[pygame.Surface], App]] = {
    "home": shot_home, "setup": shot_setup, "play15": shot_play15, "play3": shot_play3,
    "modal": shot_modal, "review": shot_review, "demo": shot_demo, "help": shot_help,
}  # fmt: skip


def capture(names: list[str], out: Path, theme: str = DEFAULT_THEME) -> list[Path]:
    """Sinh ảnh cho các màn `names` vào `out`; trả danh sách file."""
    set_theme(theme)
    pygame.init()
    out.mkdir(parents=True, exist_ok=True)
    surf = pygame.Surface(WINDOW)
    paths = []
    for name in names:
        app = SHOTS[name](surf)
        app.tick()
        app.tick()  # frame 2: hover / modal đã đồng bộ
        path = out / f"{name}.png"
        pygame.image.save(surf, str(path))
        paths.append(path)
    return paths


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Chụp ảnh headless các màn GUI.")
    ap.add_argument("--theme", choices=sorted(THEMES), default=DEFAULT_THEME)
    ap.add_argument("--out", type=Path, default=OUT_DIR)
    ap.add_argument("--only", nargs="+", choices=list(SHOTS), default=list(SHOTS))
    args = ap.parse_args(argv)
    for p in capture(args.only, args.out, args.theme):
        print(p.relative_to(ROOT) if p.is_relative_to(ROOT) else p)


if __name__ == "__main__":
    main()
