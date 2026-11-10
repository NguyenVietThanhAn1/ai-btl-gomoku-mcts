# E1 — Alpha-Beta tiết kiệm bao nhiêu nút? — `gameai/experiments/e1_nodes.py`

> Mục tiêu của file này: agent/thành viên khác dùng được module **mà không cần đọc code**.
> Cập nhật cùng lúc với code.

**Trạng thái:** ✅ full đã chạy (2026-11-10)  ·  **Task:** E1 (D-17)  ·  **Cập nhật:** 2026-11-10

## Mục đích
Đo số nút / thời gian của Minimax thuần so với Alpha-Beta (không ordering, có ordering, ordering + TT) và
kiểm AB cho **cùng giá trị gốc và nước đi** như Minimax (đề ý 1).

## Public API
```python
G3, G15: GameSpec; VARIANTS_3: dict[str, AgentSpec]
def variants_15(depth: int) -> dict[str, AgentSpec]      # depth 2 có thêm minimax, ab_evalonly
def make_position(game_spec, plies) -> tuple[list[int], int]   # (chuỗi nước, seed)
def build_game(game_spec, moves) -> Game
def measure(spec, game, repeats) -> (kết quả, trung vị thời gian, root_values | None)
def run_position(board, pos_id, game_spec, moves, depth, variants, repeats,
                 skip_minimax=False) -> list[dict]       # 1 dòng / biến thể
def summarize(rows) -> list[dict]                        # 1 dòng / (bàn, depth, biến thể)
def run(quick: bool) -> list[dict]                       # ghi 3 CSV
```

## Chạy
```
python -m gameai.experiments.e1_nodes --quick   # 2 thế/bàn, 1 lần đo, ghi e1quick_* (~5 s)
python -m gameai.experiments.e1_nodes           # full, ~1 phút (59 s đo được), ghi e1_*
```
Chạy **tuần tự** (không song song) vì có đo thời gian. Không dùng `run_match`/arena (không có ván đấu).

## Thiết lập
- **3×3 (k=3), tìm tới kết thúc** (`depth=None`): bàn trống + 5 thế sau 2, 3, 4, 5, 6 nước.
  Biến thể: `minimax`; `ab` (không tùy chọn); `ab_order` (`order=move_score`); `ab_order_tt` (+ `use_tt`).
- **15×15 (k=5)**, `eval=evaluate`: 5 thế sau 6, 10, 14, 18, 22 nước (X đi), depth 2 và 3.
  Biến thể: `ab` (`delta=delta_eval`, không ordering); `ab_order` (+ `order=move_score`); chỉ depth 2 thêm
  `minimax` (eval ở lá, không delta) và `ab_evalonly` (AB eval ở lá, không delta, không ordering — để tách
  tác dụng của `delta_eval` khỏi cắt tỉa khi so **thời gian** với Minimax). **Minimax depth 3 không chạy**
  (~10⁶ nút × eval toàn bàn). Nếu Minimax depth 2 một thế > 60 s thì bỏ các thế còn lại (không xảy ra:
  0,5–2,2 s/thế).
- **Thế cờ cố định:** playout ngẫu nhiên trên `candidate_moves()`, seed nhỏ nhất ≥ 0 cho ván chưa kết thúc
  sau đúng số nước (`make_position`). Toàn bộ chuỗi nước ghi ở `e1_positions.csv`. Lưu ý: ở cả hai bàn,
  seed 0 cho mọi thế → **các thế lồng nhau** (thế sau = thế trước + thêm nước), không độc lập.
- Tất cả `seeded=False` (tất định): nước chọn = nước tốt nhất đầu tiên theo thứ tự duyệt.
- Thời gian = trung vị 3 lần (`stats["time"]`, agent dựng mới mỗi lần); nếu lần đầu > 5 s thì chỉ 1 lần.
  `nodes` phải giống nhau mọi lần (assert).

## Output (`results/tables/`)
- `e1_nodes.csv` — mỗi (thế, biến thể) một dòng: `nodes, time, cutoffs, tt_hits, value, move`,
  `value_same_as_minimax`, `move_same_as_minimax`, `move_optimal` (nước chọn có giá trị minimax gốc = giá
  trị tối ưu; chỉ khi có Minimax cùng thế), `nodes_saving_vs_minimax_pct`, `time_saving_vs_minimax_pct`,
  `*_vs_ab_*` (so với `ab` cùng thế, cho `ab_order`/`ab_order_tt`). Tiết kiệm % = 100·(1 − x/ref); **âm =
  chậm/nhiều hơn**. Ô trống = không áp dụng.
- `e1_summary.csv` — mỗi (bàn, depth, biến thể): tổng nút/thời gian; tiết kiệm **gộp** (1 − Σx/Σref, bị
  thế nặng chi phối) và **trung bình** theo thế; đếm "k/n" giá trị/nước giống.
- `e1_positions.csv` — chuỗi nước từng thế.
- Báo cáo nên nêu cả gộp và trung bình, và bảng thế bàn trống riêng (549 946 → 20 866 → 1 856 → 990 nút).

## Kết quả full (đọc từ `e1_summary.csv`, `e1_nodes.csv`)
- **Đúng đắn:** giá trị gốc của AB (cả 3 biến thể) = Minimax ở 6/6 thế 3×3 và 5/5 thế 15×15 depth 2;
  ở 15×15 depth 3 giá trị `ab` = `ab_order` ở 5/5 (không có Minimax để so). **Nước đi:** `ab` = Minimax 6/6;
  `ab_order`, `ab_order_tt` chỉ **3/6** *giống hệt* nước của Minimax ở 3×3 nhưng **6/6 tối ưu** (giá trị
  minimax của nước chọn = giá trị gốc): khác nhau chỉ vì hòa giá trị + thứ tự duyệt khác (ordering đổi nước
  đầu tiên trong nhóm bằng điểm). 15×15 depth 2: cả 5/5 nước giống Minimax.
- **3×3:** nút so với Minimax — gộp: `ab` −96,13 %, `ab_order` −99,60 %, `ab_order_tt` −99,76 %;
  trung bình theo thế: −63,49 / −78,78 / −79,45 % (thế gần cuối ván Minimax đã nhỏ nên % thấp). Bàn trống:
  549 946 → 20 866 → 1 856 → 990. Ordering so với `ab`: gộp −89,59 %; thêm TT: −93,91 %.
- **15×15 depth 2:** nút Minimax 46 825 → `ab` 21 612 (−53,85 %) → `ab_order` 1 416 (−96,98 %; −93,45 % so với `ab`).
  **Thời gian:** Minimax 7,01 s → `ab_evalonly` 3,69 s (−47,3 %: tác dụng thuần của cắt tỉa) → `ab` 0,247 s
  (−96,5 %: cộng `delta_eval`) → `ab_order` 0,265 s: **ordering giảm 93 % nút nhưng không giảm thời
  gian** (−7,5 % so với `ab`, tức chậm hơn) vì `move_score` phải chấm mọi nước ở mọi nút mở rộng.
- **15×15 depth 3:** `ab` 553 574 nút / 5,46 s → `ab_order` 48 504 nút (−91,24 %) / 1,26 s (−76,98 % thời gian).
  Ordering bắt đầu có lợi về thời gian khi cây đủ sâu.

## Giải thích cho báo cáo
- Minimax duyệt hết cây (O(b^d)); Alpha-Beta cắt nhánh không thể đổi quyết định nhưng **không đổi kết quả**
  — vì vậy đo "giống nhau" là kiểm tra đúng đắn chứ không phải kết quả thí nghiệm.
- Số nút tốt nhất lý thuyết O(b^(d/2)) khi nước tốt xếp trước; ordering bằng `move_score` (thắng/chặn
  trước, rồi theo delta) tiến gần giới hạn này (15×15 depth 2: 21 612 → 1 416 nút).
- Chi phí ordering là O(b) lần `move_score` mỗi nút mở rộng → tiết kiệm nút ≠ tiết kiệm thời gian ở cây nông.
- TT lợi ở 3×3 vì có nhiều chuyển vị (cùng thế từ các thứ tự nước khác nhau); ở 15×15 depth ≤ 3 không đo.
- Nước đi "khác nhau" giữa hai thuật toán khi có nhiều nước cùng giá trị tối ưu không phải lỗi: kiểm bằng
  `move_optimal`.

## Phụ thuộc
- Dùng: `agents/{minimax,alphabeta,registry}.py`, `heuristics/kinrow_eval.py` (qua registry), `games/kinrow.py`.
- Được dùng bởi: P7.1 (bảng/hình từ `e1_*.csv`).

## Test
- `tests/test_e1_nodes.py` (~5 s): thế cố định tất định và chưa kết thúc; 3×3 giữa ván — giá trị bằng nhau,
  `move_optimal`, AB < Minimax, ordering < AB, công thức % khớp; 15×15 depth 2 `ab` = `ab_evalonly` < Minimax
  về nút, mọi giá trị bằng nhau, depth 3 không có Minimax, `skip_minimax`; `summarize` gộp ≠ trung bình.

## Hạn chế / TODO
- Chỉ 5 thế/bàn và **lồng nhau** (cùng playout seed 0); tiết kiệm phụ thuộc thế. Không có CI.
- Thời gian đo trên một máy, không cô lập tải; trung vị 3 lần giảm nhiễu nhưng không loại bỏ.
- TT không đo ở 15×15; Minimax depth 3 ở 15×15 không đo.
