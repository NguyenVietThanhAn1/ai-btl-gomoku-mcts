# Màn ngoài ván — `gameai/gui/scenes.py`

> Mục tiêu của file này: agent/thành viên khác dùng được module **mà không cần đọc code**.
> Cập nhật cùng lúc với code.

**Trạng thái:** 🔄 đang làm  ·  **Task:** P6.3 (D-29)  ·  **Cập nhật:** 2026-11-17

## Mục đích
Các màn Home, Setup (chọn chế độ), Demo thí nghiệm, Hướng dẫn.

## Public API
```python
class HomeScene(Scene):   name = "home";  buttons: {"play", "demo", "help", "quit"}     # Esc → thoát
class SetupScene(Scene):  name = "setup"
    cfg: GameConfig                 # giữ giữa các lần vào màn
    controls: dict[str, Widget]     # "game", "mode", "side", "ai_kind", "ai_level", "ai_o_kind", "ai_o_level", "delay", "seed"
    back, start: Button
    def set(self, **changes)        # đổi cfg + dựng lại control
    def ai_lines(self) -> list[str] # "AI: Khó = MCTS h300 5000 iter, c=1.4, tactics — cấu hình E3"
    def on_start(self)              # → play với AppState(base=build_preset(cfg), config=cfg, Phân tích tắt)
class DemoScene(Scene):   name = "demo";  buttons: {preset_key: Button}   # → play với AppState(preset_key)
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

- Setup: Cờ tướng disabled ("sắp có — P6.2"). "Bạn cầm" chỉ ở người vs AI; AI vs AI có 2 hàng AI (X, O) + **Độ trễ AI**
  (0–5 s, bước 0,25); 2 người không có hàng AI. Hộp dưới cùng ghi tên cấu hình thật + nguồn của từng bên.

## Phụ thuộc
- Dùng: `gui/game_config.py`, `gui/presets.py`, `gui/play_scene.py` (`AppState`), `gui/scene.py`, `gui/widgets.py`.

## Test
- `tests/test_gui_scenes.py`: điều hướng Home/Setup/Demo/Help + Esc; Cờ tướng không chọn được; click lựa chọn → `cfg` →
  `build_preset` → spec trong ván + nguồn trên thẻ; control theo chế độ (độ trễ, seed); Demo giữ spec P6.1.

## Hạn chế / TODO
- ✂ Hướng dẫn chi tiết (hiện: luật + phím tắt).
