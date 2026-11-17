# Ảnh headless — `gameai/gui/screenshots.py`

> Mục tiêu của file này: agent/thành viên khác dùng được module **mà không cần đọc code**.
> Cập nhật cùng lúc với code.

**Trạng thái:** 🔄 đang làm (3a)  ·  **Task:** P6.3 phiên 3 (D-29)  ·  **Cập nhật:** 2026-11-17

## Mục đích
Sinh ảnh PNG các màn GUI không cần màn hình (`SDL_VIDEODRIVER=dummy`) — duyệt giao diện + hình cho báo cáo/video.

## Cách chạy
```
python -m gameai.gui.screenshots                                   # mọi màn, theme mặc định → report/figures/gui/
python -m gameai.gui.screenshots --theme warm --only home play15 play3 --out report/figures/gui/style/warm
```
- Màn (`--only`): `home`, `setup`, `play15` (người X vs MCTS Vừa, 4 nước, Phân tích + W/N, chuột trên ô trống),
  `play3` (người X vs MCTS Khó, Phân tích), `modal` (2 người 15×15, X thắng), `review` (xem lại nước 5), `demo`, `help`.
- Chụp với animation tắt (trạng thái cuối ngay), theme mặc định = dark (An chọn ở cuối 3a).
- Ván tất định theo seed (MCTS theo iteration); thời gian trên thẻ khác nhau giữa các lần chạy → ảnh không trùng byte.

## Public API
```python
SHOTS: dict[str, Callable[[Surface], App]]
def capture(names, out: Path, theme="dark") -> list[Path]
```

## Test
- `tests/test_gui_style.py::test_screenshots_capture` (3 màn vào `tmp_path`).
