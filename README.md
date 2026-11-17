# BTL Trí tuệ nhân tạo — Bài 1: k-in-a-row với Minimax/Alpha-Beta và MCTS-UCT (+ Cờ tướng)

## Trạng thái hiện tại
Xem mục "Đang ở đâu" đầu [PROGRESS.md](PROGRESS.md) (single source of truth). Kế hoạch & tiêu chí từng task: [PLAN.md](PLAN.md); quyết định thiết kế: [docs/DECISIONS.md](docs/DECISIONS.md). Số liệu thí nghiệm k-in-row khóa ở tag `kinrow-final`; bảng tổng hợp cho báo cáo: [results/tables/summary_kinrow.md](results/tables/summary_kinrow.md).

## Cài đặt
Xem [docs/SETUP.md](docs/SETUP.md) (venv `.venv`, Python 3.11+, `python -m pip install -r requirements.txt`). Windows: dùng `python`, không dùng `python3`.

```powershell
python -m pytest -q                              # test (phải xanh)
python -m ruff check . --fix; python -m ruff format .
python -m gameai.experiments.plots --check       # bảng/hình báo cáo sinh lại từ results/raw
python -m gameai.gui.pygame_app                  # GUI (sau P6)
```

## Quy ước làm việc nhóm (D-27)
- **Branch:** `master` = bản ổn định / nộp được, chỉ merge từ `develop` ở mốc, **không commit thẳng**. `develop` = tích hợp. Mỗi task một branch `feat/<task-id>` (vd. `feat/P6.1`) tạo từ `develop`; merge về `develop` khi `pytest` + `ruff` xanh và spec-reviewer PASS.
- **Commit:** `<TaskID>: <mô tả ngắn>` (vd. `P3.1: MCTS-UCT core with root stats`). Không push khi chưa thống nhất.
- **Golden test:** `tests/test_regression_kinrow.py` phải luôn xanh (hành vi k-in-row khóa ở `kinrow-final`).
- **Không sửa `gameai/agents/`** (và interface `Game`/`Agent`) khi chưa ghi lý do vào `docs/DECISIONS.md`; sửa agent thì thêm tham số có mặc định giữ hành vi cũ.
- **Mỗi module `X.py` có `X.md` cạnh nó** theo [docs/MODULE_TEMPLATE.md](docs/MODULE_TEMPLATE.md), cập nhật cùng thay đổi code.
- **PROGRESS.md:** mỗi người chỉ sửa dòng task của mình (cột Owner); session log chỉ thêm ở đầu, không sửa dòng của người khác.
- **Dữ liệu:** không sửa tay `results/raw/`; bảng/hình chỉ sinh bằng script trong `gameai/experiments/`. File `*quick*` và `results/*.log` không commit.
- **Thí nghiệm dài (> 2 phút):** chạy `--quick` trước, báo thời gian ước tính, hỏi trước khi chạy full.
