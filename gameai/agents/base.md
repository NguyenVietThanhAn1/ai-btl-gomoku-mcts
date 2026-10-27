# Agent base — `gameai/agents/base.py`

> Mục tiêu của file này: agent/thành viên khác dùng được module **mà không cần đọc code**.

**Trạng thái:** ✅ ổn định  ·  **Task:** P2.1  ·  **Cập nhật:** 2026-10-28

## Mục đích
Lớp trừu tượng `Agent`: hợp đồng chung để arena/thí nghiệm gọi mọi agent giống nhau và đọc thống kê.

## Public API
```python
class Agent(ABC):
    stats: dict[str, float]            # thống kê của lần select_move gần nhất
    name: str                          # property, mặc định = tên lớp
    def reset_stats(self) -> None      # gán stats = {}
    def select_move(self, game: Game) -> Move   # KHÔNG override: reset_stats() rồi _select_move()
    @abstractmethod
    def _select_move(self, game: Game) -> Move  # agent con override hàm này
```
- `select_move` (template method, D-7): gọi `reset_stats()` rồi `_select_move(game)`.
- `_select_move`: trả nước hợp lệ cho `game.current_player()`; **không để lại thay đổi trên `game`**
  (dùng `undo`/`clone`). Precondition: ván chưa kết thúc.
- Quy ước khóa `stats` (agent nào không có thì bỏ qua hoặc ghi 0): `nodes`, `iterations`, `time` (giây).
  `stats` được `select_move` làm mới ở mỗi lượt, không cộng dồn giữa các lượt; agent con không cần gọi `reset_stats()`.

## Phụ thuộc
- Dùng: `core/game.py` (`Game`, `Move`).
- Được dùng bởi: mọi agent trong `agents/`, `arena.py`, `experiments/`.

## Thiết kế & quyết định
- ABC thay vì Protocol để có `stats`/`name` dùng chung. Agent con phải gọi `super().__init__()`.
- Template method (D-7): reset `stats` ép ở một chỗ, agent con không thể quên.
- Tính ngẫu nhiên: agent nhận `seed` và giữ `random.Random` riêng, không dùng `random` toàn cục.

## Test
- `tests/test_random_agent.py` (`Agent` là abstract, `stats`/`name`, `stats` không cộng dồn giữa 2 lần `select_move`).
- Chạy: `python -m pytest tests/test_random_agent.py -q`

## Hạn chế / TODO
- Chưa có giới hạn thời gian/budget chung; từng agent tự có tham số (depth, iterations).
