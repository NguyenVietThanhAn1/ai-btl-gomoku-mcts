# PROGRESS — BTL AI Bài 1

> Single source of truth cho tiến độ. Cập nhật **cuối mỗi task / mỗi phiên** (`/wrap-up`).
> Ký hiệu: ⬜ chưa làm · 🔄 đang làm · ✅ xong · ⛔ bị chặn
> Định nghĩa task: xem `PLAN.md`.

## Đang ở đâu (đọc mục này trước tiên)

- **Task hiện tại:** P2.1 (chưa bắt đầu; P0.1, P1.1, P1.2 ✅)
- **Việc đang dở:** —
- **Bước tiếp theo:** chạy `/next-task` → P2.1 (`agents/base.py` + `random_agent.py`, `stats` dict, seed riêng).
- **Cảnh báo / blocker:** —

## Bảng trạng thái

| ID | Task | Trạng thái | Owner | Cập nhật | Ghi chú |
|---|---|---|---|---|---|
| P0.1 | Repo, venv, skeleton | ✅ | An | 2026-10-28 | spec-reviewer PASS |
| P1.1 | core/game.py interface | ✅ | An | 2026-10-28 | spec-reviewer PASS; quyết định ở D-5 |
| P1.2 | games/kinrow.py | ✅ | An | 2026-10-28 | spec-reviewer PASS |
| P2.1 | Agent base + Random | ⬜ | An | | |
| P2.2 | Heuristic eval k-in-row | ⬜ | An | | |
| P2.3 | Minimax | ⬜ | An | | |
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
| P8.1 | Xiangqi rules + perft | ⬜ | An | | |
| P8.2 | Xiangqi eval + AB | ⬜ | An | | |
| P8.3 | Xiangqi MCTS | ⬜ | An | | |
| P8.4 | Xiangqi experiments | ⬜ | An | | |

## Kết quả thí nghiệm đã có

<!-- Mỗi thí nghiệm chạy xong: 1–3 dòng số liệu chính + đường dẫn file CSV/hình. -->

## Session log (mới nhất ở trên)

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
