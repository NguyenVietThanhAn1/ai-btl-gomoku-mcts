# MCTS-UCT — `gameai/agents/mcts.py`

> Mục tiêu của file này: agent/thành viên khác dùng được module **mà không cần đọc code**.
> Cập nhật cùng lúc với code.

**Trạng thái:** ✅ ổn định  ·  **Task:** P3.1  ·  **Cập nhật:** 2026-11-10

## Mục đích
Monte Carlo Tree Search với công thức chọn UCT (đề ý 2). Có `final_move` (max N / max W/N) cho E4,
rollout policy là tham số cho E5, `check_tactics` cho E6. Chạy trên mọi `Game` (chỉ dùng interface).

## Public API
```python
class MCTSAgent(Agent):
    def __init__(self, iterations: int | None = 1000, time_limit: float | None = None,
                 c: float = math.sqrt(2), rollout_policy: str | RolloutPolicy = "random",
                 score_fn: MoveFn | None = None, rollout_limit: int | None = None,
                 value_fn: ValueFn | None = None, final_move: str = "max_n",
                 check_tactics: bool = False, seed: int | None = None): ...
    def select_move(self, game: Game) -> Move                       # từ Agent (template method, D-7)
    def last_root_stats(self) -> list[tuple[Move, float, int, float]]  # (move, W, N, W/N), N giảm dần
    root: Node | None                                               # cây của lần tìm gần nhất

class Node: move, parent, children, untried, W, N, player_just_moved   # __slots__
def uct(child: Node, log_np: float, c: float) -> float               # W/N + c·sqrt(log_np / N)
def select_child(node: Node, c: float) -> Node
def backpropagate(node: Node, z: float) -> None                      # z = điểm của P1 ∈ [0, 1]
TACTIC_NONE, TACTIC_WIN, TACTIC_BLOCK, TACTIC_RESTRICT = 0, 1, 2, 3
```
- **Ngân sách:** `iterations` và/hoặc `time_limit` (giây); dừng khi chạm cái nào trước; cả hai `None` →
  `ValueError`. Luôn chạy ≥ 1 iteration. `time_limit` tính cả thời gian `check_tactics`.
- `c`: hằng số khám phá (≥ 0), mặc định √2.
- `rollout_policy`: `"random"` (mặc định), `"heavy"` (cần `score_fn`, vd. `kinrow_eval.move_score`), hoặc
  một callable `(game, rng) -> Move` (xem `rollout.md`). MCTS không import heuristic (giống D-9).
- `rollout_limit`: số nước mô phỏng tối đa (`None` = chơi tới kết thúc). Bị cắt → z = `value_fn(g)`
  (xác suất P1 thắng, vd. `rollout.sigmoid_value(evaluate, scale)`), không có `value_fn` → 0,5.
- `final_move`: `"max_n"` (N lớn nhất, bằng → W lớn hơn) hoặc `"max_wn"` (W/N lớn nhất, bằng → N lớn hơn);
  còn bằng → con mở rộng trước.
- `check_tactics` (mặc định **tắt**, để E6 đo tác dụng): xem "Thiết kế".
- `seed`: `random.Random(seed)` tạo một lần ở `__init__` (dùng cho expansion và rollout). Agent mới, cùng
  seed, cùng `iterations`, cùng thế cờ → cùng nước và cùng `last_root_stats()`. `time_limit` thì không
  tái lập được (số iteration phụ thuộc máy).
- `stats`: `iterations`, `nodes` (số node của cây, kể cả gốc), `time` (giây), `value` (W/N của nước chọn,
  ∈ [0, 1] — khác thang AB), `max_depth` (độ sâu lá sâu nhất đã tới), `rollout_plies` (tổng số nước mô
  phỏng), `tactic` (0/1/2/3). Đi tắt bằng tactic: `iterations = nodes = 0`, `value` = 1 (thắng) / NaN (chặn),
  `last_root_stats() == []`.
- Không làm thay đổi `game`. Precondition: ván chưa kết thúc (`AssertionError`).

## Phụ thuộc
- Dùng: `agents/base.py`, `agents/rollout.py`, `agents/alphabeta.py` (kiểu `MoveFn`), `core/game.py`
  (`P1`, `DRAW`, `result_for`).
- Được dùng bởi: `experiments/` (E2–E6), arena/CLI/GUI (chưa có; GUI đọc `last_root_stats()` cho overlay).

## Thiết kế & quyết định (D-11)
- **Node:** `untried` = `candidate_moves()` lúc tạo node (`[]` nếu kết thúc). Gốc có
  `player_just_moved = −current_player()`. Không dùng lại cây giữa các lượt.
- **Một iteration:** `g = game.clone()` (1,5 µs trên 15×15 — rẻ hơn undo ~90 nước rollout) → selection →
  expansion 1 node (rút ngẫu nhiên trong `untried` bằng swap-pop O(1)) → simulation → backprop.
- **Góc nhìn (bất biến):** W/N của node = tỷ lệ điểm của `player_just_moved`. Cha chọn con có W/N cao ⇒
  selection và chọn nước cuối **không lật**. **Chỗ lật duy nhất** là `backpropagate`:
  `W += z if player_just_moved == P1 else 1 − z`, `z = result_for(winner, P1)` (D-5). Tính theo người của
  từng node, không đảo `1 − r` qua mỗi tầng.
- **Bất biến cây** (test kiểm): gốc `N = ΣN_c` và `W = Σ(N_c − W_c)` (mọi iteration đều đi xuống một con);
  node không kết thúc khác gốc `N = 1 + ΣN_c` và `W − Σ(N_c − W_c)` = điểm của lượt thăm đầu (lượt tạo
  node) ∈ {0; 0,5; 1} (∈ [0, 1] nếu có `value_fn`); node kết thúc: W/N ∈ {0; 0,5; 1}.
- **`check_tactics`** (chỉ dùng play/undo → dùng được cho cờ tướng): có nước thắng ngay → đi luôn
  (tactic 1). Ngược lại S = các nước mà sau đó đối thủ không thắng ngay: |S| = 1 → đi luôn (2); S = ∅ (đã
  thua) hoặc S = mọi nước → search bình thường (0); còn lại → search chỉ trên S (3; với k-in-row không xảy
  ra vì nước của ta không tạo được ô thắng cho đối thủ). Chi phí O(b²) play/undo, ~80 ms với 148 candidate
  khi không có đe dọa; không dùng RNG nên thế cờ yên tĩnh cho cùng cây như khi tắt.
- **Tốc độ đo được** (máy dev, rollout random): 3×3 1000 iter ≈ 19 ms; 15×15 ≈ 0,32–0,40 ms/iter (rollout
  trung bình 78–89 nước) → 1000 iter ≈ 0,3–0,4 s/nước. Gốc 15×15 có ~25–150 con nên 1000 iter chỉ cho cây
  sâu ~2.
- **Hành vi đã ghi nhận** (đo trong lúc phát triển; số liệu báo cáo lấy từ E2/E6):
  - Tắt tactics, 15×15, phải chặn four (thế `BLOCK15` trong test): chặn đúng 0/10 seed ở 1000 iter,
    2/10 ở 5000 iter. Lý do: mỗi con của gốc ~10 lượt thăm → chỉ mở rộng ~10/100 nước đáp trả, ít khi gặp ô
    thắng của đối thủ; rollout random chọn trúng ô đó ~1%.
  - 20 ván vs `MinimaxAgent` hoàn hảo 3×3, tắt tactics: **1000 iter đủ** — 0 thua (20 hòa). Không cần tăng.
  - MCTS **không chiết khấu độ sâu**: ở 3×3 `. . X / X O X / . O .` (O đi), O thắng ngay ở 1 nhưng O đi 8 cũng
    thắng chắc (3 đường dọa) → cả hai có W/N = 1 chính xác, N bằng nhau, tie-break theo thứ tự mở rộng có
    thể chọn 8. Không mất thắng, nhưng không phải "thắng ngay". Trong bộ 30 thế của test (16 thế có
    nước thắng, 14 thế phải chặn), MCTS chọn đúng nước thắng ngay ở 15/16 thế; thế còn lại chính là thế này.

## Giải thích cho báo cáo
**Bản chất.** MCTS xây dần một cây tìm kiếm không đối xứng: thay vì duyệt hết như minimax, mỗi vòng lặp đi
xuống theo nhánh hứa hẹn nhất, thêm một nút mới, chơi thử ngẫu nhiên tới hết ván để ước lượng giá trị, rồi
cập nhật thống kê trên đường đi. Nhánh tốt được thăm nhiều nên cây mọc sâu ở đó. UCT xem việc chọn con như
bài toán multi-armed bandit (UCB1): hạng tỷ lệ thắng W/N là **khai thác**, hạng c·sqrt(ln N_p / N_i) là
**khám phá**, lớn với con ít được thăm; c điều chỉnh cân bằng giữa hai hạng.

**Công thức.** `UCT(i) = W_i/N_i + c·sqrt(ln N_p / N_i)`, chỉ dùng khi mọi con đã được thăm (N_i ≥ 1).
W tính theo góc nhìn **người vừa đi vào node**: thắng 1, hòa 0,5, thua 0.

**Pseudocode** (khớp `_search`, `_simulate`, `backpropagate`):
```
MCTS(s0):
    root = Node(player_just_moved = đối thủ của người đi ở s0, untried = candidates(s0))
    lặp tới hết ngân sách:
        s = clone(s0); v = root
        while v.untried rỗng và v có con:                 # 1. Selection
            v = argmax_con UCT(con);  play(s, v.move)
        if v.untried khác rỗng:                           # 2. Expansion
            m = rút ngẫu nhiên khỏi v.untried; p = người đi ở s; play(s, m)
            v = con mới (move m, player_just_moved p, untried = candidates(s))
        đi ngẫu nhiên (rollout policy) tới khi s kết thúc  # 3. Simulation
        z = result_for(winner(s), P1)                     #    (bị cắt: value_fn(s) hoặc 0,5)
        while v ≠ null:                                   # 4. Backpropagation
            v.N += 1;  v.W += z nếu v.player_just_moved = P1, ngược lại 1 − z;  v = v.parent
    return con của root có N lớn nhất                     # final_move = "max_n"
```

**Ví dụ trace tay** (3×3, X đi; X ở 0, 7, 8; O ở 1, 4, 6; trống 2, 3, 5 — cùng thế cờ với `minimax.md`;
O dọa ô 2 theo chéo 2-4-6). c = √2, giả sử thứ tự mở rộng 2, 3, 5 và kết quả rollout như dưới:
```
X O .    it1: mở rộng X2; rollout O3, X5 → X thắng, z=1.  X2: W=1 N=1   gốc (O): W=0 N=1
. O .    it2: mở rộng X3; rollout O2 → O thắng, z=0.      X3: W=0 N=1   gốc: W=1 N=2
O X X    it3: mở rộng X5; rollout O2 → O thắng, z=0.      X5: W=0 N=1   gốc: W=2 N=3
it4: gốc đã mở rộng hết, ln 3 = 1,099: UCT(X2) = 1 + 1,414·1,048 = 2,48; UCT(X3) = UCT(X5) = 1,48 → X2.
     X2 còn untried {3, 5}: mở rộng O3 (node của O); rollout X5 → X thắng, z=1.
     O3: W += 1 − 1 = 0 (N=1);  X2: W=2 N=2;  gốc: W=2 N=4
it5: ln 4 = 1,386: UCT(X2) = 1 + 1,414·0,832 = 2,18 > UCT(X3) = 1,66 → X2; mở rộng O5; rollout X3 → hòa,
     z=0,5.  O5: W=0,5 N=1;  X2: W=2,5 N=3;  gốc: W=2,5 N=5
```
Kết quả: chọn X2 (N = 3, W/N = 0,83) — đúng nước chặn duy nhất, giống Minimax. Kiểm bất biến: gốc
N = 3 + 1 + 1 = 5, W = (3 − 2,5) + (1 − 0) + (1 − 0) = 2,5; X2: N = 1 + 2, W − Σ(N_c − W_c) = 2,5 − (1 + 0,5) = 1
= điểm lượt thăm đầu (it1). Node của O nhận 1 − z: đây là chỗ lật góc nhìn duy nhất.

**Vì sao chọn N lớn nhất (E4).** N là số lần UCT đã "tin" nước đó đủ để chọn lại; một con có W/N cao nhưng
N nhỏ (vd. 1/1) là ước lượng nhiễu. Khi tìm lâu, con tốt nhất gom phần lớn lượt thăm nên max-N ổn định hơn.

**Chọn tham số.** c = √2 là giá trị lý thuyết của UCB1 với điểm trong [0, 1]; E3 quét c ∈ {0,5; 1; 1,4; 2}.
3×3: 1000 iter đủ để không thua Minimax (đo ở test). 15×15: rollout random, `candidate_moves` bán kính 2
(D-3); `check_tactics` tắt khi đo thuật toán gốc, bật khi demo/so khả năng chơi (E6).

## Test
- File: `tests/test_mcts.py` (+ `tests/test_rollout.py`, xem `rollout.md`):
  - UCT: công thức, `select_child` (kể cả c = 0). Backprop dựng tay: z = 1 / 0 / 0,5 / 0,25 trên chuỗi 3 node.
  - Góc nhìn: thắng ngay 3×3 cho X và O (W/N con thắng = 1 đúng), phải chặn 3×3 cho X và O, bộ 30 thế 3×3
    (có thắng → nước thắng chắc theo Minimax và mọi nước thắng ngay có W/N = 1; phải chặn → đúng ô
    chặn), thế "thắng ngay vs thắng chắc" ở
    trên; `value_fn` "P1 luôn thắng" cho W/N = 1 ở gốc X và 0 ở gốc O; cắt rollout không `value_fn` → 0,5.
  - Bất biến cây: 3×3 và 7×7 k=4 (`value_fn=None`, điểm ∈ {0; 0,5; 1}) và với `value_fn` (∈ [0, 1]);
    `nodes` = số node đếm được.
  - Tactics: thắng ngay / chặn four 15×15 (X và O), thua chắc (S = ∅) vẫn search, thế yên tĩnh cho cùng cây
    như khi tắt, game bốc sỏi (`Pile`) cho tactic 2 và 3 (lọc gốc theo S); MCTS chơi đúng `Pile` khi tắt.
  - `xfail(strict=False)`: tắt tactics, 15×15, 1000 iter không chặn được four (ghi nhận, E6).
  - `max_n` / `max_wn` khớp `last_root_stats()`; stats đủ khóa; không mutate (bật/tắt tactics); heavy
    rollout (3×3 thắng ngay; 15×15 có `rollout_limit` + `sigmoid_value`).
  - Ngân sách: iteration chính xác, `time_limit`, cả hai, `time_limit` cực nhỏ vẫn ≥ 1 iteration; tham số
    sai → `ValueError`; ván đã kết thúc → `AssertionError`.
  - Seed: cùng seed cùng nước + cùng stats (3×3, 15×15), cùng chuỗi nước qua 5 lượt; seed khác cho nước khác.
  - Đối đầu: không thua Random 3×3 (20 ván, đổi lượt); `slow`: thắng Random 15×15 ở cả hai lượt (300 iter,
    ~7 s), 20 ván vs Minimax 3×3 tắt tactics không thua (1000 iter, ~19 s).
- Đột biến đã thử (không có trong repo): lật toàn cục ở backprop, viết cứng góc nhìn P1, đảo `1 − r` từ lá,
  lật trong UCT — mỗi đột biến làm fail nhiều test ở trên (lật toàn cục vẫn giữ bất biến cây nhưng fail test
  thắng ngay/chặn/`value_fn`).
- Chạy riêng: `python -m pytest tests/test_mcts.py -q` (~6 s không tính `slow`; `-m slow` thêm ~26 s).

## Hạn chế / TODO
- Không dùng lại cây giữa các lượt, không progressive widening / FPU: gốc 15×15 có ~100 con nên 1000 iter
  chỉ cho cây rất nông.
- Không chiết khấu độ sâu / không MCTS-Solver: không phân biệt thắng ngay với thắng chắc về sau.
- `check_tactics` O(b²); với k-in-row có thể O(b) bằng `move_score` (bậc BLOCK) nếu cần nhanh hơn.
- Heavy rollout chậm (~0,5 ms/bước trên 15×15) — tăng tốc ở P3.2.
