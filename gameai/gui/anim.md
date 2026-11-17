# Chuyển động — `gameai/gui/anim.py`

> Mục tiêu của file này: agent/thành viên khác dùng được module **mà không cần đọc code**.
> Cập nhật cùng lúc với code.

**Trạng thái:** ✅ ổn định  ·  **Task:** P6.3 phiên 3 (D-29)  ·  **Cập nhật:** 2026-11-17

## Mục đích
Tween theo `dt` cho các chuyển động nhẹ của GUI, có cờ tắt toàn cục (test headless, ảnh tất định, `--no-anim`).

## Public API
```python
ENABLED: bool;  def set_enabled(on) -> None          # tắt → mọi Tween ở giá trị cuối ngay, pulse() = 1
PLACE = 0.15; HOVER = 0.10; MODAL = 0.20; SCENE = 0.15; WIN_LINE = 0.30; PULSE_PERIOD = 1.2   # giây
def ease_out_cubic(t) -> float;  def lerp(a, b, t)    # a, b: số hoặc tuple (màu RGBA)
class Tween(start, end, duration, ease=ease_out_cubic):
    value; progress; done;  update(dt);  retarget(end, duration=None)   # đổi đích từ giá trị hiện tại
def pulse(t, period=PULSE_PERIOD) -> float            # 0 → 1 → 0 theo sin (chỉ báo "đang nghĩ")
```

| Chuyển động | Ở đâu | Cách vẽ (không phình cache) |
|---|---|---|
| Đặt quân 150 ms (scale 0,6 → 1 + fade) | `PlayScene._step_animations` → `KInRowView.anim_move` | `render.scaled` + `render.faded` từ sprite chuẩn |
| Hover nút 100 ms | `Button.update` (tween RGBA) | `render.tint(rounded_mask)` khi đang chuyển; xong → sprite token |
| Modal fade + slide 200 ms | `Modal.update` / `Modal.draw` | vẽ lên layer tạm rồi `set_alpha` (chỉ khi đang mở) |
| Chuyển scene 150 ms | `SceneManager.switch` / `tick` | chụp frame cũ, `set_alpha` giảm dần |
| Đường thắng 300 ms | `PlayScene` → `KInRowView.win_progress` | cắt vùng blit của sprite vạch đầy đủ (cache 1 entry) |
| "Đang nghĩ" pulse | `PlayScene._draw_card` | `render.tint(mask, alpha theo pulse)` |

## Phụ thuộc
- Không phụ thuộc pygame. Được dùng bởi: `gui/widgets.py` (Button, Modal), `gui/scene.py` (crossfade),
  `gui/play_scene.py` (đặt quân, đường thắng, pulse), `gui/pygame_app.py` (`--no-anim`), `gui/screenshots.py`.

## Test
- `tests/test_gui_polish.py`: ease theo dt, tắt → giá trị cuối; chạy trọn animation đặt quân + hover qua 60 frame →
  `render.cache_sizes()` không đổi (chỉnh 1 của An); modal / đường thắng / crossfade chạy hết; màu hover trung gian
  không vào cache. `tests/conftest.py` tắt animation cho mọi test khác.

## Hạn chế / TODO
- ✂ (D-29) không có animation lật/xóa quân khi Đi lại; đồng hồ đếm ngược, âm thanh chưa làm.
