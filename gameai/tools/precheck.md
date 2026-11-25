# precheck — `gameai/tools/precheck.py`

**Trạng thái:** ✅ ổn định  ·  **Task:** P6.4 (hạ tầng; sau sự cố push 2026-11-18)  ·  **Cập nhật:** 2026-11-18

## Mục đích
Một lệnh kiểm tra trước mỗi push `develop`, thay cho chạy tay từng lệnh (và tránh lỗi lấy exit code của `| tail`).

## Public API
```
python -m gameai.tools.precheck        # exit 0 = mọi bước PASS, 1 = có bước FAIL
```
```python
precheck(steps=STEPS, runner=run_command, tail=15, out=print) -> int
run_command(cmd) -> (exit_code, output)   # subprocess ở gốc repo, không shell/pipe, UTF-8
STEPS = [pytest -q, ruff check ., ruff format --check ., report_check, plots --check]
```
- Chạy **mọi** bước (không dừng ở lỗi đầu), in `[PASS]/[FAIL] <bước> (giây, exit)`; bước FAIL in thêm `tail` dòng cuối
  của output; cuối cùng in bảng tóm tắt `precheck: k/5 PASS`. Exit code của tiến trình = 1 nếu có bước FAIL.
- Chạy bằng `sys.executable` (cùng venv đang chạy). Thời gian ~ vài phút (pytest + `plots --check` chiếm phần lớn).

## Phụ thuộc
Dùng: `pytest`, `ruff`, `gameai.experiments.report_check`, `gameai.experiments.plots`. Được nhắc ở AGENTS.md, WORKFLOW.md §1 bước 9, README.

## Thiết kế & quyết định
- Python (không shell) để chạy giống nhau trên Windows; runner tiêm được để test không chạy lệnh thật.
- Luật: chỉ báo "xanh" / push khi `python -m gameai.tools.precheck; echo EXIT=$?` ra `EXIT=0` (không pipe).

## Test
`tests/test_precheck.py`: tất cả PASS → 0; một bước FAIL → 1 nhưng vẫn chạy hết các bước + in đuôi; danh sách bước đúng 5
lệnh; `run_command` trả exit code thật (7).

## Hạn chế / TODO
Không có `--skip`/`--only` (cố ý: một đường duy nhất). Không thay `git fetch` + `git rebase` (vẫn làm tay, từng lệnh).
