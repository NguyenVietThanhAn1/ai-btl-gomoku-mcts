# Widget — `gameai/gui/widgets.py`

> Mục tiêu của file này: agent/thành viên khác dùng được module **mà không cần đọc code**.
> Cập nhật cùng lúc với code.

**Trạng thái:** 🔄 đang làm  ·  **Task:** P6.3 (D-29)  ·  **Cập nhật:** 2026-11-17

## Mục đích
Widget tự viết bằng pygame (không thêm thư viện UI) + theme màu tối kiểu chess.com cho mọi màn GUI.

## Public API
```python
# theme: BG, PANEL, CARD, CARD_ACTIVE, INK, MUTED, ACCENT, BUTTON, DANGER, BORDER, SELECT, ... (RGB)
def ellipsize(text, font, width) -> str          # cắt "…" cho vừa width px
def draw_text(surf, text, pos, size=18, color=INK, bold=False, anchor="topleft", max_width=None) -> Rect
def is_click(ev) -> bool                         # MOUSEBUTTONDOWN nút trái

class Widget:  rect; visible; enabled; hover;  handle_event(ev) -> bool (True = đã tiêu thụ);  draw(surf)
class Button(Widget):   (rect, text, on_click=None, *, primary=False, danger=False, size=20, enabled=True, hint=None)
class Toggle(Widget):   (rect, label, value=False, on_change=None)          # click → value đảo, on_change(value)
class SegmentedControl(Widget): (rect, options=[(key, nhãn)], selected, on_change=None, *, disabled=(), hints={})
    rect_of(key) -> Rect                         # ô của một lựa chọn (test click)
class Stepper(Widget):  (rect, value, step, lo, hi, on_change=None, fmt=str)   # nút − / + (minus, plus)
class Modal(Widget):    show(title, lines, buttons, title_color); close(); open: bool
class ScrollList(Widget): (rect, row_h=26, on_click=None, columns=())
    rows; selected; offset;  set_rows(rows, follow=False); scroll(d); ensure_visible(i); row_rect(i)
```
- Button **disabled** vẫn tiêu thụ click trong rect nhưng không gọi `on_click`. Segmented bỏ qua mục trong `disabled`.
- Modal khi `open`: chuyển sự kiện cho nút của nó, chặn mọi sự kiện chuột còn lại (không lọt xuống bàn).
- ScrollList: dòng là chuỗi hoặc tuple ô vẽ theo cột `columns` (px); bánh xe cuộn khi chuột ở trên; `offset` kẹp trong
  [0, `max_offset`]; `follow=True` tự cuộn xuống cuối khi có dòng mới.

## Phụ thuộc
- Dùng: pygame, `gui/view.py` (`get_font`). Được dùng bởi: `gui/scene.py`, `gui/scenes.py`, `gui/play_scene.py`.

## Thiết kế & quyết định
- Không có hệ layout: mỗi màn đặt `rect` tuyệt đối (cửa sổ cố định 1280×720, D-28).
- Trạng thái hover cập nhật từ `MOUSEMOTION`; vẽ hoàn toàn từ trạng thái → test headless chỉ cần gửi event.

## Test
- `tests/test_gui_scenes.py::test_widgets_basic` (Button disabled, Toggle, Segmented disabled, ScrollList kẹp/cuộn,
  Modal chặn click); các test màn dùng click thật lên `rect` của widget.
