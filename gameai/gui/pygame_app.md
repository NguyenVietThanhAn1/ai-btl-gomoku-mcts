# GUI pygame — `gameai/gui/pygame_app.py`

> Mục tiêu của file này: agent/thành viên khác dùng được module **mà không cần đọc code**.
> Cập nhật cùng lúc với code.

**Trạng thái:** ✅ ổn định  ·  **Task:** P6.1 (D-28; thay cho ✂ P4.3 CLI)  ·  **Cập nhật:** 2026-11-17

## Mục đích
Cửa sổ chơi k-in-row (người vs AI, AI vs AI) để demo và quay video P7.4. Ghép `GameController`
(logic) + `GameView` (vẽ/input) + panel thông tin.

## Cách chạy
```
python -m gameai.gui.pygame_app [--preset KEY] [--seed S] [--delay GIÂY] [--iterations N] [--swap]
                                [--no-overlay] [--wn] [--autoplay] [--max-frames F] [--timeout GIÂY]
```
- `--preset`: `3x3_human_mcts` (mặc định) | `15_human_h300` | `15_h300_vs_ab2` (xem `presets.md`).
- `--autoplay`: tự đánh thay người (nước ngẫu nhiên có seed trong `candidate_moves`), thoát khi hết ván,
  in một dòng tóm tắt ASCII — kiểm tra headless với `SDL_VIDEODRIVER=dummy`. Mã thoát 1 nếu AI lỗi.

| Phím | Tác dụng |
|---|---|
| `1` `2` `3` | chọn preset (đổi bên / iteration / độ trễ về mặc định của preset) |
| `N` | ván mới cùng cấu hình |
| `S` | đổi bên người ↔ AI (ván mới): người cầm O, AI đi trước |
| `[` `]` | seed −1 / +1 (ván mới) |
| `I` `K` | iteration MCTS ×2 / ÷2 (ván mới) |
| `-` `=` | độ trễ AI −/+ 0,25 s (áp dụng ngay) |
| `O` / `W` | bật/tắt overlay N / thêm W/N |
| `Space` | tạm dừng / chạy tiếp AI |
| `Esc` | thoát |

Lệnh quay 3 cảnh video (P7.4):
```
python -m gameai.gui.pygame_app --preset 3x3_human_mcts --seed 0          # rồi S để quay vai còn lại
python -m gameai.gui.pygame_app --preset 15_human_h300 --seed 0
python -m gameai.gui.pygame_app --preset 15_h300_vs_ab2 --seed 0 --delay 0.5 --wn
```

## Public API
```python
WINDOW = (1280, 720); BOARD_RECT = Rect(20, 20, 680, 680); FPS = 30
def set_dpi_aware() -> None                 # win32: SetProcessDpiAware(), lỗi thì bỏ qua
@dataclass class AppState: preset_key; seed; swapped; iterations; delay; overlay: OverlayOpts
    def preset(self) -> Preset              # PRESETS[key] → swap_sides → with_iterations
class App:
    def __init__(self, state, surface=None) # surface None → display.set_mode(WINDOW)
    ctrl: GameController; view: GameView; running: bool
    def restart(self); def handle_key(self, key); def handle_click(self, pos) -> bool
    def handle_event(self, ev); def tick(self)   # update controller + vẽ
def run(state, autoplay=False, max_frames=None, timeout=None) -> App
def main(argv=None) -> None
```

## Phụ thuộc
- Dùng: pygame, `gui/controller.py`, `gui/presets.py`, `gui/view.py` (+ `kinrow_view.py` qua `make_view`).

## Thiết kế & quyết định (D-28)
- Cửa sổ cố định 1280×720 (không resize) để khung quay ổn định; `SetProcessDpiAware` (chỉ win32, try/except)
  để Windows không scale mờ. Khóa 30 fps (`Clock.tick(30)`).
- Panel: preset, hai bên (`side_label`), seed, độ trễ, lượt / "AI đang nghĩ…" / kết quả, số nước, nước cuối +
  thời gian/nước + iterations + nút (hoặc "tactic (thắng ngay / chặn ngay)"), top 6 nước ở gốc MCTS (N, W/N).
- Overlay chỉ hiện khi nước cuối là nước AI có `root_stats` (cây của nước vừa đi); người đi tiếp, hoặc AB / tactic đi → overlay tắt.
- Click chỉ được xử lý khi là lượt người và AI không nghĩ; mọi đổi cấu hình (trừ độ trễ, overlay, pause) đều
  tạo ván mới qua `restart()`.
- **Thời gian/nước trong GUI chậm hơn số thí nghiệm**: thread AI tranh GIL với vòng lặp vẽ (30 fps) nên
  cùng số iteration mất lâu hơn so với `arena` / E3. Số thời gian trên panel **chỉ để minh họa**, không trích
  vào báo cáo (số liệu báo cáo lấy từ `results/`).

## Test
- `tests/test_gui_controller.py::test_app_draws_headless_with_overlay`: App trên Surface headless — vẽ sau nước
  AI có overlay + W/N, click của người, phím 2 / K / S / ] / = / Esc.
- `test_ai_vs_ai_15x15_full_game`: preset 3 với 50 iter chạy hết ván.
- Kiểm tra cả ván (headless): `SDL_VIDEODRIVER=dummy python -m gameai.gui.pygame_app --preset <KEY> --autoplay`.

## Hạn chế / TODO
- Chưa có menu bằng chuột; cấu hình bằng phím / dòng lệnh.
- P6.2 thêm view cờ tướng + preset; controller không cần đổi.
