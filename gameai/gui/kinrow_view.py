"""View k-in-row cho GUI: 1 click = 1 nước; nhãn tọa độ, quân mờ khi hover, overlay N, W/N."""

from __future__ import annotations

import pygame

from gameai.agents.registry import GameSpec
from gameai.core.game import Game, Move
from gameai.games.kinrow import KInRow
from gameai.gui.controller import MoveInfo
from gameai.gui.view import GameView, OverlayOpts, get_font, register_view

BOARD_BG = (222, 184, 135)
GRID = (90, 60, 30)
X_COLOR = (25, 25, 25)
O_COLOR = (245, 245, 245)
X_LINE = (200, 40, 40)  # 3×3 vẽ chữ X/O
O_LINE = (30, 90, 200)
LAST = (230, 30, 30)
WIN = (40, 170, 60)
HEAT = (255, 120, 0)
CHOSEN = (160, 0, 200)
TEXT_DARK = (20, 20, 20)
LAST_FILL = (247, 236, 91, 120)  # tô nước cuối (nền vàng mờ)
LABEL = (200, 196, 188)
LABEL_MARGIN = 24  # px dành cho nhãn cột (dưới) và hàng (trái)
GHOST_ALPHA = 110

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


class KInRowView(GameView):
    """Bàn n×n vẽ dạng ô; quân đặt trong ô."""

    def __init__(self, n: int, k: int, rect: pygame.Rect) -> None:
        super().__init__(rect)
        self.n, self.k = n, k
        avail_w, avail_h = self.rect.w - LABEL_MARGIN, self.rect.h - LABEL_MARGIN
        self.cell = min(avail_w, avail_h) // n
        side = self.cell * n
        self.origin = (
            self.rect.x + LABEL_MARGIN + (avail_w - side) // 2,
            self.rect.y + (avail_h - side) // 2,
        )

    # ------------------------------------------------------------ hình học
    def cell_rect(self, move: int) -> pygame.Rect:
        r, c = divmod(move, self.n)
        return pygame.Rect(self.origin[0] + c * self.cell, self.origin[1] + r * self.cell,
                           self.cell, self.cell)  # fmt: skip

    def hit_test(self, pos: tuple[int, int], game: Game) -> Move | None:
        x, y = pos[0] - self.origin[0], pos[1] - self.origin[1]
        side = self.cell * self.n
        if not (0 <= x < side and 0 <= y < side) or game.is_terminal():
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

    # ------------------------------------------------------------ vẽ
    def draw(self, surf: pygame.Surface, game: Game, last: MoveInfo | None,
             overlay_info: MoveInfo | None, opts: OverlayOpts) -> None:  # fmt: skip
        assert isinstance(game, KInRow)
        side = self.cell * self.n
        board_rect = pygame.Rect(*self.origin, side, side)
        pygame.draw.rect(surf, BOARD_BG, board_rect)
        stats = overlay_info.root_stats if (opts.show and overlay_info is not None) else []
        if stats:
            self._draw_heat(surf, stats)
        if last is not None:
            layer = pygame.Surface(self.cell_rect(last.move).size, pygame.SRCALPHA)
            layer.fill(LAST_FILL)
            surf.blit(layer, self.cell_rect(last.move))
        self._draw_labels(surf)
        for i in range(self.n + 1):
            off = i * self.cell
            pygame.draw.line(surf, GRID, (self.origin[0] + off, self.origin[1]),
                             (self.origin[0] + off, self.origin[1] + side))  # fmt: skip
            pygame.draw.line(surf, GRID, (self.origin[0], self.origin[1] + off),
                             (self.origin[0] + side, self.origin[1] + off))  # fmt: skip
        for m, v in enumerate(game.board):
            if v:
                self._draw_piece(surf, m, v)
        if last is not None:
            pygame.draw.rect(surf, LAST, self.cell_rect(last.move), width=2)
        for m in self.winning_cells(game, last):
            pygame.draw.rect(surf, WIN, self.cell_rect(m).inflate(-4, -4), width=4)
        if stats:
            self._draw_numbers(surf, stats, overlay_info.move, opts.show_wn)
        for m in self.highlights(game):
            pygame.draw.rect(surf, WIN, self.cell_rect(m), width=2)

    def _draw_labels(self, surf: pygame.Surface) -> None:
        font = get_font(15 if self.n > 5 else 20, bold=True)
        side = self.cell * self.n
        for i in range(self.n):
            mid = i * self.cell + self.cell // 2
            img = font.render(self.col_label(i), True, LABEL)
            below = self.origin[1] + side + LABEL_MARGIN // 2
            surf.blit(img, img.get_rect(center=(self.origin[0] + mid, below)))
            img = font.render(str(i + 1), True, LABEL)
            surf.blit(img, img.get_rect(center=(self.origin[0] - LABEL_MARGIN // 2,
                                                self.origin[1] + mid)))  # fmt: skip

    def draw_ghost(self, surf: pygame.Surface, move: Move, player: int) -> None:
        rc = self.cell_rect(int(move))
        layer = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        self._draw_piece(layer, int(move), 1 if player == 1 else 2)
        layer.set_alpha(GHOST_ALPHA)
        surf.blit(layer, rc, area=rc)

    def _draw_piece(self, surf: pygame.Surface, m: int, v: int) -> None:
        rc = self.cell_rect(m)
        if self.n <= 5:  # bàn nhỏ: chữ X / O
            pad = self.cell // 5
            box = rc.inflate(-2 * pad, -2 * pad)
            w = max(4, self.cell // 14)
            if v == 1:
                pygame.draw.line(surf, X_LINE, box.topleft, box.bottomright, w)
                pygame.draw.line(surf, X_LINE, box.topright, box.bottomleft, w)
            else:
                pygame.draw.circle(surf, O_LINE, box.center, box.w // 2, w)
            return
        radius = self.cell // 2 - 3
        pygame.draw.circle(surf, X_COLOR if v == 1 else O_COLOR, rc.center, radius)
        pygame.draw.circle(surf, TEXT_DARK, rc.center, radius, 1)

    def _draw_heat(self, surf: pygame.Surface, stats: list) -> None:
        max_n = max(n for _, _, n, _ in stats) or 1
        layer = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        for move, _w, n, _wn in stats:
            alpha = int(30 + 190 * n / max_n)
            layer.fill((*HEAT, alpha), self.cell_rect(int(move)))
        surf.blit(layer, (0, 0))

    def _draw_numbers(self, surf: pygame.Surface, stats: list, chosen: Move, show_wn: bool) -> None:
        size = max(11, self.cell // (4 if show_wn else 3))
        font = get_font(size, bold=True)
        for move, _w, n, wn in stats:
            rc = self.cell_rect(int(move))
            on_stone = int(move) == int(chosen)
            color = (255, 255, 255) if on_stone and self.n > 5 else TEXT_DARK
            lines = [str(n)] + ([f"{wn:.2f}"] if show_wn else [])
            total = len(lines) * font.get_linesize()
            y = rc.centery - total // 2
            for line in lines:
                img = font.render(line, True, color)
                surf.blit(img, img.get_rect(midtop=(rc.centerx, y)))
                y += font.get_linesize()
            if on_stone:
                pygame.draw.rect(surf, CHOSEN, rc.inflate(-2, -2), width=2)


register_view("kinrow", lambda spec, rect: KInRowView(spec.params.get("n", 15),
                                                       spec.params.get("k", 5), rect))  # fmt: skip


def view_for(spec: GameSpec, rect: pygame.Rect) -> KInRowView:
    """Tiện ích cho test."""
    return KInRowView(spec.params.get("n", 15), spec.params.get("k", 5), rect)
