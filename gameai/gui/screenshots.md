# Ảnh headless — `gameai/gui/screenshots.py`

> Mục tiêu của file này: agent/thành viên khác dùng được module **mà không cần đọc code**.
> Cập nhật cùng lúc với code.

**Trạng thái:** ✅ ổn định  ·  **Task:** P6.3 phiên 3 (D-29), P6.2 (D-37)  ·  **Cập nhật:** 2026-11-25

## Mục đích
Sinh ảnh PNG các màn GUI không cần màn hình (`SDL_VIDEODRIVER=dummy`) — duyệt giao diện + hình cho báo cáo/video.

## Cách chạy
```
python -m gameai.gui.screenshots                                   # các màn k-in-row (DEFAULT_SHOTS) → report/figures/gui/
python -m gameai.gui.screenshots --only xq_check xq_flipped xq_end --out local_out/p62   # ảnh duyệt cờ tướng (P6.2)
python -m gameai.gui.screenshots --theme warm --only home play15 play3 --out report/figures/gui/style/warm
```
- Màn (`--only`): `home`, `setup`, `play15` (người X vs MCTS Vừa, 4 nước, Phân tích + W/N, chuột trên ô trống),
  `play3` (người X vs MCTS Khó, Phân tích), `modal` (2 người 15×15, X thắng), `review` (xem lại nước 5), `demo`, `help`.
- Cờ tướng (P6.2, chụp qua App thật, không nằm trong mặc định): `xq_check` (2 người, ván ngẫu nhiên seed ≥ 0 tới thế
  Đỏ bị chiếu, ply ≥ 14, ≥ 20 quân; click chọn quân nhiều nước nhất + hover ô đích), `xq_flipped` (người cầm Đen vs
  AB Dễ tất định, 12 nước ngẫu nhiên seed 7 → bàn xoay, chọn quân), `xq_end` (2 người, ván ngẫu nhiên đầu tiên kết thúc
  bằng chiếu bí → modal "… thắng" / "Chiếu bí").
- Chụp với animation tắt (trạng thái cuối ngay), theme mặc định = dark (An chọn ở cuối 3a).
- Ván tất định theo seed (MCTS theo iteration); thời gian trên thẻ khác nhau giữa các lần chạy → ảnh không trùng byte.

## Public API
```python
SHOTS: dict[str, Callable[[Surface], App]]; DEFAULT_SHOTS: list[str]   # mặc định = mọi màn trừ xq_*
def xq_random_line(done, seed0, max_ply=160) -> list[int]   # nước của ván ngẫu nhiên đầu tiên chạm `done(game)`
def capture(names, out: Path, theme="dark") -> list[Path]
```

## Test
- `tests/test_gui_style.py::test_screenshots_capture` (3 màn vào `tmp_path`).
