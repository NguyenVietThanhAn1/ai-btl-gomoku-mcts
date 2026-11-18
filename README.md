# BTL Trí tuệ nhân tạo — Bài 1: k-in-a-row với Minimax/Alpha-Beta và MCTS-UCT (+ Cờ tướng)

## Trạng thái hiện tại
Xem mục "Đang ở đâu" đầu [PROGRESS.md](PROGRESS.md) (single source of truth). Kế hoạch & tiêu chí từng task: [PLAN.md](PLAN.md); quyết định thiết kế: [docs/DECISIONS.md](docs/DECISIONS.md). Số liệu thí nghiệm k-in-row khóa ở tag `kinrow-final`; bảng tổng hợp cho báo cáo: [results/tables/summary_kinrow.md](results/tables/summary_kinrow.md).

**Luật & quy trình (mọi công cụ, D-31):** luật dự án ở [AGENTS.md](AGENTS.md) (nguồn duy nhất; `CLAUDE.md` chỉ import nó); quy trình làm task / wrap-up: [docs/WORKFLOW.md](docs/WORKFLOW.md); review: [docs/REVIEW.md](docs/REVIEW.md).

## Cài đặt
Xem [docs/SETUP.md](docs/SETUP.md) (venv `.venv`, Python 3.11+, `python -m pip install -r requirements.txt`). Windows: dùng `python`, không dùng `python3`.

```powershell
python -m pytest -q                              # test (phải xanh)
python -m ruff check . --fix; python -m ruff format .
python -m gameai.experiments.plots --check       # bảng/hình báo cáo sinh lại từ results/raw
python -m gameai.gui.pygame_app --preset 3x3_human_mcts   # GUI; preset: 3x3_human_mcts | 15_human_h300 | 15_h300_vs_ab2 (phím: gameai/gui/pygame_app.md)
```

## Quy ước làm việc nhóm (D-32)
Luật đầy đủ cho người/agent: [AGENTS.md](AGENTS.md).

- **Branch:** làm và commit **thẳng trên `develop`**; feature branch chỉ khi thay đổi lớn/rủi ro (không bắt buộc). `master` = bản ổn định / nộp được: chỉ merge từ `develop` ở mốc, qua PR "Create a merge commit" (không squash), không push thẳng. Quy trình từng bước: [docs/WORKFLOW.md](docs/WORKFLOW.md); review: [docs/REVIEW.md](docs/REVIEW.md).
- **Trước mỗi push `develop`:** đồng bộ (`git fetch origin` rồi `git rebase origin/develop`; người gõ tay có thể dùng `git pull` với `pull.rebase true`); `python -m pytest -q` (gồm golden) + `python -m ruff check .` xanh; nếu đụng `report/` hoặc `gameai/experiments/`: thêm `report_check` + `python -m gameai.experiments.plots --check`. Cấm `git push --force`, cấm rebase commit đã push.
- **Commit:** `<TaskID>: <mô tả ngắn>` (vd. `P3.1: MCTS-UCT core with root stats`). Push `develop` sau khi qua các kiểm tra trên; không push thẳng `master` (D-32).
- **Golden test:** `tests/test_regression_kinrow.py` phải luôn xanh (hành vi k-in-row khóa ở `kinrow-final`).
- **Vùng nhạy cảm** (`gameai/agents/`, interface `Game`/`Agent`, `gameai/core/`, `results/`, `report/report.md`): báo người kia trước khi sửa; agent phải dừng và hỏi người dùng. Đổi interface/agent cần ghi lý do vào `docs/DECISIONS.md`; sửa agent thì thêm tham số có mặc định giữ hành vi cũ.
- **Mỗi module `X.py` có `X.md` cạnh nó** theo [docs/MODULE_TEMPLATE.md](docs/MODULE_TEMPLATE.md), cập nhật cùng thay đổi code.
- **PROGRESS.md:** mỗi người chỉ sửa dòng task của mình (cột Owner) và khối "Đang ở đâu" của mình; session log nằm trong khối của từng người (`### An` / `### Thành viên 2`), mới nhất ở đầu khối mình.
- **Dữ liệu:** không sửa tay `results/raw/`; bảng/hình chỉ sinh bằng script trong `gameai/experiments/`. File `*quick*` và `results/*.log` không commit.
- **Thí nghiệm dài (> 2 phút):** chạy `--quick` trước, báo thời gian ước tính, hỏi trước khi chạy full.
