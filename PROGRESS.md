# PROGRESS — BTL AI Bài 1

> Single source of truth cho tiến độ. Cập nhật **cuối mỗi task / mỗi phiên** (`/wrap-up`).
> Ký hiệu: ⬜ chưa làm · 🔄 đang làm · ✅ xong · ⛔ bị chặn
> Định nghĩa task: xem `PLAN.md`.

## Đang ở đâu (đọc mục này trước tiên)

- **Task hiện tại:** P2.4 (chưa bắt đầu; P0.1–P2.3 ✅)
- **Việc đang dở:** —
- **Bước tiếp theo:** chạy `/next-task` → P2.4 (`agents/alphabeta.py`). Dùng lại `terminal_score`/`WIN_SCORE`/`EvalFn` từ `agents/minimax.py`; test so giá trị với `MinimaxAgent.value()`/`root_values()` trên 3×3. Lưu ý: P2.4 phải cộng dồn `delta_eval` và dùng `WIN − depth` (xem `heuristics/kinrow_eval.md`, D-8); đổi player → ô dùng `cell_of`.
- **Cảnh báo / blocker:** —

## Bảng trạng thái

| ID | Task | Trạng thái | Owner | Cập nhật | Ghi chú |
|---|---|---|---|---|---|
| P0.1 | Repo, venv, skeleton | ✅ | An | 2026-10-28 | spec-reviewer PASS |
| P1.1 | core/game.py interface | ✅ | An | 2026-10-28 | spec-reviewer PASS; quyết định ở D-5 |
| P1.2 | games/kinrow.py | ✅ | An | 2026-10-28 | spec-reviewer PASS |
| P2.1 | Agent base + Random | ✅ | An | 2026-10-28 | spec-reviewer PASS |
| P2.2 | Heuristic eval k-in-row | ✅ | An | 2026-10-28 | spec-reviewer PASS; quyết định ở D-8 |
| P2.3 | Minimax | ✅ | An | 2026-11-04 | spec-reviewer PASS |
| P2.4 | Alpha-Beta | ⬜ | An | | |
| P2.5 | Greedy agent | ⬜ | An | | |
| P3.1 | MCTS-UCT | ⬜ | An | | |
| P3.2 | Rollout policies | ⬜ | An | | |
| P4.1 | Arena | ⬜ | An | | |
| P4.2 | Experiment runner | ⬜ | An | | |
| P4.3 | CLI | ⬜ | An | | |
| E1 | Nodes Minimax vs AB | ⬜ | An | | |
| E2 | 3×3 never lose | ⬜ | An | | |
| E3 | c sweep | ⬜ | An | | |
| E4 | N vs W/N | ⬜ | An | | |
| E5 | Random vs heuristic rollout | ⬜ | An | | |
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
