# Widget — `gameai/gui/widgets.py`

> Mục tiêu của file này: agent/thành viên khác dùng được module **mà không cần đọc code**.
> Cập nhật cùng lúc với code.

**Trạng thái:** 🔄 đang làm  ·  **Task:** P6.3 (D-29; làm lại ở phiên 3a)  ·  **Cập nhật:** 2026-11-17

## Mục đích
Design tokens (`Theme`) + widget tự viết bằng pygame (không thêm thư viện UI) cho mọi màn GUI. Mọi hình
bo góc / tròn vẽ qua `render` (khử răng cưa, cache).

## Public API
```python
@dataclass(frozen=True) class Theme:  # màu: bg, surface1/2/3, border, ink, muted, faint, accent(+_hover,
    # _ink), win, lose, last_move, select, heat, board_light/dark/grain/frame, grid, label,
    # stone_dark(+_hi), stone_light(+_hi), x_color, o_color; shadow_alpha, dim_alpha, radius=10, radius_small=6
DARK (tối, nhấn xanh lá) · WARM (sáng, gỗ ấm, nhấn cam đất) · THEMES · DEFAULT_THEME = "dark"
def current_theme() -> Theme;  T = current_theme;  def set_theme(name) -> Theme
CAPTION, BODY, TITLE, DISPLAY, WORDMARK = 14, 16, 20, 30, 52;  def space(n) -> int   # lưới 8 px
def panel(surf, rect, color=None, radius=None, shadow=False)   # card bo góc (+ bóng)
def ellipsize(text, font, width) -> str          # cắt "…" cho vừa width px
def draw_text(surf, text, pos, size=BODY, color=None, bold=False, anchor="topleft", max_width=None,
              weight=None) -> Rect   # ảnh chữ cache trong render.text
def is_click(ev) -> bool                         # MOUSEBUTTONDOWN nút trái

class Widget:  rect; visible; enabled; hover;  handle_event(ev) -> bool (True = đã tiêu thụ);  draw(surf)
class Button(Widget):   (rect, text, on_click=None, *, primary=False, danger=False, size=BODY, enabled=True,
                        hint=None, icon=None, ghost=False)   # icon trái nhãn; ghost = không nền tới khi hover
class IconButton(Button): (rect, icon_name, on_click=None, *, ghost=True, size=BODY)
class Toggle(Widget):   (rect, label, value=False, on_change=None)          # click → value đảo, on_change(value)
class SegmentedControl(Widget): (rect, options=[(key, nhãn)], selected, on_change=None, *, disabled=(), hints={})
    rect_of(key) -> Rect                         # ô của một lựa chọn (test click)
class Stepper(Widget):  (rect, value, step, lo, hi, on_change=None, fmt=str)   # nút − / + (minus, plus)
class Modal(Widget):    (rect, ..., dim_rect=None)  show(title, lines, buttons, title_color); close(); open
class Tooltip(Widget):  (rect, lines | () -> lines, width=340)   # hiện khi hover rect; vẽ sau cùng
class Disclosure(Widget): (rect, label, open_=False, on_toggle=None)  # "Tùy chọn nâng cao" thu gọn / mở
def wrap_text(text, size, width, weight="regular") -> list[str]   # gói dòng theo từ
Widget.update(dt)   # tween mỗi frame (Scene.update gọi); Button: màu hover RGBA 100 ms; Modal: fade + slide
class ScrollList(Widget): (rect, row_h=26, on_click=None, columns=())
    rows; selected; offset;  set_rows(rows, follow=False); scroll(d); ensure_visible(i); row_rect(i)
```
- Button **disabled** vẫn tiêu thụ click trong rect nhưng không gọi `on_click`. Segmented bỏ qua mục trong `disabled`.
- Modal khi `open`: chuyển sự kiện cho nút của nó, chặn mọi sự kiện chuột còn lại (không lọt xuống bàn).
- ScrollList: dòng là chuỗi hoặc tuple ô vẽ theo cột `columns` (px); bánh xe cuộn khi chuột ở trên; `offset` kẹp trong
  [0, `max_offset`]; `follow=True` tự cuộn xuống cuối khi có dòng mới.

## Phụ thuộc
- Dùng: pygame, `gui/render.py`, `gui/icons.py`, `gui/view.py` (`get_font`). Được dùng bởi: `gui/scene.py`, `gui/scenes.py`, `gui/play_scene.py`.

## Thiết kế & quyết định
- Không có hệ layout: mỗi màn đặt `rect` tuyệt đối (cửa sổ cố định 1280×720, D-28).
- Trạng thái hover cập nhật từ `MOUSEMOTION`; vẽ hoàn toàn từ trạng thái → test headless chỉ cần gửi event.
- 3b: màu đang chuyển (hover) vẽ bằng `render.tint(mask)` (không cache); `ScrollList.symbols` = ký hiệu → sprite
  (font không có glyph ● ○, dùng cho lịch sử Đen/Trắng).

## Test
- `tests/test_gui_scenes.py::test_widgets_basic` (Button disabled, Toggle, Segmented disabled, ScrollList kẹp/cuộn,
  Modal chặn click); các test màn dùng click thật lên `rect` của widget.
