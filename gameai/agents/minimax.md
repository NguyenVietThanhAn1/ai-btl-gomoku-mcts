# Minimax — `gameai/agents/minimax.py`

> Mục tiêu của file này: agent/thành viên khác dùng được module **mà không cần đọc code**.
> Cập nhật cùng lúc với code.

**Trạng thái:** ✅ ổn định  ·  **Task:** P2.3  ·  **Cập nhật:** 2026-11-04

## Mục đích
Minimax thuần (không cắt tỉa), có thể giới hạn độ sâu, **đếm số nút** đã thăm. Là mốc so sánh cho
Alpha-Beta (đề ý 1, thí nghiệm E1) và đối thủ "chơi hoàn hảo" trên 3×3 (E2, P3).

## Public API
```python
WIN_SCORE = 10**12
EvalFn = Callable[[Game, int], float]            # eval_fn(game, player) -> điểm theo góc nhìn player
def terminal_score(winner: int, player: int, ply: int) -> float   # ±(WIN_SCORE − ply), hòa 0

class MinimaxAgent(Agent):
    def __init__(self, depth: int | None = None, eval_fn: EvalFn | None = None,
                 use_candidates: bool = True, seed: int | None = None): ...
    def select_move(self, game: Game) -> Move                     # từ Agent (template method)
    def root_values(self, game: Game) -> list[tuple[Move, float]] # giá trị từng nước ở gốc
    def value(self, game: Game) -> float                          # giá trị minimax của gốc
```
- `depth`: số nước tối đa tính từ gốc; `None` → tìm tới trạng thái kết thúc. `depth < 1` → `ValueError`.
- `eval_fn`: gọi ở nút chạm `depth` mà chưa kết thúc, theo góc nhìn **người đi ở gốc**. `None` → 0.
  Với k-in-row dùng `kinrow_eval.evaluate` (chữ ký khớp).
- `use_candidates`: duyệt `candidate_moves()` (mặc định) hay `legal_moves()`. Trên 3×3 hai tập trùng nhau.
- `seed`: `None` → chọn nước tốt nhất **đầu tiên** theo thứ tự nước (tất định); có seed → chọn ngẫu nhiên
  trong các nước bằng giá trị tốt nhất (`random.Random` riêng).
- Giá trị trả về (`value`, `root_values`) theo góc nhìn `game.current_player()` ở gốc.
- `stats` (sau `select_move`/`root_values`/`value`): `nodes` (số nút, **kể cả gốc**), `iterations` = 0,
  `time` (giây), `value` (giá trị gốc).
- Không làm thay đổi `game` (play/undo đối xứng). Precondition: ván chưa kết thúc.

## Phụ thuộc
- Dùng: `agents/base.py` (`Agent`), `core/game.py` (`Game`, `Move`, `DRAW`).
- Được dùng bởi: `agents/alphabeta.py` (P2.4 dùng lại `terminal_score`, `WIN_SCORE`, `EvalFn`),
  `experiments/e1_nodes.py`, `e2_never_lose.py` (chưa có).

## Thiết kế & quyết định
- Viết dạng **max/min tường minh** (không negamax) theo góc nhìn cố định `root` để khớp sách giáo khoa và
  báo cáo. Tầng MAX khi `current_player() == root`.
- Đếm nút: mỗi lần vào `_minimax` (+1) và nút gốc (+1). Nút lá/terminal cũng được đếm.
- Terminal: `WIN_SCORE − ply` → giữa hai nước cùng thắng, chọn thắng nhanh hơn; giữa hai nước cùng thua,
  chọn thua chậm hơn. `WIN_SCORE = 10^12` lớn hơn mọi điểm heuristic (`kinrow_eval` WIN = 10^(k+1)).
- Tìm kiếm bằng `play`/`undo` trên cùng đối tượng (không clone) → O(độ sâu) bộ nhớ.
- Độ phức tạp: O(b^d) nút. Cây 3×3 đầy đủ: **549 946 nút**, ~1,3 s (Python 3.13). Không dùng được cho
  15×15 ngoài depth rất nhỏ — đó là việc của Alpha-Beta.

## Giải thích cho báo cáo
**Bản chất.** Minimax giả định cả hai bên chơi tối ưu: người đi ở gốc (MAX) chọn nước có giá trị lớn nhất,
đối thủ (MIN) chọn nước làm giá trị nhỏ nhất. Giá trị một nút được tính đệ quy từ lá lên. Khi giới hạn độ
sâu, nút ở độ sâu tối đa được thay bằng hàm lượng giá heuristic.

**Pseudocode** (khớp `_minimax`):
```
MINIMAX(s, ply):
    nodes += 1
    if s kết thúc:          return +(WIN − ply) nếu root thắng, −(WIN − ply) nếu thua, 0 nếu hòa
    if ply = depth:         return eval(s, root)
    if lượt của root:       return max_{m}  MINIMAX(play(s, m), ply + 1)
    else:                   return min_{m}  MINIMAX(play(s, m), ply + 1)
Chọn nước: argmax_m MINIMAX(play(gốc, m), 1)
```

**Ví dụ trace tay** (3×3, X đi; X ở 0, 7, 8; O ở 1, 4, 6; ô trống 2, 3, 5; O dọa thắng chéo 2–4–6):
```
X O .        X đi 2 (chặn): O chọn min{ O3 → X5 thắng cột 2-5-8: +(W−3) ;  O5 → X3: hòa 0 } = 0
. O .        X đi 3:        O2 thắng ngay: −(W−2)  → min = −(W−2)
O X X        X đi 5:        O2 thắng ngay: −(W−2)  → min = −(W−2)
```
Gốc = max{0, −(W−2), −(W−2)} = 0 → chọn ô 2. Số nút = 1 (gốc) + 5 + 4 + 4 = **14** (khớp `stats["nodes"]`).

**Chọn tham số.** 3×3 dùng `depth=None` (tìm hết, đảm bảo chơi hoàn hảo). Trên bàn lớn minimax chỉ dùng làm
mốc đếm nút ở depth nhỏ (E1) cùng `eval_fn=kinrow_eval.evaluate`.

## Test
- File: `tests/test_minimax.py` — cây 3×3 đầy đủ đúng 549 946 nút và giá trị 0; `terminal_score` ưu tiên
  thắng nhanh/thua chậm; thắng ngay; chặn thua ngay; không mutate `game`; `root_values` phủ mọi nước;
  minimax-vs-minimax 3×3 luôn hòa (tất định + 2 seed); không thua RandomAgent (cả hai lượt, 5 seed);
  đếm nút depth 1/2 (10, 82); `depth=0` lỗi; 7×7 k=4 depth 1/2 với `evaluate` thắng ngay / chặn.
- Chạy riêng: `python -m pytest tests/test_minimax.py -q` (~30 s do tìm hết cây 3×3 nhiều lần).

## Hạn chế / TODO
- Không cắt tỉa, không transposition table (cố ý: là mốc so sánh cho Alpha-Beta).
- Không có giới hạn thời gian; chỉ giới hạn độ sâu.
