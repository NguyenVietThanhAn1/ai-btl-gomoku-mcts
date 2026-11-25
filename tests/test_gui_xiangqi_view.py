"""P6.2: view cờ tướng — tọa độ/xoay bàn, máy trạng thái chọn quân, glyph + font dự phòng,
end_reason / status_text, lề viền đôi, đánh dấu (D-28, D-37)."""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from pathlib import Path  # noqa: E402

import pygame  # noqa: E402
import pytest  # noqa: E402

from gameai.games.xiangqi import NUM_SQ, Xiangqi, iccs_to_move  # noqa: E402
from gameai.gui import render, view  # noqa: E402
from gameai.gui.controller import MoveInfo  # noqa: E402
from gameai.gui.play_scene import BOARD_RECT  # noqa: E402
from gameai.gui.view import OverlayOpts, get_cjk_font  # noqa: E402
from gameai.gui.xiangqi_view import (  # noqa: E402
    ALL_CHARS,
    FILES,
    RANKS,
    XiangqiView,
    _piece_sprite,
    end_reason,
)


def sq(text: str) -> int:
    """'e0' → ô."""
    return int(text[1]) * FILES + ord(text[0]) - ord("a")


@pytest.fixture(autouse=True)
def _pygame():
    pygame.init()
    yield
    pygame.quit()


def click(v: XiangqiView, g: Xiangqi, square: int):
    return v.hit_test(v.sq_center(square), g)


# ---------------------------------------------------------------- tọa độ
@pytest.mark.parametrize("flipped", [False, True])
def test_round_trip_all_90_points(flipped):
    v = XiangqiView(BOARD_RECT, flipped)
    centers = set()
    for s in range(NUM_SQ):
        c = v.sq_center(s)
        centers.add(c)
        assert v.sq_at(*v.screen_cr(s)) == s
        assert v.pos_to_sq(c) == s
        assert v.pos_to_sq((c[0] + v.cell // 2 - 1, c[1] - v.cell // 2 + 1)) == s  # mép vùng bắt
    assert len(centers) == NUM_SQ
    assert v.pos_to_sq((v.origin[0] - v.cell, v.origin[1])) is None  # ngoài lưới


def test_labels_follow_flip():
    v = XiangqiView(BOARD_RECT)
    assert [v.col_label(c) for c in range(FILES)] == list("abcdefghi")
    assert [v.row_label(r) for r in range(RANKS)] == [str(9 - r) for r in range(RANKS)]
    assert v.screen_cr(sq("a0")) == (0, RANKS - 1)  # Đỏ ở dưới, a0 góc dưới-trái
    f = XiangqiView(BOARD_RECT, flipped=True)
    assert [f.col_label(c) for c in range(FILES)] == list("ihgfedcba")
    assert [f.row_label(r) for r in range(RANKS)] == [str(r) for r in range(RANKS)]
    assert f.screen_cr(sq("a0")) == (FILES - 1, 0)  # Đen ở dưới, a0 góc trên-phải


def test_margins_double_border_clear_of_pieces():
    v = XiangqiView(BOARD_RECT)
    inner, outer = v.border_offsets()
    assert inner >= v.piece_radius() + 6
    assert outer + 2 < v.margin  # viền ngoài (cả nét dày) nằm trong vùng gỗ
    board = v.board_rect()
    assert BOARD_RECT.contains(board.inflate(20, 20))  # khung FRAME_PAD vẫn trong BOARD_RECT
    assert board.x - 26 >= BOARD_RECT.x  # chừa lề nhãn hàng bên trái
    assert v.cell >= 55


# ---------------------------------------------------------------- input (D-28)
def test_select_deselect_switch_and_move():
    g, v = Xiangqi(), XiangqiView(BOARD_RECT)
    assert click(v, g, sq("a9")) is None and v.selected is None  # quân đối phương: không chọn
    assert click(v, g, sq("a0")) is None and v.selected == sq("a0")  # chọn xe
    assert click(v, g, sq("a0")) is None and v.selected is None  # click lại: bỏ chọn
    click(v, g, sq("a0"))
    assert click(v, g, sq("h0")) is None and v.selected == sq("h0")  # đổi chọn sang mã
    assert click(v, g, sq("e5")) is None and v.selected is None  # ô không hợp lệ: bỏ chọn
    click(v, g, sq("a0"))
    assert v.preview(v.sq_center(sq("a2")), g) == iccs_to_move("a0a2")
    assert v.preview(v.sq_center(sq("b2")), g) is None
    assert v.selected == sq("a0")  # preview không đổi trạng thái
    assert {m // NUM_SQ for m in v.highlights(g)} == {sq("a0")}
    assert click(v, g, sq("a2")) == iccs_to_move("a0a2") and v.selected is None
    assert v.hit_test((0, 0), g) is None and v.selected is None
    v.selected = sq("h0")
    v.reset_input()
    assert v.selected is None


def test_capture_on_last_move_target_still_highlighted():
    """Ô ăn quân trùng ô đến của nước cuối: highlights() vẫn trả nước ăn, vẽ không lỗi."""
    g = Xiangqi()
    last = iccs_to_move("b2b9")  # pháo Đỏ ăn mã, đứng ở b9
    g.play(last)
    v = XiangqiView(BOARD_RECT)
    assert click(v, g, sq("a9")) is None and v.selected == sq("a9")
    cap = iccs_to_move("a9b9")
    assert cap in v.highlights(g) and cap % NUM_SQ == last % NUM_SQ
    surf = pygame.Surface((720, 720))
    v.draw(surf, g, MoveInfo(last, 1, True), None, OverlayOpts(False, False))
    assert click(v, g, sq("b9")) == cap


def test_selection_disc_drawn_under_piece():
    g, v = Xiangqi(), XiangqiView(BOARD_RECT)
    a, b = pygame.Surface((720, 720)), pygame.Surface((720, 720))
    v.draw(a, g, None, None, OverlayOpts(False, False))
    v.selected = sq("e3")
    v.draw(b, g, None, None, OverlayOpts(False, False))
    cx, cy = v.sq_center(sq("e3"))
    edge = (cx, round(cy - v.piece_radius() - 3))  # vành đĩa lộ ra ngoài quân
    assert a.get_at(edge) != b.get_at(edge)
    assert a.get_at((cx, cy)) == b.get_at((cx, cy))  # tâm quân không bị phủ


def test_selected_king_in_check_shows_disc_and_outer_check_ring():
    g = Xiangqi("3k5/9/9/9/9/9/9/9/9/3R1K3 b - - 0 1")  # Đen bị chiếu, tướng d9
    v = XiangqiView(BOARD_RECT)
    king = sq("d9")
    plain, sel = pygame.Surface((720, 720)), pygame.Surface((720, 720))
    v.draw(plain, g, None, None, OverlayOpts(False, False))  # chỉ quầng chiếu
    assert click(v, g, king) is None and v.selected == king
    v.draw(sel, g, None, None, OverlayOpts(False, False))
    cx, cy = v.sq_center(king)
    d = (v.piece_radius() + 3) * 0.7071  # vành quanh quân, chéo trên-trái (tránh bóng, đường kẻ)
    pt = (round(cx - d), round(cy - d))
    a, b = plain.get_at(pt), sel.get_at(pt)
    assert a.r - a.g > 40  # không chọn: vành đỏ của quầng chiếu
    assert b.g - b.r > a.g - a.r + 40  # chọn: thấy đĩa accent xanh, không bị đỏ trộn
    ring_r = (v.cell + 16) / 2 - 1.5
    red = sel.get_at((cx, round(cy - ring_r)))  # vòng chiếu đẩy ra ngoài đĩa (phía trên, ô trống)
    assert red.r > red.g + 60


@pytest.mark.parametrize(
    ("fen", "frm"),
    [
        (
            "4k4/9/9/9/4p4/9/4P4/4C4/9/4K4 w - - 0 1",
            "e2",
        ),  # pháo: ngòi e3 (quân mình), ăn qua ngòi e5
        ("4k4/9/9/9/9/9/9/2P6/2H6/4K4 w - - 0 1", "c1"),  # mã bị cản chân ở c2
    ],
)
def test_highlights_equal_legal_moves_cannon_screen_and_horse_leg(fen, frm):
    g, v = Xiangqi(fen), XiangqiView(BOARD_RECT)
    assert click(v, g, sq(frm)) is None and v.selected == sq(frm)
    assert sorted(v.highlights(g)) == sorted(m for m in g.legal_moves() if m // NUM_SQ == sq(frm))


def test_click_when_game_over_returns_none():
    g, v = Xiangqi("3k5/9/9/9/9/9/9/9/3R5/4K4 b - - 0 1"), XiangqiView(BOARD_RECT)  # chiếu bí
    assert g.is_terminal()
    assert click(v, g, sq("d9")) is None and v.selected is None and v.highlights(g) == []
    assert v.preview(v.sq_center(sq("e9")), g) is None


# ---------------------------------------------------------------- font
def test_packaged_font_has_all_glyphs():
    assert view.CJK_FILE.exists()
    font = get_cjk_font(40)
    assert font is not None
    notdef = pygame.image.tobytes(font.render("￿", True, (0, 0, 0)), "RGBA")
    for ch in ALL_CHARS:
        assert font.metrics(ch)[0] is not None, ch
        assert pygame.image.tobytes(font.render(ch, True, (0, 0, 0)), "RGBA") != notdef, ch


def test_font_fallback_to_vietnamese_names(monkeypatch):
    monkeypatch.setattr(view, "CJK_FILE", Path("khong_co_font.otf"))
    monkeypatch.setattr(view, "CJK_SYSTEM", ())
    view._load_cjk.cache_clear()
    render.clear_caches()
    try:
        assert get_cjk_font(20) is None
        assert get_cjk_font(20, path=Path("khong_co_font.otf")) is None
        sprite = _piece_sprite(5, 53)  # Xe → chữ "Xe"
        assert sprite.get_size() == (53, 53)
        g, v = Xiangqi(), XiangqiView(BOARD_RECT)
        v.draw(pygame.Surface((720, 720)), g, None, None, OverlayOpts(False, False))
    finally:
        view._load_cjk.cache_clear()
        render.clear_caches()


# ---------------------------------------------------------------- lời văn
@pytest.mark.parametrize(
    ("fen", "reason"),
    [
        ("3k5/9/9/9/9/9/9/9/3R5/4K4 b - - 0 1", "Chiếu bí"),
        ("3k5/R8/9/9/9/9/9/9/9/4K4 b - - 0 1", "Bí nước"),
    ],
)
def test_end_reason_mate_and_stalemate(fen, reason):
    g = Xiangqi(fen)
    assert g.is_terminal()
    assert end_reason(g) == reason == XiangqiView(BOARD_RECT).end_reason(g)
    assert XiangqiView(BOARD_RECT).status_text(g) is None  # hết ván: không báo chiếu


def test_end_reason_draws_and_none():
    assert end_reason(Xiangqi()) is None
    g = Xiangqi(max_plies=2)
    for s in ("h0g2", "h9g7"):
        g.play(iccs_to_move(s))
    assert end_reason(g) == "Hòa — đạt giới hạn 2 nước"
    g = Xiangqi()
    for _ in range(2):
        for s in ("h0g2", "h9g7", "g2h0", "g7h9"):
            g.play(iccs_to_move(s))
    assert g.is_terminal() and end_reason(g) == "Hòa — lặp thế 3 lần"


def test_status_text_check():
    v = XiangqiView(BOARD_RECT)
    g = Xiangqi("3k5/9/9/9/9/9/9/9/9/3R1K3 b - - 0 1")  # Đen bị chiếu, còn đường thoát e9
    assert not g.is_terminal() and v.status_text(g) == "Đen đang bị chiếu"
    assert v.status_text(Xiangqi()) is None
