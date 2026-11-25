"""P6.2: cờ tướng trong PlayScene — click 2 bước, xoay bàn, dòng trạng thái chiếu, modal lý do kết
thúc, undo bỏ chọn, autoplay mọi chế độ (D-28, D-37). Animation tắt, headless."""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import random  # noqa: E402

import pygame  # noqa: E402
import pytest  # noqa: E402

from gameai.agents.registry import GameSpec  # noqa: E402
from gameai.core.game import DRAW, P1, P2  # noqa: E402
from gameai.experiments.p83_mcts_check import xq_mcts_spec  # noqa: E402
from gameai.games.xiangqi import NUM_SQ, iccs_to_move  # noqa: E402
from gameai.gui import anim  # noqa: E402
from gameai.gui.game_config import AIChoice, GameConfig, build_preset  # noqa: E402
from gameai.gui.play_scene import CARD_BOTTOM, CARD_TOP, AppState  # noqa: E402
from gameai.gui.presets import Preset, level_for  # noqa: E402
from gameai.gui.pygame_app import App  # noqa: E402
from gameai.gui.screenshots import _mate, _mid_check, xq_random_line  # noqa: E402
from gameai.gui.view import OverlayOpts  # noqa: E402
from gameai.gui.widgets import current_theme  # noqa: E402


def sq(text: str) -> int:
    return int(text[1]) * 9 + ord(text[0]) - ord("a")


@pytest.fixture(autouse=True)
def _pygame():
    pygame.init()
    was = anim.ENABLED
    anim.set_enabled(False)
    yield
    anim.set_enabled(was)
    pygame.quit()


def app_for(cfg: GameConfig) -> App:
    app = App(
        AppState(None, cfg.seed, delay=0.0, overlay=OverlayOpts(False, False),
                 base=build_preset(cfg), config=cfg),
        surface=pygame.Surface((1280, 720)),
    )  # fmt: skip
    app.tick()
    return app


def click_sq(app: App, square: int) -> None:
    app.handle_event(
        pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=app.view.sq_center(square))
    )
    app.tick()


def test_two_step_click_moves_and_history_label():
    app = app_for(GameConfig("xiangqi", "two_players"))
    click_sq(app, sq("h2"))  # pháo Đỏ
    assert app.view.selected == sq("h2") and app.ctrl.ply == 0
    click_sq(app, sq("e2"))
    assert app.ctrl.ply == 1 and app.ctrl.history[0].move == iccs_to_move("h2e2")
    assert app.view.selected is None
    assert app.play.history_rows()[0][1:3] == ("●", "h2e2")
    click_sq(app, sq("h9"))  # mã Đen (tới lượt Đen)
    click_sq(app, sq("g7"))
    assert app.ctrl.ply == 2 and app.play.history_rows()[1][1:3] == ("○", "h9g7")
    app.tick()


def test_undo_clears_selection():
    app = app_for(GameConfig("xiangqi", "two_players"))
    click_sq(app, sq("h2"))
    click_sq(app, sq("e2"))
    click_sq(app, sq("h9"))
    assert app.view.selected == sq("h9")
    app.play.on_undo()
    assert app.view.selected is None and app.ctrl.ply == 0


@pytest.mark.parametrize(
    ("mode", "side", "flipped"),
    [("human_ai", "O", True), ("human_ai", "X", False), ("two_players", "X", False),
     ("ai_ai", "X", False)],
)  # fmt: skip
def test_board_flips_only_for_single_black_human(mode, side, flipped):
    cfg = GameConfig("xiangqi", mode, side, AIChoice("alphabeta", "easy"),
                     AIChoice("alphabeta", "easy"))  # fmt: skip
    app = app_for(cfg)
    app.ctrl.paused = True
    assert app.view.flipped is flipped
    top, bottom = app.play.card_layout()
    assert (top, bottom) == (((P1, CARD_TOP), (P2, CARD_BOTTOM)) if flipped
                             else ((P2, CARD_TOP), (P1, CARD_BOTTOM)))  # fmt: skip
    app.play.restart()  # dựng lại view: giữ quy tắc xoay
    assert app.view.flipped is flipped


def test_flip_follows_side_swap_key():
    app = app_for(GameConfig("xiangqi", "human_ai", "X", AIChoice("alphabeta", "easy")))
    assert not app.view.flipped
    app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_s))  # đổi bên → người cầm Đen
    assert app.play.single_human == P2 and app.view.flipped


def test_status_line_red_when_in_check():
    app = app_for(GameConfig("xiangqi", "two_players"))
    text, color = app.play.status_line()
    assert text == "Lượt Đỏ · mời Đỏ đi" and color == current_theme().ink
    for m in xq_random_line(_mid_check, 0):
        app.ctrl.submit_human_move(m)
    app.tick()
    text, color = app.play.status_line()
    assert text == "Đỏ đang bị chiếu · mời Đỏ đi" and color == current_theme().lose


def test_end_modal_shows_reason():
    app = app_for(GameConfig("xiangqi", "two_players"))
    for m in xq_random_line(_mate, 0):
        app.ctrl.submit_human_move(m)
    app.tick()
    assert app.ctrl.over and app.play.modal.open
    title, lines, _ = app.play.result_view()
    winner = app.play.side(app.ctrl.outcome)
    assert title == f"{winner} thắng" and lines[0] == "Chiếu bí"
    assert app.play.result_text() == f"{winner} thắng — Chiếu bí"
    assert app.play.status_line()[0] == f"{winner} thắng — Chiếu bí"


def test_draw_reason_repetition():
    app = app_for(GameConfig("xiangqi", "two_players"))
    for _ in range(2):
        for s in ("h0g2", "h9g7", "g2h0", "g7h9"):
            app.ctrl.submit_human_move(iccs_to_move(s))
    app.tick()
    assert app.ctrl.outcome == DRAW
    title, lines, _ = app.play.result_view()
    assert title == "Hòa" and lines[0] == "Lặp thế 3 lần"


# ---------------------------------------------------------------- autoplay (D-37: mọi chế độ)
SHORT = GameSpec("xiangqi", {"max_plies": 24})
FAST_MCTS = xq_mcts_spec(time_limit=None, iterations=40, tactics=True)


@pytest.mark.parametrize(
    "preset",
    [
        Preset("xq_ai_ai", "", SHORT, level_for("xiangqi", "alphabeta", "easy").spec, FAST_MCTS),
        Preset("xq_human_red", "", SHORT, None, FAST_MCTS),
        Preset("xq_human_black", "", SHORT, level_for("xiangqi", "alphabeta", "easy").spec, None),
        Preset("xq_two", "", GameSpec("xiangqi", {}), None, None),
    ],
    ids=lambda p: p.key,
)
def test_autoplay_to_end_without_error(preset):
    app = App(AppState(None, 3, delay=0.0, base=preset), surface=pygame.Surface((1280, 720)))
    rng = random.Random(11)
    for _ in range(400):
        app.ctrl.run_until_idle(60)
        app.tick()
        if app.ctrl.over:
            break
        if app.ctrl.is_human_turn():  # người: click 2 bước qua view (như chuột thật)
            move = rng.choice(app.ctrl.game.legal_moves())
            click_sq(app, move // NUM_SQ)
            click_sq(app, move % NUM_SQ)
    assert app.ctrl.over and app.ctrl.error is None
    assert app.play.modal.open and app.play.result_view()[1]
    app.play.enter_review(app.ctrl.ply // 2)  # xem lại vẽ được
    app.tick()
