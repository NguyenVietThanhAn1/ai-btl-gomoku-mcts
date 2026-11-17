# Màn ván đấu — `gameai/gui/play_scene.py`

> Mục tiêu của file này: agent/thành viên khác dùng được module **mà không cần đọc code**.
> Cập nhật cùng lúc với code.

**Trạng thái:** 🔄 đang làm  ·  **Task:** P6.3 (D-29)  ·  **Cập nhật:** 2026-11-17

## Mục đích
Màn chơi kiểu chess.com: bàn bên trái (nhãn tọa độ), panel phải với thẻ 2 người chơi, lịch sử, nút, Phân tích;
modal kết thúc; xem lại. Giữ toàn bộ phím tắt P6.1.

## Public API
```python
BOARD_RECT = Rect(16, 16, 688, 688)      # gồm lề nhãn (view tự chừa 24 px)
@dataclass class AppState:
    preset_key: str | None; seed; swapped; iterations; delay; overlay: OverlayOpts
    base: Preset | None; config: GameConfig | None
    def preset(self) -> Preset            # (base | PRESETS[key]) → swap_sides → with_iterations
    experiment: bool                      # preset_key khác None (Demo / --preset)
class PlayScene(Scene):  name = "play"
    on_enter(state: AppState)             # tạo GameController + view
    state; ctrl; view; review: int | None; modal: Modal; history: ScrollList
    b_undo, b_new, b_resign, b_menu, b_prev, b_next, b_exit_review: Button;  t_analysis, t_wn: Toggle
    restart(); handle_click(pos) -> bool; handle_key(key)
    result_view() -> (tiêu đề, dòng phụ, màu); open_result(); enter_review(ply); step(±1); exit_review()
    displayed() -> (Game, MoveInfo | None)   # thế đang vẽ: bản dựng lại khi xem lại, không thì ván thật
    player_name(side) -> (tên, dòng cấu hình)
```

## Bố cục (1280×720)
| Vùng | Nội dung |
|---|---|
| Bàn (16–704) | `GameView`; nước cuối nền vàng + viền đỏ; đường thắng viền xanh; quân mờ khi hover ô hợp lệ |
| Thẻ trên / dưới | O (đi sau) / X (đi trước): ký hiệu, tên ("Bạn", "Người chơi X", "MCTS · Khó"), cấu hình + nguồn, "đang nghĩ…" / "đến lượt", nước cuối + tổng giây |
| Trạng thái | lượt / AI đang nghĩ / kết quả / "Xem lại: nước k / n"; số nước |
| Lịch sử | mỗi nước một dòng: số, bên, nước (cùng ký hiệu nhãn bàn), giây, AI/tactic; tự cuộn xuống cuối |
| Nút | Đi lại · Ván mới · Đầu hàng · Menu (xem bảng) |
| Phân tích | công tắc Phân tích (= overlay N P6.1) + W/N; hộp: nước cuối + top 5 gốc MCTS; khóa khi ván không có MCTS |

| Trạng thái | Nút 1 | Nút 3 |
|---|---|---|
| người vs AI | Đi lại (khóa khi AI nghĩ / chưa có nước người) | Đầu hàng |
| 2 người | Đi lại (1 ply) | "X đầu hàng" / "O đầu hàng" theo bên tới lượt |
| AI vs AI | Tạm dừng / Tiếp tục | (ẩn) |
| hết ván | Đi lại (nếu được) | Kết quả (mở lại modal) |
| xem lại | ‹ Trước · Sau › | Thoát xem lại |

- Modal kết thúc (mở khi ván vừa hết): người vs AI "Bạn thắng!" / "Bạn thua" / "Bạn đã đầu hàng" / "Hòa"; khác: "X thắng",
  "O đầu hàng", "Hòa"; dòng phụ `result_text` + số nước + seed; nút Chơi lại / Xem lại / Về menu.
- Xem lại (chỉ sau khi hết ván; ✂ khi đang chơi): ‹ › / ← →, click dòng lịch sử; `ctrl.position_at(k)` dựng thế, ván thật không đổi; click bàn bị bỏ.
- Phím: P6.1 (1/2/3, N, S, [ ], I/K, −/=, O, W, Space) + ← → (xem lại). Esc: modal mở → đóng, không thì thoát.

## Phụ thuộc
- Dùng: `gui/controller.py`, `gui/presets.py`, `gui/game_config.py`, `gui/view.py`, `gui/widgets.py`, `gui/scene.py`.

## Thiết kế & quyết định (D-29)
- Nút Menu tạm dừng controller cũ; ván mới luôn tạo controller mới → thread cũ chạy nốt rồi bị bỏ.
- Nguồn cấu hình trên thẻ: tra ngược `presets.find_level`; vào từ Demo thì ghi "cấu hình thí nghiệm (E…)".
- Thời gian trên thẻ/lịch sử chỉ minh họa (GIL với vòng vẽ, D-28); số đo GUI ở `p63_gui_timing`.

## Test
- `tests/test_gui_scenes.py`: Đi lại / Đầu hàng / Menu bằng click; Đi lại khóa khi AI nghĩ; nhãn đầu hàng 2 người; AI vs AI
  không có Đầu hàng + Tạm dừng; modal X thắng + đường thắng + Chơi lại; Bạn thắng / Bạn thua; xem lại ‹ / click lịch sử / ←,
  thế = `position_at`, ván thật không đổi; lịch sử không click được khi đang chơi; quân mờ; vẽ mọi trạng thái 15×15.
