# kinrow_eval — `gameai/heuristics/kinrow_eval.py`

> Mục tiêu của file này: agent/thành viên khác dùng được module **mà không cần đọc code**.
> Cập nhật cùng lúc với code.

**Trạng thái:** ✅ ổn định  ·  **Task:** P2.2  ·  **Cập nhật:** 2026-10-28

## Mục đích
Hàm lượng giá theo pattern cho `KInRow(n, k)`, đối xứng hai bên. Dùng chung cho Alpha-Beta
(P2.4: lá + move ordering), `GreedyAgent` (P2.5) và `HeuristicRollout` (P3.2).

## Public API
```python
def evaluate(game: KInRow, player: int) -> int
def delta_eval(game: KInRow, move: int) -> int
def move_score(game: KInRow, move: int) -> int
def win_score(k: int) -> int        # WIN   = 10**k * 10   (k=5: 1_000_000; k=3: 10_000)
def block_bonus(k: int) -> int      # BLOCK = WIN // 10    (k=5: 100_000)
def windows(n: int, k: int) -> tuple[tuple[int, ...], ...]          # cache
def windows_through(n: int, k: int) -> tuple[tuple[int, ...], ...]  # cache: ô → id cửa sổ
```
- `evaluate(g, p)`: điểm theo góc nhìn `p`. Ván xong: `+WIN` (p thắng) / `-WIN` / `0` (hòa).
  Phản đối xứng: `evaluate(g, X) == -evaluate(g, O)`.
- `delta_eval(g, m)`: **đúng bằng** `evaluate(sau m) − evaluate(trước m)` theo góc nhìn người đang đi.
  Chỉ quét cửa sổ qua `m`; không play/undo, không copy bàn. Nước thắng/hòa cần tổng toàn bàn nên chậm hơn.
- `move_score(g, m)`: điểm **ưu tiên chiến thuật** (không bằng delta): thắng ngay → `WIN`;
  chặn nước thắng ngay của đối thủ → `delta_eval + BLOCK`; còn lại `delta_eval`.
- Yêu cầu: `delta_eval`/`move_score` gọi khi ván chưa kết thúc và `m` là ô trống. Không mutate `game`.

## Phụ thuộc
- Dùng: `games/kinrow.py` (`KInRow`, `cell_of`, `_DIRS`), `core/game.py` (`DRAW`).
- Được dùng bởi: `agents/alphabeta.py`, `agents/greedy.py`, `agents/rollout.py` (chưa có).

## Thiết kế & quyết định
- **Cửa sổ:** mọi đoạn k ô liên tiếp theo 4 hướng, tiền tính theo `(n, k)` (15×15, k=5: 572 cửa sổ;
  mỗi ô nằm trong ≤ 20 cửa sổ). Dựng bằng tọa độ `(r, c)` nên không quấn hàng.
- **Điểm cửa sổ:** chỉ có quân một bên, `c` quân → `W[c] = 10^(c-1)`; có cả hai màu hoặc trống → 0.
- Pattern tự phân cấp, không cần bảng pattern: open-four (2 cửa sổ 4 quân = 2000) > four bị chặn (1000)
  > open-three (3 cửa sổ = 300) > three bị chặn (~100).
- **Bậc của `move_score`:** WIN > BLOCK > delta. Lý do: delta thuần cho nước tạo open-four lớn hơn nước
  chặn four của đối thủ, nên agent chọn theo delta sẽ thua ngay (ví dụ test: tạo open-four +1915, chặn four
  +1143). Biên độ delta thường ≤ 4k·10^(k-2) < BLOCK nên bậc BLOCK luôn trên bậc thường (đúng với k ≤ ~24).
- **Hòa:** nước lấp ô cuối mà không thắng → `evaluate` sau = 0, `delta_eval`/`move_score` xử lý riêng.
- Độ phức tạp: `evaluate` O(#cửa sổ·k) (~2900 phép ở 15×15); `delta_eval`/`move_score` O(4k·k) ≈ 100.

## Dùng cho alpha-beta (P2.4 làm theo)
- Không gọi `evaluate` toàn bàn ở lá. **Cộng dồn `delta_eval` dọc nhánh**: giữ `score` theo góc nhìn
  một bên cố định, mỗi nút con `score += ±delta_eval(game, move)` tính *trước* `play` (O(k²)/nút).
- Terminal dùng **`WIN − depth`** (depth = số nước từ gốc) để ưu tiên thắng nhanh / thua chậm.
- Move ordering: sắp candidate giảm dần theo `move_score`.
- Greedy: chọn `argmax move_score` (tie-break ngẫu nhiên có seed). Rollout: nước thắng/chặn đã có sẵn
  trong bậc của `move_score`.

## Giải thích cho báo cáo
**Bản chất.** Thay vì đếm riêng từng pattern (open-three, four, …), ta xét mọi "cửa sổ" k ô liên tiếp.
Một cửa sổ còn khả năng thành k-in-a-row cho một bên chỉ khi không có quân đối phương; càng nhiều quân
của bên đó trong cửa sổ thì càng gần thắng. Điểm vị trí là tổng điểm các cửa sổ của ta trừ của đối thủ.

**Công thức.**
```
score(cửa sổ w) = +W[a]  nếu w chỉ có a quân của ta (a ≥ 1)
                  −W[b]  nếu w chỉ có b quân của đối thủ (b ≥ 1)
                  0      nếu trống hoặc có cả hai màu
W[c] = 10^(c-1)
evaluate(g, p) = Σ_w score(w)        (ván xong: ±WIN hoặc 0)
```

**Ví dụ trace tay** (15×15, k=5, chỉ xét hàng 7, ba quân X ở cột 6, 7, 8, bàn không còn quân khác):
- Open-three: cửa sổ chứa cả 3 quân là cột 4–8, 5–9, 6–10 → 3 × W[3] = 300; chứa đúng 2 quân: 3–7, 7–11
  → 2 × W[2] = 20; chứa đúng 1 quân: 2–6, 8–12 → 2 × W[1] = 2. Tổng hàng = 322 (toàn bàn 367 khi cộng các
  cửa sổ dọc/chéo 1 quân).
- Three bị chặn (thêm O ở cột 5): chỉ còn cửa sổ 6–10 chứa đủ 3 quân → 100; thêm 7–11 → 10 và 8–12 → 1;
  hàng = 111 (toàn bàn, tính cả quân O: 140). Open-three (367) > three bị chặn (140) như kỳ vọng.
- Chặn vs tấn công: X có open-three, O có four hàng 10 cột 5–8 (đầu cột 4 đã bị X chặn). Ô (10, 9) là nước
  thắng duy nhất của O. `delta_eval`: tạo open-four ở (7, 9) = +1915 > chặn (10, 9) = +1143, nhưng
  `move_score`: chặn = 1143 + 100000 = 101143 > 1915 → chọn chặn.

**Chọn tham số.** Hệ số 10 giữa hai mức `c` liên tiếp để một cửa sổ nhiều quân hơn luôn áp đảo vài cửa sổ
ít quân hơn; WIN = 10·10^k lớn hơn mọi tổng cửa sổ; BLOCK = WIN/10 nằm giữa delta thường và WIN.

## Test
- File: `tests/test_kinrow_eval.py` — bàn trống = 0; hình học 572 cửa sổ (không quấn hàng); ±WIN/hòa 0;
  phản đối xứng trên playout ngẫu nhiên (3×3, 7×7 k=4, 15×15); thứ tự pattern; `delta_eval` khớp
  brute-force play/undo trên nhiều vị trí (4 cỡ bàn) và không mutate; chặn four thắng tạo open-four;
  thắng ngay thắng chặn; 3×3 thắng/chặn.
- Chạy riêng: `python -m pytest tests/test_kinrow_eval.py -q`

## Hạn chế / TODO
- Trọng số chưa tinh chỉnh; chưa có thưởng quyền đi trước hay phân biệt double-three/four-three.
- `move_score` chỉ nhận ra chặn k−1 quân; chặn open-three (nước phòng thủ sớm) chỉ nhờ phần delta.
- Chỉ hỗ trợ `KInRow`; cờ tướng (P8) sẽ có eval riêng.
