# AGENTS.md — BTL Trí tuệ nhân tạo (Bài 1: k-in-a-row, Minimax/Alpha-Beta, MCTS-UCT, Cờ tướng)

> **Quy trình làm task:** [docs/WORKFLOW.md](docs/WORKFLOW.md). **Review:** [docs/REVIEW.md](docs/REVIEW.md).
> File này là **nguồn luật duy nhất** cho mọi agent (Claude Code, Codex, Cursor, Copilot, Gemini…) và người code tay (D-31). File khác chỉ link tới đây, không chép lại.

## Bắt đầu mỗi phiên — đọc theo thứ tự, KHÔNG đọc toàn bộ source
1. `PROGRESS.md` → mục "Đang ở đâu" (khối của mình).
2. `PLAN.md` → chỉ phần của task hiện tại.
3. File `.md` cạnh các module liên quan (vd. `gameai/agents/mcts.md`). Chỉ mở `.py` khi cần sửa hoặc khi `.md` thiếu/không khớp.
4. `docs/DECISIONS.md` nếu task đụng tới interface hoặc thiết kế chung.

## Quy tắc bắt buộc
- **Một task một lần.** Không làm sang task khác khi chưa cập nhật PROGRESS.
- **Module doc:** mỗi `X.py` mới/đổi phải có `X.md` cạnh nó theo `docs/MODULE_TEMPLATE.md`. Cập nhật `.md` trong cùng thay đổi với code. `.md` phải đủ để agent khác dùng module mà không đọc code.
- **PROGRESS.md** là nơi duy nhất ghi trạng thái. Cuối task: cập nhật bảng, "Đang ở đâu", thêm session log. Nếu dừng giữa chừng: ghi rõ đã làm gì, còn dở gì, bước tiếp theo cụ thể.
- **Không đổi interface `Game`/`Agent`** (xem PLAN.md §2) khi chưa ghi lý do vào `docs/DECISIONS.md`.
- **Không sửa tay dữ liệu thí nghiệm** trong `results/raw/` (không sửa, không xóa file trong đó). Bảng/hình chỉ sinh bằng script trong `gameai/experiments/`.
- **Không bịa số liệu** vào báo cáo; mọi con số phải truy được về file trong `results/`.
- Thí nghiệm dài (> 2 phút): chạy `--quick` trước, báo thời gian ước tính, hỏi trước khi chạy full.
- Hỏi lại khi đề bài mơ hồ thay vì tự chọn rồi im lặng; ghi lựa chọn vào DECISIONS.md.

## Lệnh nguy hiểm — cấm / phải hỏi
(Trước đây chỉ ép bằng `.claude/settings.json`; agent khác không đọc file đó nên ghi thành luật ở đây.)
- **Cấm:** xóa đệ quy (`rm -rf`, `Remove-Item -Recurse`), `git reset --hard`, sửa/xóa file trong `results/raw/`.
- **Cấm:** `git push --force` / `-f`.
- **Phải hỏi người trước:** cài gói mới (`pip install <gói>`; riêng `python -m pip install -r requirements.txt` thì được), mọi `git push` (xem mục Commit & push).
- Được chạy không cần hỏi: pytest, ruff, `python -m gameai…`, `git status/diff/log/add/commit`.
- **Không pipe output của `git pull/push/merge/rebase` qua `| tail`/`| head` trong chuỗi `&&`** — exit code của pipeline là của lệnh cuối, lỗi bị nuốt. Chạy từng lệnh, kiểm exit code trước khi làm bước tiếp.
- **Nếu `git pull --rebase` báo "Cannot rebase onto multiple branches":** chạy ngay `git branch -vv` và `cat .git/FETCH_HEAD` để lưu bằng chứng, rồi dùng `git fetch origin` + `git rebase origin/develop`.

## Làm việc nhóm (D-32, thay D-27/D-31 phần branch/push — chi tiết: [README.md § Quy ước làm việc nhóm](README.md#quy-ước-làm-việc-nhóm-d-32))
- Làm và commit **thẳng trên `develop`**. Feature branch chỉ khi thay đổi lớn/rủi ro (không bắt buộc).
- **Trước mỗi push `develop`:** `git pull --rebase`; `python -m pytest -q` (gồm `tests/test_regression_kinrow.py`) + `python -m ruff check .` xanh; nếu đụng `report/` hoặc `gameai/experiments/`: thêm `report_check` + `python -m gameai.experiments.plots --check`.
- **Cấm** `git push --force` (và `-f`), cấm rebase commit đã push.
- **Vùng nhạy cảm:** `gameai/agents/`, interface `Game`/`Agent`, `gameai/core/`, `results/`, `report/report.md` → báo người kia trước khi sửa. **Agent phải dừng và hỏi người dùng trước khi sửa vùng này.**
- `master`: chỉ merge từ `develop` ở mốc, qua PR "Create a merge commit" (không squash); không push thẳng `master`.
- Trong `PROGRESS.md` chỉ sửa **dòng task của mình** (cột Owner), **khối "Đang ở đâu" của mình** (`### <Tên>`) và **khối session log của mình**; log mới nhất ở đầu khối.
- Số quyết định `D-xx` trong `docs/DECISIONS.md`: lấy số ngay sau `git pull`; nếu rebase thấy trùng số thì người rebase sau đổi số của mình.
- Golden test `tests/test_regression_kinrow.py` phải luôn xanh.

## Lệnh
- Môi trường: Windows, venv `.venv`. Dùng `python`, không dùng `python3`.
- Test: `python -m pytest -q` (một file: `python -m pytest tests/test_mcts.py -q`)
- Lint/format: `python -m ruff check . --fix` và `python -m ruff format .`
- Chạy module: `python -m gameai.cli ...`, `python -m gameai.experiments.e3_c_sweep --quick`

## Code style
- Python 3.11+, type hints cho hàm public, docstring ngắn. Tên biến/hàm tiếng Anh; `.md` và báo cáo tiếng Việt.
- Ưu tiên rõ ràng hơn tối ưu vi mô, NHƯNG đường nóng của MCTS/rollout (play, win check, candidate moves) phải nhanh: không copy cả bàn trong vòng lặp nếu tránh được, win check chỉ quanh nước vừa đi.
- Mọi thứ ngẫu nhiên nhận `seed` / `random.Random` riêng — không dùng `random` toàn cục.
- Agent ghi thống kê vào `self.stats` (nodes, iterations, time) để thí nghiệm đọc.

## Thuật ngữ (giữ thống nhất trong code, doc, báo cáo)
- `W`, `N`: tổng điểm và số lần thăm của node; điểm tính theo góc nhìn **người vừa đi vào node** (thắng 1, hòa 0.5, thua 0).
- `N_p`: số lần thăm node cha. `c`: hằng số khám phá.
- `candidate_moves`: các ô trống trong bán kính `radius` quanh quân đã đặt.

## Sản phẩm nộp
Sản phẩm nộp: **báo cáo .docx + video demo** (không vấn đáp). Với module thuật toán (minimax, alphabeta, mcts, rollout, eval), mục "Giải thích cho báo cáo" trong `.md` là bắt buộc: bản chất, công thức/pseudocode, ví dụ nhỏ trace tay. Đây là nguyên liệu cho mục 3 (Phương pháp) của báo cáo, viết sao cho chép sang báo cáo được gần như nguyên văn.

## Commit & push
- Message: `<TaskID>: <mô tả ngắn>` — ví dụ `P3.1: MCTS-UCT core with root stats`. Không thêm trailer (Co-Authored-By, "Generated with…").
- **Được push `develop`** sau khi đã chạy các kiểm tra ở mục "Làm việc nhóm" và **hỏi người dùng trước** khi push. **KHÔNG push thẳng `master`**; không force-push.
