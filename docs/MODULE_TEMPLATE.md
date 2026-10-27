# <tên module> — `gameai/<đường dẫn>/<module>.py`

> Mục tiêu của file này: agent/thành viên khác dùng được module **mà không cần đọc code**.
> Cập nhật cùng lúc với code. Giữ ngắn: ~40–120 dòng.

**Trạng thái:** ⬜ stub / 🔄 đang làm / ✅ ổn định  ·  **Task:** P?.?  ·  **Cập nhật:** YYYY-MM-DD

## Mục đích
1–3 câu: module này giải quyết việc gì, thuộc yêu cầu nào của đề.

## Public API
```python
class Foo:
    def __init__(self, a: int, seed: int | None = None): ...
    def bar(self, game: Game) -> Move: ...   # ý nghĩa, đơn vị, giá trị trả về
```
- Tham số quan trọng + giá trị mặc định + ý nghĩa.
- `stats` mà module ghi ra (nếu là agent).

## Phụ thuộc
- Dùng: `core/game.py` (Game), ...
- Được dùng bởi: `experiments/e3_c_sweep.py`, ...

## Thiết kế & quyết định
- Cấu trúc dữ liệu chính, vì sao chọn.
- Invariants (điều luôn đúng), vd. "W tính theo góc nhìn người vừa đi vào node".
- Độ phức tạp / điểm nóng hiệu năng.

## Giải thích để vấn đáp (bắt buộc với module thuật toán)
- Bản chất thuật toán bằng lời.
- Ví dụ nhỏ trace tay (3×3 hoặc cây vài nút).
- 3–5 câu hỏi hay bị hỏi + trả lời ngắn.

## Test
- File: `tests/test_<module>.py` — liệt kê các hành vi được test.
- Cách chạy riêng: `python -m pytest tests/test_<module>.py -q`

## Hạn chế / TODO
- Việc chưa làm, bug đã biết, ý tưởng tối ưu.
