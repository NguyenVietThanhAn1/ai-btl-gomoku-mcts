# PROGRESS — BTL AI Bài 1

> Single source of truth cho tiến độ. Cập nhật **cuối mỗi task / mỗi phiên** (`/wrap-up`).
> Ký hiệu: ⬜ chưa làm · 🔄 đang làm · ✅ xong · ⛔ bị chặn
> Định nghĩa task: xem `PLAN.md`.

## Đang ở đâu (đọc mục này trước tiên)

- **Task hiện tại:** P4.1 (chưa bắt đầu; P3.2 ✅)
- **Việc đang dở:** —
- **Bước tiếp theo:** `/next-task` → P4.1 Arena (`play_game` / `play_match`), rồi P3.3 quét sơ bộ T / `rollout_limit` / `scale` của heavy (thiết lập đã duyệt ở D-12: cùng `time_limit` 0,5 s, Greedy + AB depth 2, 20 ván/cấu hình/đối thủ, 4 worker, `scale` bằng hồi quy logistic trên seed 50 000–50 199). Heavy cho k-in-row: dùng `KInRowHeavyRollout(T)` (`heuristics/kinrow_rollout.md`).
- **Cảnh báo / blocker:** chờ nhóm xác nhận phần làm rõ "Done P3 — thắng ngay" ở D-11 (MCTS không chiết khấu độ sâu: test kiểm "nước thắng chắc theo Minimax" + W/N nước thắng ngay = 1, thay vì đúng nước thắng ngay).

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
| P4.1 | Arena | ⬜ | An | | |
| P3.3 | Quét sơ bộ T / rollout_limit / scale (heavy) | ⬜ | An | | sau P4.1; D-12 |
| P4.2 | Experiment runner | ⬜ | An | | |
| P4.3 | CLI | ⬜ | An | | |
| E1 | Nodes Minimax vs AB | ⬜ | An | | |
| E2 | 3×3 never lose | ⬜ | An | | |
| E3 | c sweep | ⬜ | An | | |
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

<!-- Mỗi thí nghiệm chạy xong: 1–3 dòng số liệu chính + đường dẫn file CSV/hình. -->

## Session log (mới nhất ở trên)

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
