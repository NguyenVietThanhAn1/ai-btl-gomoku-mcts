# Presets GUI — `gameai/gui/presets.py`

> Mục tiêu của file này: agent/thành viên khác dùng được module **mà không cần đọc code**.
> Cập nhật cùng lúc với code.

**Trạng thái:** ✅ ổn định  ·  **Task:** P6.1 (D-28)  ·  **Cập nhật:** 2026-11-17

## Mục đích
Các chế độ chơi của GUI, mô tả bằng `GameSpec` + `AgentSpec` của registry — **cùng spec với thí nghiệm**
(không tự dựng tham số riêng), để AI trong video đúng là AI trong báo cáo.

## Public API
```python
HUMAN = None
@dataclass(frozen=True)
class Preset:
    key: str; title: str; game: GameSpec
    x: AgentSpec | None             # đi trước (P1); None = người
    o: AgentSpec | None             # đi sau (P2)
    delay: float = 0.0              # giây chờ tối thiểu trước mỗi nước AI
    has_human: bool                 # property
MCTS_3X3 = e2_never_lose.mcts_spec(1000)          # 1000 iter, c = √2, tactics tắt (D-16)
MCTS_H300 = e3_c_sweep.mcts_spec(15, 1.4, 5000)   # h300 + tactics (D-14), 5000 iter
PRESETS: dict[str, Preset]; PRESET_ORDER: list[str]   # phím 1/2/3 theo thứ tự này
def swap_sides(p) -> Preset                 # đổi X ↔ O
def with_iterations(p, n) -> Preset         # đổi iterations mọi bên MCTS (ValueError nếu n < 1)
def mcts_iterations(p) -> int | None        # iteration của bên MCTS đầu tiên
def side_label(spec) -> str                 # nhãn hiển thị ("Người", "MCTS h300 5000 iter, c=1.4, tactics", ...)
```

| key | Bàn | X | O | delay |
|---|---|---|---|---|
| `3x3_human_mcts` | 3×3 k3 | người | MCTS random 1000 (spec E2) | 0 |
| `15_human_h300` | 15×15 k5 | người | MCTS h300 5000 + tactics (spec E3) | 0 |
| `15_h300_vs_ab2` | 15×15 k5 | MCTS h300 5000 + tactics | `e3_c_sweep.AB2` (depth 2) | 0,5 s |

## Phụ thuộc
- Dùng: `agents/registry.py`, `experiments/e2_never_lose.py` (`mcts_spec`), `experiments/e3_c_sweep.py`
  (`mcts_spec`, `AB2`, `GAME3`, `GAME15`).
- Được dùng bởi: `gui/controller.py`, `gui/pygame_app.py`.

## Thiết kế & quyết định (D-28)
- 15×15 dùng 5000 iter: E3 (c = 1,4) h300 vs Greedy thắng 0,92 ở 5000 iter, chỉ 0,48 ở 1000 iter
  (`results/tables/e3_greedy.csv`). Chi phí ~2,1 s/nước (đo một lần trên máy dev, thế 5 quân, ngoài GUI).
- Lưu ý cho video: h300 5000 vs AB2 chỉ thắng 0,22 (`results/tables/e3_ab2.csv`) → ở preset 3 AB thường
  thắng; đúng với số liệu, không phải lỗi.
- Đổi tham số chỉ tạo spec mới (`dataclasses.replace`), preset gốc không đổi.

## Test
- `tests/test_gui_controller.py`: spec preset == spec thí nghiệm, dựng được agent; `with_iterations`, `swap_sides`.

## Hạn chế / TODO
- Cờ tướng (P6.2) thêm preset với `GameSpec` kind mới.
