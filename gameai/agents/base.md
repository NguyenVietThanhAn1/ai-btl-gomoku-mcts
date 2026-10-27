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
    @abstractmethod
    def select_move(self, game: Game) -> Move
```
- `select_move`: trả nước hợp lệ cho `game.current_player()`; **không để lại thay đổi trên `game`**
  (dùng `undo`/`clone`). Precondition: ván chưa kết thúc.
- Quy ước khóa `stats` (agent nào không có thì bỏ qua hoặc ghi 0): `nodes`, `iterations`, `time` (giây).
  `stats` được làm mới ở mỗi lượt (gọi `reset_stats()` đầu `select_move`), không cộng dồn giữa các lượt.

## Phụ thuộc
- Dùng: `core/game.py` (`Game`, `Move`).
- Được dùng bởi: mọi agent trong `agents/`, `arena.py`, `experiments/`.

## Thiết kế & quyết định
- ABC thay vì Protocol để có `stats`/`name` dùng chung. Agent con phải gọi `super().__init__()`.
- Tính ngẫu nhiên: agent nhận `seed` và giữ `random.Random` riêng, không dùng `random` toàn cục.

## Test
- `tests/test_random_agent.py` (kiểm `Agent` là abstract, `stats`/`name`).
- Chạy: `python -m pytest tests/test_random_agent.py -q`

## Hạn chế / TODO
- Chưa có giới hạn thời gian/budget chung; từng agent tự có tham số (depth, iterations).
