# Controller GUI — `gameai/gui/controller.py`

> Mục tiêu của file này: agent/thành viên khác dùng được module **mà không cần đọc code**.
> Cập nhật cùng lúc với code.

**Trạng thái:** ✅ ổn định  ·  **Task:** P6.1 (D-28), P6.3 (D-29)  ·  **Cập nhật:** 2026-11-17

## Mục đích
Giữ trạng thái một ván trong GUI (game, lượt, lịch sử nước, lỗi) và chạy AI trong thread mà không treo
cửa sổ. **Không import pygame** → test được headless. Không phụ thuộc game cụ thể (chỉ dùng `Game`).

## Public API
```python
@dataclass class MoveInfo:   # một nước đã đi
    move; player; by_ai: bool; time: float          # AI: giây quanh select_move (trong thread); người: từ lúc tới lượt
    iterations: int | None; nodes: int | None; tactic: int   # từ agent.stats
    root_stats: list[(move, W, N, W/N)]              # MCTS.last_root_stats(); [] nếu không phải MCTS / đi tactic
    is_tactic: bool                                  # property: tactic ∈ {1 thắng ngay, 2 chặn ngay}
@dataclass class AIResult:   game_id, ply, player, move, stats, root_stats, time, error

class GameController:
    def __init__(self, preset, seed=0, delay=None, clock=time.monotonic)  # delay None → preset.delay;
        # clock: đồng hồ (giây) cho độ trễ AI + thời gian nghĩ của người — tiêm được cho test (P6.3)
    game; preset; seed; delay; paused; game_id; history: list[MoveInfo]; error: str | None
    specs / agents: dict[player, AgentSpec | None] / dict[player, Agent | None]   # None = người
    thinking: bool; ply; last; last_ai; over; winner; ai_vs_ai
    resigned: int | None; outcome: int | None      # outcome tính cả đầu hàng; winner = game.winner()
    human_sides: list[int]
    def new_game(self, preset=None, seed=None) -> None
    def is_human_turn(self) -> bool;  def is_ai_turn(self) -> bool
    def submit_human_move(self, move) -> bool
    def update(self, now: float | None = None) -> None    # gọi mỗi frame
    def result_text(self) -> str | None                   # "X thắng" / "O thắng" / "Hòa" / "X đầu hàng — O thắng" / lỗi; None khi chưa hết
    can_undo: bool;  def undo(self) -> bool                # P6.3, xem dưới
    can_resign: bool;  def resign_side(self) -> int | None;  def resign(self, player=None) -> bool
    def side_time(self, player) -> float                  # tổng giây một bên đã dùng
    def position_at(self, ply) -> Game                    # thế sau `ply` nước; ván mới + replay, không đụng self.game
    def run_until_idle(self, timeout=60.0) -> None        # test/autoplay; TimeoutError nếu quá hạn
```
- `new_game`: `game_id += 1`, dựng game và agent **mới** từ spec; seed agent = `arena.derive_seed(seed, "X"/"O")`
  → cùng seed + cùng nước người + ngân sách iteration ⇒ cùng ván (quay lại được).
- `submit_human_move` trả False, không đổi gì, nếu: AI đang nghĩ, không phải lượt người, ván hết, nước ∉ `legal_moves()`.
- `undo()` (P6.3): lùi tới khi bỏ được đúng 1 nước của người → người vs AI 2 ply (1 ply nếu ván vừa kết thúc bằng nước
  của người), 2 người 1 ply. False, không đổi gì, khi: AI đang nghĩ, AI vs AI, đã đầu hàng / lỗi, chưa có nước của người.
  Sau ván thắng/hòa bằng nước đi vẫn lùi được (ván tiếp tục).
- `resign(player=None)`: mặc định `resign_side()` = người (người vs AI) hoặc bên đang tới lượt (2 người); AI vs AI → None/False.
- `update(now)`: (1) rút hết hàng đợi, chỉ áp dụng kết quả có `game_id` **và** `ply` khớp và ván chưa dừng; nước AI không hợp lệ
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
- **Undo / đầu hàng (D-29):** undo khóa khi AI đang nghĩ (không hủy được thread vì không sửa `agents/` → tránh dồn
  thread mồ côi). Undo, ván mới, đầu hàng đều `game_id += 1` → kết quả cũ bị bỏ kể cả khi `ply` trùng (lùi rồi đi lại).
  Undo dựng lại agent (MCTS giữ `root`, rollout heavy có trạng thái) → sau undo chuỗi nước không còn tái lập theo
  seed của cả ván.
- Input nhiều bước (cờ tướng) nằm ở view (`gui/view.md`); controller chỉ nhận nước hoàn chỉnh.

## Test
- `tests/test_gui_controller.py`: người (ngẫu nhiên có seed) vs MCTS 3×3 hết ván, MCTS không thua, cả hai vai;
  đổi bên → AI đi trước, người cầm O; AI vs AI 3×3 và 15×15 (h300 50 iter vs AB2) hết ván; cùng seed cùng ván; root stats (N giảm dần,
  ΣN = iterations); tactic thắng ngay 15×15 → không root stats; không mutate khi đang nghĩ (key không đổi),
  ván mới bỏ kết quả cũ; pause; delay; agent lỗi → `error`.
  P6.3: undo người vs AI 2 ply (key về thế cũ, `game_id` tăng, agent mới); người cầm O không lùi được nước mở của AI;
  undo khóa khi AI nghĩ + kết quả cũ trùng ply bị bỏ theo `game_id`; 2 người 1 ply, lùi sau ván thắng; AI vs AI khóa;
  đầu hàng (kết quả AI tới sau bị bỏ, chữ kết quả, bên đầu hàng ở 2 người); `position_at` không đổi ván thật; `side_time`.
- Chạy: `python -m pytest tests/test_gui_controller.py -q`

## Hạn chế / TODO
- Thread AI bị bỏ vẫn chạy tới hết nước đó (tốn CPU tới khi xong).
