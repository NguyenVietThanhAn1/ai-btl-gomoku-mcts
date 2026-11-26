"""P6.3: scene manager, widget, màn Setup/Demo/ván, modal kết thúc, xem lại (headless)."""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402
import pytest  # noqa: E402

from gameai.agents.base import Agent  # noqa: E402
from gameai.agents.registry import AgentSpec  # noqa: E402
from gameai.core.game import P1, P2  # noqa: E402
from gameai.gui.game_config import AIChoice, GameConfig, build_preset  # noqa: E402
from gameai.gui.kinrow_view import KInRowView  # noqa: E402
from gameai.gui.play_scene import AppState, PlayScene  # noqa: E402
from gameai.gui.presets import GAME3, GAME15, OWN_CONFIG, PRESETS, Preset, level_for  # noqa: E402
from gameai.gui.pygame_app import App, run  # noqa: E402
from gameai.gui.widgets import (  # noqa: E402
    Button,
    Modal,
    ScrollList,
    SegmentedControl,
    Toggle,
)


class FirstAgent(Agent):
    """AI tức thì: nước hợp lệ nhỏ nhất (kịch bản thắng/thua tất định)."""

    def __init__(self, seed: int | None = None) -> None:
        super().__init__()

    def _select_move(self, game):
        return min(game.legal_moves())


FIRST = AgentSpec("tests.test_gui_scenes:FirstAgent")


def press(pos) -> pygame.event.Event:
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=tuple(pos))


def click(app: App, pos) -> None:
    app.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=tuple(pos)))


def key(app: App, k: int) -> None:
    app.handle_event(pygame.event.Event(pygame.KEYDOWN, key=k))


def new_app(state: AppState | None = None) -> App:
    pygame.init()
    app = App(state, surface=pygame.Surface((1280, 720)))
    app.tick()
    return app


def play_app(preset: Preset, seed: int = 0) -> App:
    return new_app(AppState(None, seed, delay=0.0, base=preset))


def settle(app: App) -> None:
    """AI đi xong (nếu tới lượt) rồi vẽ một frame."""
    app.ctrl.run_until_idle(30)
    app.tick()


def click_cell(app: App, move: int) -> None:
    click(app, app.view.cell_rect(move).center)
    app.tick()


# ---------------------------------------------------------------- chuyển màn
def test_home_navigation_and_quit():
    app = new_app()
    assert app.manager.current_name == "home"
    home = app.manager.current
    click(app, home.buttons["play"].rect.center)
    assert app.manager.current_name == "setup"
    click(app, app.manager.current.back.rect.center)
    assert app.manager.current_name == "home"
    for name in ("demo", "help"):
        click(app, app.manager.current.buttons[name].rect.center)
        assert app.manager.current_name == name
        app.tick()
        key(app, pygame.K_ESCAPE)  # Esc ở màn phụ → Home
        assert app.manager.current_name == "home" and app.running
    click(app, app.manager.current.buttons["quit"].rect.center)
    assert not app.running
    app2 = new_app()
    key(app2, pygame.K_ESCAPE)
    assert not app2.running


def test_setup_esc_back_home():
    app = new_app()
    click(app, app.manager.current.buttons["play"].rect.center)
    key(app, pygame.K_ESCAPE)
    assert app.manager.current_name == "home"


def test_setup_xiangqi_playable_red_black_names():  # P6.2: không còn "Sắp có"
    app = new_app()
    click(app, app.manager.current.buttons["play"].rect.center)
    s = app.manager.current
    click(app, s.controls["game"].rect_of("xiangqi").center)
    assert s.cfg.game == "xiangqi"
    click(app, s.controls["side"].rect_of("O").center)
    click(app, s.controls["ai_kind"].rect_of("alphabeta").center)
    click(app, s.controls["ai_level"].rect_of("easy").center)
    assert s.cfg == GameConfig("xiangqi", "human_ai", "O", AIChoice("alphabeta", "easy"))
    labels = dict(s.controls["side"].options)
    assert labels["X"] == "Đỏ · đi trước" and labels["O"] == "Đen · đi sau"
    assert s.ai_lines() and "cấu hình E7" in s.ai_lines()[0]  # AB Dễ = cùng tham số a1
    click(app, s.controls["mode"].rect_of("ai_ai").center)
    assert s.ai_lines()[0].startswith("Đỏ: ") and s.ai_lines()[1].startswith("Đen: ")
    click(app, s.controls["mode"].rect_of("human_ai").center)
    app.tick()
    click(app, s.start.rect.center)
    assert app.manager.current_name == "play"
    assert app.ctrl.preset == build_preset(s.cfg)
    assert app.view.flipped  # người duy nhất cầm Đen → bàn xoay
    name, detail = app.play.player_name(P1)
    assert name == "Alpha-Beta · Dễ" and "cấu hình E7" in detail


def test_setup_choices_to_agent_spec_and_start():
    app = new_app()
    click(app, app.manager.current.buttons["play"].rect.center)
    s = app.manager.current
    click(app, s.controls["game"].rect_of("3x3").center)
    click(app, s.controls["side"].rect_of("O").center)
    click(app, s.controls["ai_kind"].rect_of("alphabeta").center)
    click(app, s.controls["ai_level"].rect_of("easy").center)
    assert s.cfg == GameConfig("3x3", "human_ai", "O", AIChoice("alphabeta", "easy"))
    assert any(OWN_CONFIG in line for line in s.ai_lines())
    click(app, s.controls["ai_level"].rect_of("hard").center)
    assert any("cấu hình E1" in line for line in s.ai_lines())
    app.tick()
    click(app, s.start.rect.center)
    assert app.manager.current_name == "play"
    assert app.ctrl.preset == build_preset(s.cfg)
    assert app.ctrl.preset.x == level_for(3, "alphabeta", "hard").spec and app.ctrl.preset.o is None
    name, detail = app.play.player_name(P1)
    assert name == "Alpha-Beta · Khó" and "cấu hình E1" in detail
    assert app.play.player_name(P2)[0] == "Bạn"


def test_setup_modes_show_right_controls():
    app = new_app()
    click(app, app.manager.current.buttons["play"].rect.center)
    s = app.manager.current
    click(app, s.controls["mode"].rect_of("ai_ai").center)
    assert {"ai_kind", "ai_o_kind", "delay"} <= set(s.controls) and "side" not in s.controls
    click(app, s.controls["delay"].plus.rect.center)
    assert s.cfg.delay == pytest.approx(0.75)
    assert len(s.ai_lines()) == 2 and s.ai_lines()[0].startswith("Đen: ")  # 15×15: Đen/Trắng
    assert s.ai_lines()[1].startswith("Trắng: ")
    app.tick()
    click(app, s.controls["mode"].rect_of("two_players").center)
    assert "ai_kind" not in s.controls and "delay" not in s.controls
    assert "seed" not in s.controls  # seed nằm trong "Tùy chọn nâng cao" (thu gọn mặc định)
    click(app, s.controls["advanced"].rect.center)
    assert "seed" in s.controls
    click(app, s.controls["seed"].plus.rect.center)
    assert s.cfg.seed == 1
    click(app, s.start.rect.center)
    assert app.ctrl.preset.x is None and app.ctrl.preset.o is None and app.ctrl.seed == 1


def test_demo_presets_unchanged_and_labeled():
    for k in PRESETS:
        app = new_app()
        click(app, app.manager.current.buttons["demo"].rect.center)
        click(app, app.manager.current.buttons[k].rect.center)
        assert app.manager.current_name == "play" and app.state.preset_key == k
        assert app.ctrl.preset == PRESETS[k] and app.state.experiment
        ai = P2 if PRESETS[k].o is not None else P1
        assert "cấu hình thí nghiệm" in app.play.player_name(ai)[1]
        app.ctrl.paused = True
        app.tick()


# ---------------------------------------------------------------- ván: nút, đi lại, đầu hàng
def test_play_undo_resign_menu_buttons():
    app = play_app(Preset("t", "t", GAME3, None, FIRST))
    p = app.play
    assert not p.b_undo.enabled and p.b_resign.text == "Đầu hàng"
    click_cell(app, 4)
    settle(app)
    assert app.ctrl.ply == 2 and p.b_undo.enabled
    click(app, p.b_undo.rect.center)
    app.tick()
    assert app.ctrl.ply == 0
    click_cell(app, 4)
    settle(app)
    click(app, p.b_resign.rect.center)
    app.tick()
    assert p.modal.open and p.result_view()[0] == "Bạn đã đầu hàng"
    click_cell(app, 8)  # modal chặn click bàn
    assert app.ctrl.ply == 2
    key(app, pygame.K_ESCAPE)  # Esc đóng modal, không thoát
    assert not p.modal.open and app.running
    app.tick()
    assert p.b_resign.text == "Kết quả"
    click(app, p.b_resign.rect.center)  # mở lại modal
    assert p.modal.open
    click(app, p.modal.buttons[2].rect.center)  # Về menu
    assert app.manager.current_name == "home"


def test_undo_button_disabled_while_ai_thinking():
    import tests.test_gui_controller as tc

    app = play_app(Preset("t", "t", GAME3, None, tc.SLOW))
    gate = __import__("sys").modules[type(app.ctrl.agents[P2]).__module__].GATE
    gate.clear()
    click_cell(app, 4)
    app.tick()
    assert app.ctrl.thinking and not app.play.b_undo.enabled
    click(app, app.play.b_undo.rect.center)
    assert app.ctrl.ply == 1
    gate.set()
    settle(app)
    assert app.ctrl.ply == 2 and app.play.b_undo.enabled


def test_two_players_resign_label_and_ai_vs_ai_buttons():
    app = play_app(Preset("t", "t", GAME3, None, None))
    p = app.play
    # "X đầu hàng" (kèm icon) không vừa nút 126 px → chữ ngắn "Đầu hàng"; vẫn đầu hàng bên tới lượt.
    assert p.b_resign.fits(p.b_resign.text)
    assert p.b_resign.text == ("X đầu hàng" if p.b_resign.fits("X đầu hàng") else "Đầu hàng")
    click_cell(app, 4)
    assert app.ctrl.resign_side() == P2 and p.b_resign.fits(p.b_resign.text)
    click(app, p.b_resign.rect.center)
    app.tick()
    assert app.ctrl.outcome == P1 and p.result_view()[0] == "O đầu hàng"
    aiai = play_app(Preset("t", "t", GAME3, FIRST, FIRST))
    aiai.ctrl.delay = 100
    aiai.tick()
    assert not aiai.play.b_resign.visible and aiai.play.b_undo.text == "Tạm dừng"
    click(aiai, aiai.play.b_undo.rect.center)
    aiai.tick()
    assert aiai.ctrl.paused and aiai.play.b_undo.text == "Tiếp tục"


# ---------------------------------------------------------------- kết thúc + xem lại
def test_end_modal_win_line_replay_and_restart():
    app = play_app(Preset("t", "t", GAME3, None, None))
    p = app.play
    for m in (0, 3, 1, 4, 2):  # X thắng hàng trên
        click_cell(app, m)
    assert app.ctrl.over and p.modal.open
    title, lines, _ = p.result_view()
    assert title == "X thắng" and "5 nước" in lines[-1] and "X thắng" not in lines
    assert sorted(p.view.winning_cells(app.ctrl.game, app.ctrl.last)) == [0, 1, 2]
    click(app, p.modal.buttons[0].rect.center)  # Chơi lại
    app.tick()
    assert app.ctrl.ply == 0 and not p.modal.open and not app.ctrl.over


def test_human_win_and_review_does_not_touch_game():
    app = play_app(Preset("t", "t", GAME3, None, FIRST))  # AI luôn đi ô nhỏ nhất
    p = app.play
    for m in (4, 2, 6):  # X: 4, AI 0; X: 2, AI 1; X: 6 → chéo 2-4-6
        click_cell(app, m)
        settle(app)
    assert app.ctrl.outcome == P1 and p.modal.open and p.result_view()[0] == "Bạn thắng!"
    key_before, n = app.ctrl.game.key(), app.ctrl.ply
    click(app, p.modal.buttons[1].rect.center)  # Xem lại
    app.tick()
    assert p.review == n and not p.modal.open
    click(app, p.b_prev.rect.center)
    app.tick()
    assert p.review == n - 1
    game, last = p.displayed()
    assert game.key() == app.ctrl.position_at(n - 1).key() and last is app.ctrl.history[n - 2]
    click(app, p.history.row_rect(0).center)  # click dòng lịch sử
    app.tick()
    assert p.review == 1 and p.history.selected == 0
    key(app, pygame.K_LEFT)
    app.tick()
    assert p.review == 0 and p.displayed()[1] is None
    assert not p.b_prev.enabled
    click(app, app.view.cell_rect(8).center)  # click bàn khi xem lại bị bỏ
    assert app.ctrl.game.key() == key_before and app.ctrl.ply == n
    click(app, p.b_exit_review.rect.center)
    app.tick()
    assert p.review is None and p.displayed()[0] is app.ctrl.game


def test_history_click_ignored_during_live_game():
    app = play_app(Preset("t", "t", GAME3, None, None))
    click_cell(app, 4)
    click(app, app.play.history.row_rect(0).center)
    assert app.play.review is None


def test_human_loss_title():
    app = play_app(Preset("t", "t", GAME3, FIRST, None))  # AI X đi 0, 1, 2
    for m in (4, 8):
        settle(app)
        click_cell(app, m)
    settle(app)
    assert app.ctrl.outcome == P1 and app.play.result_view()[0] == "Bạn thua"


# ---------------------------------------------------------------- view + widget
def test_preview_ghost_and_labels():
    app = play_app(Preset("t", "t", GAME3, None, None))
    v = app.view
    assert isinstance(v, KInRowView)
    click_cell(app, 4)
    assert v.preview(v.cell_rect(4).center, app.ctrl.game) is None
    assert v.preview(v.cell_rect(0).center, app.ctrl.game) == 0
    app.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=v.cell_rect(0).center, rel=(0, 0),
                                        buttons=(0, 0, 0)))  # fmt: skip
    app.tick()  # vẽ quân mờ không lỗi
    assert app.ctrl.ply == 1
    assert v.move_label(4) == "b2" and v.col_label(0) == "a"
    v15 = KInRowView(15, 5, pygame.Rect(16, 16, 688, 688))
    assert v15.move_label(112) == "H8" and v15.origin[0] >= 16 + 24


def test_widgets_basic():
    hits = []
    b = Button((0, 0, 100, 40), "b", lambda: hits.append(1), enabled=False)
    ev = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(10, 10))
    assert b.handle_event(ev) and hits == []
    b.enabled = True
    b.handle_event(ev)
    assert hits == [1]
    t = Toggle((0, 0, 100, 30), "t", False, hits.append)
    t.handle_event(ev)
    assert t.value is True and hits[-1] is True
    seg = SegmentedControl((0, 0, 300, 40), [("a", "A"), ("b", "B"), ("c", "C")], "a",
                           hits.append, disabled=["b"])  # fmt: skip
    seg.handle_event(press(seg.rect_of("b").center))
    assert seg.selected == "a"
    seg.handle_event(press(seg.rect_of("c").center))
    assert seg.selected == "c" and hits[-1] == "c"
    sl = ScrollList((0, 0, 200, 100), row_h=25)
    sl.set_rows([str(i) for i in range(10)], follow=True)
    assert sl.offset == 6 == sl.max_offset
    sl.scroll(10)
    assert sl.offset == 6
    sl.scroll(-100)
    assert sl.offset == 0
    sl.ensure_visible(9)
    assert sl.offset == 6
    m = Modal((0, 0, 300, 200))
    assert not m.handle_event(ev)
    m.show("t", [], [])
    assert m.handle_event(ev)  # chặn click phía sau


# ---------------------------------------------------------------- chạy
def test_run_autoplay_preset_and_menu_start():
    app = run(AppState("3x3_human_mcts", seed=1), autoplay=True, timeout=60)
    assert app.ctrl.over and app.ctrl.error is None
    app = run(None, max_frames=3)
    assert app.manager.current_name == "home"


def test_play_scene_draws_all_states_headless():
    """Mọi trạng thái vẽ được: đang chơi có overlay, xem lại, modal (15×15, AB không có cây)."""
    ab2 = level_for(15, "alphabeta", "medium").spec
    st = AppState(None, 0, delay=0.0, base=Preset("t", "t", GAME15, None, ab2))
    st.overlay.show = True
    app = new_app(st)
    click_cell(app, 112)
    settle(app)
    assert isinstance(app.play, PlayScene) and app.ctrl.ply == 2
    click(app, app.play.b_resign.rect.center)
    app.tick()
    app.play.enter_review(1)
    app.tick()
