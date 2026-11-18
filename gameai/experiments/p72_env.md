# p72_env — `gameai/experiments/p72_env.py`

**Trạng thái:** ✅ ổn định · **Task:** P7.2 · **Cập nhật:** 2026-11-18

## Mục đích
Ghi môi trường phần mềm (Python, numpy/pandas/matplotlib/pygame/pytest, OS) vào `results/tables/p72_env.csv` để mục 4
báo cáo có nguồn. Runinfo của E5/E6 chỉ ghi CPU, số luồng, nguồn điện, commit — **không** ghi phiên bản Python.

## Public API
```python
collect() -> list[dict[str, str]]   # [{"key": "python", "value": "3.12.x"}, ..., {"key": "recorded", ...}]
write(path=OUT) -> Path             # ghi CSV 2 cột key,value
```
Chạy: `python -m gameai.experiments.p72_env`.

## Phụ thuộc
- Chỉ thư viện chuẩn (`platform`, `importlib.metadata`).
- Được dùng bởi: `report/report.md` mục 4 (nguồn `src`).

## Thiết kế & quyết định
- Đo **lúc viết báo cáo** (cột `recorded`), cùng venv chạy thí nghiệm — báo cáo ghi rõ điều này (D-30). Không ghi RAM
  (không có nguồn đo đáng tin trong thư viện chuẩn).
- CPU / số luồng / nguồn điện lấy từ `results/raw/e5_runinfo.csv`, `e6_runinfo.csv`, không lặp ở đây.

## Test
- `tests/test_p72_env.py`: có khóa `python` khớp `sys.version_info`, đủ các gói, CSV đọc lại được.

## Hạn chế / TODO
- Không chứng minh phiên bản lúc chạy E1–E6 trùng phiên bản lúc ghi (venv không đổi theo `requirements.txt`, nhưng không
  có bản ghi thời điểm chạy).
