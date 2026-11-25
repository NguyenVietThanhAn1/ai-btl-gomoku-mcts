# Màn ngoài ván — `gameai/gui/scenes.py`

> Mục tiêu của file này: agent/thành viên khác dùng được module **mà không cần đọc code**.
> Cập nhật cùng lúc với code.

**Trạng thái:** ✅ ổn định  ·  **Task:** P6.3 (D-29), P6.2 (D-37)  ·  **Cập nhật:** 2026-11-25

## Mục đích
Các màn Home, Setup (chọn chế độ), Demo thí nghiệm, Hướng dẫn.

## Public API
```python
class HomeScene(Scene):   name = "home";  buttons: {"play", "demo", "help", "quit"}     # Esc → thoát
    # wordmark MoveMind + 4 nút có icon (trái), bàn 9×9 minh họa (phải, hero_board cache theo theme);
    # không chữ kỹ thuật (Minimax/BTL…, D-29 phiên 3)
class SetupScene(Scene):  name = "setup"
    cfg: GameConfig                 # giữ giữa các lần vào màn
    controls: dict[str, Widget]     # "game", "mode", "side", "ai_kind", "ai_level", "ai_o_kind", "ai_o_level", "delay", "seed"
    back, start: Button
    def set(self, **changes)        # đổi cfg + dựng lại control
    def ai_lines(self) -> list[str] # "AI: Khó = MCTS h300 5000 iter, c=1.4, tactics — cấu hình E3"
    def on_start(self)              # → play với AppState(base=build_preset(cfg), config=cfg, Phân tích tắt)
class DemoScene(Scene):   name = "demo";  buttons: {preset_key: Button}   # → play với AppState(preset_key)
    sources(key) -> str     # "E2" / "E3" / "E3 · E3/E5": tra ngược từ spec các bên AI (find_level), không gõ tay
class HelpScene(Scene):   name = "help"
def level_line(cfg, choice) -> str
```

| Màn | Sự kiện | Tới |
|---|---|---|
| Home | Chơi / Demo thí nghiệm / Hướng dẫn | Setup / Demo / Help |
| Home | Thoát, Esc | đóng app |
| Setup | Bắt đầu | Play (`build_preset(cfg)`) |
| Setup / Demo / Help | Quay lại, Esc | Home |
| Demo | chọn preset | Play (preset P6.1 nguyên spec, nhãn "cấu hình thí nghiệm") |

- Setup (3b): card "Ván mới"; 15×15 ghi "Đen · đi trước" / "Trắng · đi sau", AI vs AI "AI Đen" / "AI Trắng";
  dưới hàng AI là tóm tắt "Đối thủ: MCTS · Khó" + ⓘ (tooltip: spec + nguồn); seed trong "Tùy chọn nâng cao"
  (`controls["advanced"]`, thu gọn mặc định). Demo: 3 card, nhãn "CẤU HÌNH THÍ NGHIỆM · E2/E3" hiện rõ.
  Help: card Luật chơi / Trong ván (gói dòng) + card Phím tắt (chip).
- Setup: Cờ tướng chọn được (P6.2): "Đỏ · đi trước" / "Đen · đi sau", "AI Đỏ" / "AI Đen" (`GameConfig.side_name`).
  Help: thêm dòng luật cờ tướng (chiếu bí / hết nước = thua; lặp lần 3 / quá 300 nước = hòa; không xét chiếu dai — D-22)
  và cách đi 2 bước. "Bạn cầm" chỉ ở người vs AI; AI vs AI có 2 hàng AI (X, O) + **Độ trễ AI**
  (0–5 s, bước 0,25); 2 người không có hàng AI. Hộp dưới cùng ghi tên cấu hình thật + nguồn của từng bên.

## Phụ thuộc
- Dùng: `gui/game_config.py`, `gui/presets.py`, `gui/play_scene.py` (`AppState`), `gui/scene.py`, `gui/widgets.py`.

## Test
- `tests/test_gui_scenes.py`: điều hướng Home/Setup/Demo/Help + Esc; Setup Cờ tướng → nhãn Đỏ/Đen → Play (bàn xoay khi cầm Đen); click lựa chọn → `cfg` →
  `build_preset` → spec trong ván + nguồn trên thẻ; control theo chế độ (độ trễ, seed); Demo giữ spec P6.1.

## Hạn chế / TODO
- ✂ Hướng dẫn chi tiết (hiện: luật + phím tắt).
