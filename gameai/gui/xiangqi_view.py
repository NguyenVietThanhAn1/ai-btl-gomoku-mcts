"""View cờ tướng cho GUI (P6.2, D-37): bàn 9×10 giao điểm như bàn thật (sông ngắt đường dọc, cung,
dấu chữ thập pháo/tốt), quân đĩa tròn viền đôi chữ Hán, input 2 bước (chọn quân → ô đích),
nước cuối, quầng tướng bị chiếu, xoay bàn khi người cầm Đen."""

from __future__ import annotations

import pygame

from gameai.agents.registry import GameSpec
from gameai.core.game import DRAW, P1, Game, Move
from gameai.games.xiangqi import NUM_SQ, Xiangqi, move_to_iccs
from gameai.gui import render
from gameai.gui.controller import MoveInfo
from gameai.gui.view import GameView, OverlayOpts, get_cjk_font, get_font, register_view
from gameai.gui.widgets import CAPTION, Theme, current_theme, draw_text

FILES, RANKS = 9, 10
LABEL_MARGIN = 26  # px cho nhãn hàng (trái) và cột (dưới)
FRAME_PAD = 10  # khung gỗ quanh vùng bàn
SHADOW_PAD = 28  # lớp tĩnh rộng hơn rect để bóng khung không bị cắt
PIECE_INSET = 6  # đường kính quân = cell − 6 → bán kính = cell/2 − 3
BORDER_GAP = 6  # khe tối thiểu giữa mép quân ở giao điểm biên và viền trong
BORDER_STEP = 5  # khoảng giữa viền trong (mảnh) và viền ngoài (dày) của viền đôi
EDGE_PAD = 16  # thêm vào nửa ô: lề gỗ từ giao điểm biên tới mép gỗ (chứa viền đôi)
GHOST_ALPHA = 120
LINE_ALPHA = 215
SELECT_ALPHA = 90  # đĩa t.accent dưới quân đang chọn
SELECT_GROW = 8  # đĩa chọn rộng hơn quân: d = cell + 8 (quân d = cell − 6) → lộ vành 7 px
CORNER_LEN = 0.26  # độ dài mỗi cạnh góc của khung nước cuối (theo cạnh khung)
CORNER_W = 3

# Chữ trên quân theo |quân| (1 tướng … 7 tốt); Đỏ / Đen dùng chữ khác nhau như bàn thật.
RED_CHARS = {1: "帥", 2: "仕", 3: "相", 4: "傌", 5: "俥", 6: "炮", 7: "兵"}
BLACK_CHARS = {1: "將", 2: "士", 3: "象", 4: "馬", 5: "車", 6: "砲", 7: "卒"}
RIVER_CHARS = "楚河漢界"
# Chữ Việt trên quân khi máy không có font chữ Hán.
VI_NAMES = {1: "Tướng", 2: "Sĩ", 3: "Tượng", 4: "Mã", 5: "Xe", 6: "Pháo", 7: "Tốt"}
ALL_CHARS = "".join(RED_CHARS.values()) + "".join(BLACK_CHARS.values()) + RIVER_CHARS

PIECE_FACE = (240, 222, 186)
PIECE_HI = (255, 248, 228)
PIECE_RIM = (128, 88, 50)
RED_INK = (178, 30, 30)
BLACK_INK = (26, 26, 26)
CHECK_GLOW = (226, 48, 40)

# Dấu chữ thập: vị trí pháo (rank 2/7, file b/h) và tốt (rank 3/6, file a c e g i).
CANNON_MARKS = [(f, r) for r in (2, 7) for f in (1, 7)]
PAWN_MARKS = [(f, r) for r in (3, 6) for f in (0, 2, 4, 6, 8)]
MARKERS = CANNON_MARKS + PAWN_MARKS


def piece_char(piece: int) -> str:
    """Chữ Hán của quân có dấu (Đỏ dương, Đen âm)."""
    return (RED_CHARS if piece > 0 else BLACK_CHARS)[abs(piece)]


def end_reason(game: Xiangqi) -> str | None:
    """Lý do kết thúc: "Chiếu bí" / "Bí nước" (bên tới lượt hết nước → thua), "Hòa - lặp thế 3 lần",
    "Hòa - đạt giới hạn N nước" (`max_plies`); None khi ván chưa hết.

    Chỉ dùng API công khai: hòa mà `ply < max_plies` ⇒ do lặp thế (D-22: lặp lần 3 ưu tiên hơn
    `max_plies`; khi cả hai cùng xảy ra ở đúng ply giới hạn thì ghi là giới hạn nước)."""
    w = game.winner()
    if w is None:
        return None
    if w == DRAW:
        if game.ply >= game.max_plies:
            return f"Hòa - đạt giới hạn {game.max_plies} nước"
        return "Hòa - lặp thế 3 lần"
    return "Chiếu bí" if game.in_check() else "Bí nước"


class XiangqiView(GameView):
    """Quân đứng trên giao điểm. `flipped` = Đen ở dưới (người duy nhất cầm Đen)."""

    def __init__(self, rect: pygame.Rect, flipped: bool = False) -> None:
        super().__init__(rect)
        avail_w = self.rect.w - LABEL_MARGIN - 2 * FRAME_PAD
        avail_h = self.rect.h - LABEL_MARGIN - 2 * FRAME_PAD
        # Vùng bàn = lưới + lề `margin` = cell//2 + EDGE_PAD mỗi phía
        # → cell ≤ (avail − 2·EDGE_PAD) // số giao điểm.
        self.cell = min(
            (avail_w - 2 * EDGE_PAD) // FILES, (avail_h - 2 * EDGE_PAD) // RANKS
        )  # khoảng cách giữa 2 giao điểm (BOARD_RECT 672 px → 59)
        self.margin = self.cell // 2 + EDGE_PAD  # giao điểm biên → mép vùng bàn
        bw, bh = self.board_size()
        self.board_origin = (
            self.rect.x + LABEL_MARGIN + FRAME_PAD + (avail_w - bw) // 2,
            self.rect.y + FRAME_PAD + (avail_h - bh) // 2,
        )
        self.origin = (self.board_origin[0] + self.margin, self.board_origin[1] + self.margin)
        self.flipped = flipped
        self.selected: int | None = None  # ô quân đang chọn (máy trạng thái input, D-28)
        self._board: list[int] | None = None  # bàn của lần draw gần nhất (cho draw_ghost)
        self._static: tuple[tuple[str, bool], pygame.Surface] | None = None

    # ------------------------------------------------------------ hình học
    def board_size(self) -> tuple[int, int]:
        return (
            (FILES - 1) * self.cell + 2 * self.margin,
            (RANKS - 1) * self.cell + 2 * self.margin,
        )

    def board_rect(self) -> pygame.Rect:
        """Vùng gỗ có lưới (không gồm khung / nhãn)."""
        return pygame.Rect(*self.board_origin, *self.board_size())

    def piece_radius(self) -> float:
        return (self.cell - PIECE_INSET) / 2

    def border_offsets(self) -> tuple[float, float]:
        """Khoảng cách (px) từ giao điểm biên tới viền trong / viền ngoài của viền đôi."""
        inner = self.piece_radius() + BORDER_GAP
        return inner, inner + BORDER_STEP

    def screen_cr(self, sq: int) -> tuple[int, int]:
        """(cột, hàng) trên màn hình, hàng 0 ở trên."""
        rank, file = divmod(sq, FILES)
        if self.flipped:
            return FILES - 1 - file, rank
        return file, RANKS - 1 - rank

    def sq_at(self, col: int, row: int) -> int:
        """Ô tại (cột, hàng) màn hình — nghịch đảo của `screen_cr`."""
        if self.flipped:
            return row * FILES + (FILES - 1 - col)
        return (RANKS - 1 - row) * FILES + col

    def sq_center(self, sq: int) -> tuple[int, int]:
        col, row = self.screen_cr(sq)
        return self.origin[0] + col * self.cell, self.origin[1] + row * self.cell

    def pos_to_sq(self, pos: tuple[int, int]) -> int | None:
        """Giao điểm gần nhất trong bán kính nửa ô; None nếu ngoài bàn."""
        x, y = pos[0] - self.origin[0], pos[1] - self.origin[1]
        col, row = round(x / self.cell), round(y / self.cell)
        if not (0 <= col < FILES and 0 <= row < RANKS):
            return None
        if abs(x - col * self.cell) > self.cell / 2 or abs(y - row * self.cell) > self.cell / 2:
            return None
        return self.sq_at(col, row)

    def col_label(self, col: int) -> str:
        """Nhãn cột màn hình = file ICCS (a–i), xoay theo `flipped`."""
        return chr(ord("a") + self.sq_at(col, 0) % FILES)

    def row_label(self, row: int) -> str:
        """Nhãn hàng màn hình = rank ICCS (0–9), xoay theo `flipped`."""
        return str(self.sq_at(0, row) // FILES)

    # ------------------------------------------------------------ input (D-28)
    @staticmethod
    def _own(piece: int, player: int) -> bool:
        return piece > 0 if player == P1 else piece < 0

    def _targets(self, game: Xiangqi, frm: int) -> list[Move]:
        return [m for m in game.legal_moves() if m // NUM_SQ == frm]

    def hit_test(self, pos: tuple[int, int], game: Game) -> Move | None:
        """Click 1 chọn quân mình (click lại → bỏ chọn); click 2 vào đích hợp lệ → `Move`."""
        assert isinstance(game, Xiangqi)
        sq = self.pos_to_sq(pos)
        if sq is None or game.is_terminal():
            self.selected = None
            return None
        if self.selected is not None:
            move = self.selected * NUM_SQ + sq
            if move in self._targets(game, self.selected):
                self.selected = None
                return move
        if sq != self.selected and self._own(game.board[sq], game.current_player()):
            self.selected = sq
        else:
            self.selected = None
        return None

    def preview(self, pos: tuple[int, int], game: Game) -> Move | None:
        """Nước nếu click ở `pos` (đích hợp lệ của quân đang chọn); không đổi `selected`."""
        assert isinstance(game, Xiangqi)
        if self.selected is None or game.is_terminal():
            return None
        sq = self.pos_to_sq(pos)
        if sq is None:
            return None
        move = self.selected * NUM_SQ + sq
        return move if move in self._targets(game, self.selected) else None

    def reset_input(self) -> None:
        self.selected = None

    def highlights(self, game: Game) -> list[Move]:
        assert isinstance(game, Xiangqi)
        if self.selected is None or game.is_terminal():
            return []
        return self._targets(game, self.selected)

    # ------------------------------------------------------------ lời văn
    def move_label(self, move: Move) -> str:
        return move_to_iccs(int(move))

    def side_name(self, player: int) -> str:
        return "Đỏ" if player == P1 else "Đen"

    def side_symbol(self, player: int) -> str:
        """Ký hiệu cột "bên" của lịch sử: PlayScene thay "●"/"○" bằng `side_dot`."""
        return "●" if player == P1 else "○"

    def side_dot(self, player: int, d: int) -> pygame.Surface:
        """Đĩa trơn màu bên (Đỏ / Đen) đường kính `d` — chấm lịch sử."""
        ink = RED_INK if player == P1 else BLACK_INK
        return render.stone(d, ink, PIECE_HI if player == P1 else (90, 90, 90), PIECE_RIM)

    def avatar(self, player: int, d: int) -> pygame.Surface:
        """Quân tướng của bên (帥 Đỏ / 將 Đen) đường kính `d` — avatar thẻ người chơi."""
        return _piece_sprite(1 if player == P1 else -1, d)

    def status_text(self, game: Game) -> str | None:
        assert isinstance(game, Xiangqi)
        if game.is_terminal() or not game.in_check():
            return None
        return f"{self.side_name(game.current_player())} đang bị chiếu"

    def end_reason(self, game: Game) -> str | None:
        assert isinstance(game, Xiangqi)
        return end_reason(game)

    # ------------------------------------------------------------ sprite
    def piece_sprite(self, piece: int) -> pygame.Surface:
        """Sprite (cache) của quân có dấu ở cỡ chuẩn của bàn."""
        return _piece_sprite(piece, self.cell - PIECE_INSET)

    def static_layer(self, theme: Theme | None = None) -> pygame.Surface:
        """Bóng + khung + gỗ + đường kẻ + sông + nhãn; dựng lại khi đổi theme / xoay bàn."""
        t = theme or current_theme()
        key = (t.name, self.flipped)
        if self._static is not None and self._static[0] == key:
            return self._static[1]
        layer = pygame.Surface(
            self.rect.inflate(2 * SHADOW_PAD, 2 * SHADOW_PAD).size, pygame.SRCALPHA
        )
        board = self.board_rect().move(SHADOW_PAD - self.rect.x, SHADOW_PAD - self.rect.y)
        frame = board.inflate(2 * FRAME_PAD, 2 * FRAME_PAD)
        blur = 16
        layer.blit(render.shadow(frame.w, frame.h, 12, blur, t.shadow_alpha),
                   (frame.x - blur, frame.y - blur + 6))  # fmt: skip
        layer.blit(render.rounded_rect(frame.w, frame.h, 12, t.board_frame), frame)
        inner = frame.inflate(-6, -6)
        wood = render.wood(inner.w, inner.h, t.board_light, t.board_dark, t.board_grain).copy()
        ox = self.origin[0] - self.rect.x + SHADOW_PAD - inner.x
        oy = self.origin[1] - self.rect.y + SHADOW_PAD - inner.y
        wood.blit(self._lines(inner.size, (ox, oy), t), (0, 0))
        self._draw_river(wood, (ox, oy), t)
        wood.blit(render.rounded_mask(inner.w, inner.h, 9), (0, 0),
                  special_flags=pygame.BLEND_RGBA_MULT)  # fmt: skip
        layer.blit(wood, inner)
        lx = self.origin[0] - self.rect.x + SHADOW_PAD
        ly = self.origin[1] - self.rect.y + SHADOW_PAD
        by, bx = frame.bottom + LABEL_MARGIN // 2, frame.x - LABEL_MARGIN // 2
        for col in range(FILES):
            draw_text(layer, self.col_label(col), (lx + col * self.cell, by), CAPTION, t.label,
                      weight="semibold", anchor="center")  # fmt: skip
        for row in range(RANKS):
            draw_text(layer, self.row_label(row), (bx, ly + row * self.cell), CAPTION, t.label,
                      weight="semibold", anchor="center")  # fmt: skip
        self._static = (key, layer)
        return layer

    def _lines(self, size: tuple[int, int], o: tuple[int, int], t: Theme) -> pygame.Surface:
        """Đường kẻ vẽ ở 4× rồi thu nhỏ (khử răng cưa). Đường dọc trong ngắt ở sông."""
        ss = render.SS
        big = pygame.Surface((size[0] * ss, size[1] * ss), pygame.SRCALPHA)
        color = (*t.grid, LINE_ALPHA)
        s = self.cell

        def pt(col: float, row: float) -> tuple[int, int]:
            return round((o[0] + col * s) * ss), round((o[1] + row * s) * ss)

        def seg(a: tuple[float, float], b: tuple[float, float], w: float = 2) -> None:
            pygame.draw.line(big, color, pt(*a), pt(*b), round(w * ss))

        for row in range(RANKS):
            seg((0, row), (FILES - 1, row))
        for col in range(FILES):
            if col in (0, FILES - 1):
                seg((col, 0), (col, RANKS - 1))
            else:  # ngắt ở sông (giữa hàng 4 và 5)
                seg((col, 0), (col, 4))
                seg((col, 5), (col, RANKS - 1))
        for r0 in (0, 7):  # chéo cung (đối xứng → không phụ thuộc xoay)
            seg((3, r0), (5, r0 + 2))
            seg((5, r0), (3, r0 + 2))
        # Viền đôi (trong mảnh, ngoài dày) cách giao điểm biên ≥ bán kính quân + BORDER_GAP.
        grid = pygame.Rect(*pt(0, 0), (FILES - 1) * s * ss, (RANKS - 1) * s * ss)
        for off, w in zip(self.border_offsets(), (1.6, 3), strict=True):
            half = round(w * ss) // 2  # nét pygame.draw.rect vẽ vào trong → lùi ra nửa nét
            r = grid.inflate(2 * (round(off * ss) + half), 2 * (round(off * ss) + half))
            pygame.draw.rect(big, color, r, round(w * ss))
        g, ln = 0.07, 0.17  # khe + độ dài nét dấu chữ thập (theo ô)
        for f, r in MARKERS:
            col, row = self.screen_cr(r * FILES + f)
            for dx in (-1, 1):
                if not 0 <= col + dx < FILES:
                    continue  # cột biên: chỉ nửa dấu phía trong
                for dy in (-1, 1):
                    corner = (col + dx * g, row + dy * g)
                    seg(corner, (col + dx * (g + ln), row + dy * g), 1.6)
                    seg(corner, (col + dx * g, row + dy * (g + ln)), 1.6)
        return pygame.transform.smoothscale(big, size)

    def _draw_river(self, surf: pygame.Surface, o: tuple[int, int], t: Theme) -> None:
        """楚河 (trái) 漢界 (phải) giữa hàng 4 và 5; bỏ qua nếu không có font chữ Hán."""
        font = get_cjk_font(int(self.cell * 0.5))
        if font is None:
            return
        y = o[1] + 4.5 * self.cell
        for ch, col in zip(RIVER_CHARS, (1.5, 2.5, 5.5, 6.5), strict=True):
            img = font.render(ch, True, t.grid)
            img.set_alpha(190)
            surf.blit(img, img.get_rect(center=(round(o[0] + col * self.cell), round(y))))

    # ------------------------------------------------------------ vẽ
    def draw(self, surf: pygame.Surface, game: Game, last: MoveInfo | None,
             overlay_info: MoveInfo | None, opts: OverlayOpts) -> None:  # fmt: skip
        """Overlay N/W/N của MCTS không vẽ trên bàn cờ tướng (✂ PLAN P6.2)."""
        assert isinstance(game, Xiangqi)
        t = current_theme()
        self._board = game.board
        surf.blit(self.static_layer(t), (self.rect.x - SHADOW_PAD, self.rect.y - SHADOW_PAD))
        selecting = self.selected is not None and not game.is_terminal()
        if game.in_check() and game.winner() != DRAW:  # quầng đỏ dưới tướng bị chiếu
            king = 1 if game.current_player() == P1 else -1
            if king in game.board:
                ksq = game.board.index(king)
                c = self.sq_center(ksq)
                if selecting and self.selected == ksq:
                    # Đang chọn chính tướng bị chiếu: bỏ quầng tô (trộn màu với đĩa chọn),
                    # đẩy vòng đỏ ra ngoài đĩa → thấy cả đĩa chọn lẫn dấu chiếu.
                    ring = render.ring(self.cell + SELECT_GROW + 8, 3, (*CHECK_GLOW, 235))
                else:
                    glow = render.circle(self.cell + 10, (*CHECK_GLOW, 120))
                    surf.blit(glow, glow.get_rect(center=c))
                    ring = render.ring(self.cell + 2, 4, (*CHECK_GLOW, 235))
                surf.blit(ring, ring.get_rect(center=c))
        if selecting:  # đang chọn: đĩa mờ DƯỚI quân (sau quầng chiếu)
            assert self.selected is not None
            disc = render.circle(self.cell + SELECT_GROW, (*t.accent, SELECT_ALPHA))
            surf.blit(disc, disc.get_rect(center=self.sq_center(self.selected)))
        for sq, piece in enumerate(game.board):
            if piece:
                self.draw_piece(surf, sq, piece)
        if last is not None:  # nước cuối: khung 4 góc vuông ở ô đi và ô đến
            corners = _corner_marks(self.cell - 2, t.last_move)
            for sq in (int(last.move) // NUM_SQ, int(last.move) % NUM_SQ):
                surf.blit(corners, corners.get_rect(center=self.sq_center(sq)))
        for m in self.highlights(game):
            to = int(m) % NUM_SQ
            c = self.sq_center(to)
            if game.board[to]:  # ô ăn quân: vòng
                hl = render.ring(self.cell - 4, 5, (*t.accent, 200))
            else:  # ô trống: chấm
                hl = render.circle(max(10, self.cell // 4), (*t.accent, 200))
            surf.blit(hl, hl.get_rect(center=c))

    def draw_piece(self, surf: pygame.Surface, sq: int, piece: int, alpha: int = 255) -> None:
        t = current_theme()
        sprite = self.piece_sprite(piece)
        c = self.sq_center(sq)
        if alpha >= 255:
            sh = render.stone_shadow(sprite.get_width(), max(30, t.shadow_alpha))
            surf.blit(sh, sh.get_rect(center=(c[0] + 1, c[1] + 3)))
        else:
            sprite = render.faded(sprite, alpha)
        surf.blit(sprite, sprite.get_rect(center=c))

    def draw_ghost(self, surf: pygame.Surface, move: Move, player: int) -> None:
        """Quân đang chọn, mờ, ở ô đích (bàn lấy từ lần `draw` ngay trước)."""
        if self._board is None:
            return
        piece = self._board[int(move) // NUM_SQ]
        if piece:
            self.draw_piece(surf, int(move) % NUM_SQ, piece, alpha=GHOST_ALPHA)


@render._cached(8)
def _corner_marks(d: int, color: tuple[int, ...]) -> pygame.Surface:
    """Khung 4 góc vuông cạnh `d` (nét CORNER_W) — dấu nước cuối, khác hẳn vòng tròn / đĩa."""
    out = pygame.Surface((d, d), pygame.SRCALPHA)
    arm, w = max(6, round(d * CORNER_LEN)), CORNER_W
    for x0, dx in ((0, 1), (d - 1, -1)):
        for y0, dy in ((0, 1), (d - 1, -1)):
            xs = sorted((x0, x0 + dx * (arm - 1)))
            ys = sorted((y0, y0 + dy * (w - 1)))
            out.fill(color, pygame.Rect(xs[0], ys[0], xs[1] - xs[0] + 1, ys[1] - ys[0] + 1))
            xs = sorted((x0, x0 + dx * (w - 1)))
            ys = sorted((y0, y0 + dy * (arm - 1)))
            out.fill(color, pygame.Rect(xs[0], ys[0], xs[1] - xs[0] + 1, ys[1] - ys[0] + 1))
    return out


@render._cached(32)
def _piece_sprite(piece: int, d: int) -> pygame.Surface:
    """Đĩa gỗ sáng (gradient như quân caro) + viền ngoài tối + viền trong màu bên + chữ."""
    ink = RED_INK if piece > 0 else BLACK_INK
    out = render.stone(d, PIECE_FACE, PIECE_HI, PIECE_RIM).copy()
    inner = render.ring(round(d * 0.82), max(2, d // 24), ink)
    out.blit(inner, inner.get_rect(center=(d // 2, d // 2)))
    font = get_cjk_font(round(d * 0.54 * render.SS))
    if font is not None:
        big = font.render(piece_char(piece), True, ink)
        img = pygame.transform.smoothscale(
            big, (max(1, big.get_width() // render.SS), max(1, big.get_height() // render.SS))
        )
    else:
        name = VI_NAMES[abs(piece)]
        size = max(10, round(d * (0.36 if len(name) <= 3 else 0.27)))
        img = get_font(size, weight="bold").render(name, True, ink)
    out.blit(img, img.get_rect(center=(d // 2, d // 2)))
    return out


register_view("xiangqi", lambda spec, rect: XiangqiView(rect))


def view_for(spec: GameSpec, rect: pygame.Rect, flipped: bool = False) -> XiangqiView:
    """Tiện ích cho test."""
    return XiangqiView(rect, flipped)
