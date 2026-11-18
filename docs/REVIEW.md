# REVIEW — checklist review độc lập một task

Luật dự án: [AGENTS.md](../AGENTS.md). Giao cho agent bất kỳ bằng câu: **"Review task `<ID>` theo docs/REVIEW.md"** (Claude Code: subagent `spec-reviewer`). Nên review ở phiên/agent khác với phiên đã code.

Reviewer **KHÔNG sửa file** — chỉ đọc, chạy test và báo cáo.

## Các bước

1. Đọc mục task `<ID>` trong `PLAN.md` → liệt kê từng tiêu chí "Done khi" + Definition of Done (§5).
2. Xác định file liên quan (theo `PLAN.md` §2 và `PROGRESS.md`). Đọc code + `.md` cạnh code.
3. Chạy:
   ```
   python -m pytest -q
   python -m ruff check .
   ```
4. Kiểm tra:
   - Mỗi tiêu chí có test chứng minh không? Test có thực sự kiểm tra hành vi (không phải `assert True`)?
   - `.md` có đủ mục theo `docs/MODULE_TEMPLATE.md`; Public API trong `.md` khớp chữ ký thật trong code.
   - Đúng thuật toán theo đề: UCT = W/N + c·sqrt(ln N_p / N); chọn nước cuối theo N lớn nhất (mặc định); W theo góc nhìn người vừa đi; alpha-beta trả cùng giá trị minimax; ngẫu nhiên có seed.
   - Không có số liệu thí nghiệm bị sửa tay / hard-code.
   - Golden test `tests/test_regression_kinrow.py` xanh.
5. Trả về đúng định dạng dưới.

## Định dạng output

```
TASK <ID> — PASS | FAIL
Tiêu chí:
- [PASS|FAIL] <tiêu chí> — <bằng chứng: tên test / file:dòng>
Doc sync: PASS|FAIL — <chi tiết lệch>
Test: <n passed / failed>; Ruff: <sạch / n lỗi>
Cần sửa (theo mức ưu tiên):
1. ...
```
