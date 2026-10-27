---
name: wrap-up
description: Kết thúc phiên làm việc - ghi lại chính xác tiến độ, việc dở và bước tiếp theo vào PROGRESS.md để phiên/agent sau tiếp tục được.
disable-model-invocation: true
---

Người dùng sắp dừng phiên. Ghi lại trạng thái để một agent mới (không có lịch sử hội thoại này) tiếp tục được ngay:

1. Xem lại những gì đã thay đổi trong phiên (`git status`, `git diff --stat` nếu có git; nếu không, dựa vào hội thoại).
2. Chạy `python -m pytest -q` và ghi kết quả (kể cả khi đỏ — ghi test nào đỏ và vì sao).
3. Với mỗi module `.py` đã đổi: kiểm tra `.md` cạnh nó còn khớp (API, trạng thái). Sửa nếu lệch.
4. Cập nhật `PROGRESS.md`:
   - Bảng trạng thái: ✅ / 🔄 / ⛔ đúng thực tế. Không đánh ✅ nếu test chưa xanh hoặc thiếu `.md`.
   - "Đang ở đâu": task hiện tại; **việc đang dở cụ thể** (file nào, hàm nào, đang thử gì); **bước tiếp theo** dạng hành động; blocker.
   - Thêm một mục session log ở đầu phần log.
   - Nếu có kết quả thí nghiệm mới: ghi số liệu chính + đường dẫn file.
5. Thêm vào `docs/DECISIONS.md` nếu phiên có quyết định thiết kế.
6. Commit WIP nếu là git repo: `git commit -am "<TaskID>: WIP - <mô tả>"`.
7. In ra cho người dùng 3–5 dòng: đã xong gì, còn dở gì, lệnh để tiếp tục (`/next-task <ID>`).
