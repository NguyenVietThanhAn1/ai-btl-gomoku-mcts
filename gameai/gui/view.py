"""Lớp view chung cho mọi game trong GUI + font tiếng Việt."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import pygame

from gameai.agents.registry import GameSpec
from gameai.core.game import Game, Move
from gameai.gui.controller import MoveInfo

FONT_NAMES = ("segoeui", "arial")  # fallback hệ thống (có dấu tiếng Việt trên Windows)
FONT_DIR = Path(__file__).resolve().parent / "assets" / "fonts"
FONT_FILES = {"regular": "Regular", "medium": "Medium", "semibold": "SemiBold", "bold": "Bold"}
BOLD_WEIGHTS = ("semibold", "bold")


def font_path(weight: str = "regular") -> Path | None:
    """File Be Vietnam Pro đóng gói cho `weight` (None nếu thiếu)."""
    path = FONT_DIR / f"BeVietnamPro-{FONT_FILES[weight]}.ttf"
    return path if path.exists() else None


def get_font(size: int, bold: bool = False, weight: str | None = None) -> pygame.font.Font:
    """Font tiếng Việt: Be Vietnam Pro đóng gói (D-29) → Segoe UI → Arial → font mặc định.

    `weight` ∈ regular / medium / semibold / bold; không truyền → `bold` (tương thích P6.1).
    Có cache; cache bị xóa khi `pygame.quit()` (font cũ không dùng được nữa → access violation).
    """
    global _quit_hook
    if not pygame.font.get_init():
        pygame.font.init()
    if not _quit_hook:  # pygame bỏ danh sách register_quit sau mỗi lần quit → đăng ký lại
        pygame.register_quit(_on_quit)
        _quit_hook = True
    return _load_font(size, weight or ("bold" if bold else "regular"))


_quit_hook = False


def _on_quit() -> None:
    global _quit_hook
    _load_font.cache_clear()
    _quit_hook = False


@lru_cache(maxsize=64)
def _load_font(size: int, weight: str) -> pygame.font.Font:
    path = font_path(weight)
    if path is not None:
        return pygame.font.Font(str(path), size)
    bold = weight in BOLD_WEIGHTS
    for name in FONT_NAMES:
        sys_path = pygame.font.match_font(name, bold=bold)
        if sys_path:
            return pygame.font.Font(sys_path, size)
    font = pygame.font.Font(None, size)
    font.set_bold(bold)
    return font


@dataclass
class OverlayOpts:
    """Tùy chọn overlay thống kê gốc MCTS."""

    show: bool = True
    show_wn: bool = False


class GameView(ABC):
    """Vẽ bàn và chuyển click thành nước đi.

    Input là máy trạng thái nằm trong view: `hit_test` nhận một click, trả **nước hoàn chỉnh**
    hoặc None (click chưa đủ / không hợp lệ). Game cần nhiều click (cờ tướng: chọn quân → ô
    đích) giữ trạng thái chọn dở trong view, báo ô cần tô qua `highlights`; controller không đổi.
    """

    def __init__(self, rect: pygame.Rect) -> None:
        self.rect = pygame.Rect(rect)

    @abstractmethod
    def draw(self, surf: pygame.Surface, game: Game, last: MoveInfo | None,
             overlay_info: MoveInfo | None, opts: OverlayOpts) -> None:  # fmt: skip
        """Vẽ bàn, quân, nước cuối `last`, overlay root stats của `overlay_info` (nếu bật)."""

    @abstractmethod
    def hit_test(self, pos: tuple[int, int], game: Game) -> Move | None:
        """Một click ở `pos` → nước hợp lệ hoàn chỉnh, hoặc None."""

    def reset_input(self) -> None:  # noqa: B027 — mặc định không có trạng thái
        """Xóa trạng thái chọn dở (gọi khi ván mới / tới lượt AI)."""

    def highlights(self, game: Game) -> list[Move]:
        """Các nước cần tô sáng do trạng thái input hiện tại (mặc định: không có)."""
        return []

    @abstractmethod
    def move_label(self, move: Move) -> str:
        """Tên nước đi để hiện trên panel."""

    # ---- P6.3: hook có mặc định (view cờ tướng không bắt buộc cài)
    def preview(self, pos: tuple[int, int], game: Game) -> Move | None:
        """Nước sẽ đi nếu click ở `pos` (để vẽ quân mờ khi hover). Không đổi trạng thái input."""
        return None

    def draw_ghost(self, surf: pygame.Surface, move: Move, player: int) -> None:  # noqa: B027
        """Vẽ quân mờ của `player` tại `move` (mặc định: không vẽ)."""

    def winning_cells(self, game: Game, last: MoveInfo | None) -> list[Move]:
        """Các ô của đường thắng (tính từ bàn + nước cuối); [] nếu không có."""
        return []


ViewFactory = Callable[[GameSpec, pygame.Rect], GameView]
VIEWS: dict[str, ViewFactory] = {}


def register_view(kind: str, factory: ViewFactory) -> None:
    VIEWS[kind] = factory


def make_view(spec: GameSpec, rect: pygame.Rect) -> GameView:
    """View cho `spec.kind` (KeyError nếu chưa đăng ký)."""
    import gameai.gui.kinrow_view  # noqa: F401 — đăng ký view k-in-row

    return VIEWS[spec.kind](spec, rect)
