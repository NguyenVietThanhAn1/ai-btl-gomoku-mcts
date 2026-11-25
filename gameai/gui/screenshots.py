"""Chụp ảnh headless các màn GUI (P6.3, D-29) → PNG cho báo cáo / duyệt giao diện.

Mặc định (theme mặc định → report/figures/gui/):
    python -m gameai.gui.screenshots
Ảnh so sánh theme (3a):
    python -m gameai.gui.screenshots --theme warm --only home play15 play3
        --out report/figures/gui/style/warm
Ảnh duyệt cờ tướng (P6.2):
    python -m gameai.gui.screenshots --only xq_check xq_flipped xq_end --out local_out/p62
"""

from __future__ import annotations

import argparse
import os
import random
from collections.abc import Callable
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402

from gameai.core.game import DRAW, P1  # noqa: E402
from gameai.games.xiangqi import NUM_SQ, Xiangqi  # noqa: E402
from gameai.gui import anim  # noqa: E402
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


# ---------------------------------------------------------------- cờ tướng (P6.2)
def _click(app: App, pos: tuple[int, int]) -> None:
    app.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos))


def xq_random_line(done: Callable[[Xiangqi], bool], seed0: int, max_ply: int = 160) -> list[int]:
    """Nước của ván ngẫu nhiên đầu tiên (seed = seed0, seed0 + 1, …) chạm điều kiện `done`."""
    for seed in range(seed0, seed0 + 5000):
        rng, g, moves = random.Random(seed), Xiangqi(), []
        while g.ply < max_ply and not g.is_terminal():
            m = rng.choice(g.legal_moves())
            g.play(m)
            moves.append(m)
            if done(g):
                return moves
    raise RuntimeError("không tìm được thế cờ thỏa điều kiện")


def _xq_select_busiest(app: App) -> None:
    """Click (qua App) quân của bên tới lượt có nhiều nước nhất, rồi hover ô đích đầu tiên."""
    game, view = app.ctrl.game, app.view
    froms = [m // NUM_SQ for m in game.legal_moves()]
    frm = max(set(froms), key=lambda s: (froms.count(s), -s))
    _click(app, view.sq_center(frm))
    _hover(app, view.sq_center(view.highlights(game)[0] % NUM_SQ))


def _mid_check(g: Xiangqi) -> bool:
    return (g.ply >= 14 and g.in_check() and not g.is_terminal() and g.current_player() == P1
            and sum(1 for p in g.board if p) >= 20)  # fmt: skip


def shot_xq_check(surf: pygame.Surface) -> App:
    """2 người, giữa ván Đỏ đang bị chiếu; chọn quân nhiều nước nhất + hover ô đích."""
    app = _game_app(surf, GameConfig("xiangqi", "two_players"), OverlayOpts(False, False))
    for m in xq_random_line(_mid_check, 0):
        app.ctrl.submit_human_move(m)
    app.tick()
    _xq_select_busiest(app)
    return app


def shot_xq_flipped(surf: pygame.Surface) -> App:
    """Người cầm Đen vs Alpha-Beta Dễ (tất định) → bàn xoay; 12 nước ngẫu nhiên seed 7 của người."""
    cfg = GameConfig("xiangqi", "human_ai", "O", AIChoice("alphabeta", "easy"))
    app = _game_app(surf, cfg, OverlayOpts(False, False))
    rng = random.Random(7)
    for _ in range(12):
        app.ctrl.run_until_idle(120)
        if app.ctrl.over:
            break
        app.ctrl.submit_human_move(rng.choice(app.ctrl.game.legal_moves()))
    app.ctrl.run_until_idle(120)
    app.tick()
    _xq_select_busiest(app)
    return app


def _mate(g: Xiangqi) -> bool:
    return g.is_terminal() and g.winner() != DRAW and g.in_check()


def shot_xq_end(surf: pygame.Surface) -> App:
    """2 người, ván ngẫu nhiên kết thúc bằng chiếu bí → modal "… thắng — Chiếu bí"."""
    app = _game_app(surf, GameConfig("xiangqi", "two_players"), OverlayOpts(False, False))
    for m in xq_random_line(_mate, 0):
        app.ctrl.submit_human_move(m)
    return app


SHOTS: dict[str, Callable[[pygame.Surface], App]] = {
    "home": shot_home, "setup": shot_setup, "play15": shot_play15, "play3": shot_play3,
    "modal": shot_modal, "review": shot_review, "demo": shot_demo, "help": shot_help,
    "xq_check": shot_xq_check, "xq_flipped": shot_xq_flipped, "xq_end": shot_xq_end,
}  # fmt: skip
DEFAULT_SHOTS = [k for k in SHOTS if not k.startswith("xq_")]  # ảnh báo cáo (k-in-row)


def capture(names: list[str], out: Path, theme: str = DEFAULT_THEME) -> list[Path]:
    """Sinh ảnh cho các màn `names` vào `out`; trả danh sách file."""
    set_theme(theme)
    was = anim.ENABLED
    anim.set_enabled(False)  # trạng thái cuối ngay → ảnh tất định
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
    anim.set_enabled(was)
    return paths


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Chụp ảnh headless các màn GUI.")
    ap.add_argument("--theme", choices=sorted(THEMES), default=DEFAULT_THEME)
    ap.add_argument("--out", type=Path, default=OUT_DIR)
    ap.add_argument("--only", nargs="+", choices=list(SHOTS), default=DEFAULT_SHOTS)
    args = ap.parse_args(argv)
    for p in capture(args.only, args.out, args.theme):
        print(p.relative_to(ROOT) if p.is_relative_to(ROOT) else p)


if __name__ == "__main__":
    main()
