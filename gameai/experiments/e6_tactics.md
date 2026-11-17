# E6 — Tác dụng `check_tactics` — `gameai/experiments/e6_tactics.py`

> Mục tiêu của file này: agent/thành viên khác dùng được module **mà không cần đọc code**.
> Cập nhật cùng lúc với code.

**Trạng thái:** ✅ full xong  ·  **Task:** E6 (D-21)  ·  **Cập nhật:** 2026-11-17

## Mục đích
Đo tác dụng của bước kiểm tra "thắng ngay / chặn ngay" (`MCTSAgent(check_tactics=True)`) trước khi search, trên
15×15, ngân sách iteration. Thiết kế lại theo D-21 vì PLAN gốc (rand vs Greedy/AB2) kẹt sàn ngay cả khi bật (E5).

| Phần | Đo gì | Output |
|---|---|---|
| (a) bộ thế cờ | tắt tactics: tỷ lệ chọn đúng theo iter {100, 500, 1000, 2500, 5000}, rand và h300, 10 seed/thế; bật: sanity 100 % | `e6_choice.csv`, `e6_sanity.csv`, `e6_choice.png` |
| (b) win rate | `randoff_i1000` vs mref; `h300off_i1000` vs `h300_i1000`; `h300off_iN` vs Greedy (N ∈ {1000, 5000}) | `e6_match.csv`, `e6_paired.csv`, `e6_match.png` |
| (c) chi phí | thời gian `_tactics`, % nước đi thẳng, thời gian/nước bật vs tắt | `e6_cost_check.csv`, `e6_tactic_rate.csv`, `e6_time.csv` |

## Cách chạy
```
python -m gameai.experiments.e6_tactics all --quick   # bench → positions → sanity → choice → match → cost → bảng/hình → ước tính
python -m gameai.experiments.e6_tactics all           # full (hỏi An trước)
python -m gameai.experiments.e6_tactics <step>        # bench | positions | sanity | choice | match | cost | tables
```
Cờ chung `--workers` (4; dùng cho choice và match), `--allow-code-change`. `all` dừng nếu sanity < 100 %.
**Phần (c) (`cost`) chỉ chạy khi cắm sạc (AC)** — không AC thì bỏ qua, không ghi file; nên chạy khi máy rảnh.
Mọi bước ghi một dòng `e6_runinfo.csv` kèm `power` (AC/battery) và `battery_pct`.
Choice và match resume được (choice theo khóa `pos_id, rollout, seed`; match theo `run_match`).

## Public API
- Ô thắng: `is_win_cell(board, n, k, cell, stone)`, `win_cells(game, player) -> set`, `WinTracker(game)` (`.cells[P1/P2]`,
  `.play(move)` cập nhật tăng dần), `classify(mine, opp) -> 'win'|'block'|'open4'|'quiet'`, `keeps_win(game, move)`.
- Thế: `scan_game(moves)`, `extract_positions(raw_dir) -> (cands, counts)`, `select_positions(cands, quick)`,
  `run_positions`, `load_positions`, `position_game`, `correct_set`, `stratum_of(n_cand)`.
- Nguồn/tốc độ: `power_status() -> ('AC'|'battery'|'unknown', % pin)`, `log_run(step, quick, started, t0, **fields)`,
  `run_bench(quick) -> trung vị speed_vs_e5`. Trọng số tầng: `pool_weights(quick) -> {loại: {tầng: w}}`.
- Spec: `spec_off(rollout, iterations)` = `e5_rollout.mcts_spec` với `check_tactics = False`, nhãn `<rollout>off_i<N>`.
- (a): `run_sanity`, `checkpoint_moves(game, agent, checkpoints)` (yield `(k, root, giây)`), `choice_task(pos, rollout,
  seed, checkpoints)`, `run_choice`.
- (b): `MatchPoint`, `match_points()`, `match_raw`, `on_source(pt, quick) -> (source, path, lý do)`, `run_matches`.
- (c): `run_cost`. Bảng: `choice_table(choice, positions, sanity, weights)`, `_weighted_block`, `build_tables`, `_boot_ci`, `_side_rows`; `estimate_full`, `make_figures`.

## File
- Raw (`results/raw/`): `e6_positions.csv` (`pos_id, type ∈ {block, win, quiet}, source, game_id, ply, mover,
  n_candidates, n_mine, n_opp, correct_cells, phase, stratum, moves`), `e6_choice.csv` (1 dòng/(thế, rollout, seed,
  iter): `move, correct, keeps_win` (loại 2), `correct_expanded, n_correct, wn_correct, n_chosen, root_children, time_s`
  (giây search tích lũy), `git_commit, git_dirty`), `e6_<part>_<label_a>.csv` (+ `_moves`), `e6_runinfo.csv`.
- Bảng (`results/tables/`): `e6_positions_summary.csv` (mỗi loại: số lần gặp, số ván, số thế khác nhau, đã chọn, số
  thế mỗi tầng `sel_*`, số thế trong pool mỗi tầng `pool_*`, min/trung vị/max candidate), `e6_bench.csv`,
  `e6_sanity.csv`, `e6_choice.csv` (loại × rollout (`on` = bật) × iter × tầng `all` (trọng số pool) / `sample` /
  `<60` / `60-100` / `>100` / (loại 2) `mine=1` / `mine>=2`: `weighting, n_pos, n_runs, correct_rate`, Wilson (trống ở
  dòng có trọng số), **bootstrap cụm thế** `boot_lo/hi` (dòng `all`: bootstrap phân tầng),
  `pos_all_correct, pos_none_correct`, loại 2 thêm `nolose_*`, `expanded_rate, median_n_correct`), `e6_match.csv`
  (`part, iters, tactics, source, raw` + `SUMMARY_COLUMNS`), `e6_paired.csv` (`mean_on, mean_off, diff` = bật − tắt,
  khoảng cặp/độc lập), `e6_tactic_rate.csv`, `e6_time.csv`, `e6_cost_check.csv`.
- Quick: tiền tố `e6quick_` (không commit), `e6quick_estimate.csv`.

## Thiết kế & quyết định (D-21)
- **Không sửa code agent/game** → điều kiện tái dùng E3/E5 (`e5_rollout.e3_reusable`: spec, game, base_seed, dirty,
  `git diff` code rỗng) vẫn giữ; bản bật của (b) lấy từ `e5_mref_rand_i1000.csv`, `e3_greedy_c1.4_i{1000,5000}.csv`.
- **Ô thắng ngay** của người chơi p = ô trống mà đặt quân p vào tạo ≥ k quân liên tiếp (khớp `KInRow`). Khi replay, chỉ
  xét lại các ô trên 4 đường qua nước vừa đi trong bán kính k − 1 (trạng thái của ô y chỉ đổi khi có quân đặt trên một
  đường qua y trong khoảng đó). Test so với brute force (play/undo cho người đi, quét cả bàn cho đối thủ).
- **Phân loại** thế (người đi = "ta"): ta có ô thắng → `win`; không, đối thủ đúng 1 ô → `block`; đối thủ ≥ 2 ô →
  `open4` (bị loại, đã thua); còn lại `quiet`. Four gãy `XX_XX` tính như four.
- **Lấy mẫu:** mỗi ván ≤ 1 thế/loại (lần đầu; `quiet` mỗi nhóm ply 0–9/10–19/≥ 20 một thế, ply ≥ 4), khử trùng theo
  `key()`, sắp theo sha256(bàn + lượt). Loại 1/2 **phân tầng theo `n_candidates`**: 15 thế/tầng (quick 2) = N đầu của
  tầng → tất định, quick ⊂ full; tầng thiếu thì lấy hết. Thế yên tĩnh 14/nhóm (quick 2).
- **Tỷ lệ chung có trọng số** (D-21): Σ w_s · tỷ lệ tầng s, w_s = tỷ lệ tầng trong pool đầy đủ → ước lượng cho phân bố
  thế thật trong ván E3/E5, dù mẫu lấy đều các tầng. Khoảng: bootstrap phân tầng. `n_mine` = 1 vs ≥ 2 chỉ là phân tầng
  offline (không trọng số).
- **Checkpoint:** `checkpoint_moves` gọi `MCTSAgent._search` nối tiếp trên cùng gốc với `iterations` = phần tăng thêm.
  Vòng lặp chỉ phụ thuộc gốc, `rng`, `c` → nước tại checkpoint k **giống hệt** một lần chạy `iterations = k` cùng seed
  (test `test_checkpoint_equals_separate_runs`, rand và h300). Một task = một cây tới 5000 iter thay vì 5 lần chạy.
- **Seed:** MCTS seed = `derive_seed(seed, pos_id)`, chung cho rand và h300 (so cặp theo thế/seed).
- **Độ đo loại 2:** chính = "thắng ngay"; phụ = "không mất thắng" = thắng ngay ∪ `keeps_win` (sau nước đó đối thủ không
  có ô thắng và ta còn ≥ 2 ô thắng). Điều kiện đủ → cận dưới. Lý do: MCTS không chiết khấu độ sâu (D-11).
- **CI cho (a):** seed trong một thế không độc lập → khoảng chính là bootstrap theo cụm thế (2 000 lần, seed 21);
  Wilson trên n = thế × seed để tham khảo (hẹp giả).
- **Phân tầng `n_candidates`** < 60 / 60–100 / > 100 (sanity D-14: ~58 candidate chặn 5/5, ~100 candidate 0/5 ở 5000
  iter): con đúng phải được mở rộng và được thăm đủ; số con của gốc càng nhiều thì càng chậm.
- **c2:** bỏ nước ply 0 (bàn trống có 1 candidate → `_tactics` cho `|S| = 1` → tactic 2 "giả"), đếm riêng `n_ply0`.
- **c3:** `agent_time` trong ván đấu 4 worker → nhiễu; số chính về overhead là microbench đơn luồng c1.

## Giải thích cho báo cáo
**`check_tactics` làm gì.** Trước khi search, MCTS kiểm hai điều chỉ bằng `play`/`undo` (nên dùng được cho mọi trò chơi):
```
check_tactics(s):
    C = candidates(s)
    với m ∈ C: nếu play(s, m) thắng → đi m                      # tactic 1: thắng ngay
    S = {m ∈ C : sau m, không nước đáp r ∈ candidates nào làm đối thủ thắng}
    |S| = 1  → đi nước duy nhất trong S                         # tactic 2: chặn ngay
    0 < |S| < |C| → search chỉ trên S                            # tactic 3 (k-in-row không xảy ra)
    còn lại → search bình thường
```
Chi phí O(|C|²) lần play/undo (chặn sớm khi gặp nước thắng của đối thủ).

**Vì sao MCTS thuần (tắt tactics) bỏ sót four.** Ở gốc 15×15 có ~50–150 con. Một nước *không chặn* chỉ bị phạt khi
nút con của nó đã mở rộng đúng nước thắng của đối thủ — mở rộng chọn ngẫu nhiên trong ~50–150 nước chưa thử, nên cần
cỡ hàng chục lượt thăm *mỗi con* trước khi nhánh sai bị bác bỏ. Trong khi đó rollout random chọn trúng ô thắng của
đối thủ với xác suất ~1/|C| mỗi bước → W/N của nước sai vẫn cao. Với 1000 iter, mỗi con được ~10 lượt → hiếm khi
thấy được đe dọa (mcts.md: chặn 0/10 seed ở 1000 iter, 2/10 ở 5000 iter trên thế `BLOCK15`). Rollout heavy chặn/thắng
ngay trong rollout nên ước lượng tốt hơn, nhưng vẫn phải chờ cây mở rộng nước đáp trả.

**Ví dụ (trace).** Thế loại 1 có 100 candidate, 1000 iter: gốc mở rộng hết 100 con sau 100 iter; 900 iter còn lại
chia cho 100 con → ~9 lượt/con. Con "không chặn" X_j cần mở rộng ô thắng w của đối thủ trong số ~100 nước chưa thử:
xác suất trong 9 lần mở rộng ≈ 9/100. Nên ~91 % con sai chưa từng thấy w; W/N của chúng ≈ W/N của con chặn → chọn
theo N gần như ngẫu nhiên. `check_tactics` giải quyết bằng 100 × 100 = 10⁴ play/undo (~vài chục ms), rẻ hơn nhiều so
với số iteration cần để search tự thấy.


## Quick lần 2 (2026-11-17, commit `d8f09af`, AC, thiết kế sau sửa D-21)
88 s; bench / `e5_bench` = 0,98; sanity 12/12; ước tính full ~23 phút (thực tế 24). File `e6quick_*` của lần 1 đã xóa.

## Quick lần 1 (2026-11-17, commit `6e86acc`, **pin**, thiết kế cũ 40 thế/loại — đã thay)
- 724 s, **máy chạy pin** → chậm 2,5–5× so với `e5_bench.csv`; thời gian/ước tính bị phóng to (xem D-21).
- Thế: block 1 526 thế khác nhau, win 2 828, open4 2 864 (đúng 1 lần/ván có thắng thua → thế loại 2 luôn là nước
  cuối của người thắng). Bộ full 40 thế/loại theo tầng candidate: block 9 / 27 / 4, win 3 / 23 / 14 (< 60 / 60–100 / > 100).
- Sanity bật 8/8; test checkpoint pass. Choice (4 thế × 2 seed): block rand 0,125 → 0,50, h300 0–0,25; win rand 0 → 1,0
  từ 2 500 iter, h300 thắng ngay 0,25 nhưng không mất thắng 0,75.
- Match 1 cặp/điểm: bản tắt thua 2/2 ở mọi điểm; E3/E5 tái dùng `ok`. Ước tính full trên pin ~191 phút
  (self 5000 ~74, choice ~54, greedy 5000 ~32).

## Kết quả full (2026-11-17, commit `d8f09af`)
Thời gian thực **1 433 s ≈ 24 phút** (dòng `tổng` trong `results/e6_full.log`; runinfo 10:20:47 → 10:44:35 = 1 428 s), **cắm sạc (AC) suốt** mọi bước, `git_dirty = 0`
(`results/raw/e6_runinfo.csv`). Bench đầu full: tốc độ / `e5_bench.csv` = 0,98–1,03 (trung vị 0,99) → máy ở trạng thái
như E5. Choice 1 800 task 667 s (4 worker); match 4 điểm mới 699 s; cost 50 s (đơn luồng). 200 ván mới, 0 lỗi,
`distinct_games` 50/50 (49/50 ở `h300off_i1000` vs Greedy). Bản bật lấy từ E5/E3 (`source`, điều kiện tái dùng `ok`).

**Bộ thế** (`e6_positions_summary.csv`): từ 2 870 ván, pool sau khử trùng block 1 526 (tầng < 60 / 60–100 / > 100:
413 / 989 / 124 → trọng số 0,27 / 0,65 / 0,08), win 2 828 (180 / 2 015 / 633 → 0,06 / 0,71 / 0,22). Chọn 15/tầng =
45 thế/loại; loại 2: `n_mine` = 1 ở 22 thế, ≥ 2 ở 23; 14 thế đối thủ cũng có ô thắng. Thế loại 2 luôn là nước cuối của
người thắng (mọi agent nguồn đều thắng ngay / chặn four đơn). **Sanity bật: 90/90.**

**(a) Tỷ lệ chọn đúng khi tắt tactics** (dòng `all` = có trọng số pool, [bootstrap phân tầng 95 %]; 10 seed/thế):

| iter | block rand | block h300 | win rand: thắng ngay | win h300: thắng ngay | win h300: không mất thắng |
|---|---|---|---|---|---|
| 100 | 0,03 [0,01; 0,06] | 0,50 [0,40; 0,61] | 0,05 [0,03; 0,07] | 0,27 [0,17; 0,40] | 0,54 [0,40; 0,70] |
| 500 | 0,08 [0,05; 0,11] | 0,22 [0,12; 0,34] | 0,74 [0,66; 0,81] | 0,28 [0,17; 0,40] | 0,55 [0,40; 0,71] |
| 1000 | 0,12 [0,08; 0,16] | 0,14 [0,06; 0,25] | 0,97 [0,95; 0,99] | 0,28 [0,17; 0,40] | 0,55 [0,40; 0,71] |
| 2500 | 0,26 [0,20; 0,33] | 0,13 [0,05; 0,24] | 1,00 | 0,29 [0,18; 0,41] | 0,56 [0,42; 0,71] |
| 5000 | 0,38 [0,30; 0,46] | 0,48 [0,36; 0,61] | 1,00 | 0,39 [0,26; 0,54] | 0,66 [0,51; 0,81] |
| bật | 1,00 | 1,00 | 1,00 | 1,00 | 1,00 |

win rand "không mất thắng": 0,24 / 0,87 / 1,00 / 1,00 / 1,00.
- **Theo tầng `n_candidates`** (5000 iter, block): rand < 60: 0,48, 60–100: 0,36, > 100: 0,17; h300 0,97 [0,94; 1,00] /
  0,31 / 0,15. Win rand 500 iter: 0,98 / 0,87 / 0,29. Càng nhiều candidate càng chậm, đúng như sanity D-14.
- **Theo `n_mine`** (win, h300): `n_mine ≥ 2` "không mất thắng" 0,99–1,00 ở mọi iter trong khi "thắng ngay" chỉ
  0,44–0,47 → h300 chọn một nước thắng chắc khác (D-11). `n_mine = 1`: thắng ngay 0,12 (100–1000 iter), 0,17 (2500),
  0,49 (5000); "không mất thắng" 0,15–0,53 — nhưng `keeps_win` chỉ là điều kiện đủ nên **không** kết luận được h300
  đánh rơi thắng ở các thế này.
- **block h300 không đơn điệu** (0,50 → 0,14 → 0,48) — đã kiểm chứng bằng chạy lại cây, xem mục "Kiểm chứng cơ chế"
  bên dưới (`e6_mechanism.py`).

## Kiểm chứng cơ chế block h300 (P7.1, 2026-11-17; `e6_mechanism.py`)
Chạy lại đúng 900 cây block (45 thế × 10 seed × rand/h300), **khớp `e6_choice.csv` 100 %** (4 500 checkpoint), không
ván mới; dự đoán ghi ở D-21 trước khi chạy, áp dụng chính cho nhóm **chọn sai** (`correct = 0`). Số: trung bình
[bootstrap cụm thế 95 %], `results/tables/e6_mechanism.csv`, hình `results/figures/e6_mechanism.png`.

| Bước | Dự đoán | Số đo (h300, trừ khi ghi khác) | Kết luận |
|---|---|---|---|
| 100 iter (a) | rollout heavy phạt nước không chặn: tỷ lệ con sai có W = 0 cao (≥ ~0,8), cao hơn rõ rand | mọi lần chạy 0,73 [0,64; 0,82] vs rand 0,55 [0,53; 0,57]; nhóm chọn sai 0,81, chọn đúng 0,66 | **một phần**: cao hơn rand rõ (khoảng tách), nhưng dưới ngưỡng 0,8 ở số gộp |
| 100 iter (b) | lần chọn sai: nước sai "thoát phạt" (W/N > 0), ô chặn ít lượt (N ≤ 2); lần chọn đúng: N ô chặn > N mọi con sai | chọn sai: W/N > 0 chỉ 61 % (W/N TB 0,31 [0,23; 0,39]); N ô chặn trung vị 1, **W/N ô chặn 0,17** [0,11; 0,24]. Chọn đúng: N ô chặn > max N con sai 68 %, W/N ô chặn 0,95 | **một phần**: lần sai ở 100 iter chủ yếu do **rollout đầu tiên của chính ô chặn thua** (W/N ≈ 0 → không được thăm lại), không phải do nước sai thoát phạt |
| 1000 iter | nước sai được chọn W/N ≈ 0,6 (0,5–0,7) và ≥ W/N ô chặn; ô thắng của đối thủ hiếm khi đã mở (< ~0,3) | W/N nước sai được chọn **0,90** [0,86; 0,93]; ≥ W/N ô chặn ở 100 % lần (ô chặn 0,65 [0,58; 0,71]); đã mở ô thắng 0,20 [0,11; 0,29] | **khớp cơ chế, không khớp độ lớn**: nước sai trông còn tốt hơn dự đoán (~0,9 chứ không ~0,6) |
| 5000 iter | ô thắng đối thủ được mở dưới nước sai (tăng rõ so với 1000); khi đã mở, W/N nước sai thấp hơn | đã mở 0,20 → **0,97** [0,91; 1,00] (chọn sai), gộp 0,16 → 0,96; W/N nút sai top khi đã mở 0,69 vs chưa mở 0,94; W/N nước sai được chọn 0,90 → 0,70 | **khớp** |

Đọc thêm: tỷ lệ đã mở tăng mạnh từ 2 500 iter (0,76 ở nhóm chọn sai) nhưng tỷ lệ đúng vẫn 0,13 — nút bác bỏ mới có
trung vị 2 lượt, W/N nước sai mới giảm về 0,83; ở 5 000 iter (trung vị 3) W/N nước sai 0,70 vẫn > ô chặn 0,60 trong
nhóm chọn sai → việc bác bỏ mới bắt đầu, nên chỉ ~½ lần chọn đúng. Rand có quỹ đạo mở ô thắng tương tự (0,21 → 0,83)
nhưng W/N ô chặn ≈ 0,47–0,49 ở mọi iter (rollout random không phân biệt) → chỉ cây mới sửa được, tăng đơn điệu chậm.
**Kết luận cho báo cáo:** đường chữ U của h300 = (100 iter) rollout heavy đánh giá đúng ngay từ 1–2 lượt thăm (phạt nước
không chặn, thưởng ô chặn) → (500–2 500) cây con của nước sai mở các nước đáp **không** phải ô thắng, rollout heavy từ
đó cho ta tự chặn → nước sai W/N ≈ 0,9, hút lượt thăm → (5 000) ô thắng của đối thủ được mở dưới nước sai, W/N của nó
giảm. `check_tactics` bỏ qua cả quá trình này bằng một phép kiểm O(|C|²).

**(b) Win rate** (50 ván, Wilson 95 %; so cặp theo `game_id`, d = bật − tắt):

| Điểm | tắt | bật | d [cặp 95 %] |
|---|---|---|---|
| rand 1000 vs mref | 0,46 [0,33; 0,60] | 0,50 [0,37; 0,63] (E5) | +0,04 [−0,10; 0,18] |
| h300 1000 vs Greedy | 0,10 [0,04; 0,21] | 0,48 [0,35; 0,62] (E3) | **+0,38** [0,23; 0,53] |
| h300 5000 vs Greedy | 0,30 [0,19; 0,44] | 0,92 [0,81; 0,97] (E3) | **+0,62** [0,47; 0,77] |
| h300 1000 tắt vs bật (đối đầu) | 16/50 | **34/50 = 0,68** [0,54; 0,79] | — |

Tactics quan trọng khi đối thủ biết tạo và kết thúc đe dọa (Greedy, h300 bật); vs mref (MCTS rollout random, ít tạo
four có chủ đích) không thấy khác biệt.

**(c) Chi phí** (c1 đơn luồng, AC):
- Một lần `_tactics`: thế loại 1 trung vị 13,3 ms (max 56), loại 2 0,15 ms (dừng ở nước thắng đầu tiên), thế yên tĩnh
  27,4 ms (max 98,5; trung vị 72 candidate; ~5,4 µs/candidate²). Theo giai đoạn (yên tĩnh): ply 0–9 10,7 ms, 10–19
  31,3 ms, ≥ 20 46,6 ms.
- So với MCTS 1000 iter tắt tactics trên cùng thế yên tĩnh: **overhead trung vị 7,3 % (rand, max 22,8 %), 4,4 %
  (h300)**; theo giai đoạn rand 2,6 / 7,3 / 12,0 %.
- c2 — nước đi thẳng (bỏ ply 0): rand 1000 vs mref 6,1 % (25 thắng + 16 chặn / 672); h300 1000 đối đầu 17,2 %; h300 vs
  Greedy 21,3 % (1000) và 31,0 % (5000). Tactic 3 (restrict) = 0 mọi nơi (đúng thiết kế k-in-row).
- c3 — `agent_time` trung bình/nước tắt vs bật: vs mref 0,46 vs 0,44 s; đối đầu 1000 0,66 vs 0,61 s; vs Greedy 1000
  0,69 vs 1,18 s, 5000 3,33 vs 3,28 s. Nước đi thẳng 5–25 ms. Bản bật vs Greedy là ván E3 (chạy lúc khác, thế cờ khác)
  → chỉ tham khảo; số overhead chính là c1.

## Phụ thuộc
`experiments/common.py` (`run_match`, `summarize`, `read_rows`, `moves_path_for`, `add_runner_args`, `git_info`,
`wilson`), `experiments/e5_rollout.py` (`mcts_spec`, `MREF`, `e3_reusable`, `paired_diff`, `phase_of`, `_keep_pairs`,
`_write`, `_append_csv`, `cpu_name`, `fnum`, style hình), `experiments/e3_c_sweep.py` (`GAME15`, `GREEDY`),
`agents/mcts.py` (`MCTSAgent._search/_final_child/_tactics`, `Node` — dùng nội bộ, không sửa), `agents/registry.py`,
`arena.derive_seed`, `games/kinrow.py`, matplotlib (Agg).

## Test
`tests/test_e6_tactics.py`: `WinTracker`/`win_cells` = brute force trên playout ngẫu nhiên (cả hai bên); phân loại
block / open4 / four gãy / win / quiet trên thế dựng tay; `keeps_win`; `stratum_of`; trích thế tất định + khử trùng + ≤ 1
thế/ván/loại + bỏ file quick + quick ⊂ full; **checkpoint = chạy riêng `iterations = k`** (rand, h300, 2 seed, so nước,
số con gốc, iterations); `choice_task`; sanity bật (tactic 2 / 1); spec bật trùng E3/E5, spec tắt chỉ khác
`check_tactics`; điểm match + đường dẫn duy nhất; bootstrap tất định; `choice_table` (tầng, "không mất thắng", dòng
`on`); `_side_rows` bỏ ply 0. Chạy: `python -m pytest tests/test_e6_tactics.py -q`.

## Hạn chế / TODO
- `keeps_win` chỉ bắt thắng chắc kiểu "≥ 2 ô thắng sau 1 nước"; thắng chắc sâu hơn không được tính.
- c3 đo trong ván song song 4 worker; bản bật Greedy lấy từ E3 (chạy ở thời điểm khác) → so thời gian chỉ tham khảo.
