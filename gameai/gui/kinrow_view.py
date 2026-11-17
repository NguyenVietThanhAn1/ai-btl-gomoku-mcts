"""View k-in-row cho GUI (P6.1, làm lại P6.3): 1 click = 1 nước; bàn gỗ + khung + bóng (lớp tĩnh
cache), quân sprite khử răng cưa, nước cuối một màu, đường thắng vạch nối tâm, overlay top-8."""

from __future__ import annotations

import pygame

from gameai.agents.registry import GameSpec
from gameai.core.game import Game, Move
from gameai.games.kinrow import KInRow
from gameai.gui import render
from gameai.gui.controller import MoveInfo
from gameai.gui.view import GameView, OverlayOpts, register_view
from gameai.gui.widgets import CAPTION, Theme, current_theme, draw_text

LABEL_MARGIN = 26  # px cho nhãn hàng (trái) và cột (dưới)
FRAME_PAD = 10  # khung gỗ quanh lưới
GHOST_ALPHA = 120
SHADOW_PAD = 28  # lớp tĩnh rộng hơn rect để bóng khung không bị cắt
TOP_K = 8  # overlay chỉ K nước N lớn nhất
DIRECTIONS = ((0, 1), (1, 0), (1, 1), (1, -1))


def winning_line(board: bytearray, n: int, k: int, move: int) -> list[int]:
    """Các ô cùng màu thẳng hàng ≥ k đi qua `move` (rỗng nếu không có). Chỉ đọc `board`."""
    color = board[move]
    if color == 0:
        return []
    r0, c0 = divmod(move, n)
    for dr, dc in DIRECTIONS:
        cells = [move]
        for sign in (1, -1):
            r, c = r0 + sign * dr, c0 + sign * dc
            while 0 <= r < n and 0 <= c < n and board[r * n + c] == color:
                cells.append(r * n + c)
                r, c = r + sign * dr, c + sign * dc
        if len(cells) >= k:
            return cells
    return []


def top_k(stats: list, k: int = TOP_K) -> list[tuple[int, Move, int, float]]:
    """(hạng 1.., move, N, W/N) của k nước N lớn nhất (hòa N → giữ thứ tự gốc)."""
    ranked = sorted(stats, key=lambda s: -s[2])[:k]
    return [(i + 1, m, n, wn) for i, (m, _w, n, wn) in enumerate(ranked)]


class KInRowView(GameView):
    """Bàn n×n dạng ô, quân đặt trong ô. Lớp tĩnh (bóng, khung, gỗ, lưới, nhãn) dựng 1 lần/theme."""

    def __init__(self, n: int, k: int, rect: pygame.Rect) -> None:
        super().__init__(rect)
        self.n, self.k = n, k
        avail_w = self.rect.w - LABEL_MARGIN - 2 * FRAME_PAD
        avail_h = self.rect.h - LABEL_MARGIN - 2 * FRAME_PAD
        self.cell = min(avail_w, avail_h) // n
        side = self.cell * n
        self.origin = (
            self.rect.x + LABEL_MARGIN + FRAME_PAD + (avail_w - side) // 2,
            self.rect.y + FRAME_PAD + (avail_h - side) // 2,
        )
        self.win_progress = 1.0  # 0→1: đường thắng vẽ dần (animation ở scene)
        self._static: tuple[str, pygame.Surface] | None = None

    # ------------------------------------------------------------ hình học
    @property
    def side(self) -> int:
        return self.cell * self.n

    def board_rect(self) -> pygame.Rect:
        return pygame.Rect(*self.origin, self.side, self.side)

    def cell_rect(self, move: int) -> pygame.Rect:
        r, c = divmod(move, self.n)
        return pygame.Rect(self.origin[0] + c * self.cell, self.origin[1] + r * self.cell,
                           self.cell, self.cell)  # fmt: skip

    def hit_test(self, pos: tuple[int, int], game: Game) -> Move | None:
        x, y = pos[0] - self.origin[0], pos[1] - self.origin[1]
        if not (0 <= x < self.side and 0 <= y < self.side) or game.is_terminal():
            return None
        move = (y // self.cell) * self.n + x // self.cell
        assert isinstance(game, KInRow)
        return move if game.board[move] == 0 else None

    def preview(self, pos: tuple[int, int], game: Game) -> Move | None:
        return self.hit_test(pos, game)  # k-in-row: hit_test không có trạng thái

    def col_label(self, c: int) -> str:
        """Cột: a–c khi bàn nhỏ (n ≤ 5), A–O khi bàn lớn."""
        return chr(ord("a" if self.n <= 5 else "A") + c)

    def move_label(self, move: Move) -> str:
        r, c = divmod(int(move), self.n)
        return f"{self.col_label(c)}{r + 1}"

    def winning_cells(self, game: Game, last: MoveInfo | None) -> list[Move]:
        assert isinstance(game, KInRow)
        if last is None or game.winner() in (None, 0):
            return []
        return winning_line(game.board, self.n, self.k, int(last.move))

    # ------------------------------------------------------------ sprite
    def piece_sprite(self, player_cell: int, theme: Theme | None = None) -> pygame.Surface:
        """Sprite chuẩn (cache) của quân: 1 = X (đen / chữ X), 2 = O (trắng / chữ O)."""
        t = theme or current_theme()
        if self.n <= 5:
            d = self.cell - 2 * (self.cell // 6)
            return render.x_mark(d, t.x_color) if player_cell == 1 else render.o_mark(d, t.o_color)
        d = self.cell - 6
        if player_cell == 1:
            return render.stone(d, t.stone_dark, t.stone_dark_hi, (0, 0, 0))
        return render.stone(d, t.stone_light, t.stone_light_hi, (150, 146, 140))

    def static_layer(self, theme: Theme | None = None) -> pygame.Surface:
        """Bóng + khung + gỗ + lưới + nhãn, kích thước `self.rect`; dựng lại khi đổi theme."""
        t = theme or current_theme()
        if self._static is not None and self._static[0] == t.name:
            return self._static[1]
        layer = pygame.Surface(
            self.rect.inflate(2 * SHADOW_PAD, 2 * SHADOW_PAD).size, pygame.SRCALPHA
        )
        board = self.board_rect().move(SHADOW_PAD - self.rect.x, SHADOW_PAD - self.rect.y)
        frame = board.inflate(2 * FRAME_PAD, 2 * FRAME_PAD)
        blur = 16
        layer.blit(
            render.shadow(frame.w, frame.h, 12, blur, t.shadow_alpha),
            (frame.x - blur, frame.y - blur + 6),
        )
        layer.blit(render.rounded_rect(frame.w, frame.h, 12, t.board_frame), frame)
        inner = frame.inflate(-6, -6)
        wood = render.wood(inner.w, inner.h, t.board_light, t.board_dark, t.board_grain).copy()
        lines = pygame.Surface(inner.size, pygame.SRCALPHA)
        width = 1 if self.n > 5 else 3
        alpha = 150 if self.n > 5 else 200
        ox, oy = board.x - inner.x, board.y - inner.y
        for i in range(self.n + 1):
            if self.n <= 5 and i in (0, self.n):
                continue  # 3×3: chỉ vạch trong như bàn tic-tac-toe
            off = i * self.cell
            pygame.draw.line(
                lines, (*t.grid, alpha), (ox + off, oy), (ox + off, oy + self.side), width
            )
            pygame.draw.line(
                lines, (*t.grid, alpha), (ox, oy + off), (ox + self.side, oy + off), width
            )
        wood.blit(lines, (0, 0))
        wood.blit(
            render.rounded_mask(inner.w, inner.h, 9), (0, 0), special_flags=pygame.BLEND_RGBA_MULT
        )
        layer.blit(wood, inner)
        size = CAPTION if self.n > 5 else 18
        for i in range(self.n):
            mid = i * self.cell + self.cell // 2
            draw_text(layer, self.col_label(i), (board.x + mid, frame.bottom + LABEL_MARGIN // 2),
                      size, t.label, weight="semibold", anchor="center")  # fmt: skip
            draw_text(
                layer,
                str(i + 1),
                (frame.x - LABEL_MARGIN // 2, board.y + mid),
                size,
                t.label,
                weight="semibold",
                anchor="center",
            )
        self._static = (t.name, layer)
        return layer

    # ------------------------------------------------------------ vẽ
    def draw(self, surf: pygame.Surface, game: Game, last: MoveInfo | None,
             overlay_info: MoveInfo | None, opts: OverlayOpts) -> None:  # fmt: skip
        assert isinstance(game, KInRow)
        t = current_theme()
        surf.blit(self.static_layer(t), (self.rect.x - SHADOW_PAD, self.rect.y - SHADOW_PAD))
        ranked = top_k(overlay_info.root_stats) if (opts.show and overlay_info is not None) else []
        for rank, move, _n, _wn in ranked:  # nền overlay dưới quân
            rc = self.cell_rect(int(move)).inflate(-4, -4)
            alpha = 215 - 20 * (rank - 1)
            surf.blit(render.rounded_rect(rc.w, rc.h, 6, (*t.heat, alpha)), rc)
        for m, v in enumerate(game.board):
            if v:
                self.draw_piece(surf, m, v)
        self._draw_win_line(surf, game, last, t)
        if ranked:
            self._draw_ranks(surf, ranked, game, opts.show_wn, t)
        if last is not None:
            self.draw_last_marker(surf, int(last.move), t)
        for m in self.highlights(game):
            rc = self.cell_rect(int(m)).inflate(-2, -2)
            surf.blit(render.rounded_rect(rc.w, rc.h, 6, (*t.accent, 90)), rc)

    def draw_piece(self, surf: pygame.Surface, m: int, v: int, scale: float = 1.0,
                   alpha: int = 255) -> None:  # fmt: skip
        """Vẽ quân `v` (1/2) ở ô `m`; `scale`/`alpha` cho animation đặt quân (không thêm cache)."""
        t = current_theme()
        sprite = self.piece_sprite(v, t)
        center = self.cell_rect(m).center
        if self.n > 5 and scale >= 0.999:
            sh = render.stone_shadow(sprite.get_width(), max(30, t.shadow_alpha))
            surf.blit(sh, sh.get_rect(center=(center[0] + 1, center[1] + 3)))
        if scale < 0.999:
            sprite = render.scaled(sprite, scale)
        if alpha < 255:
            sprite = render.faded(sprite, alpha)
        surf.blit(sprite, sprite.get_rect(center=center))

    def draw_last_marker(self, surf: pygame.Surface, move: int, theme: Theme | None = None) -> None:
        """Nước cuối: một màu `last_move` mọi bàn — vòng quanh quân (15×15), khung bo (3×3)."""
        t = theme or current_theme()
        rc = self.cell_rect(move)
        if self.n > 5:
            sprite = render.ring(self.cell - 1, 3, t.last_move)
        else:
            box = rc.inflate(-8, -8)
            sprite = render.rounded_outline(box.w, box.h, 12, 5, t.last_move)
        surf.blit(sprite, sprite.get_rect(center=rc.center))

    def draw_ghost(self, surf: pygame.Surface, move: Move, player: int) -> None:
        self.draw_piece(surf, int(move), 1 if player == 1 else 2, alpha=GHOST_ALPHA)

    def _draw_win_line(
        self, surf: pygame.Surface, game: KInRow, last: MoveInfo | None, t: Theme
    ) -> None:
        cells = self.winning_cells(game, last)
        if not cells or self.win_progress <= 0:
            return
        ends = sorted(cells, key=lambda m: divmod(int(m), self.n))
        p0, p1 = self.cell_rect(int(ends[0])).center, self.cell_rect(int(ends[-1])).center
        thick = max(6, self.cell // 6)
        dx, dy = p1[0] - p0[0], p1[1] - p0[1]
        sprite = render.line(dx, dy, thick, (*t.win, 235))
        topleft = (min(p0[0], p1[0]) - thick, min(p0[1], p1[1]) - thick)
        prog = min(1.0, self.win_progress)
        if prog >= 0.999:
            surf.blit(sprite, topleft)
            return
        # vẽ dần: cắt hộp bao từ p0 tới p0 + prog·(p1 − p0) (đường đơn điệu → hộp bao đúng)
        cx, cy = p0[0] + dx * prog, p0[1] + dy * prog
        clip = pygame.Rect(min(p0[0], cx) - thick, min(p0[1], cy) - thick,
                           abs(cx - p0[0]) + 2 * thick, abs(cy - p0[1]) + 2 * thick)  # fmt: skip
        area = clip.move(-topleft[0], -topleft[1])
        surf.blit(sprite, clip.topleft, area=area)

    def _draw_ranks(
        self, surf: pygame.Surface, ranked: list, game: KInRow, show_wn: bool, t: Theme
    ) -> None:
        size = 12 if self.n > 5 else 22
        step = size + 1
        for rank, move, n, wn in ranked:
            rc = self.cell_rect(int(move))
            occupied = game.board[int(move)] != 0
            dark_stone = occupied and game.board[int(move)] == 1 and self.n > 5
            ink = (255, 255, 255) if dark_stone else (24, 20, 16)
            lines = [f"#{rank}", str(n)] + ([f"{wn:.2f}".lstrip("0")] if show_wn else [])
            y = rc.centery - step * len(lines) // 2
            for i, line in enumerate(lines):
                draw_text(surf, line, (rc.centerx, y + i * step), size, ink,
                          weight="bold" if i == 0 else "semibold", anchor="midtop")  # fmt: skip


register_view("kinrow", lambda spec, rect: KInRowView(spec.params.get("n", 15),
                                                       spec.params.get("k", 5), rect))  # fmt: skip


def view_for(spec: GameSpec, rect: pygame.Rect) -> KInRowView:
    """Tiện ích cho test."""
    return KInRowView(spec.params.get("n", 15), spec.params.get("k", 5), rect)
