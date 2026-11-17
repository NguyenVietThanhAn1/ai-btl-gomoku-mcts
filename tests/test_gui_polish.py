"""P6.3 phiên 3b: animation, overlay, Đen/Trắng, bố cục panel, modal, clock giả (D-29)."""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402
import pytest  # noqa: E402

from gameai.core.game import P1, P2  # noqa: E402
from gameai.gui import anim, render  # noqa: E402
from gameai.gui.controller import GameController, MoveInfo  # noqa: E402
from gameai.gui.kinrow_view import KInRowView  # noqa: E402
from gameai.gui.play_scene import ANALYSIS_CARD, MODAL_RECT, AppState  # noqa: E402
from gameai.gui.presets import GAME3, GAME15, Preset  # noqa: E402
from gameai.gui.pygame_app import App  # noqa: E402
from gameai.gui.view import OverlayOpts  # noqa: E402
from gameai.gui.widgets import Button  # noqa: E402

SURF = (1280, 720)


@pytest.fixture(autouse=True)
def _pygame():
    pygame.init()
    yield


def play(preset: Preset, overlay: OverlayOpts | None = None) -> App:
    st = AppState(None, 0, delay=0.0, base=preset, overlay=overlay or OverlayOpts(False, False))
    app = App(st, surface=pygame.Surface(SURF))
    app.tick()
    return app


def motion(app: App, pos) -> None:
    app.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=pos, rel=(0, 0), buttons=(0, 0, 0)))


# ---------------------------------------------------------------- anim
def test_tween_eases_by_dt_and_disabled_is_final():
    anim.set_enabled(True)
    tw = anim.Tween(0.0, 1.0, 0.2)
    assert tw.value == 0.0
    tw.update(0.1)
    assert 0.5 < tw.value < 1.0  # ease-out: quá nửa sau nửa thời gian
    tw.update(0.2)
    assert tw.done and tw.value == 1.0
    c = anim.Tween((0.0, 0.0, 0.0), (100.0, 50.0, 0.0), 0.1)
    c.update(0.05)
    assert 0 < c.value[0] < 100 and c.value[2] == 0
    anim.set_enabled(False)
    assert anim.Tween(0.0, 1.0, 5.0).value == 1.0 and anim.pulse(0.3) == 1.0


def test_cache_does_not_grow_with_frames_during_animation():
    """Chỉnh 1 của An: animation đặt quân + hover → số entry cache không tăng theo số frame."""
    anim.set_enabled(True)
    app = play(Preset("t", "t", GAME15, None, None))
    btn = app.play.b_new
    # vòng 1: làm nóng cache (một lần đặt quân + hover vào/ra nút)
    app.handle_click(app.view.cell_rect(112).center)
    motion(app, btn.rect.center)
    for _ in range(10):
        app.tick(1 / 30)
    motion(app, (5, 5))
    for _ in range(10):
        app.tick(1 / 30)
    # vòng 2: nước mới (quân Trắng, dòng lịch sử mới = nội dung mới) → mốc lấy SAU frame đầu
    app.handle_click(app.view.cell_rect(113).center)
    app.tick(1 / 240)
    assert app.view.anim_move is not None and app.view.anim_move[0] == 113
    motion(app, btn.rect.center)
    app.tick(1 / 240)
    motion(app, (5, 5))
    app.tick(1 / 240)
    before = render.cache_sizes()
    seen_mid = False
    for i in range(60):
        motion(app, btn.rect.center if i % 6 < 3 else (5, 5))
        app.tick(1 / 120)  # dt nhỏ → nhiều frame giữa chừng
        am = app.view.anim_move
        seen_mid |= am is not None and 0.6 <= am[1] < 1.0
    assert seen_mid  # thật sự có frame đang scale
    assert render.cache_sizes() == before


def test_place_animation_and_modal_progress():
    anim.set_enabled(True)
    app = play(Preset("t", "t", GAME3, None, None))
    for m in (0, 3, 1, 4):
        app.handle_click(app.view.cell_rect(m).center)
        app.tick(1.0)
    app.handle_click(app.view.cell_rect(2).center)
    app.tick(0.001)
    p = app.play
    assert p.modal.open and p.modal.progress < 0.2  # vừa mở: đang fade/slide
    assert app.view.win_progress < 0.2  # đường thắng mới bắt đầu vẽ
    for _ in range(20):
        app.tick(1 / 30)
    assert p.modal.progress == 1.0 and app.view.win_progress == 1.0 and app.view.anim_move is None


def test_scene_crossfade_finishes():
    anim.set_enabled(True)
    app = App(None, surface=pygame.Surface(SURF))
    app.tick()
    app.manager.switch("help")
    assert app.manager._fade is not None
    for _ in range(10):
        app.tick(1 / 30)
    assert app.manager._fade is None and app.manager.current_name == "help"


def test_button_hover_tween_uses_tint_not_cache():
    anim.set_enabled(True)
    b = Button((0, 0, 120, 40), "x", ghost=False)
    surf = pygame.Surface((200, 100))
    b.update(0)
    b.handle_event(
        pygame.event.Event(pygame.MOUSEMOTION, pos=(10, 10), rel=(0, 0), buttons=(0, 0, 0))
    )
    b.update(0.03)
    assert not b._bg_tween.done
    before = render.cache_sizes()["rounded_rect"]
    b.draw(surf)
    assert render.cache_sizes()["rounded_rect"] == before  # màu trung gian không vào cache
    b.update(0.2)
    assert b._bg_tween.done


# ---------------------------------------------------------------- overlay
def _root(move, n, wn=0.5):
    return (move, n * wn, n, wn)


def test_overlay_occupied_cell_only_badge_and_3x3_lighter():
    v15 = KInRowView(15, 5, pygame.Rect(24, 24, 672, 672))
    g = GameController(Preset("t", "t", GAME15, None, None)).game
    g.play(112)
    info = MoveInfo(112, P1, True, root_stats=[_root(112, 50), _root(113, 30)])
    surf = pygame.Surface(SURF)
    v15.draw(surf, g, info, info, OverlayOpts(True, True))
    center = v15.cell_rect(112).center
    stone_px = surf.get_at(center)
    assert stone_px.r < 80  # tâm ô vẫn là quân đen (không bị ô màu + chữ đè)
    empty = surf.get_at(v15.cell_rect(113).inflate(-10, -10).topleft)
    t = __import__("gameai.gui.widgets", fromlist=["x"]).current_theme()
    assert abs(empty.r - t.heat[0]) < 40  # ô trống vẫn tô màu overlay
    # 3×3: alpha thấp hơn 15×15 ở cùng hạng
    v3 = KInRowView(3, 3, pygame.Rect(24, 24, 672, 672))
    g3 = GameController(Preset("t", "t", GAME3, None, None)).game
    info3 = MoveInfo(4, P1, True, root_stats=[_root(0, 50)])
    s3 = pygame.Surface(SURF)
    v3.draw(s3, g3, None, info3, OverlayOpts(True, False))
    base = pygame.Surface(SURF)
    v3.draw(base, g3, None, None, OverlayOpts(False, False))
    pt = v3.cell_rect(0).inflate(-20, -20).topleft
    a, b = s3.get_at(pt), base.get_at(pt)
    mix = (a.g - b.g) / (t.heat[1] - b.g)  # tỉ lệ pha màu overlay
    assert 0.2 < mix < 0.6  # vân gỗ vẫn thấy (≈ alpha 120/255)


# ---------------------------------------------------------------- Đen / Trắng
def test_black_white_wording_15x15_and_xo_3x3():
    app = play(Preset("t", "t", GAME15, None, None))
    p = app.play
    app.tick()
    assert p.side(P1) == "Đen" and p.side(P2) == "Trắng"
    assert p.b_resign.text == "Đen đầu hàng"
    assert p.player_name(P1)[0] == "Người chơi Đen"
    for m in (112, 128, 113, 129, 114, 130, 115, 131, 116):
        app.handle_click(app.view.cell_rect(m).center)
        app.tick()
    assert p.result_view()[0] == "Đen thắng" and p.result_text() == "Đen thắng"
    rows = p.history_rows()
    assert rows[0][1] == "●" and rows[1][1] == "○"
    assert set(p.history.symbols) == {"●", "○"}
    app3 = play(Preset("t", "t", GAME3, None, None))
    assert app3.play.side(P1) == "X" and app3.play.history_rows() == []
    app3.handle_click(app3.view.cell_rect(4).center)
    app3.tick()
    assert app3.play.history_rows()[0][1] == "X" and app3.play.b_resign.text == "O đầu hàng"


def test_status_line_uses_black_white():
    seen: list[str] = []
    orig = render.text

    def spy(s, *a):
        seen.append(s)
        return orig(s, *a)

    app = play(Preset("t", "t", GAME15, None, None))
    import gameai.gui.widgets as w

    w.render.text = spy
    try:
        app.tick()
    finally:
        w.render.text = orig
    assert any(s.startswith("Lượt Đen") for s in seen)


# ---------------------------------------------------------------- bố cục
def test_analysis_table_fits_card_and_modal_off_board():
    from gameai.experiments import e2_never_lose

    app = play(Preset("t", "t", GAME3, None, e2_never_lose.mcts_spec(200)), OverlayOpts(True, True))
    app.handle_click(app.view.cell_rect(4).center)
    app.ctrl.run_until_idle(30)
    seen: list[tuple[str, pygame.Rect]] = []
    import gameai.gui.play_scene as ps

    orig = ps.draw_text

    def spy(surf, text, pos, *a, **k):
        r = orig(surf, text, pos, *a, **k)
        seen.append((text, r))
        return r

    ps.draw_text = spy
    try:
        app.tick()
    finally:
        ps.draw_text = orig
    table = [r for s, r in seen if r.colliderect(ANALYSIS_CARD)]
    assert len(table) >= 4 * 5  # header + 5 dòng × 4 cột
    assert max(r.bottom for r in table) <= ANALYSIS_CARD.bottom - 8  # đủ lề dưới
    assert not MODAL_RECT.colliderect(app.view.rect)  # modal không che bàn


def test_disclosure_hides_seed_by_default():
    app = App(None, surface=pygame.Surface(SURF))
    app.manager.switch("setup")
    s = app.manager.current
    assert "seed" not in s.controls and not s.advanced
    app.handle_event(
        pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=s.controls["advanced"].rect.center)
    )
    assert s.advanced and "seed" in s.controls
    app.tick()


def test_setup_summary_short_name_and_tooltip_detail():
    app = App(None, surface=pygame.Surface(SURF))
    s = app.manager.switch("setup")
    s.set(game="15x15", mode="human_ai")
    assert [n for _, n, _ in s.summary] == ["MCTS · Vừa"]
    tip = s.tips[0]
    assert tip.lines[0].startswith("MCTS h300 1000 iter") and tip.lines[1] == "Cấu hình E3"
    s.set(game="3x3", ai=s.cfg.ai.__class__("alphabeta", "easy"))
    assert s.tips[0].lines[1].startswith("Cấu hình riêng")


# ---------------------------------------------------------------- clock giả
def test_human_think_time_with_fake_clock():
    now = [100.0]
    ctrl = GameController(Preset("t", "t", GAME3, None, None), clock=lambda: now[0])
    now[0] += 2.5
    assert ctrl.submit_human_move(4)
    now[0] += 0.75
    assert ctrl.submit_human_move(0)
    assert [m.time for m in ctrl.history] == [pytest.approx(2.5), pytest.approx(0.75)]
    assert ctrl.side_time(P1) == pytest.approx(2.5) and all(m.time > 0 for m in ctrl.history)
