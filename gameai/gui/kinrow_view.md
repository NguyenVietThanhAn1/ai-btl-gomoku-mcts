# View k-in-row — `gameai/gui/kinrow_view.py`

> Mục tiêu của file này: agent/thành viên khác dùng được module **mà không cần đọc code**.
> Cập nhật cùng lúc với code.

**Trạng thái:** ✅ ổn định  ·  **Task:** P6.1 (D-28), P6.3 (D-29)  ·  **Cập nhật:** 2026-11-17

## Mục đích
`GameView` cho `KInRow` (3×3 và 15×15): bàn gỗ + khung + bóng (lớp tĩnh cache), quân sprite khử răng cưa,
nước cuối, đường thắng vạch nối tâm, overlay top-8 gốc MCTS (P6.3 phiên 3a).

## Public API
```python
class KInRowView(GameView):
    def __init__(self, n: int, k: int, rect: pygame.Rect)
    n, k, cell: int; origin: tuple[int, int]          # ô vuông `cell` px, bàn căn giữa trong rect
    def cell_rect(self, move: int) -> pygame.Rect
    def hit_test(self, pos, game) -> int | None       # r*n+c nếu ô trống, trong bàn, ván chưa hết
    def col_label(self, c) -> str                     # a–c khi n ≤ 5, A–O khi bàn lớn
    def move_label(self, move) -> str                 # cột + hàng 1.. từ trên xuống: 112 → "H8" (15×15), 4 → "b2" (3×3)
    def preview(self, pos, game) -> int | None        # = hit_test (k-in-row không có trạng thái input)
    def draw_ghost(self, surf, move, player) -> None  # quân mờ (alpha 110)
    def winning_cells(self, game, last) -> list[int]  # winning_line quanh nước cuối nếu có người thắng
    def draw(self, surf, game, last, overlay_info, opts) -> None
    def static_layer(theme=None) -> Surface          # bóng + khung + gỗ + lưới + nhãn; dựng lại khi đổi theme
    def piece_sprite(v, theme=None) -> Surface       # sprite chuẩn (cache) của quân 1 = X / 2 = O
    def draw_piece(surf, m, v, scale=1.0, alpha=255) # scale/alpha cho animation (không thêm cache)
    def draw_last_marker(surf, move, theme=None)     # một màu last_move: vòng quanh quân 15×15, khung bo 3×3
    win_progress: float                             # 0→1, đường thắng vẽ dần (scene điều khiển)
    anim_move: (ô, scale, alpha) | None             # quân đang đặt (scene điều khiển)
    hover_move: int | None                          # ô đang hover (quân mờ): ẩn nhãn overlay ô đó, hiện lại khi rời
    stones: bool; side_name(p) -> "Đen"/"Trắng" (15×15) | "X"/"O" (3×3); side_symbol(p) -> "●"/"○" | "X"/"O"
def winning_line(board, n, k, move) -> list[int]      # ô thẳng hàng ≥ k qua move (chỉ đọc board)
def top_k(stats, k=8) -> [(hạng, move, N, W/N)]      # overlay: K nước N lớn nhất, màu đậm theo hạng
```
- Đăng ký `VIEWS["kinrow"]` khi import.
- Overlay (3b): ô trống tô màu theo hạng (15×15 alpha 215 → 75; 3×3 nhạt hơn 120 → 36 để vân gỗ + chữ đọc rõ) + "#hạng",
  N, (W/N); ô đã có quân (thường #1 = nước AI vừa đi) không tô, chỉ gắn badge "#k" ở góc trên-phải, vẽ sau vòng nước cuối.
- Vẽ: 3×3 (n ≤ 5) chữ X đỏ / O xanh; 15×15 quân đen (X) / trắng (O). Nhãn tọa độ: cột dưới bàn, hàng bên trái (lề 24 px,
  khớp `move_label` trong lịch sử). Nước cuối: nền vàng mờ + khung đỏ. Đường thắng: khung xanh lá.
- Overlay (khi `opts.show` và `overlay_info.root_stats` khác rỗng): mỗi nước ở gốc tô cam với độ đậm ∝ N/maxN,
  ghi N (và W/N 2 chữ số nếu `opts.show_wn`); nước được chọn có viền tím. App truyền `overlay_info` = nước cuối
  nếu là nước AI → overlay là cây của **nước vừa đi**, mất khi bên kia đi tiếp.

## Phụ thuộc
- Dùng: `gui/view.py`, `games/kinrow.py` (đọc `board`), `gui/controller.py` (`MoveInfo`).
- Được dùng bởi: `gui/pygame_app.py` qua `make_view`.

## Thiết kế & quyết định
- Không gọi hàm nội bộ của `KInRow`; đường thắng tính lại từ `board` quanh nước cuối (O(k)).
- Kích thước ô = (cạnh rect − 24) // n (`BOARD_RECT` 688 px → 221 px cho 3×3, 44 px cho 15×15).

## Test
- `tests/test_gui_controller.py`: `hit_test` góc / giữa / mép / ngoài bàn / ô đã có quân (3×3, 15×15),
  `move_label`, `winning_line`, vẽ có overlay + W/N trên Surface headless.
- `tests/test_gui_scenes.py::test_preview_ghost_and_labels`: preview chỉ ô trống, quân mờ, nhãn a/A, origin chừa lề.

## Hạn chế / TODO
- Hàng đánh số từ trên xuống (khớp ký hiệu đã dùng từ P6.1).
