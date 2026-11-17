# GUI pygame — `gameai/gui/pygame_app.py`

> Mục tiêu của file này: agent/thành viên khác dùng được module **mà không cần đọc code**.
> Cập nhật cùng lúc với code.

**Trạng thái:** ✅ ổn định  ·  **Task:** P6.1 (D-28; thay cho ✂ P4.3 CLI), P6.3 (D-29)  ·  **Cập nhật:** 2026-11-17

## Mục đích
Cửa sổ game Caro AI (người vs AI, AI vs AI, 2 người) để chơi, demo và quay video P7.4. Từ P6.3 là chủ
`SceneManager`: Home / Setup / Demo / Hướng dẫn / ván (`scenes.md`, `play_scene.md`).

## Cách chạy
```
python -m gameai.gui.pygame_app [--preset KEY] [--seed S] [--delay GIÂY] [--iterations N] [--swap]
                                [--no-overlay] [--wn] [--autoplay] [--max-frames F] [--timeout GIÂY]
```
- Không có `--preset` → mở **Home** (menu). Có `--preset` (`3x3_human_mcts` | `15_human_h300` | `15_h300_vs_ab2`, xem
  `presets.md`) → vào thẳng màn ván với cấu hình thí nghiệm; các cờ khác như P6.1. `--autoplay` không kèm preset → preset 1.
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
| `←` `→` | xem lại (sau khi hết ván) |
| `Esc` | trong ván: đóng hộp thoại, không thì thoát; Setup/Demo/Hướng dẫn → Home; Home → thoát |

Lệnh quay 3 cảnh video (P7.4):
```
python -m gameai.gui.pygame_app --preset 3x3_human_mcts --seed 0          # rồi S để quay vai còn lại
python -m gameai.gui.pygame_app --preset 15_human_h300 --seed 0
python -m gameai.gui.pygame_app --preset 15_h300_vs_ab2 --seed 0 --delay 0.5 --wn
```

## Public API
```python
WINDOW = (1280, 720); FPS = 30; BOARD_RECT (từ play_scene); AppState (từ play_scene, xem play_scene.md)
def set_dpi_aware() -> None                 # win32: SetProcessDpiAware(), lỗi thì bỏ qua
class App:
    def __init__(self, state: AppState | None = None, surface=None)   # state None → Home; có → màn ván
    manager: SceneManager; play: PlayScene; in_play: bool; running: bool (get/set)
    ctrl / view / state                     # của màn ván (tương thích P6.1)
    def restart(self); def handle_key(self, key)   # phím → màn hiện tại
    def handle_click(self, pos) -> bool     # click bàn của màn ván
    def handle_event(self, ev); def tick(self)
def autoplay_move(app, rng)                 # chỉ khi đang ở màn ván, lượt người
def run(state: AppState | None, autoplay=False, max_frames=None, timeout=None) -> App
def main(argv=None) -> None
```

## Phụ thuộc
- Dùng: pygame, `gui/scene.py`, `gui/scenes.py`, `gui/play_scene.py`, `gui/controller.py`, `gui/presets.py`, `gui/view.py`.
- Được dùng bởi: `experiments/p63_gui_timing.py` (`App`, `AppState`, `autoplay_move`).

## Thiết kế & quyết định (D-28)
- Cửa sổ cố định 1280×720 (không resize) để khung quay ổn định; `SetProcessDpiAware` (chỉ win32, try/except)
  để Windows không scale mờ. Khóa 30 fps (`Clock.tick(30)`).
- Panel (P6.3): xem `play_scene.md` (thẻ người chơi, lịch sử, nút, Phân tích, modal, xem lại).
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
- `tests/test_gui_scenes.py::test_run_autoplay_preset_and_menu_start`: `run` với preset + autoplay hết ván; không preset → Home.
- Kiểm tra cả ván (headless): `SDL_VIDEODRIVER=dummy python -m gameai.gui.pygame_app --preset <KEY> --autoplay`.

## Hạn chế / TODO
- P6.2 thêm view cờ tướng + preset; controller không cần đổi.
