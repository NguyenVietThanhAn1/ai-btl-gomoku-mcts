# Cấu hình ván — `gameai/gui/game_config.py`

> Mục tiêu của file này: agent/thành viên khác dùng được module **mà không cần đọc code**.
> Cập nhật cùng lúc với code.

**Trạng thái:** ✅ ổn định  ·  **Task:** P6.3 (D-29)  ·  **Cập nhật:** 2026-11-17

## Mục đích
Biến lựa chọn của người ở màn Setup (trò, chế độ, bên, loại AI, độ khó, seed, độ trễ) thành `Preset` cho
`GameController`. Không import pygame → test headless. Spec AI lấy từ bảng độ khó `presets.DIFFICULTY` (D-29).

## Public API
```python
GAMES = {"3x3": (GAME3, "Caro 3×3"), "15x15": (GAME15, "Caro 15×15 · 5 quân thắng"), "xiangqi": (None, "Cờ tướng")}  # None = chưa chơi được (P6.2)
MODES = {"human_ai": "Người vs AI", "ai_ai": "AI vs AI", "two_players": "2 người cùng máy"}
SIDES = {"X": ..., "O": ..., "random": "Ngẫu nhiên"};  AI_NAMES = {"mcts": "MCTS", "alphabeta": "Alpha-Beta"}
DEFAULT_AI_DELAY = 0.5

@dataclass(frozen=True) class AIChoice:  kind = "mcts"; level = "medium";  def label() -> str   # "MCTS · Vừa"
@dataclass(frozen=True) class GameConfig:
    game = "15x15"; mode = "human_ai"; side = "X"
    ai: AIChoice            # AI của người vs AI, hoặc bên X ở AI vs AI
    ai_o: AIChoice          # bên O ở AI vs AI
    seed = 0; delay = 0.5   # delay chỉ dùng ở AI vs AI
    board: int              # property: 3 / 15; ValueError với cờ tướng
    def human_side() -> "X" | "O" | None     # random → tất định theo seed; None nếu không phải người vs AI
    def level(choice) -> Level               # presets.level_for(board, kind, level)
def build_preset(cfg) -> Preset              # ValueError: trò chưa chơi được / chế độ sai
```

| mode | `Preset.x` | `Preset.o` | delay |
|---|---|---|---|
| `human_ai`, người X | None | spec của `ai` | 0 |
| `human_ai`, người O | spec của `ai` | None | 0 |
| `ai_ai` | spec của `ai` | spec của `ai_o` | `cfg.delay` (≥ 0) |
| `two_players` | None | None | 0 |

## Phụ thuộc
- Dùng: `gui/presets.py` (`Preset`, `DIFFICULTY`, `level_for`, `GAME3`, `GAME15`), `arena.py` (`derive_seed`).
- Được dùng bởi: màn Setup (P6.3, phiên 2).

## Thiết kế & quyết định
- Bên "Ngẫu nhiên" = `random.Random(derive_seed(seed, "side"))` → cùng seed cùng bên, quay lại được ván.
- Seed agent vẫn do controller suy (`derive_seed(seed, "X"/"O")`), như D-28.

## Test
- `tests/test_gui_config.py`: mọi (bàn × AI × mức × bên) → đúng spec; bên ngẫu nhiên tất định và có cả X lẫn O; 2 người;
  AI vs AI (hai spec + delay); cờ tướng → ValueError.
- Chạy: `python -m pytest tests/test_gui_config.py -q`

## Hạn chế / TODO
- Cờ tướng: thêm `GameSpec` + bảng độ khó ở P6.2.
