"""P6.3 phiên 3a: theme, sprite khử răng cưa, icon, nhận diện MoveMind, ảnh headless (D-29)."""

from __future__ import annotations

import dataclasses
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402
import pytest  # noqa: E402

from gameai.gui import brand, icons, render, widgets  # noqa: E402
from gameai.gui.game_config import GAMES, AIChoice, GameConfig, build_preset  # noqa: E402
from gameai.gui.play_scene import AppState  # noqa: E402
from gameai.gui.pygame_app import App  # noqa: E402
from gameai.gui.view import OverlayOpts  # noqa: E402


@pytest.fixture(autouse=True)
def _pygame():
    pygame.init()
    yield
    widgets.set_theme(widgets.DEFAULT_THEME)


def test_themes_have_all_tokens_and_grid():
    fields = [f.name for f in dataclasses.fields(widgets.Theme)]
    for theme in widgets.THEMES.values():
        for name in fields:
            value = getattr(theme, name)
            if isinstance(value, tuple):
                assert len(value) == 3 and all(0 <= c <= 255 for c in value), (theme.name, name)
    assert {"dark", "warm"} <= set(widgets.THEMES)
    assert all(widgets.space(n) % 8 == 0 for n in range(1, 10))
    assert widgets.set_theme("warm") is widgets.current_theme() is widgets.WARM


def test_sprites_antialiased_and_cached():
    s = render.circle(40, (255, 0, 0))
    assert s.get_size() == (40, 40) and s is render.circle(40, (255, 0, 0))
    alphas = {s.get_at((x, 6)).a for x in range(0, 20)}
    assert 0 in alphas and 255 in alphas and any(0 < a < 255 for a in alphas)  # mép mềm
    rr = render.rounded_rect(120, 48, 10, (10, 20, 30))
    assert rr.get_at((0, 0)).a < 255 and rr.get_at((60, 24)).a == 255
    t = widgets.DARK
    st = render.stone(36, t.stone_dark, t.stone_dark_hi, (0, 0, 0))
    hi, lo = st.get_at((12, 12)), st.get_at((24, 26))
    assert hi.r > lo.r  # highlight trên-trái sáng hơn
    for fn in (render.x_mark(60, t.x_color), render.o_mark(60, t.o_color)):
        assert fn.get_size() == (60, 60) and fn.get_at((30, 30)).a in range(256)


def test_render_cache_cleared_on_quit_and_redraw_ok():
    surf = pygame.Surface((1280, 720))
    App(None, surface=surf).tick()
    assert sum(render.cache_sizes().values()) > 0
    pygame.quit()
    assert sum(render.cache_sizes().values()) == 0
    pygame.init()
    app = App(None, surface=surf)
    app.tick()  # không crash với Surface cũ
    app.manager.switch("play", state=AppState("15_human_h300"))
    app.ctrl.paused = True
    app.tick()


def test_icons_exist_and_tint():
    for name in icons.PAINTERS:
        img = icons.icon(name, 24, (200, 10, 10))
        assert img.get_size() == (24, 24)
        assert max(img.get_at((x, y)).a for x in range(24) for y in range(24)) > 128, name


def test_brand_name_logo_and_window(monkeypatch):
    assert brand.APP_NAME == "MoveMind"
    logo = brand.window_icon()
    assert logo.get_size() == (64, 64) and logo.get_at((32, 4)).a == 255
    calls = {}
    monkeypatch.setattr(pygame.display, "set_caption", lambda c, *a: calls.setdefault("caption", c))
    monkeypatch.setattr(pygame.display, "set_icon", lambda s: calls.setdefault("icon", s))
    from gameai.gui.pygame_app import run

    run(None, max_frames=1)
    assert calls["caption"] == "MoveMind" and calls["icon"].get_size() == (64, 64)


def test_home_has_no_technical_text(monkeypatch):
    seen: list[str] = []
    orig = render.text

    def spy(s, *a):
        seen.append(s)
        return orig(s, *a)

    monkeypatch.setattr(render, "text", spy)
    app = App(None, surface=pygame.Surface((1280, 720)))
    app.tick()
    text = " ".join(seen)
    assert "Move" in text and "Chơi" in text
    for bad in ("Minimax", "Alpha-Beta", "MCTS", "BTL", "k-in-a-row"):
        assert bad not in text


def test_game_labels_product_wording():
    labels = [label for _, label in GAMES.values()]
    assert labels[:2] == ["Caro 3×3", "Caro 15×15 · 5 quân thắng"]
    assert not any("k=" in lab for lab in labels)


def test_play_cache_does_not_grow_with_frames():
    cfg = GameConfig("15x15", "human_ai", "X", AIChoice("mcts", "easy"))
    app = App(
        AppState(None, 0, overlay=OverlayOpts(True, True), base=build_preset(cfg), config=cfg),
        surface=pygame.Surface((1280, 720)),
    )
    app.ctrl.submit_human_move(112)
    app.ctrl.run_until_idle(60)
    for _ in range(3):
        app.tick()
    before = render.cache_sizes()
    for i in range(40):
        pos = app.view.cell_rect(i % 5).center
        app.handle_event(
            pygame.event.Event(pygame.MOUSEMOTION, pos=pos, rel=(0, 0), buttons=(0, 0, 0))
        )
        app.tick()
    after = render.cache_sizes()
    assert {k: v for k, v in after.items() if v != before.get(k)} == {}


def test_card_shows_short_name_and_tooltip_has_source():
    app = App(AppState("15_human_h300"), surface=pygame.Surface((1280, 720)))
    app.ctrl.paused = True
    app.tick()
    p = app.play
    from gameai.core.game import P2

    assert p.player_name(P2)[0] == "MCTS · Khó"
    assert p.subtitle(P2) == ("Cấu hình thí nghiệm · E3", True)
    lines = p.info_lines(P2)
    assert lines[0].startswith("MCTS h300 5000 iter") and "thí nghiệm" in lines[1]
    tip = p.tips[P2]
    app.handle_event(pygame.event.Event(pygame.MOUSEMOTION, pos=p.info[P2].rect.center, rel=(0, 0),
                                        buttons=(0, 0, 0)))  # fmt: skip
    assert tip.hover
    app.tick()  # vẽ tooltip không lỗi


def test_screenshots_capture(tmp_path):
    from gameai.gui import screenshots

    paths = screenshots.capture(["home", "play3", "demo"], tmp_path, "warm")
    assert [p.name for p in paths] == ["home.png", "play3.png", "demo.png"]
    assert all(p.stat().st_size > 10_000 for p in paths)
