# GreedyAgent — `gameai/agents/greedy.py`

> Mục tiêu của file này: agent/thành viên khác dùng được module **mà không cần đọc code**.
> Cập nhật cùng lúc với code.

**Trạng thái:** ✅ ổn định  ·  **Task:** P2.5  ·  **Cập nhật:** 2026-11-04

## Mục đích
Đối thủ rẻ cho thí nghiệm 15×15: nhìn trước đúng 1 nước (1-ply), chọn nước có điểm heuristic cao nhất,
tie-break ngẫu nhiên có seed. Mạnh hơn RandomAgent rất nhiều nhưng không tìm kiếm.

## Public API
```python
class GreedyAgent(Agent):
    def __init__(self, score_fn: MoveFn, seed: int | None = None, use_candidates: bool = True): ...
    def select_move(self, game: Game) -> Move   # từ Agent (template method, D-7)
```
- `score_fn(game, move) -> float`: điểm của nước theo góc nhìn người sắp đi, gọi *trước* `play`,
  không được mutate `game` (`MoveFn` lấy từ `agents/alphabeta.py`). K-in-row: `kinrow_eval.move_score`.
  Bắt buộc truyền (không import cứng heuristic, giống D-9).
- `seed`: `random.Random(seed)` riêng. Cùng seed → cùng chuỗi lựa chọn. `seed=None` → ngẫu nhiên theo hệ
  thống (giống RandomAgent; khác Minimax/AB vốn tất định khi không có seed). RNG chỉ được dùng khi có hòa điểm.
- `use_candidates=True` (mặc định, **khác RandomAgent** mặc định `False`): chấm `candidate_moves()`;
  `False`: chấm `legal_moves()`.
- `stats`: `nodes` = số nước đã chấm, `iterations` = 0, `time` (giây), `value` = điểm cao nhất.
- Không làm thay đổi `game`. Precondition: ván chưa kết thúc.

## Phụ thuộc
- Dùng: `agents/base.py`, `agents/alphabeta.py` (chỉ kiểu `MoveFn`), `core/game.py`.
- Hàm truyền vào: `heuristics/kinrow_eval.move_score`.
- Được dùng bởi: `experiments/` (đối thủ cho E3–E5 trên 15×15), arena/CLI (chưa có).

## Thiết kế & quyết định
- Một vòng duyệt, giữ danh sách nước bằng điểm cao nhất → O(#candidate · chi phí `score_fn`);
  15×15 với `move_score`: vài µs mỗi nước được chấm, ~0,3–1 ms mỗi lượt (60–160 candidate).
- Dùng `move_score` thay vì `delta_eval` vì `move_score` xếp **thắng ngay > chặn thua ngay > delta**
  (D-8); chọn theo delta thuần sẽ bỏ qua chặn four để tạo open-four và thua ngay.

## Giải thích cho báo cáo
**Bản chất.** Greedy (tham lam 1 nước) là minimax độ sâu 1: thử từng nước, chấm điểm trạng thái ngay sau đó
bằng heuristic (`move_score` tính trên nước, trước `play`: thay đổi lượng giá + bậc thắng/chặn), chọn nước tốt
nhất; không xét phản ứng của đối thủ. Phòng thủ chỉ có nhờ bậc BLOCK thưởng cho nước chặn nước thắng ngay.

**Pseudocode.**
```
GREEDY(s):
    best = −∞; B = []
    for m in candidate_moves(s):
        v = score(s, m)                 # move_score: WIN | delta + BLOCK | delta
        if v > best: best = v; B = [m]
        elif v = best: B.append(m)
    return B[0] nếu |B| = 1, ngược lại chọn ngẫu nhiên đều trong B (rng có seed)
```

**Ví dụ trace tay** (15×15, k=5):
- X có four hàng 7 cột 5–8 (đầu trái bị chặn), O có open-three hàng 10: ô (7, 9) có `move_score` = WIN →
  chọn thắng ngay.
- O có four hàng 10 cột 5–8, X có open-three hàng 7: tạo open-four ở (7, 9) chỉ được delta +1915, còn chặn ở
  (10, 9) được 1143 + BLOCK = 101 143 → chọn chặn.
- Sau khi X đi ô giữa, cả 24 candidate của O đều có điểm 20: mỗi trong 20 cửa sổ qua một ô trong cho +1 (hoặc
  mở cửa sổ mới cho O, hoặc phá cửa sổ 1 quân của X). Mọi ô hòa điểm → tie-break ngẫu nhiên quyết định.

**Chọn tham số.** `use_candidates=True` (bán kính 2) vì các ô xa không có ích và làm chậm.

## Test
- File: `tests/test_greedy.py` — thắng ngay; chặn four thay vì tạo open-four; nước chọn là argmax và
  `stats` đúng; tie-break: nhiều nước bằng điểm, các seed cho nước khác nhau nhưng đều thuộc tập argmax,
  cùng seed lặp lại đúng; không mutate; `score_fn` tùy biến + `legal_moves`; thắng RandomAgent (candidate)
  trên 15×15 ở cả hai lượt (4 seed); gọi trên ván đã kết thúc → `AssertionError`.
- Chạy riêng: `python -m pytest tests/test_greedy.py -q` (<1 s).

## Hạn chế / TODO
- Không nhìn trước: không thấy double-threat (open-three + four, double open-three) của đối thủ cho tới khi quá muộn.
- `move_score` cho mọi ô trong bán kính 2 quanh một quân lẻ cùng điểm → nước khai cuộc gần như ngẫu nhiên.
- `MoveFn` đang import từ `agents/alphabeta.py` chỉ để lấy type alias; có thể dời sang `agents/base.py` khi đụng tới.
