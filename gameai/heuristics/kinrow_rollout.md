# KInRowHeavyRollout — `gameai/heuristics/kinrow_rollout.py`

> Mục tiêu của file này: agent/thành viên khác dùng được module **mà không cần đọc code**.
> Cập nhật cùng lúc với code.

**Trạng thái:** ✅ ổn định  ·  **Task:** P3.2 (D-12)  ·  **Cập nhật:** 2026-11-10

## Mục đích
Bản nhanh của heavy rollout cho k-in-a-row: **cùng phân phối, cùng chuỗi nước** với
`HeavyRollout(kinrow_eval.move_score, T)` (`agents/rollout.py`, bản chuẩn), nhưng nhanh hơn 4–11× mỗi rollout
trên 15×15. Dùng cho MCTS heavy ở E5 và các bước quét tham số.

## Public API
```python
class KInRowHeavyRollout:
    name = "heavy_kinrow"
    def __init__(self, temperature: float = 100.0): ...          # T ≤ 0 → ValueError
    temperature: float
    def __call__(self, game: KInRow, rng: random.Random) -> int:  # nước lấy mẫu theo softmax
    def move_scores(self, game: KInRow) -> list[int]:             # = [move_score(game, m) for m in candidate_moves()]
```
- Dùng trong MCTS: `MCTSAgent(..., rollout_policy=KInRowHeavyRollout(T))` (truyền object; `make_policy`
  không đổi, chuỗi `"heavy"` vẫn trả `HeavyRollout` bản chuẩn).
- Gọi khi ván chưa kết thúc (giống bản chuẩn). Không mutate `game`; chỉ dùng `rng` được truyền vào.
- **Có trạng thái nội bộ** nhưng tự đồng bộ theo `game.move_history`: dùng chung một object cho nhiều ván,
  clone, sau `undo`, hay gọi lẻ đều đúng. Đổi kích thước bàn (n, k) → tự dựng lại. Không an toàn đa luồng
  (mỗi agent/tiến trình một object).

## Phụ thuộc
- Dùng: `games/kinrow.py` (`KInRow.move_history`, `cell_of`), `heuristics/kinrow_eval.py` (`windows`,
  `windows_through`, `_weights`, `win_score`, `block_bonus`, `move_score` cho trường hợp ô trống cuối).
- Được dùng bởi: `experiments/p32_heavy_speed.py`; sẽ dùng ở bước quét tham số (P3.3) và E5.

## Thiết kế & quyết định (D-12)
- **Profile bản chuẩn** (15×15): ~80% thời gian ở `kinrow_eval._scan` — mỗi bước gọi `move_score` cho **mọi**
  candidate (50–150 ô), mỗi lần quét ~20 cửa sổ × 5 ô. Dò thắng/chặn chỉ quanh 2 nước cuối là không đủ:
  (1) softmax cần delta của mọi candidate nên bỏ delta là đổi policy; (2) đe dọa có thể nằm xa 2 nước cuối
  vì trong cây UCT các nước được mở rộng ngẫu nhiên, có thể bỏ qua đe dọa.
- **Trạng thái:** `count` = số quân X, O của từng cửa sổ; với mỗi ô × mỗi bên (X đi / O đi): `delta`,
  `win` (số cửa sổ cho thắng ngay), `block` (số cửa sổ đối thủ có k−1 quân). Điểm của ô m cho người đi p:
  `WIN nếu win[p][m] > 0, ngược lại delta[p][m] + (BLOCK nếu block[p][m] > 0)` — đúng các bậc của
  `move_score`.
- **Cập nhật khi đặt/gỡ quân ở m:** chỉ các cửa sổ qua m (≤ 4k = 20). Với mỗi cửa sổ, đóng góp cho mọi ô
  trong nó đổi từ `table[a][b]` sang `table[a'][b']` (bảng tiền tính theo k, đúng nhánh của `_scan`), làm cho
  cả hai góc nhìn. Ô đã có quân cũng được cộng nhưng không bao giờ được đọc.
- **Đồng bộ:** so `move_history` với lịch sử đã áp: tìm tiền tố chung, gỡ (−1) các nước thừa từ mới nhất về,
  áp (+1) các nước mới. Trong MCTS, mỗi iteration clone gốc nên chỉ gỡ rollout + đường cây cũ, không dựng
  lại từ đầu. Phát hiện được mọi thay đổi (kể cả undo rồi đi nước khác cùng độ dài).
- **Ô trống cuối cùng:** `move_score` dùng `−evaluate` (nước kết thúc hòa) → gọi thẳng `move_score` (chỉ 1
  candidate, rẻ).
- **Lấy mẫu:** `weights = [exp((s − max)/T)]`, `rng.choices(moves, weights)` y hệt bản chuẩn, candidate cùng
  thứ tự → cùng số ngẫu nhiên tiêu thụ → cùng nước.
- **Tốc độ đo được** (`results/tables/p32_heavy_speed.csv`, 50 rollout/ô, máy dev): 50–139 µs/bước so với
  416–778 µs; mỗi rollout nhanh hơn 7,1–10,9× (khai cuộc 6 nước), 4,1–8,4× (20 nước) — phần cố định đồng bộ
  đầu rollout chiếm nhiều khi rollout ngắn. Trong MCTS 0,5 s/nước (`p32_mcts_iterations.csv`): T=100 được
  387–577 iteration so với 53–76 của bản chuẩn và 535–637 của random.
- **Độ dài rollout** (cùng file): T=100 trung bình 9,4 nước (khai cuộc 6) / 5,1 (20); T=300: 13,3 / 5,8;
  T=1000: 33,1 / 22,4; random: 80–88. Hệ quả: ở T=100, `rollout_limit=10` gần như không có tác dụng.

## Giải thích cho báo cáo
**Bản chất.** Heavy rollout chọn nước theo softmax của điểm heuristic. Điểm của một ô chỉ phụ thuộc vào các
cửa sổ k ô đi qua nó, và một nước đi chỉ làm đổi các cửa sổ qua ô vừa đặt. Vì vậy thay vì tính lại điểm của
mọi ô ở mỗi bước, ta giữ sẵn điểm và chỉ sửa phần bị ảnh hưởng — cùng ý tưởng "đánh giá tăng dần" như
`delta_eval` của Alpha-Beta. Kết quả là đúng cùng một policy (không xấp xỉ), chỉ rẻ hơn, nên so sánh random
vs heavy ở cùng thời gian/nước (E5) công bằng hơn.

**Công thức.** Với cửa sổ có a quân của người đi, b quân của đối thủ, đóng góp cho một ô trống trong nó:
```
b = 0:            delta += W[a+1] − W[a];   thắng ngay nếu a + 1 ≥ k
a = 0, b > 0:     delta += W[b];            cần chặn nếu b = k − 1
còn lại:          0
score(m) = WIN nếu có cửa sổ thắng; ngược lại Σ delta + BLOCK nếu có cửa sổ cần chặn
khi đặt quân vào m:  với mỗi cửa sổ w ∋ m, mỗi ô c ∈ w:  điểm[c] += đóng góp_mới(w) − đóng góp_cũ(w)
```

**Ví dụ trace tay** (15×15, k = 5, W = 0, 1, 10, 100, 1000, 10000). Cửa sổ w có 1 quân X, 4 ô trống, X đặt
thêm 1 quân vào w. Với mỗi ô trống c còn lại trong w:
- góc nhìn X đi: trước `W[2] − W[1] = 9`, sau `W[3] − W[2] = 90` → `delta_X[c] += 81`;
- góc nhìn O đi: trước O đặt vào c xóa cửa sổ 1 quân X (`W[1] = 1`), sau xóa cửa sổ 2 quân (`W[2] = 10`) →
  `delta_O[c] += 9`.
Một nước đi động tới ≤ 20 cửa sổ × 5 ô × 2 góc nhìn = 200 phép cộng, thay vì ~100 candidate × 20 cửa sổ ×
5 ô = 10 000 lượt đọc ô.

## Test
- File: `tests/test_kinrow_rollout.py` — điểm từng bước = `move_score` trên 15×15, 7×7 k=4, 5×5 k=4, 3×3
  (tới hết ván); trường hợp ô trống cuối (hòa); đe dọa nằm xa 2 nước cuối (X thắng / O chặn); **cùng seed →
  cùng chuỗi nước** với `HeavyRollout(move_score, T)` ở T ∈ {1, 100, 1000} trên 4 kích thước bàn và từ thế có
  đe dọa; đồng bộ khi đổi ván, undo, undo rồi đi nước khác cùng độ dài, clone; không mutate; T ≤ 0 lỗi;
  **MCTS cùng seed + cùng số iteration cho cùng nước, cùng `last_root_stats()` và stats** (3×3, 15×15, có và
  không `rollout_limit`).
- Đột biến đã thử (không có trong repo): ngưỡng chặn k−2, bỏ cập nhật góc nhìn O, không gỡ nước khi đồng bộ,
  bỏ kiểm tiền tố — mỗi đột biến làm fail test.
- Chạy riêng: `python -m pytest tests/test_kinrow_rollout.py -q` (~2 s).

## Hạn chế / TODO
- Chỉ cho `KInRow` + `move_score` (không dùng `score_fn` khác). Cờ tướng cần policy riêng.
- Phần đồng bộ đầu rollout O(số nước khác nhau); rollout rất ngắn (T nhỏ, giữa ván) chỉ nhanh hơn ~4×.
- Vẫn tính softmax trên mọi candidate mỗi bước (O(b) `exp`) — đủ nhanh, chưa tối ưu thêm.
