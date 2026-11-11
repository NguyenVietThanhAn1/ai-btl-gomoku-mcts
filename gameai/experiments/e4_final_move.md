# E4 — Chọn nước cuối: N lớn nhất vs W/N lớn nhất — `gameai/experiments/e4_final_move.py`

> Mục tiêu của file này: agent/thành viên khác dùng được module **mà không cần đọc code**.
> Cập nhật cùng lúc với code.

**Trạng thái:** 🔄 đã chạy quick, chờ duyệt full  ·  **Task:** E4 (D-19)  ·  **Cập nhật:** 2026-11-11

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

## API
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

## File
- Raw: `results/raw/e4_roots_{3x3,15x15}.csv` — 1 dòng/(search, con), `ROOT_COLUMNS`: `board, kind (search/ref),
  c, pos_id, plies, n_moves, moves, iterations, seed, tactic, time` + cột của `root_rows`. Search bị tactic
  đi tắt = 1 dòng không có `move`. `results/raw/e4_match_3x3_i<it>.csv` (+ `_moves`), schema runner.
- `results/tables/e4_roots_summary.csv` (1 dòng/(board, c, tập, iter); tập 3×3: `all` = mọi thế ≥ 2 nước,
  `has_bad` = thế có ≥ 1 nước không tối ưu): `n_positions, n_skipped_tactic, n_differ, differ_rate,
  opt_max_{n,wn,lcb}` (mọi thế), **`differ_opt_max_{n,wn,lcb}` (chỉ số chính: trong các thế max_n ≠ max_wn)**,
  `lcb_eq_max_n`, `max_n_child_N_median`, `max_wn_child_N_{median,max}`, chẩn đoán `children_median`,
  `max_n_wn_is_1`, `max_n_tied_median`. Giá trị tối ưu chỉ có ở 3×3.
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

## Giải thích cho báo cáo
**Bản chất.** Sau khi hết ngân sách, MCTS phải chọn một con của gốc. W/N là ước lượng tỉ lệ điểm của nước;
N là số lần UCT đã chọn nước đó. Với N lượt thăm, độ lệch chuẩn của W/N cỡ √(p(1−p)/N): con 1/1 có W/N = 1,0
nhưng khoảng Wilson 95 % là [0,21; 1] — gần như không có thông tin. Chọn max W/N vì thế dễ chọn con "gặp may".
Chọn max N dựa vào chính UCT: UCT = W/N + c·√(ln N_p / N) cho con có W/N cao **và** N nhỏ điểm cao hơn ở cả
hai hạng, nên nó sẽ được thăm tiếp cho tới khi W/N tụt hoặc N đuổi kịp; con còn giữ được nhiều lượt thăm nhất
là con đã "qua kiểm tra" nhiều lần. N vừa là phiếu bầu vừa có ít phương sai nhất.

**Hệ quả kiểm chứng được.** Chính cơ chế tự kiểm tra lại đó làm hai tiêu chí **thường trùng nhau**; chúng chỉ
lệch khi ngân sách hết ngay sau khi một con ít lượt thăm vừa có kết quả tốt, hoặc khi iter nhỏ hơn số con.
Số liệu và ví dụ trace: điền sau khi chạy full (bảng `e4_roots_*`), không lấy từ thăm dò.

**max_lcb** (cận dưới Wilson lớn nhất) là tiêu chí trung gian: phạt con N nhỏ một cách tường minh; bảng tổng
báo % trùng max_n.

## Test
- `tests/test_e4_final_move.py` (13 test): đếm thế 3×3 (4 520 chưa kết thúc, bỏ thế 1 nước, không trùng key,
  thứ tự); `move_values` khớp dấu Minimax ở thế phải chặn; tie-break `choose_indices` (kể cả mọi con N = 1);
  `root_rows` khớp nước `MCTSAgent` chọn với `max_n`/`max_wn` cùng seed (3×3 và 15×15), ΣN = iter; thế 3×3 có
  nước thắng ngay, tactics tắt, 1000 iter → con thắng W/N = 1 và là max_n; cờ `optimal`; luật ví dụ 3×3
  (rule + trace) và 15×15 (theo c, bỏ thế tactic); bảng tổng + cột chẩn đoán; spec A/B chỉ khác
  `final_move`; match nhỏ + `score_ci`; hình không crash.
- Chạy: `python -m pytest tests/test_e4_final_move.py -q`.

## Hạn chế / TODO
- Thế 15×15 từ playout ngẫu nhiên thường lệch về người đi (W/N bão hòa) — ghi rõ khi báo cáo.
- Phần 1 không song song; full ước tính ở `results/tables/e4quick_estimate.csv`.
