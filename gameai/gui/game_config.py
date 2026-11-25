"""Cấu hình ván do người chọn ở màn Setup → `Preset` (không import pygame)."""

from __future__ import annotations

import random
from dataclasses import dataclass

from gameai.agents.registry import GameSpec
from gameai.arena import derive_seed
from gameai.gui.presets import (
    GAME3,
    GAME15,
    LEVEL_NAMES,
    XIANGQI,
    BoardKey,
    Level,
    Preset,
    board_key,
    level_for,
)

GAMES: dict[str, tuple[GameSpec, str]] = {
    "3x3": (GAME3, "Caro 3×3"),
    "15x15": (GAME15, "Caro 15×15 · 5 quân thắng"),
    "xiangqi": (XIANGQI, "Cờ tướng"),  # P6.2
}
# Tên bên đi trước / đi sau theo trò (Setup, lời văn). Lựa chọn bên trong GameConfig vẫn là "X"/"O".
SIDE_NAMES: dict[str, tuple[str, str]] = {
    "3x3": ("X", "O"),
    "15x15": ("Đen", "Trắng"),
    "xiangqi": ("Đỏ", "Đen"),
}
MODES = {"human_ai": "Người vs AI", "ai_ai": "AI vs AI", "two_players": "2 người cùng máy"}
SIDES = {"X": "X (đi trước)", "O": "O (đi sau)", "random": "Ngẫu nhiên"}
AI_NAMES = {"mcts": "MCTS", "alphabeta": "Alpha-Beta"}
DEFAULT_AI_DELAY = 0.5  # giây giữa các nước ở AI vs AI


@dataclass(frozen=True)
class AIChoice:
    """Loại AI + mức độ khó của một bên."""

    kind: str = "mcts"
    level: str = "medium"

    def label(self) -> str:
        return f"{AI_NAMES[self.kind]} · {LEVEL_NAMES[self.level]}"


@dataclass(frozen=True)
class GameConfig:
    """Lựa chọn ở Setup. `ai` = AI của người vs AI / bên X ở AI vs AI; `ai_o` = bên O."""

    game: str = "15x15"
    mode: str = "human_ai"
    side: str = "X"  # bên của người (chỉ người vs AI)
    ai: AIChoice = AIChoice()
    ai_o: AIChoice = AIChoice("alphabeta", "medium")
    seed: int = 0
    delay: float = DEFAULT_AI_DELAY  # chỉ AI vs AI

    @property
    def board(self) -> BoardKey:
        """Khóa trò trong bảng độ khó: 3 / 15 / "xiangqi"."""
        return board_key(GAMES[self.game][0])

    def side_name(self, side: str) -> str:
        """'X'/'O' → tên bên của trò: X/O (3×3), Đen/Trắng (15×15), Đỏ/Đen (cờ tướng)."""
        first, second = SIDE_NAMES[self.game]
        return first if side == "X" else second

    def human_side(self) -> str | None:
        """'X' / 'O' cho người vs AI (ngẫu nhiên → tất định theo seed); None ở chế độ khác."""
        if self.mode != "human_ai":
            return None
        if self.side == "random":
            return random.Random(derive_seed(self.seed, "side")).choice(["X", "O"])
        return self.side

    def level(self, choice: AIChoice) -> Level:
        return level_for(self.board, choice.kind, choice.level)


def build_preset(cfg: GameConfig) -> Preset:
    """GameConfig → Preset (spec theo bảng độ khó D-29)."""
    spec, game_name = GAMES[cfg.game]
    if cfg.mode == "two_players":
        return Preset(f"cfg_{cfg.game}_2p", f"{game_name} · 2 người", spec, None, None)
    if cfg.mode == "ai_ai":
        x, o = cfg.level(cfg.ai).spec, cfg.level(cfg.ai_o).spec
        title = f"{game_name} · {cfg.ai.label()} vs {cfg.ai_o.label()}"
        return Preset(f"cfg_{cfg.game}_aiai", title, spec, x, o, max(0.0, cfg.delay))
    if cfg.mode != "human_ai":
        raise ValueError(f"chế độ không hợp lệ: {cfg.mode!r}")
    ai = cfg.level(cfg.ai).spec
    human = cfg.human_side()
    x, o = (None, ai) if human == "X" else (ai, None)
    title = f"{game_name} · Người ({human}) vs {cfg.ai.label()}"
    return Preset(f"cfg_{cfg.game}_human_{human}", title, spec, x, o)
