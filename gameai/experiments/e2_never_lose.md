# E2 — MCTS 3×3 có bao giờ thua? — `gameai/experiments/e2_never_lose.py`

> Mục tiêu của file này: agent/thành viên khác dùng được module **mà không cần đọc code**.

**Trạng thái:** ✅ full xong  ·  **Task:** E2 (D-16)  ·  **Cập nhật:** 2026-11-10

## Mục đích
Kiểm chứng đề ý 2: MCTS-UCT không thua trên Tic-Tac-Toe 3×3. Cấu hình: rollout random, c = √2,
`check_tactics=False` (D-14: 3×3 không bật tactics), iteration ∈ {100, 250, 1000, 5000} cho **cả hai phần**
để thấy ngưỡng không thua.

## Cách chạy
```
python -m gameai.experiments.e2_never_lose all --quick     # (a) 5 cặp seed, (b) 2 base_seed
python -m gameai.experiments.e2_never_lose all [--workers 4] [--allow-code-change]
python -m gameai.experiments.e2_never_lose play | exhaustive
```
Quick ghi `results/raw/e2quick_*`, `results/tables/e2quick_*`; full ghi `e2_*`. `play` resume được (runner D-13);
`exhaustive` chạy lại từ đầu (ngắn).

## (a) Ván đấu — `run_play`
Với mỗi iter: MCTS(iter) vs {**minimax**, **random**, **mcts** cùng iter (`mcts<iter>_opp`)}, `2·N_PAIRS` = 100
ván đổi lượt. Minimax **có seed** (`depth=None`, chọn ngẫu nhiên trong các nước bằng giá trị tốt nhất; D-16) để
ván khác nhau. Bảng: `results/tables/e2_play.csv` (`SUMMARY_COLUMNS`, có W/D/L, Wilson, **`distinct_games`**).
Raw: `results/raw/e2_<iter>_vs_<opp>.csv` (+ `_moves`).

## (b) Vét cạn — `exhaustive_check(game, spec, base_seed, mcts_player)`
MCTS đi **đúng 1 nước/thế**: agent dựng mới với `seed = derive_seed(base_seed, repr(game.key()))`, nên nước chỉ
phụ thuộc thế cờ (cây tất định, memo theo `key`). Đối thủ thử **mọi** nước hợp lệ. Mỗi lá (ván kết thúc) là một
*nhánh*; trả về `branches, wins, draws, losses, mcts_decisions, loss_example` (chuỗi nước thua đầu tiên, các ô
nối bằng dấu cách, bắt đầu từ bàn trống). Chạy 10 `base_seed` × 2 vai (MCTS là X / O) × 4 iter.
Raw: `results/raw/e2_exhaustive.csv` (`EXH_COLUMNS`, mỗi dòng một (iter, seed, vai)); tổng theo iter:
`results/tables/e2_exhaustive.csv` (`branches`, `losses`, `runs_with_loss`, `loss_example`).
Số nhánh khác nhau giữa các seed vì MCTS đi khác nhau → cây đối thủ khác nhau.

## API (b) đầy đủ
- `exhaustive_check(game, spec, base_seed, mcts_player) -> dict`: `branches, wins, draws, losses,
  mcts_decisions, loss_example, mistakes` (`{(prefix, move): số nhánh thua}`, nước sai đầu tiên).
- `solve(game, cache) -> int`: minimax hoàn hảo 1/0/−1 cho người đang đi (dùng để tìm nước sai).
  `move_type(m)`: `center|corner|edge|none`.
- `summarize_exhaustive / summarize_by_role / mistake_rows / summarize_mistakes`; `run_exhaustive`,
  `run_extension(rows, quick, workers)` (luật D-16; chạy tự động cuối `exhaustive`/`all`).
- File: raw `e2_exhaustive.csv` (`EXH_COLUMNS`), `e2_exhaustive_mistakes.csv` (`MISTAKE_COLUMNS`: mỗi dòng một quyết
  định sai: iter, seed, vai, ply, prefix, move, loại ô, nước đối thủ vừa đi, số nhánh thua); tables
  `e2_exhaustive.csv`, `e2_exhaustive_by_role.csv` (số seed 0 thua theo vai), `e2_exhaustive_mistakes.csv`
  (gom theo iter/vai/ply/loại ô). Mở rộng (nếu có) dùng hậu tố `_ext`.

## Phụ thuộc
`experiments/common.py` (`run_match`, `summarize`), `agents/registry.py`, `arena.derive_seed`, `agents/mcts.py`,
`agents/minimax.py`. Test: `tests/test_e2_never_lose.py` (đếm nhánh = thắng+hòa+thua, tất định, chuỗi thua là
thật, seed khác → cây khác, tổng hợp, spec).

## Kết quả full (2026-11-10; chạy ~14 phút, 4 worker: (a) 543 s, (b) 290 s)
**(a) 100 ván/cặp, W/D/L của MCTS (`distinct_games`)** — `results/tables/e2_play.csv`:

| iter | vs Minimax | vs Random | vs MCTS cùng iter |
|---|---|---|---|
| 100 | 0/73/27 (95) | 92/5/3 (100) | 22/59/19 (96) |
| 250 | 0/83/17 (89) | 94/5/1 (99) | 11/77/12 (83) |
| 1000 | 0/98/2 (67) | 99/1/0 (96) | 1/98/1 (57) |
| 5000 | 0/100/0 (54) | 98/2/0 (88) | 0/100/0 (30) |

`distinct_games` giảm khi iter tăng (agent mạnh → ít đa dạng): 5000 vs MCTS chỉ 30 chuỗi khác nhau/100 ván, nên
số mẫu hiệu dụng nhỏ hơn 100 (non-loss 100/100, Wilson [0,963; 1]).

**(b) vét cạn** — `results/tables/e2_exhaustive*.csv`. Tổng theo iter (10 seed × 2 vai = 20 run):

| iter | nhánh đã kiểm | nhánh thua | run có thua | seed 0 thua, MCTS=X | seed 0 thua, MCTS=O |
|---|---|---|---|---|---|
| 100 | 6247 | 279 | 13/20 | 7/10 | 0/10 |
| 250 | 5967 | 84 | 10/20 | 10/10 | 0/10 |
| 1000 | 5713 | 7 | 2/20 | 10/10 | 8/10 |
| 5000 | 5674 | **0** | 0/20 | 10/10 | 10/10 |

Phát biểu đúng phạm vi: **"0 nhánh thua trên 10 seed × 2 vai ở 5000 iter"** (5674 nhánh). Luật D-16 mở rộng
(10000/20000) **không kích hoạt** vì 5000 iter không còn nhánh thua. Ví dụ chuỗi thua (1000 iter, MCTS=O, seed 0):
`8 2 0 4 6 7 3`.

**Nước sai đầu tiên** (nước làm giá trị minimax của MCTS tụt khỏi hòa; `e2_exhaustive_mistakes.csv`): gần như
toàn bộ ở vai **O**. Ply 1 (đáp nước mở đầu của X) là chỗ sai chính: 100 iter, O đáp **góc** khi X mở **góc**
(20 quyết định sai, 82 nhánh thua; đúng là đáp tâm), O đáp **cạnh** khi X mở góc (9; 58) hoặc khi X mở tâm (3; 33;
đúng là đáp góc); 250 iter: O đáp góc khi X mở góc 12 quyết định / 39 nhánh; 1000 iter: O đáp góc khi X mở góc 2 / 5, O đáp góc khi X mở cạnh
2 / 2. Ply 3 (nước thứ hai của O) sai ít hơn (vd. 100 iter 15 + 15 quyết định / 37 nhánh). Vai X: chỉ 100 iter có 3
nhánh thua (3 seed).

## Giải thích cho báo cáo
Không có thuật toán mới; module này là **thiết kế kiểm chứng**. Ván đấu chỉ cho bằng chứng thống kê ("100 ván
không thua"). Vét cạn cho bằng chứng mạnh hơn: vì MCTS tất định theo `(base_seed, thế cờ)`, tập mọi ván có thể
xảy ra khi đối thủ chơi *bất kỳ* nước nào là một cây hữu hạn (≤ 945 lá khi MCTS đi sau, ≤ 384 khi đi trước);
duyệt hết cây và đếm lá thua. 0 lá thua = với seed đó MCTS không thể thua dù đối thủ tối ưu. Giới hạn: kết
luận chỉ cho các `base_seed` đã thử, không phải cho mọi seed.

## Hạn chế / TODO
- `(b)` chỉ cho các `base_seed` 0–9 và rollout/c mặc định; không chứng minh cho mọi seed. Chưa có hình; bảng sinh bởi script (P7.1 làm hình nếu cần).
