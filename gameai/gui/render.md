# Sprite khử răng cưa — `gameai/gui/render.py`

> Mục tiêu của file này: agent/thành viên khác dùng được module **mà không cần đọc code**.
> Cập nhật cùng lúc với code.

**Trạng thái:** 🔄 đang làm (3a)  ·  **Task:** P6.3 phiên 3 (D-29)  ·  **Cập nhật:** 2026-11-17

## Mục đích
Mọi hình tròn / bo góc / quân / vạch / bóng của GUI: vẽ ở **4×** (`SS`) lên Surface SRCALPHA rồi `smoothscale` →
mép mềm. Không vẽ thẳng `pygame.draw` lên màn hình (D-29).

## Public API
```python
# mặt nạ trắng + alpha (cache)
rounded_mask(w, h, r); circle_mask(d); ring_mask(d, width)
tint(mask, color) -> Surface                      # màu RGB/RGBA (BLEND_RGBA_MULT), KHÔNG cache — cho màu đang tween
# sprite màu token (cache)
rounded_rect(w, h, r, color); rounded_outline(w, h, r, width, color); circle(d, color); ring(d, width, color)
solid(w, h, rgba)                                 # nền mờ sau modal
shadow(w, h, r, blur, alpha)                      # Surface (w+2·blur)×(h+2·blur), đặt lệch (−blur, −blur)
stone(d, base, light, rim); stone_shadow(d, alpha)   # quân 15×15: gradient tỏa (numpy) + viền tối
x_mark(d, color); o_mark(d, color)                # 3×3: nét bo tròn
line(dx, dy, thickness, color)                    # vạch dày đầu tròn (đường thắng), hộp bao lề = thickness
text(s, size, weight, color)                      # ảnh chữ (cache 1024)
wood(w, h, light, dark, grain, seed=7)            # vân gỗ sinh bằng code, tất định
# không cache
scaled(sprite, factor); faded(sprite, alpha)      # tween kích thước / độ mờ từ sprite chuẩn
cache_sizes() -> dict[str, int]; clear_caches()
```

## Thiết kế & quyết định (D-29 + chỉnh của An)
- Mọi cache là `lru_cache(maxsize=…)`; khóa chỉ gồm kích thước chuẩn + màu token (hữu hạn) → không phình theo frame.
  Tween kích thước → `scaled`, tween màu → `tint(mask)`, mờ → `faded`: không thêm entry.
- `pygame.quit()` xóa mọi cache (Surface cũ không dùng được); hook `register_quit` được đăng ký lại mỗi chu kỳ init
  (pygame bỏ danh sách sau mỗi lần quit) — cùng cơ chế `view.get_font`.
- Vân gỗ: sin theo hàng + uốn tần số thấp + nhiễu, seed cố định → không cần ảnh, không vướng license.

## Test
- `tests/test_gui_style.py`: mép mềm (alpha trung gian), cache trả cùng object, quân có highlight, quit → cache rỗng →
  init → vẽ lại không crash; 40 frame Play có hover → kích thước cache không đổi.
