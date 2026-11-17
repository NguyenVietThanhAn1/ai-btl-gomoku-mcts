# E6 — Tác dụng `check_tactics` — `gameai/experiments/e6_tactics.py`

> Mục tiêu của file này: agent/thành viên khác dùng được module **mà không cần đọc code**.
> Cập nhật cùng lúc với code.

**Trạng thái:** 🔄 full  ·  **Task:** E6 (D-21)  ·  **Cập nhật:** 2026-11-17

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

**Kết quả:** chưa có full (số liệu báo cáo chỉ từ full).

## Quick (2026-11-17, commit `6e86acc`, không commit file `e6quick_*` — không phải số liệu báo cáo)
- 724 s, **máy chạy pin** → chậm 2,5–5× so với `e5_bench.csv`; thời gian/ước tính bị phóng to (xem D-21).
- Thế: block 1 526 thế khác nhau, win 2 828, open4 2 864 (đúng 1 lần/ván có thắng thua → thế loại 2 luôn là nước
  cuối của người thắng). Bộ full 40 thế/loại theo tầng candidate: block 9 / 27 / 4, win 3 / 23 / 14 (< 60 / 60–100 / > 100).
- Sanity bật 8/8; test checkpoint pass. Choice (4 thế × 2 seed): block rand 0,125 → 0,50, h300 0–0,25; win rand 0 → 1,0
  từ 2 500 iter, h300 thắng ngay 0,25 nhưng không mất thắng 0,75.
- Match 1 cặp/điểm: bản tắt thua 2/2 ở mọi điểm; E3/E5 tái dùng `ok`. Ước tính full trên pin ~191 phút
  (self 5000 ~74, choice ~54, greedy 5000 ~32).

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
