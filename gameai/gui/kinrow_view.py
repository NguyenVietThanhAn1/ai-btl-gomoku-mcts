"""View k-in-row cho GUI: 1 click = 1 nước; overlay N, W/N của gốc MCTS."""

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
        self.cell = min(self.rect.w, self.rect.h) // n
        side = self.cell * n
        self.origin = (
            self.rect.x + (self.rect.w - side) // 2,
            self.rect.y + (self.rect.h - side) // 2,
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

    def move_label(self, move: Move) -> str:
        r, c = divmod(int(move), self.n)
        return f"{chr(ord('A') + c)}{r + 1}"

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
            pygame.draw.rect(surf, LAST, self.cell_rect(last.move), width=3)
            for m in winning_line(game.board, self.n, self.k, int(last.move)):
                pygame.draw.rect(surf, WIN, self.cell_rect(m).inflate(-4, -4), width=4)
        if stats:
            self._draw_numbers(surf, stats, overlay_info.move, opts.show_wn)
        for m in self.highlights(game):
            pygame.draw.rect(surf, WIN, self.cell_rect(m), width=2)

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
