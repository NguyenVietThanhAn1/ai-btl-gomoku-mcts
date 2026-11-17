# View k-in-row — `gameai/gui/kinrow_view.py`

> Mục tiêu của file này: agent/thành viên khác dùng được module **mà không cần đọc code**.
> Cập nhật cùng lúc với code.

**Trạng thái:** ✅ ổn định  ·  **Task:** P6.1 (D-28)  ·  **Cập nhật:** 2026-11-17

## Mục đích
`GameView` cho `KInRow` (3×3 và 15×15): vẽ bàn dạng ô, nước cuối, đường thắng, overlay thống kê gốc MCTS.

## Public API
```python
class KInRowView(GameView):
    def __init__(self, n: int, k: int, rect: pygame.Rect)
    n, k, cell: int; origin: tuple[int, int]          # ô vuông `cell` px, bàn căn giữa trong rect
    def cell_rect(self, move: int) -> pygame.Rect
    def hit_test(self, pos, game) -> int | None       # r*n+c nếu ô trống, trong bàn, ván chưa hết
    def move_label(self, move) -> str                 # cột A.. + hàng 1.. từ trên xuống, vd. 112 → "H8"
    def draw(self, surf, game, last, overlay_info, opts) -> None
def winning_line(board, n, k, move) -> list[int]      # ô thẳng hàng ≥ k qua move (chỉ đọc board)
```
- Đăng ký `VIEWS["kinrow"]` khi import.
- Vẽ: 3×3 (n ≤ 5) chữ X đỏ / O xanh; 15×15 quân đen (X) / trắng (O). Nước cuối: khung đỏ. Đường thắng: khung xanh lá.
- Overlay (khi `opts.show` và `overlay_info.root_stats` khác rỗng): mỗi nước ở gốc tô cam với độ đậm ∝ N/maxN,
  ghi N (và W/N 2 chữ số nếu `opts.show_wn`); nước được chọn có viền tím. App truyền `overlay_info` = nước cuối
  nếu là nước AI → overlay là cây của **nước vừa đi**, mất khi bên kia đi tiếp.

## Phụ thuộc
- Dùng: `gui/view.py`, `games/kinrow.py` (đọc `board`), `gui/controller.py` (`MoveInfo`).
- Được dùng bởi: `gui/pygame_app.py` qua `make_view`.

## Thiết kế & quyết định
- Không gọi hàm nội bộ của `KInRow`; đường thắng tính lại từ `board` quanh nước cuối (O(k)).
- Kích thước ô = cạnh rect // n (680 px → 226 px cho 3×3, 45 px cho 15×15).

## Test
- `tests/test_gui_controller.py`: `hit_test` góc / giữa / mép / ngoài bàn / ô đã có quân (3×3, 15×15),
  `move_label`, `winning_line`, vẽ có overlay + W/N trên Surface headless.

## Hạn chế / TODO
- Không vẽ tọa độ cạnh bàn.
