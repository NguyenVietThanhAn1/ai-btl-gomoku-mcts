# Controller GUI — `gameai/gui/controller.py`

> Mục tiêu của file này: agent/thành viên khác dùng được module **mà không cần đọc code**.
> Cập nhật cùng lúc với code.

**Trạng thái:** ✅ ổn định  ·  **Task:** P6.1 (D-28)  ·  **Cập nhật:** 2026-11-17

## Mục đích
Giữ trạng thái một ván trong GUI (game, lượt, lịch sử nước, lỗi) và chạy AI trong thread mà không treo
cửa sổ. **Không import pygame** → test được headless. Không phụ thuộc game cụ thể (chỉ dùng `Game`).

## Public API
```python
@dataclass class MoveInfo:   # một nước đã đi
    move; player; by_ai: bool; time: float          # giây quanh select_move (đo trong thread)
    iterations: int | None; nodes: int | None; tactic: int   # từ agent.stats
    root_stats: list[(move, W, N, W/N)]              # MCTS.last_root_stats(); [] nếu không phải MCTS / đi tactic
    is_tactic: bool                                  # property: tactic ∈ {1 thắng ngay, 2 chặn ngay}
@dataclass class AIResult:   game_id, ply, player, move, stats, root_stats, time, error

class GameController:
    def __init__(self, preset: Preset, seed: int = 0, delay: float | None = None)  # None → preset.delay
    game; preset; seed; delay; paused; game_id; history: list[MoveInfo]; error: str | None
    specs / agents: dict[player, AgentSpec | None] / dict[player, Agent | None]   # None = người
    thinking: bool; ply; last; last_ai; over; winner; ai_vs_ai
    def new_game(self, preset=None, seed=None) -> None
    def is_human_turn(self) -> bool;  def is_ai_turn(self) -> bool
    def submit_human_move(self, move) -> bool
    def update(self, now: float | None = None) -> None    # gọi mỗi frame
    def result_text(self) -> str | None                   # "X thắng" / "O thắng" / "Hòa" / lỗi; None khi chưa hết
    def run_until_idle(self, timeout=60.0) -> None        # test/autoplay; TimeoutError nếu quá hạn
```
- `new_game`: `game_id += 1`, dựng game và agent **mới** từ spec; seed agent = `arena.derive_seed(seed, "X"/"O")`
  → cùng seed + cùng nước người + ngân sách iteration ⇒ cùng ván (quay lại được).
- `submit_human_move` trả False, không đổi gì, nếu: AI đang nghĩ, không phải lượt người, ván hết, nước ∉ `legal_moves()`.
- `update(now)`: (1) rút hết hàng đợi, chỉ áp dụng kết quả có `game_id` **và** `ply` khớp; nước AI không hợp lệ
  hoặc exception → `error`, ván dừng; (2) nếu tới lượt AI, không `paused`, đã qua `delay` giây từ nước trước →
  khởi thread.

## Phụ thuộc
- Dùng: `agents/registry.py` (`make_agent`, `make_game`), `arena.py` (`derive_seed`), `core/game.py`, `gui/presets.py`.
- Được dùng bởi: `gui/pygame_app.py`, `gui/view.py` (kiểu `MoveInfo`).

## Thiết kế & quyết định (D-28)
- **Thread trên clone:** thread daemon gọi `agent.select_move(game.clone())`, đọc `stats` + `last_root_stats()`
  ngay trong thread rồi `queue.put`. Ván thật chỉ bị mutate trong `_apply` (assert `not thinking`), gọi từ
  luồng GUI. Mỗi agent chỉ được một thread dùng tại một thời điểm.
- **Hủy theo id ván:** không kill được thread Python → ván mới chỉ tăng `game_id`; kết quả cũ tới sau bị bỏ.
  Thoát app: thread daemon chết theo tiến trình.
- **Tactic:** `stats["tactic"] ∈ {1, 2}` → MCTS đi thẳng, `root_stats == []` → view ghi "tactic", không overlay
  (tactic 3 = search trên tập con, vẫn có root_stats).
- Input nhiều bước (cờ tướng) nằm ở view (`gui/view.md`); controller chỉ nhận nước hoàn chỉnh.

## Test
- `tests/test_gui_controller.py`: người (ngẫu nhiên có seed) vs MCTS 3×3 hết ván, MCTS không thua, cả hai vai;
  đổi bên → AI đi trước, người cầm O; AI vs AI 3×3 và 15×15 (h300 50 iter vs AB2) hết ván; cùng seed cùng ván; root stats (N giảm dần,
  ΣN = iterations); tactic thắng ngay 15×15 → không root stats; không mutate khi đang nghĩ (key không đổi),
  ván mới bỏ kết quả cũ; pause; delay; agent lỗi → `error`.
- Chạy: `python -m pytest tests/test_gui_controller.py -q`

## Hạn chế / TODO
- Thread AI bị bỏ vẫn chạy tới hết nước đó (tốn CPU tới khi xong).
