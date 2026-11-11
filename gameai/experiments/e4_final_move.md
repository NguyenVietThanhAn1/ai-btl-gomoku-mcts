# E4 — Chọn nước cuối: N lớn nhất vs W/N lớn nhất — `gameai/experiments/e4_final_move.py`

> Mục tiêu của file này: agent/thành viên khác dùng được module **mà không cần đọc code**.
> Cập nhật cùng lúc với code.

**Trạng thái:** ✅ full xong  ·  **Task:** E4 (D-19)  ·  **Cập nhật:** 2026-11-11

## Mục đích
Đề ý 4: vì sao MCTS chọn nước theo **N lớn nhất** (`final_move="max_n"`) thay vì **W/N lớn nhất**
(`"max_wn"`). Không đổi `MCTSAgent`: dùng `final_move`, `agent.root.children` (thứ tự mở rộng); tiêu chí thứ ba
`max_lcb` (cận dưới Wilson của W/N lớn nhất) tính offline.

| Phần | Thiết lập (D-19) | Output |
|---|---|---|
| `roots` 3×3 | mọi thế chưa kết thúc có ≥ 2 nước (4 298), seed 0, iter {10, 20, 50, 100, 250, 1000}, rollout random, tactics tắt | % thế max_n ≠ max_wn; % chọn nước giữ giá trị trò chơi của từng tiêu chí |
| `roots` 15×15 | 10 thế `e1_nodes.make_position` (6…24 nước) × seed 0–4 × iter {50, 250, 1000}, h300 + tactics; c = 1.4 và **c = 0.5 (độ nhạy, không phải c chuẩn)** | % khác nhau + cột chẩn đoán; ví dụ + tham chiếu 20 000 iter |
| `match` 3×3 | max_n (A) vs max_wn (B), cùng iter {10, 20, 50, 100, 250}, 200 ván/điểm, đổi lượt | **score** của max_n (+ W/L Wilson) |

Đối đầu 15×15 **bỏ** (D-19): ở c chuẩn hai tiêu chí không chọn khác nhau → hai agent đánh như nhau.

## Cách chạy
```
python -m gameai.experiments.e4_final_move all --quick   # roots + match + hình + ước tính (e4quick_*)
python -m gameai.experiments.e4_final_move roots         # full phần 1 (tuần tự, 1 tiến trình)
python -m gameai.experiments.e4_final_move match         # full phần 2 (runner, resume được)
python -m gameai.experiments.e4_final_move plot
```
Cờ chung `--workers` (4), `--allow-code-change`. Quick: 3×3 mỗi thế thứ 15 theo thứ tự chuẩn, iter {10, 100};
15×15 3 thế × seed 0 × iter {50, 250} × 2 c, tham chiếu 5 000 iter; đối đầu 2 cặp/điểm.

## Public API
- `mcts_params(board, iterations, final_move="max_n", c=1.4)`, `mcts_spec(board, iterations, final_move)`
  (nhãn `maxn_i<it>` / `maxwn_i<it>`; A và B chỉ khác `final_move`).
- `choose_indices(children) -> (i_max_n, i_max_wn, i_max_lcb)`: max_n = max (N, W); max_wn = max (W/N, N);
  max_lcb = max (cận dưới Wilson, N); bằng → con mở rộng trước — **đúng như `MCTSAgent._final_child`** (test).
- `search_root(game_spec, moves, iterations, seed, c) -> (agent, giây)`; `agent.root is None` nếu tactic đi tắt.
- `root_rows(agent, base, values=None)`: 1 dòng/con: `W, N, wn, wn_lo, wn_hi, is_max_n, is_max_wn, is_max_lcb,
  value, optimal`.
- `enumerate_3x3(min_moves=2)`: thứ tự chuẩn (số quân, `key`). `move_values(g, cache)`: giá trị trò chơi
  1/0/−1 của từng nước (`e2_never_lose.solve`, memo theo key).
- `summarize_roots(rows)`, `example_positions_3x3(rows)`, `example_searches_15(rows)`, `example_rows(...)`,
  `score_ci(rows, split)`, `plot_match(table, path)`, `estimate_full()`.
- Chạy từng phần: `run_roots(quick)` (`roots_3x3`, `roots_15x15` → raw + bảng tổng + ví dụ),
  `run_matches(quick, workers, allow)` (raw + `e4_match.csv`), `make_figures(quick)`.

## Phụ thuộc
- Dùng: `agents/mcts.py` (`MCTSAgent`, `Node`), `agents/registry.py` (`make_agent`, `make_game`),
  `experiments/common.py` (`run_match`, `summarize`, `wilson`, …), `experiments/e1_nodes.py`
  (`make_position`, `build_game`), `experiments/e2_never_lose.py` (`solve`), `experiments/e3_c_sweep.py`
  (`fit_cost`, `SERIES_COLORS`).
- Được dùng bởi: báo cáo (P7), không module nào import.

## File
- Raw: `results/raw/e4_roots_{3x3,15x15}.csv` — 1 dòng/(search, con), `ROOT_COLUMNS`: `board, kind (search/ref),
  c, pos_id, plies, n_moves, moves, iterations, seed, tactic, time` + cột của `root_rows`. Search bị tactic
  đi tắt = 1 dòng không có `move`. `results/raw/e4_match_3x3_i<it>.csv` (+ `_moves`), schema runner.
- `results/tables/e4_roots_summary.csv` (1 dòng/(board, c, tập, iter); tập 3×3: `all` = mọi thế ≥ 2 nước,
  `has_bad` = thế có ≥ 1 nước không tối ưu): `n_positions, n_skipped_tactic, n_differ, differ_rate,
  opt_max_{n,wn,lcb}` (mọi thế), **`differ_opt_max_{n,wn,lcb}` (chỉ số chính: trong các thế max_n ≠ max_wn)**,
  `lcb_eq_max_n`, `max_n_child_N_median`, `max_wn_child_N_{median,max}`, chẩn đoán `children_median`,
  `max_n_wn_is_1`, `max_n_tied_median`, `max_n_N_tie_rate` (% search có ≥ 2 con cùng N lớn nhất),
  `max_wn_is_1_rate` (% search có W/N lớn nhất = 1,0), `n_wn1_median` / `n_wn1_max` (số con có W/N = 1,0,
  chỉ trên các search đó). Giá trị tối ưu chỉ có ở 3×3.
- `results/tables/e4_roots_examples.csv`: 3×3 (iter 100, max_n ≠ max_wn và max_wn không tối ưu) 3 thế đầu
  (`rule`) + thế ít ô trống nhất (`trace`), mọi con; 15×15 mỗi c 3 search đầu có max_n ≠ max_wn (`rule` /
  `sensitivity`), top-5 theo N + con max_wn/max_lcb, cột `ref_*` = tham chiếu 20 000 iter.
- `results/tables/e4_match.csv` = `board, iterations` + `SUMMARY_COLUMNS` + `score_lo, score_hi`;
  hình `results/figures/e4_match.png`.

## Thiết kế & quyết định (D-19)
- W/N theo góc nhìn **người đi ở gốc** (thắng 1, hòa 0,5, thua 0). Chỉ xét con đã mở rộng (N ≥ 1); nước
  chưa mở rộng không phải con.
- "Tối ưu" = giữ giá trị trò chơi (thắng/hòa/thua), không dùng thang `WIN − ply` (MCTS không chiết khấu độ sâu).
- Wilson của W/N là **xấp xỉ**: có hòa 0,5 nên không nhị thức (Wilson thận trọng vì phương sai ≤ p(1−p)) và
  các lượt thăm UCT không độc lập → chỉ minh họa độ nhiễu, không phải kiểm định. Score: mean ± 1,96·sd/√n.
- **Chẩn đoán 15×15** (D-19, thăm dò): hai tiêu chí trùng vì (i) iter < số ứng viên → mọi con N = 1, luật phá
  hòa của hai tiêu chí chọn cùng con 1/1 đầu tiên; (ii) W/N bão hòa ở 1,0; (iii) UCT dồn lượt thăm vào con
  hoàn hảo → con max-N có W/N = 1 = mức trần → max_wn hòa rồi phá theo N.
- Phần 1 chạy tuần tự (tất định, seed cố định); thời gian từng search ghi ở cột `time`.

## Kết quả full (2026-11-11, chạy ở commit `71344d6`)
Roots 164 s (3×3 42 s, 15×15 120 s gồm 2 tham chiếu 20 000 iter); match 10 s, 1 000 ván, mọi ván `normal`,
`git_dirty = 0`. Bảng: `results/tables/e4_roots_{summary,examples}.csv`, `e4_match.csv`; hình `e4_match.png`.

**3×3, c = 1.4, 4 298 thế ≥ 2 nước (tập `all`).** Chỉ số chính = % chọn nước giữ giá trị trò chơi **trong các
thế max_n ≠ max_wn**:

| iter | thế khác | max_n tối ưu | max_wn tối ưu | max_lcb tối ưu | max_n bị hòa N | W/N lớn nhất = 1 |
|---|---|---|---|---|---|---|
| 10 | 188 (4,4 %) | 0,606 | **0,809** | 0,777 | 0,403 | 0,614 |
| 20 | 113 (2,6 %) | 0,752 | 0,788 | 0,788 | 0,316 | 0,559 |
| 50 | 55 (1,3 %) | 0,818 | 0,836 | 0,800 | 0,194 | 0,531 |
| 100 | 97 (2,3 %) | **0,948** | 0,928 | 0,948 | 0,124 | 0,530 |
| 250 | 112 (2,6 %) | **1,000** | 0,982 | 0,982 | 0,126 | 0,530 |
| 1000 | 112 (2,6 %) | 1,000 | 1,000 | 1,000 | 0,125 | 0,530 |

Tập `has_bad` (3 191 thế có ≥ 1 nước không tối ưu): thế khác 111 / 55 / 25 / 16 / 7 / 0; max_n vs max_wn tối ưu
0,333 vs 0,676 (10), 0,491 vs 0,564 (20), 0,600 vs 0,640 (50), 0,688 vs 0,562 (100), 1,000 vs 0,714 (250).
Trên mọi thế, max_n và max_wn tối ưu gần bằng nhau (0,878/0,886 ở 10 iter → 0,998/0,998 ở 1000). Số con có
W/N = 1 (trên các search có): trung vị 1. Ở 1000 iter, 112 thế khác nhau đều nằm ngoài `has_bad`, tức là thế
mà mọi nước cùng giá trị — chọn nước nào cũng như nhau.

**15×15 (h300 + tactics), 10 thế × 5 seed, 0 search bị tactic đi tắt.**

| c | iter | thế khác | số con (trung vị) | N con max_n (trung vị) | max_n bị hòa N | W/N lớn nhất = 1 | số con W/N = 1 (trung vị / max) |
|---|---|---|---|---|---|---|---|
| 1.4 | 50 | 0/50 | 50 | 1 | 1,00 | 1,00 | 26 / 43 |
| 1.4 | 250 | 0/50 | 96 | 4 | 0,92 | 0,98 | 9 / 39 |
| 1.4 | 1000 | 0/50 | 96 | 20 | 0,76 | 0,80 | 3 / 10 |
| 0.5 | 50 | 0/50 | 50 | 1 | 1,00 | 1,00 | 26 / 43 |
| 0.5 | 250 | 2/50 | 96 | 15 | 0,70 | 0,80 | 4,5 / 38 |
| 0.5 | 1000 | 1/50 | 96 | 60 | 0,54 | 0,64 | 2 / 7 |

Ở c = 1.4 không có thế thỏa luật ví dụ. Ví dụ độ nhạy c = 0.5 (iter 250, seed 0) kèm tham chiếu 20 000 iter
(cùng c, seed 0): thế 12 nước — max_n 67 (11/12 = 0,917 → tham chiếu 185/409 = 0,452), max_wn 97 (11/11 = 1,000 →
90/213 = 0,423); thế 18 nước — max_n 67 (25/28 = 0,893 → 156/620 = 0,252), max_wn 81 (20/21 = 0,952 → 212/816 = 0,260).

**Đối đầu 3×3** (A = max_n, 200 ván/điểm, đổi lượt): score 0,510 [0,445; 0,575] (10 iter), 0,485 [0,423; 0,547]
(20), 0,500 [0,449; 0,551] (50), 0,508 [0,466; 0,549] (100), 0,492 [0,460; 0,525] (250) — mọi khoảng chứa 0,5.
W/D/L của max_n: 89/26/85, 76/42/82, 54/92/54, 37/129/34, 21/155/24. Chênh lệch giữa A=X và A=O (vd. 100 iter:
score 0,660 vs 0,355) là lợi thế đi trước, không phải do tiêu chí. `distinct_games` 199 → 153.

## Giải thích cho báo cáo
**1. Lý thuyết: vì sao chọn N lớn nhất.** Hết ngân sách, MCTS phải chọn một con của gốc. W/N là ước lượng tỉ lệ
điểm của nước, N là số lần UCT đã chọn nước đó. Với N lượt thăm, độ lệch chuẩn của W/N cỡ √(p(1−p)/N): con 1/1
có W/N = 1,0 nhưng khoảng Wilson 95 % là [0,21; 1] — gần như không có thông tin; con 20/21 là [0,77; 0,99]. Chọn
max W/N vì thế dễ chọn con "gặp may". Chọn max N dựa vào chính UCT: `UCT = W/N + c·√(ln N_p / N)`; con có W/N
cao hơn con dẫn đầu **và** N nhỏ hơn có UCT lớn hơn ở cả hai hạng, nên được thăm tiếp cho tới khi W/N tụt hoặc N
đuổi kịp. Con giữ được nhiều lượt thăm nhất là con đã "qua kiểm tra" nhiều lần: N vừa là phiếu bầu của UCT vừa
gắn với ước lượng ít nhiễu nhất. (Wilson ở đây là xấp xỉ: có hòa 0,5 và các lượt thăm không độc lập.)

Ví dụ thật (3×3, iter 100, seed 0; ô đánh số 0–8 theo hàng; X đi):
```
X . .     con   W/N             Wilson 95 %      giá trị
. . O     2     19,5/23 = 0,848 [0,653; 0,943]   thắng   ← max_n
. . .     1     17/20  = 0,850  [0,640; 0,948]   thua    ← max_wn
```
max_wn chọn nước thua chỉ vì W/N cao hơn 0,002 với ít lượt thăm hơn; hai khoảng Wilson gần như trùng nhau.
(Thế `rule` pos 69 trong `e4_roots_examples.csv`.)

Thế `trace` (ít ô trống nhất thỏa luật; pos 435, iter 100, X đi; tổng N = 100):
```
. . X     con   W/N              Wilson 95 %      giá trị
. . O     0     18/25   = 0,720  [0,524; 0,857]   hòa    ← max_n
O X .     4     17,5/24 = 0,729  [0,529; 0,866]   hòa    ← max_wn, max_lcb
          1     16,5/23 = 0,717  [0,513; 0,859]   thắng  (X1 dọa đồng thời ô 0 và ô 4)
          3     11/18   = 0,611  [0,386; 0,797]   hòa
          8     3,5/10  = 0,350  [0,137; 0,646]   thua
```
Trace: N của ba con dẫn đầu chỉ chênh 1–2 lượt, W/N chênh < 0,013 trong khi mỗi khoảng Wilson rộng ~0,33 →
ở 100 iter không tiêu chí nào phân biệt được ba nước; cả max_n và max_wn đều bỏ lỡ nước thắng 1. Kiểm: ΣN =
25 + 24 + 23 + 18 + 10 = 100 = iter.

**2. Thực nghiệm: ưu thế của max N chỉ lộ ở vùng giữa.**
- *Iter ≲ số con* (3×3 10–20 iter, 15×15 50 iter): N ≈ 1–4 ở mọi con, max_n bị hòa N ở 40 % (3×3, 10 iter) tới
  100 % (15×15, 50 iter) số thế, nên nước của max_n thực chất do luật phá hòa (W, rồi thứ tự mở rộng) quyết
  định. Lúc này max_wn tốt hơn: trong các thế hai tiêu chí khác nhau ở 10 iter, max_wn giữ giá trị trò chơi
  0,809 so với 0,606 của max_n.
- *Vùng giữa* (3×3 100–250 iter): đúng như lý thuyết, max_n 0,948 / 1,000 so với max_wn 0,928 / 0,982
  (tập `has_bad`: 0,688 vs 0,562; 1,000 vs 0,714).
- *Iter lớn* (3×3 1000): cả hai đều tối ưu ở mọi thế khác nhau.
- Hai tiêu chí chỉ khác nhau ở 1–4 % số thế, nên trong đối đầu trực tiếp không đo được khác biệt: score của
  max_n 0,485–0,510, mọi khoảng tin cậy chứa 0,5.
- *15×15 h300:* ở c = 1.4 hai tiêu chí trùng ở 150/150 search. W/N lớn nhất = 1,0 ở 80–100 % search; khi con
  max-N có W/N = 1,0 (mức trần), max_wn hòa ở 1,0 và **trong code phá hòa theo N** nên trùng max_n — đây là đặc
  điểm cài đặt (`final_move="max_wn"` dùng khóa (W/N, N)), không phải tính chất của mọi MCTS. W/N = 1,0 ở đây
  **không** có nghĩa là ít nhiễu: ở hai ví dụ (c = 0.5) tham chiếu 20 000 iter cho chính các nước đó W/N chỉ
  0,25–0,47 (vd. 11/11 → 90/213). Ở cây nông, các nước đáp trả mạnh của đối thủ chưa được mở rộng nên W/N lạc quan; cả hai tiêu chí
  cùng chịu sai lệch này. c nhỏ hơn (0.5, độ nhạy) dồn lượt thăm mạnh hơn, W/N của con dẫn đầu rời khỏi 1,0
  sớm hơn, và mới thấy vài thế khác nhau (2/50, 1/50).

**max_lcb** (cận dưới Wilson lớn nhất) phạt con N nhỏ tường minh: trùng max_n ở 96,7–99,0 % thế 3×3; trong
các thế max_n ≠ max_wn, tỉ lệ tối ưu 0,777 (10 iter), 0,788 (20), 0,800 (50), 0,948 (100), 0,982 (250) — không
vượt tiêu chí tốt hơn ở mức iter nào.

**Ghi chú phương pháp cho báo cáo.** Ví dụ 3×3 lấy ở iter 100 — đổi từ 250 sau thăm dò vì ở 250 chỉ 2 thế
thỏa luật (D-19). "Tối ưu" = giữ giá trị thắng/hòa/thua (không chiết khấu độ sâu). Thế 15×15 sinh bằng playout
ngẫu nhiên (như E1), thường lệch về người đi.

## Test
- `tests/test_e4_final_move.py` (13 hàm test, 15 case): đếm thế 3×3 (4 520 chưa kết thúc, bỏ thế 1 nước, không trùng key,
  thứ tự); `move_values` khớp dấu Minimax ở thế phải chặn; tie-break `choose_indices` (kể cả mọi con N = 1);
  `root_rows` khớp nước `MCTSAgent` chọn với `max_n`/`max_wn` cùng seed (3×3 và 15×15), ΣN = iter; thế 3×3 có
  nước thắng ngay, tactics tắt, 1000 iter → con thắng W/N = 1 và là max_n; cờ `optimal`; luật ví dụ 3×3
  (rule + trace) và 15×15 (theo c, bỏ thế tactic); bảng tổng + cột chẩn đoán; spec A/B chỉ khác
  `final_move`; match nhỏ + `score_ci`; hình không crash.
- Chạy: `python -m pytest tests/test_e4_final_move.py -q`.

## Hạn chế / TODO
- Thế 15×15 từ playout ngẫu nhiên thường lệch về người đi (W/N bão hòa) — ghi rõ khi báo cáo.
- Phần 1 chạy tuần tự (full 164 s).
- Không đo `max_wn` phá hòa theo cách khác (vd. ngẫu nhiên) — kết luận 15×15 gắn với cài đặt hiện tại.
