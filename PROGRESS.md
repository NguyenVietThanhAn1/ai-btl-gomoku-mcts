# PROGRESS — BTL AI Bài 1

> Single source of truth cho tiến độ. Cập nhật **cuối mỗi task / mỗi phiên** (`/wrap-up`).
> Ký hiệu: ⬜ chưa làm · 🔄 đang làm · ✅ xong · ⛔ bị chặn
> Định nghĩa task: xem `PLAN.md`.

## Đang ở đâu (đọc mục này trước tiên)

- **Task hiện tại:** chưa chọn (E1 ✅, E2 ✅; P4.3 hoãn, gộp với P6)
- **Việc đang dở:** —
- **Bước tiếp theo:** `/next-task` → E3 (c sweep) hoặc task kế tiếp. Cấu hình heavy cho E5 (sơ bộ, P3.3): **h300** = `rollout="heavy_kinrow"`, `temperature=300`, không cắt rollout; mọi MCTS 15×15 bật `check_tactics=True` (D-14). Báo iteration ở E3/E5 dùng cột `*_search_iterations_per_move` (D-15): `summarize(rows, read_rows(moves_path_for(path)))`.
- **Cảnh báo / blocker:** theo P3.3, vs AB2 MCTS 0,5 s gần 0% (≤ 2/20 ở mọi cấu hình) → E3/E5 15×15 cần đối thủ phân biệt được cấu hình (kiểu `mrand`, D-14); quyết định khi tới task đó (PLAN E3/E5 hiện ghi AB2 — cần sửa lúc đó). (D-11 "Done P3 — thắng ngay" đã được duyệt 2026-11-10.)

## Bảng trạng thái

| ID | Task | Trạng thái | Owner | Cập nhật | Ghi chú |
|---|---|---|---|---|---|
| P0.1 | Repo, venv, skeleton | ✅ | An | 2026-10-28 | spec-reviewer PASS |
| P1.1 | core/game.py interface | ✅ | An | 2026-10-28 | spec-reviewer PASS; quyết định ở D-5 |
| P1.2 | games/kinrow.py | ✅ | An | 2026-10-28 | spec-reviewer PASS |
| P2.1 | Agent base + Random | ✅ | An | 2026-10-28 | spec-reviewer PASS |
| P2.2 | Heuristic eval k-in-row | ✅ | An | 2026-10-28 | spec-reviewer PASS; quyết định ở D-8 |
| P2.3 | Minimax | ✅ | An | 2026-11-04 | spec-reviewer PASS |
| P2.4 | Alpha-Beta | ✅ | An | 2026-11-04 | spec-reviewer PASS; quyết định ở D-9 |
| P2.5 | Greedy agent | ✅ | An | 2026-11-04 | spec-reviewer PASS |
| P3.1 | MCTS-UCT (+ RandomRollout, HeavyRollout bản đúng) | ✅ | An | 2026-11-10 | spec-reviewer PASS; phạm vi/quyết định ở D-11 |
| P3.2 | Tăng tốc HeavyRollout (+ test tương đương) | ✅ | An | 2026-11-10 | spec-reviewer PASS; D-12; phần chọn tham số tách sang P3.3 |
| P4.1 | Arena + runner song song/CSV/resume | ✅ | An | 2026-11-10 | spec-reviewer PASS; D-13; gộp phần runner của P4.2 cũ |
| P3.3 | Quét sơ bộ T / rollout_limit / scale (heavy) | ✅ | An | 2026-11-10 | spec-reviewer PASS; chọn h300 (sơ bộ); D-12, D-14 |
| P4.2 | Cờ dòng lệnh chung (`--quick`, …) | ✅ | An | 2026-11-10 | `--quick` trong `add_runner_args`; cột `*_search_*` ở `summarize` (D-15); phần runner ở P4.1 (D-13) |
| P4.3 | CLI | ⬜ (hoãn) | An | 2026-11-10 | hoãn, gộp với P6 (yêu cầu của An); D-17 |
| E1 | Nodes Minimax vs AB | ✅ | An | 2026-11-10 | full 59 s; D-17; `e1_*.csv` |
| E2 | 3×3 never lose | ✅ | An | 2026-11-10 | spec-reviewer PASS; full xong; D-16 |
| E3 | c sweep | 🔄 | An | 2026-11-10 | D-18; quick xong, chờ duyệt full |
| E4 | N vs W/N | ⬜ | An | | |
| E5 | Random vs heuristic rollout | ⬜ | An | | |
| E6 | Tác dụng check_tactics | ⬜ | An | | thêm theo D-11 |
| P6.1 | GUI pygame | ⬜ | An | | |
| P7.1 | Plots/tables | ⬜ | An | | |
| P7.2 | report.md | ⬜ | An | | |
| P7.3 | report.docx | ⬜ | An | | |
| P7.4 | Video demo (script + quay) | ⬜ | An | | |
| P8.1 | Xiangqi rules + perft | ⬜ | An | | |
| P8.2 | Xiangqi eval + AB | ⬜ | An | | |
| P8.3 | Xiangqi MCTS | ⬜ | An | | |
| P8.4 | Xiangqi experiments | ⬜ | An | | |

## Kết quả thí nghiệm đã có

- **E1:** giá trị gốc AB = Minimax ở 6/6 thế 3×3 (cả 3 biến thể) và 5/5 thế 15×15 depth 2; nước đi `ab` = Minimax, `ab_order`/`ab_order_tt` giống hệt 3/6 nhưng tối ưu 6/6 (hòa giá trị). Nút gộp 3×3 vs Minimax: −96,13 % (ab), −99,60 % (+ordering), −99,76 % (+TT); bàn trống 549 946 → 20 866 → 1 856 → 990. 15×15 depth 2: 46 825 → 21 612 (−53,85 %) → 1 416 (−96,98 %), nhưng thời gian ordering 0,265 s vs 0,247 s (chậm hơn 7,5 %); depth 3: 553 574 → 48 504 nút (−91,24 %), 5,46 → 1,26 s. `results/tables/e1_{nodes,summary,positions}.csv`.

- **E2:** (b) vét cạn 0 nhánh thua trên 10 seed × 2 vai ở 5000 iter (5674 nhánh); 1000 iter 7/5713 thua; 100 iter 279/6247. (a) 5000 iter 0 thua/100 ván vs Minimax, Random, MCTS. `results/tables/e2_*.csv`.
<!-- Mỗi thí nghiệm chạy xong: 1–3 dòng số liệu chính + đường dẫn file CSV/hình. -->
- **P3.3 (sơ bộ — không phải số liệu E5):** 7 cấu hình × {Greedy, AB2, mrand} × 20 ván, 0,5 s/nước, tactics bật. Thắng vs mrand: h100 / h300 / h100c10 / h1000c10 19/20, h1000 / h300c10 16/20, rand 9/20 (Wilson [0,258; 0,658], hợp lệ). Vs Greedy cao nhất 8/20 (h300, h100c10), vs AB2 ≤ 2/20. Chọn **h300** theo luật D-14. `results/tables/p33_sweep_prelim.csv`, `p33_choice_prelim.csv`, `p33_scale_prelim.csv`.

## Session log (mới nhất ở trên)

### 2026-11-10 — E1 (xong)
- Đã làm: `experiments/e1_nodes.{py,md}` — 3×3 (bàn trống + 5 thế, Minimax / AB / +ordering / +ordering+TT), 15×15 (5 thế cố định, AB depth 2, 3 × có/không ordering; Minimax chỉ depth 2; thêm `ab_evalonly` tách tác dụng `delta_eval`). Kiểm giá trị + nước đi + `move_optimal`; báo % nút và % thời gian, gộp và trung bình theo thế. `--quick` 5 s; full 58,7 s (không cần hỏi trước khi chạy: < 2 phút). P4.3 hoãn, gộp với P6 (ghi ở bảng + PLAN + D-17).
- Test: full suite pass (1 xfail chủ ý); 4 test mới trong `tests/test_e1_nodes.py`; ruff sạch.
- File đổi: `gameai/experiments/e1_nodes.{py,md}`, `tests/test_e1_nodes.py`, `results/tables/e1_{nodes,summary,positions}.csv`, `PLAN.md`, `docs/DECISIONS.md` (D-17), `PROGRESS.md`.
- Lưu ý: 5 thế mỗi bàn **lồng nhau** (cùng playout seed 0) và chỉ 5 thế → không có CI. Ordering giảm nút nhưng ở 15×15 depth 2 không giảm thời gian (chi phí `move_score`); depth 3 mới có lợi. Nước của `ab_order*` khác Minimax khi hòa giá trị là hợp lệ (xem `move_optimal`).

### 2026-11-10 — E2 (xong)
- Full: (a) 543 s, (b) 290 s. Vét cạn: 0 nhánh thua trên 10 seed × 2 vai ở 5000 iter (5674 nhánh); 1000 iter còn 7/5713 (2/20 run, MCTS=O); luật mở rộng 10000/20000 không kích hoạt. Sai chủ yếu ở vai O, nước đáp đầu. Sửa `mcts.md` ("1000 iter đủ" chỉ đúng với ván đấu). Chi tiết: `gameai/experiments/e2_never_lose.md`.

### 2026-11-10 — P4.2
- Đã làm: `add_runner_args` thêm `--quick` (chỉ đăng ký cờ; script tự định nghĩa quick + file riêng); `p33_heavy_sweep` bỏ khai `--quick` trùng. `summarize(rows, moves=None)` thêm `{a,b}_search_moves`, `{a,b}_search_iterations_per_move` (bỏ nước tactic thắng/chặn ngay; restrict vẫn tính), cột cũ giữ nguyên (D-15). Không đổi schema CSV, không chạy lại p33. Ghi cảnh báo AB2/E3/E5 vào "Cảnh báo".
- Kiểm trên dữ liệu p33 có sẵn: h300 vs Greedy 664 → 880 it/nước (123 nước search), vs mrand 805 → 968 (212 nước).
- Test: full suite pass (1 xfail chủ ý); 4 test mới/sửa trong `tests/test_experiments_common.py`; ruff sạch. spec-reviewer PASS (đã siết 1 test yếu).
- File đổi: `gameai/experiments/{common.py,common.md,p33_heavy_sweep.py}`, `tests/test_experiments_common.py`, `docs/DECISIONS.md` (D-15), `PROGRESS.md`.

### 2026-11-10 — P3.3 (chạy full, xong)
- Đã làm: luật chọn D-14 (nhóm chốt trước khi chạy) cài trong `choose_config` → `results/tables/p33_choice_prelim.csv`; commit `217aabd`, chạy full 4 worker: 21 match, 420 ván, 11 phút 27 s, mọi ván `normal`, `git_dirty = 0`, `distinct_games` = 20/20 ở cả 21 ô (không cần `random_opening`).
- Kết quả (sơ bộ — không phải E5), thắng/20 vs mrand · Greedy · AB2 (không có hòa): rand 9 · 0 · 0; h100 19 · 6 · 2; h300 19 · 8 · 0; h1000 16 · 2 · 0; h100c10 19 · 8 · 2; h300c10 16 · 4 · 0; h1000c10 19 · 5 · 1. Kiểm tra hợp lệ rand vs mrand 9/20, Wilson [0,258; 0,658] ∋ 0,5. Bốn cấu hình hòa nhất vs mrand (19/20, Wilson [0,764; 0,991]), cả 6 cấu hình heavy chồng CI → phá hòa: Greedy 0,40 (h300 = h100c10) → không cắt → **h300**.
- Lưu ý: `a_iterations_per_move` tính cả nước đi thẳng nhờ tactics (0 iteration): rand vs greedy 897 trên 102 nước, 1 040 trên 88 nước có search (`p33_rand_vs_greedy_moves.csv`). So cùng nước (seed 0–1, 14 nước có search) quick 1 worker / quick 4 worker / full: 1 464 / 1 264 / 1 273 → full không bị tải thêm so với quick 4 worker. Vs AB2 gần sàn (≤ 2/20) → mrand là đối thủ phân biệt được cấu hình.
- Test: 290 full suite (289 passed + 1 xfail chủ ý), 23 trong `tests/test_p33_heavy_sweep.py` (thêm 4 test luật chọn); ruff sạch. spec-reviewer PASS (đã sửa 1 số không truy được trong `p33_heavy_sweep.md`).
- File đổi: `gameai/experiments/p33_heavy_sweep.{py,md}`, `tests/test_p33_heavy_sweep.py`, `gameai/agents/rollout.md`, `docs/DECISIONS.md` (D-14 luật chọn), `PROGRESS.md`, `results/raw/p33_*_vs_*.csv` (+ `_moves.csv`), `results/tables/p33_{sweep,choice}_prelim.csv`. File `p33quick_*` không commit.

### 2026-11-10 — P3.3
- Đã làm: `experiments/p33_heavy_sweep.{py,md}` — `calibrate` (mỗi T một scale, mọi thế dọc rollout heavy sau khai cuộc 4–20 quân, seed 50 000–50 199, lưới D-12 + mở rộng khi chạm biên) và `sweep` (7 cấu hình × Greedy / AB2, 0,5 s/nước, `--quick` = 1 seed + kiểm tra worker 1 vs 4). D-12 bổ sung 5 điểm. Commit `4d6a8d9` trước khi chạy (`git_dirty = False`).
- Test: 286 full suite (285 passed + 1 xfail chủ ý); 19 mới trong `tests/test_p33_heavy_sweep.py` (gồm khớp `value_fn` của MCTS với σ(eval_P1/scale) đã fit ở cả lượt X và O — không lệch dấu); ruff sạch.
- Hiệu chỉnh (`results/tables/p33_scale_prelim.csv`, 9 343 thế, 1,9 s): T=100 → scale 500 (LL 300/500/1000: −0,6045 / **−0,5590** / −0,5686, 1 554 thế); T=300 → 500 (−0,5855 / **−0,5657** / −0,5835, 1 962 thế); T=1000 → 1000 (500/1000/2000: −0,6862 / **−0,6619** / −0,6670, 5 827 thế). Không chạm biên, không mở rộng lưới. LL gần log 0,5 = −0,693 (nhất là T=1000) → eval dự đoán yếu kết quả rollout.
- `--quick` (`results/tables/p33quick_sweep_prelim.csv`, không commit; 1 phút 27 s tổng): 7 cấu hình × 2 đối thủ × 2 ván = 28 ván, **MCTS thua cả 28** (termination normal, không lỗi), ván trung bình 9,5–27,5 nước; MCTS không chặn four (`check_tactics=False`). Iteration/nước: rand ~1 530, h100 ~1 100, h300 ~860–935, h1000 ~530–720, cấu hình c10 1 200–1 800. Ước tính full: vs Greedy 140 ván ~7 phút tuần tự / ~2 phút 4 worker; vs AB2 140 ván ~8 / ~2 phút. Kiểm tra worker (rand vs greedy, 4 ván): 1 worker 1 106 it/nước, 4 worker 1 282 (+15,9%) → 4 worker không làm giảm iteration.
- File đổi: `gameai/experiments/p33_heavy_sweep.{py,md}`, `tests/test_p33_heavy_sweep.py`, `gameai/agents/rollout.md`, `gameai/heuristics/kinrow_rollout.md`, `docs/DECISIONS.md`, `PROGRESS.md`, `results/raw/p33_calib_positions.csv`, `results/tables/p33_scale_prelim.csv`.
- Còn dở: chờ quyết định về floor effect rồi chạy full; chọn cấu hình cho E5; spec-reviewer.
- **Tiếp (cùng ngày) — D-14:** sanity check (script tạm, không lưu; 3 thế 15×15 có four của O, tactics tắt, h100 iteration cố định, 5 seed): 2000 iteration chặn 0/5 ở cả 3 thế (ô chặn chiếm 1–3% N gốc); 5000 iteration chặn 5/5 ở 2 thế ~58 candidate (3–5% N), 0/5 ở thế chéo ~100 candidate; 20 000 (seed 0) chặn ở cả 3, ô chặn W/N 0,39–0,75, cao nhất. Không phải bug: nước sai chỉ bị bác bỏ sau khi nút con mở rộng tới nước thắng của O. Iteration/nước ở 0,5 s (thế four kín): rand 1 682, h100 1 104, h300 867, h1000 389. → D-14: `check_tactics=True` cho mọi MCTS 15×15 (P3.3, E3, E5), chỉ E6 so bật/tắt; thêm đối thủ `mrand`. PLAN + doc cập nhật; xóa file `p33quick_*` cũ (chưa commit, config cũ).
- `--quick` lần 2 (42 ván, 3 phút 23 s, `results/tables/p33quick_sweep_prelim.csv`, không commit): MCTS thắng/hòa/thua — vs Greedy 4/0/10 (h300c10 2/2, h100 1/2, h100c10 1/2, còn lại 0), vs AB2 1/0/13 (chỉ h100 1/2), vs mrand 11/0/3 (rand 0/2, h300c10 1/2, còn lại 2/2). Độ dài ván TB (trung bình các cấu hình): 17,2 / 16,4 / 23,1 nước. Ước tính full: Greedy ~8 phút tuần tự / ~2 phút 4 worker; AB2 ~8 / ~2; mrand ~24 / ~6. Kiểm tra worker: 1 worker 1 256 it/nước, 4 worker 1 124 (−10,5%, dưới ngưỡng 15%).

### 2026-11-10 — P4.1
- Đã làm: D-11 (làm rõ "Done P3 — thắng ngay") được nhóm duyệt. `agents/registry.py` — `AgentSpec`/`GameSpec` (params JSON, pickle được) + `make_agent`/`make_game`. `arena.py` — `play_game` (time do arena đo + bản sao stats mỗi nước; exception / nước sai / mutate game → thua), `derive_seed` (sha256), `random_opening_moves`, `play_seeded_game` (agent mới mỗi ván), `play_match`. `experiments/common.py` — `run_match` (song song, mặc định 4 worker, ghi ván + `*_moves.csv` ngay khi xong, resume: dòng cắt dở, moves mồ côi, `config_hash`, `git_commit`/`git_dirty` + `allow_code_change`), `summarize` (Wilson cho win rate và non-loss, score, `distinct_games`, tách A=X / A=O), `write_summary`, `add_runner_args`. PLAN: gộp runner vào P4.1, P4.2 chỉ còn cờ dòng lệnh. DECISIONS: D-13.
- Test: 267 test full suite (266 passed + 1 xfail chủ ý); 57 mới trong `tests/test_arena.py` + `tests/test_experiments_common.py` (~40 s, có spawn tiến trình), agent lỗi giả ở `tests/arena_helpers.py`; ruff sạch. Đột biến: 11 đột biến (không đổi lượt, seed bỏ tag, đảo người thắng khi lỗi, bỏ kiểm mutate, không xóa moves mồ côi, không bỏ dòng cắt dở, distinct bỏ vai, không bỏ ván đã xong, bỏ kiểm commit, đổi seed A/B, `FIRST_EXCEPTION`) đều bị test bắt.
- File đổi: `gameai/arena.{py,md}`, `gameai/agents/registry.{py,md}`, `gameai/experiments/common.{py,md}`, `tests/test_arena.py`, `tests/test_experiments_common.py`, `tests/arena_helpers.py`, `PLAN.md`, `docs/DECISIONS.md`, `PROGRESS.md`.
- Lưu ý: phát hiện khi kill thật: bản đầu dùng `wait(FIRST_EXCEPTION)` nên chế độ song song chỉ ghi khi **cả batch** xong; đã sửa sang `FIRST_COMPLETED` và thêm test. Đã kill thật một lần giữa batch 15×15 (2 worker): 4 ván giữ nguyên, chạy lại chỉ chơi 16 ván còn thiếu. `git_dirty` không tính file chưa track và không phân biệt hai trạng thái dirty khác nhau cùng commit → commit trước khi chạy dài. Script thí nghiệm phải gọi `run_match` trong `if __name__ == "__main__":`. Đo thử (không phải số liệu): MCTS heavy_kinrow 0,05 s/nước vs Greedy 15×15 thắng 12/80.

### 2026-11-10 — P3.2
- Đã làm: profile `HeavyRollout` (~80% ở `kinrow_eval._scan`, chấm lại mọi candidate mỗi bước). `heuristics/kinrow_rollout.py` — `KInRowHeavyRollout(T)`: giữ số quân mỗi cửa sổ + (delta, win, block) mỗi ô × mỗi bên, chỉ cập nhật cửa sổ qua ô vừa đặt; tự đồng bộ theo tiền tố `move_history` (gỡ/áp nước). `KInRow.move_history` (property chỉ đọc). `experiments/p32_heavy_speed.py` đo tốc độ. Thêm mục "So sánh với Minimax: thắng ngay hay thắng chắc" vào `mcts.md` (tư liệu báo cáo, thuộc D-11). PLAN: tách P3.2 / P3.3 (quét tham số, sau P4.1). DECISIONS: D-12.
- Test: 210 test full suite, 209 passed + 1 xfail chủ ý; 27 mới trong `tests/test_kinrow_rollout.py` (~2 s) + 1 trong `tests/test_kinrow.py`; ruff sạch. 4 đột biến (ngưỡng chặn, bỏ góc nhìn O, không gỡ khi đồng bộ, bỏ kiểm tiền tố) đều bị test bắt.
- Kết quả đo (`results/tables/p32_heavy_speed.csv`, `p32_mcts_iterations.csv` — số đo phát triển, không phải E5): 300/300 rollout giống hệt bản chuẩn; nhanh hơn 7,1–10,9×/rollout (khai cuộc 6 nước), 4,1–8,4× (20 nước). MCTS 0,5 s/nước, T=100: 387–577 iteration (bản chuẩn 53–76, random 535–637).
- File đổi: `gameai/heuristics/kinrow_rollout.{py,md}`, `gameai/experiments/p32_heavy_speed.{py,md}`, `gameai/games/kinrow.{py,md}`, `gameai/agents/{rollout,mcts}.md`, `gameai/heuristics/kinrow_eval.md`, `tests/test_kinrow_rollout.py`, `tests/test_kinrow.py`, `results/raw/p32_heavy_speed.csv`, `results/tables/p32_{heavy_speed,mcts_iterations}.csv`, `PLAN.md`, `docs/DECISIONS.md`, `PROGRESS.md`.
- Lưu ý: rollout heavy rất ngắn ở T nhỏ (T=100: 9,4 nước sau khai cuộc 6, 5,1 sau 20) → `rollout_limit=10` gần như không tác dụng ở T=100. Console Windows cp1252 không in được tiếng Việt → script in ASCII. Đối tượng `KInRowHeavyRollout` có trạng thái: mỗi agent/tiến trình một object.

### 2026-11-10 — P3.1
- Đã làm: `agents/mcts.py` — `MCTSAgent` (UCT, `iterations` và/hoặc `time_limit`, `final_move` max_n/max_wn, `rollout_limit` + `value_fn`, `check_tactics` mặc định tắt, seed riêng), `Node`, `uct`, `select_child`, `backpropagate` (chỗ lật góc nhìn duy nhất), `last_root_stats()`, `root`. `agents/rollout.py` — `RandomRollout`, `HeavyRollout` (softmax trên `score_fn`, T=100, chưa tối ưu), `make_policy`, `sigmoid_value`. PLAN: phạm vi P3.1/P3.2, đối thủ chuẩn 15×15 (Greedy + AB depth 2), thêm E6. DECISIONS: D-10, D-11.
- Test: 182 test, 181 passed + 1 xfail chủ ý (full suite ~2 phút gồm `slow`); 59 mới trong `tests/test_mcts.py` + `tests/test_rollout.py` (~5 s không tính `slow`, ~23 s cả `slow`); ruff sạch. Đã thử 4 đột biến lật dấu (backprop lật toàn cục / viết cứng P1 / đảo 1−r từ lá / lật trong UCT) → đều bị test bắt.
- File đổi: `gameai/agents/{mcts,rollout}.{py,md}`, `tests/test_{mcts,rollout}.py`, `gameai/heuristics/kinrow_eval.md`, `PLAN.md`, `docs/DECISIONS.md`, `PROGRESS.md`.
- Lưu ý: tốc độ 3×3 1000 iter ≈ 19 ms; 15×15 ≈ 0,32–0,40 ms/iter (cây sâu ~2 ở 1000 iter). Tắt tactics: 15×15 chặn four 0/10 seed ở 1000 iter, 2/10 ở 5000 (số đo phát triển — báo cáo lấy từ E6). 20 ván vs Minimax 3×3 tắt tactics: 1000 iter đủ, 0 thua. MCTS không phân biệt thắng ngay / thắng chắc (thế `. . X / X O X / . O .`) → làm rõ Done P3 ở D-11, chờ nhóm duyệt. `check_tactics` tốn O(b²) (~80 ms với 148 candidate). Heavy trên 15×15 phải có `rollout_limit` cho tới khi P3.2 tăng tốc.

### 2026-11-04 — P2.5
- Đã làm: `agents/greedy.py` — `GreedyAgent(score_fn, seed=None, use_candidates=True)`: argmax `score_fn` trên candidate (1-ply), tie-break `random.Random(seed)` chỉ khi hòa điểm; stats `nodes` (= số nước chấm), `iterations`, `time`, `value`.
- Test: 123 passed full suite (~59 s); 11 mới trong `tests/test_greedy.py`; ruff sạch.
- File đổi: `gameai/agents/greedy.{py,md}`, `tests/test_greedy.py`, `PROGRESS.md`.
- Lưu ý: dùng `GreedyAgent(move_score, seed=s)`. `use_candidates` mặc định True (RandomAgent mặc định False). Sau khi X đi giữa bàn, mọi candidate của O cùng điểm 20 → khai cuộc của Greedy gần như ngẫu nhiên. Greedy thắng Random(candidate) trong 9–10 nước ở mọi seed đã thử. `MoveFn` import từ `alphabeta.py` (có thể dời sang `base.py` sau).

### 2026-11-04 — P2.4
- Đã làm: `agents/alphabeta.py` — `AlphaBetaAgent` (cùng tham số Minimax + `order_fn`, `delta_fn`, `use_tt`), fail-soft, TT có cờ EXACT/LOWER/UPPER, khóa `(key, độ sâu còn lại)`, điểm thắng lưu theo khoảng cách; `search()` trả (move, value); stats thêm `cutoffs`, `tt_hits`. D-9 trong DECISIONS (gồm cả `WIN_SCORE` chung từ P2.3).
- Test: 112 passed full suite (~86 s; 111 với `-m "not slow"`), 16 mới trong `tests/test_alphabeta.py`; ruff sạch. Bàn trống 3×3: AB 20 866 nút, ordering+TT 990 (Minimax 549 946) — đo thử, chưa phải số liệu E1.
- File đổi: `gameai/agents/alphabeta.{py,md}`, `tests/test_alphabeta.py`, `docs/DECISIONS.md`, `PROGRESS.md`.
- Lưu ý: 15×15 nên dùng `AlphaBetaAgent(depth=2|3, eval_fn=evaluate, delta_fn=delta_eval, order_fn=move_score)`. Full suite ~1–1,5 phút; `test_kinrow_eval.py::test_delta_eval_matches_brute_force[15-5]` mất ~70 s (có từ P2.2) — đã đánh dấu `slow` (bỏ qua bằng `python -m pytest -m "not slow"`).

### 2026-11-04 — P2.3
- Đã làm: `agents/minimax.py` — `MinimaxAgent(depth=None, eval_fn=None, use_candidates=True, seed=None)`, max/min tường minh theo góc nhìn người đi ở gốc, đếm nút (kể cả gốc), `root_values`/`value` để so với AB; `terminal_score` = ±(`WIN_SCORE` − ply), `WIN_SCORE = 10**12`.
- Test: 96 passed (17 mới trong `tests/test_minimax.py`); ruff sạch. Cây 3×3 đầy đủ = 549 946 nút, giá trị 0, ~1,3 s. File test chạy ~30 s.
- File đổi: `gameai/agents/minimax.{py,md}`, `tests/test_minimax.py`, `PROGRESS.md`.
- Lưu ý: seed=None → chọn nước tốt nhất đầu tiên (tất định); có seed → ngẫu nhiên trong các nước tốt nhất. Terminal dùng `WIN_SCORE` chung (không phải `win_score(k)`) để AB/minimax cùng thang điểm; AB nên import từ `minimax.py`.

### 2026-10-28 — P2.2
- Đã làm: `heuristics/kinrow_eval.py` — eval theo cửa sổ k ô (`W[c]=10^(c-1)`), `evaluate`, `delta_eval` (= evaluate sau − trước, quét cục bộ), `move_score` (bậc WIN > BLOCK > delta). Thêm `cell_of(player)` vào `kinrow.py`.
- Test: 79 passed (23 mới trong `tests/test_kinrow_eval.py`); ruff sạch.
- File đổi: `gameai/heuristics/kinrow_eval.{py,md}`, `gameai/games/kinrow.{py,md}`, `tests/test_kinrow_eval.py`, `docs/DECISIONS.md` (D-8), `PROGRESS.md`.
- Lưu ý: delta thuần thích tạo open-four (+1915) hơn chặn four (+1143) nên greedy/ordering/rollout phải dùng `move_score`. AB (P2.4) cộng dồn `delta_eval` + terminal `WIN − depth`. Trọng số chưa tinh chỉnh.

### 2026-10-28 — P2.1
- Đã làm: `Agent` ABC (`stats` dict, `name`, `reset_stats`, `select_move` abstract); `RandomAgent(seed, use_candidates=False)` với `random.Random` riêng.
- Test: 56 passed (9 mới trong `tests/test_random_agent.py`); ruff sạch.
- File đổi: `gameai/agents/{base,random_agent}.py` + `.md`, `tests/test_random_agent.py`, `PROGRESS.md`.
- Lưu ý: `Agent.select_move` (template method) tự reset stats rồi gọi `_select_move` — agent con chỉ override `_select_move` (D-7). Khóa stats: `nodes`, `iterations`, `time`.

### 2026-10-28 — P1.2
- Đã làm: `KInRow(n, k, radius=2)` với board `bytearray`, thắng tăng dần (4 hướng qua nước vừa đi), `candidate_moves` giữ tăng dần bằng `_near` + `_cand` cập nhật trong `play`/`undo`, undo bằng stack, `clone` độc lập, `key=(bytes(board), player)`.
- Test: 47 passed (28 mới trong `tests/test_kinrow.py`); `ruff check` và `ruff format --check` sạch.
- File đổi: `gameai/games/kinrow.py`, `gameai/games/kinrow.md`, `tests/test_kinrow.py`, `PROGRESS.md`.
- Lưu ý: `board` lưu 0/1/2 còn người chơi là 1/-1 → eval (P2.2) phải ánh xạ `1 if p == X else 2`. Candidate trả list đã sort (tất định). Bàn trống 3×3 trả toàn bộ ô, bàn lớn trả ô giữa.

### 2026-10-28 — P1.1
- Đã làm: `Protocol Game` (10 hàm, `@runtime_checkable`), `Move = Hashable`, `P1/P2/DRAW`, hàm `result_for(winner, player)`; `game.md` ghi hợp đồng từng hàm; D-5 trong DECISIONS.
- Test: 19 passed (12 mới trong `tests/test_game_interface.py`); `ruff check .` sạch.
- File đổi: `gameai/core/game.py`, `gameai/core/game.md`, `tests/test_game_interface.py`, `docs/DECISIONS.md`, `PROGRESS.md`.
- Lưu ý cho P1.2: alias `X = P1`, `O = P2` đặt trong `kinrow.py`, không đặt ở core. Hợp đồng chỉ được ép bằng test của từng game, Protocol không ép được.

### 2026-10-28 — P0.1
- Đã làm: skeleton `gameai/{core,games,heuristics,agents,gui,experiments}` + `__init__.py`, `tests/`, `results/{raw,tables,figures}`, `report/` (`.gitkeep`); `tests/test_smoke.py` (import các gói).
- Test: 7 passed; `ruff check .` sạch.
- File đổi: xem commit `P0.1`.
- Lưu ý: `ruff format --check` từng báo `docs/MODULE_TEMPLATE.md` (code block trong file md) → đã thêm `extend-exclude = ["*.md"]` vào `[tool.ruff]` (commit `P0.1: exclude md from ruff`), nay sạch. pytest cảnh báo không ghi được `.pytest_cache` (WinError 5, quyền Windows) — không ảnh hưởng kết quả. Python venv là 3.13.

<!-- Mẫu:
### YYYY-MM-DD — <task ID>
- Đã làm: ...
- Test: N passed
- File đổi: ...
- Còn dở / lưu ý cho phiên sau: ...
-->
