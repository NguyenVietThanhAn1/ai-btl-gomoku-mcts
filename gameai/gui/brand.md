# Nhận diện — `gameai/gui/brand.py`

> Mục tiêu của file này: agent/thành viên khác dùng được module **mà không cần đọc code**.
> Cập nhật cùng lúc với code.

**Trạng thái:** ✅ ổn định  ·  **Task:** P6.3 phiên 3 (D-29)  ·  **Cập nhật:** 2026-11-17

## Mục đích
Tên sản phẩm (một chỗ duy nhất), logo và wordmark vẽ bằng code.

## Public API
```python
APP_NAME = "MoveMind"                 # caption cửa sổ, Home; đổi tên ở đây
def logo(size, theme=None) -> Surface # ô bo góc màu nhấn + 3 quân chéo (quân giữa rỗng); cache theo (cỡ, màu)
def window_icon() -> Surface          # logo 64 px → pygame.display.set_icon (pygame_app.run)
def draw_wordmark(surf, center, size, theme=None, with_logo=True) -> Rect   # logo + "Move" (chữ chính) + "Mind" (màu nhấn)
```

- `logo_surface(size, accent, stone, hollow)`: bản cache theo màu mà `logo()` gọi (cache xóa khi `pygame.quit`).

## Phụ thuộc
- Dùng: `gui/render.py`, `gui/widgets.py` (Theme). Được dùng bởi: `gui/scenes.py` (Home), `gui/pygame_app.py`.

## Test
- `tests/test_gui_style.py::test_brand_name_logo_and_window` (tên, logo 64 px, caption + icon cửa sổ khi `run`).

## Hạn chế / TODO
- Wordmark dùng font đóng gói; thiếu font → fallback hệ thống, tỷ lệ chữ có thể khác ảnh.
