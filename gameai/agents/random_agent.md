# RandomAgent — `gameai/agents/random_agent.py`

> Mục tiêu của file này: agent/thành viên khác dùng được module **mà không cần đọc code**.

**Trạng thái:** ✅ ổn định  ·  **Task:** P2.1  ·  **Cập nhật:** 2026-10-28

## Mục đích
Đối thủ cơ sở: chọn đều ngẫu nhiên một nước. Dùng làm mốc so sánh và smoke test cho arena.

## Public API
```python
class RandomAgent(Agent):
    def __init__(self, seed: int | None = None, use_candidates: bool = False): ...
    def select_move(self, game: Game) -> Move
```
- `seed`: khởi tạo `random.Random` riêng → cùng seed cho cùng chuỗi nước trên cùng trạng thái.
- `use_candidates=False`: chọn trong `legal_moves()`; `True`: chọn trong `candidate_moves()`
  (mạnh hơn trên 15×15 vì không rải quân khắp bàn).
- `stats`: `{"nodes": 0, "iterations": 0}`.

## Phụ thuộc
- Dùng: `agents/base.py`, `core/game.py`.
- Được dùng bởi: `arena.py`, `experiments/`, test các agent khác (đối thủ yếu).

## Thiết kế & quyết định
- Mặc định `legal_moves()` để Random đúng nghĩa "ngẫu nhiên hoàn toàn".
- Không đụng `random` toàn cục (có test).

## Test
- `tests/test_random_agent.py`: nước hợp lệ, `game` không đổi, cùng seed cùng kết quả,
  không phụ thuộc `random` toàn cục, `use_candidates`, chơi hết ván 3×3 và 15×15, lỗi trên ván xong.
- Chạy: `python -m pytest tests/test_random_agent.py -q`

## Hạn chế / TODO
- Không.
