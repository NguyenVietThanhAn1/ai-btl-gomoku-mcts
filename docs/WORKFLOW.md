# WORKFLOW — quy trình làm task (mọi người / mọi agent)

Luật dự án: [AGENTS.md](../AGENTS.md). File này chỉ là checklist thao tác. Giao cho agent bất kỳ bằng câu:
**"Làm task `<ID>` theo docs/WORKFLOW.md"** (bỏ trống ID = task tiếp theo). Claude Code: `/next-task <ID>` và `/wrap-up` gọi đúng các mục dưới.

## 1. Làm task

> Lệnh git chạy **từng lệnh một, kiểm exit code** trước bước sau; không pipe `git pull/push/merge/rebase` qua `tail`/`head` trong chuỗi `&&`. Gặp lỗi "Cannot rebase onto multiple branches": xem [AGENTS.md § Lệnh nguy hiểm](../AGENTS.md).

Task: `<ID>` được giao; nếu không có → task 🔄 đang dở của mình, hoặc task ⬜ đầu tiên theo thứ tự trong `PROGRESS.md`. Làm đúng thứ tự, không bỏ bước.

- [ ] **0. Đồng bộ.** Làm trên `develop` (D-32): `git switch develop`, rồi `git fetch origin` rồi `git rebase origin/develop` (từng lệnh, kiểm exit code; xem AGENTS.md mục Lệnh nguy hiểm). Không làm việc trên `master`. (Feature branch chỉ khi thay đổi lớn/rủi ro.) Nếu task đụng vùng nhạy cảm (`gameai/agents/`, interface `Game`/`Agent`, `gameai/core/`, `results/`, `report/report.md`) → **dừng, báo người dùng/người kia trước**.
- [ ] **1. Định vị.**
  - Đọc `PROGRESS.md`: khối "Đang ở đâu" của mình + dòng của task.
  - Đọc phần task trong `PLAN.md` (mục tiêu, output, "Done khi") + §5 Definition of Done.
  - Đọc `.md` của các module phụ thuộc. Không đọc source không liên quan.
- [ ] **2. Kế hoạch ngắn** (≤ 10 dòng): file sẽ tạo/sửa, test sẽ viết, rủi ro. Nếu task lớn hoặc đụng interface `Game`/`Agent` → **dừng, trình kế hoạch, chờ người xác nhận**.
- [ ] **3. Đánh dấu bắt đầu:** trong `PROGRESS.md` đổi dòng task sang 🔄, điền Owner, cập nhật khối "Đang ở đâu" của mình.
- [ ] **4. Test trước:** viết test theo "Done khi" của `PLAN.md`.
- [ ] **5. Code** cho tới khi `python -m pytest -q` xanh (gồm golden `tests/test_regression_kinrow.py`) và `python -m ruff check .` sạch.
- [ ] **6. Module doc:** tạo/cập nhật `X.md` cạnh mỗi `X.py` đã đổi theo `docs/MODULE_TEMPLATE.md` (module thuật toán phải có mục "Giải thích cho báo cáo").
- [ ] **7. Tự kiểm:** review theo [docs/REVIEW.md](REVIEW.md) với task ID — tốt nhất bằng một phiên/agent khác hoặc người khác (Claude Code: subagent `spec-reviewer`). Sửa mọi điểm FAIL.
- [ ] **8. Cập nhật `PROGRESS.md`:** dòng task → ✅ (hoặc giữ 🔄 + ghi còn dở gì), cột Cập nhật = ngày hôm nay; thêm session log ở đầu khối log của mình (đã làm, số test pass, file đổi, lưu ý); sửa khối "Đang ở đâu" của mình → bước tiếp theo cụ thể. Quyết định thiết kế mới → thêm vào `docs/DECISIONS.md`.
- [ ] **9. Commit & push:** `git add -A` rồi `git commit -m "<ID>: <mô tả>"`; `git fetch origin` rồi `git rebase origin/develop`; chạy lại `python -m pytest -q` + `python -m ruff check .` (đụng `report/` hoặc `gameai/experiments/`: thêm `report_check` + `python -m gameai.experiments.plots --check`); rồi **hỏi người dùng trước khi** `git push` lên `develop`. Cấm `--force`.
- [ ] **10. Báo cáo** (ngắn): đã làm gì, kết quả test, điều cần người quyết định, task tiếp theo.

## 2. Kết thúc phiên (wrap-up)

Dùng khi dừng giữa chừng hoặc xong task, để một người/agent mới (không có lịch sử hội thoại) tiếp tục được ngay.

- [ ] **1.** Xem lại thay đổi trong phiên: `git status`, `git diff --stat`.
- [ ] **2.** Chạy `python -m pytest -q`, ghi kết quả (kể cả khi đỏ: test nào đỏ, vì sao).
- [ ] **3.** Với mỗi `.py` đã đổi: `.md` cạnh nó còn khớp (API, trạng thái)? Sửa nếu lệch.
- [ ] **4.** Cập nhật `PROGRESS.md` — **chỉ dòng task của mình, khối "Đang ở đâu" và khối session log của Owner hiện tại** (`### <Tên>`), không đụng khối người khác:
  - Bảng: ✅ / 🔄 / ⛔ đúng thực tế. Không đánh ✅ nếu test chưa xanh hoặc thiếu `.md`.
  - "Đang ở đâu": task hiện tại; **việc đang dở cụ thể** (file, hàm, đang thử gì); **bước tiếp theo** dạng hành động; blocker.
  - Thêm một mục session log ở đầu khối log của mình.
  - Có kết quả thí nghiệm mới: ghi số liệu chính + đường dẫn file trong `results/`.
- [ ] **5.** Có quyết định thiết kế → thêm vào `docs/DECISIONS.md`.
- [ ] **6.** Commit WIP: `git add -A && git commit -m "<ID>: WIP - <mô tả>"`; `git fetch origin` rồi `git rebase origin/develop`; chạy pytest + ruff (như bước 9 mục 1); hỏi người dùng trước khi `git push` lên `develop`.
- [ ] **7.** In 3–5 dòng: đã xong gì, còn dở gì, câu lệnh để tiếp tục ("Làm task `<ID>` theo docs/WORKFLOW.md" / `/next-task <ID>`).
