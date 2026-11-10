# E2 — MCTS 3×3 có bao giờ thua? — `gameai/experiments/e2_never_lose.py`

> Mục tiêu của file này: agent/thành viên khác dùng được module **mà không cần đọc code**.

**Trạng thái:** 🟡 code + `--quick` xong, **chưa chạy full**  ·  **Task:** E2 (D-16)  ·  **Cập nhật:** 2026-11-10

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

## Phụ thuộc
`experiments/common.py` (`run_match`, `summarize`), `agents/registry.py`, `arena.derive_seed`, `agents/mcts.py`,
`agents/minimax.py`. Test: `tests/test_e2_never_lose.py` (đếm nhánh = thắng+hòa+thua, tất định, chuỗi thua là
thật, seed khác → cây khác, tổng hợp, spec).

## Kết quả quick (KHÔNG phải số liệu báo cáo; chỉ để kiểm pipeline và ước thời gian)
(a) 10 ván/ô: 0 thua vs random ở mọi iter; vs minimax thua 2/10 ở 100 và 250 iter, 0/10 ở 1000 và 5000; vs mcts
thua ≤ 2/10 ở 100–250, 0/10 ở 1000–5000; `distinct_games` 10/10 (9/10 ở 5000 vs mcts).
(b) 2 base_seed × 2 vai: 100 iter 54 nhánh thua / 1239; 250 iter 16 / 1187; 1000 iter 3 / 1132 (1/4 run,
MCTS cầm O, ví dụ `8 2 0 4 6 7 3`); **5000 iter 0 / 1133**. Ngưỡng "vét cạn không thua" có vẻ nằm trên 1000 iter
(ghi chú: kết luận chỉ chốt khi chạy full 10 seed).

## Ước thời gian full (4 worker, từ quick)
(a) ≈ 10–15 phút (Minimax đầy đủ ~1,3 s/nước ở gốc là phần chính); (b) ≈ 7–8 phút (5000 iter ≈ 20–60 s/run,
40 run). Tổng ≈ 20 phút.

## Giải thích cho báo cáo
Không có thuật toán mới; module này là **thiết kế kiểm chứng**. Ván đấu chỉ cho bằng chứng thống kê ("100 ván
không thua"). Vét cạn cho bằng chứng mạnh hơn: vì MCTS tất định theo `(base_seed, thế cờ)`, tập mọi ván có thể
xảy ra khi đối thủ chơi *bất kỳ* nước nào là một cây hữu hạn (≤ 945 lá khi MCTS đi sau, ≤ 384 khi đi trước);
duyệt hết cây và đếm lá thua. 0 lá thua = với seed đó MCTS không thể thua dù đối thủ tối ưu. Giới hạn: kết
luận chỉ cho các `base_seed` đã thử, không phải cho mọi seed.

## Hạn chế / TODO
- Chưa chạy full (chờ duyệt). Chưa có hình; bảng sinh bởi script (P7.1 làm hình nếu cần).
