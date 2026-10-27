---
name: next-task
description: Làm task tiếp theo (hoặc task ID được chỉ định) của BTL theo PLAN.md, kèm test, module .md và cập nhật PROGRESS.md.
argument-hint: "[task-id, vd. P3.1 — bỏ trống = task tiếp theo]"
disable-model-invocation: true
---

Task được yêu cầu: $ARGUMENTS (nếu trống → task ⬜ đầu tiên theo thứ tự trong PROGRESS.md, hoặc task 🔄 đang dở).

Quy trình — làm đúng thứ tự, không bỏ bước:

1. **Định vị**
   - Đọc `PROGRESS.md` (mục "Đang ở đâu" + dòng của task).
   - Đọc phần task đó trong `PLAN.md` (mục tiêu, output, "Done khi").
   - Đọc `.md` của các module phụ thuộc. Không đọc source không liên quan.
2. **Kế hoạch ngắn** (≤10 dòng): file sẽ tạo/sửa, test sẽ viết, rủi ro. Nếu task lớn hoặc đụng interface → dừng, trình kế hoạch, chờ xác nhận.
3. **Đánh dấu bắt đầu:** trong PROGRESS.md đổi task sang 🔄, cập nhật "Đang ở đâu".
4. **Test trước khi code xong:** viết test theo "Done khi" của PLAN.md.
5. **Code** cho tới khi `python -m pytest -q` xanh và `python -m ruff check .` sạch.
6. **Module doc:** tạo/cập nhật `X.md` cạnh mỗi `X.py` đã đổi, theo `docs/MODULE_TEMPLATE.md` (module thuật toán phải có mục "Giải thích để vấn đáp").
7. **Tự kiểm:** gọi subagent `spec-reviewer` với task ID để đối chiếu acceptance criteria + đồng bộ `.md`. Sửa các điểm nó báo FAIL.
8. **Cập nhật PROGRESS.md:** task → ✅ (hoặc giữ 🔄 + ghi rõ còn dở gì), cột Cập nhật = ngày hôm nay, thêm session log (đã làm, số test pass, file đổi, lưu ý), sửa "Đang ở đâu" → bước tiếp theo cụ thể. Nếu có quyết định thiết kế mới → thêm vào `docs/DECISIONS.md`.
9. **Commit** (nếu là git repo): `git add -A` rồi `git commit -m "<TaskID>: <mô tả>"`. Không push.
10. **Báo cáo cho người dùng** (ngắn): đã làm gì, kết quả test, điều cần người dùng quyết định, task tiếp theo. Kèm 1–2 câu hỏi kiểm tra hiểu bài nếu task là thuật toán.
