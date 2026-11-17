# Icon — `gameai/gui/icons.py`

> Mục tiêu của file này: agent/thành viên khác dùng được module **mà không cần đọc code**.
> Cập nhật cùng lúc với code.

**Trạng thái:** 🔄 đang làm (3a)  ·  **Task:** P6.3 phiên 3 (D-29)  ·  **Cập nhật:** 2026-11-17

## Mục đích
Icon nút vẽ bằng code (không thêm thư viện / font icon).

## Public API
```python
PAINTERS: dict[str, Painter]   # undo, new_game, flag, home, play, pause, chevron_left, chevron_right, info, chart, close, book, flask
def icon_mask(name, size) -> Surface   # mặt nạ trắng, vẽ 4× + smoothscale, cache (128)
def icon(name, size, color) -> Surface # tô màu (không cache)
```
- Thêm icon: viết `_painter(surf, n)` vẽ trắng trên Surface n×n (n = size·4), đăng ký vào `PAINTERS`.

## Test
- `tests/test_gui_style.py::test_icons_exist_and_tint`: mọi icon đúng cỡ, có pixel đặc.
