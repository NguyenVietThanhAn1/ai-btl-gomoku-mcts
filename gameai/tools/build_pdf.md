# Xuất báo cáo PDF — `gameai/tools/build_pdf.py`

> Mục tiêu của file này: agent/thành viên khác dùng được module **mà không cần đọc code**.
> Cập nhật cùng lúc với code.

**Trạng thái:** ✅ ổn định  ·  **Task:** P7.3 (D-40)  ·  **Cập nhật:** 2026-11-26

## Mục đích
Sinh `report/report.pdf` (bản nộp, D-34) từ `report/report.md`. **Không sửa tay PDF**; đổi báo cáo/hình thì build lại.

## Cách chạy
```
python -m gameai.tools.build_pdf                      # → report/report.pdf (~1 phút)
python -m gameai.tools.build_pdf --pages              # thêm: trang của từng mục / bảng / hình
python -m gameai.tools.build_pdf --out X.pdf --keep DIR   # ra chỗ khác, giữ HTML trung gian
```
Cần có sẵn trên máy (không cài gói Python): **pandoc** (đã chạy với 3.14) và **Chrome/Edge** (Chrome 158; số trang
cần Chrome ≥ 131 vì dùng ô lề `@page`). Chỉ đường bằng biến môi trường `PANDOC`, `CHROME`. Font hệ thống Windows:
Times New Roman, Consolas, Cambria Math.

## Đường đi
`report.md` → bỏ comment nguồn số liệu → pandoc `gfm+tex_math_dollars+yaml_metadata_block+implicit_figures`
(công thức thành MathML) → HTML + CSS A4 → Chrome headless in PDF. Bố cục: trang 1 tiêu đề + Tóm tắt, rồi mục lục
(có số trang, bấm được), thân bài từ trang mới. Thân 11,5 pt; bảng 9,5 pt (tự thu nếu rộng, sàn 8 pt); công thức khối
rộng thu tới ≥ 9,5 pt; khối mã dài thu tới ≥ 8 pt; hình thí nghiệm một đồ thị in rộng 120 mm.
Số trang mục lục lấy từ chính PDF (in 2 lượt; đọc đích nội bộ bằng thư viện chuẩn).

## Tự kiểm khi build (lỗi → exit ≠ 0, không ghi đè PDF)
- Bảng / hình đánh số liên tục (1, 2, … và B.1, B.2, …); mọi "Bảng N" / "Hình N" trong lời văn có đích (thành liên kết).
- Mọi ảnh tồn tại; pandoc không cảnh báo (công thức không dịch được).
- Không bảng / công thức / khối mã / ảnh nào rộng hơn vùng chữ 170 mm.
- Mọi liên kết nội bộ có đích; mọi font được nhúng.

Không kiểm số liệu: dùng `report_check` và `plots --check` (có trong `precheck`).

## Public API
```python
build(src=SRC, out=OUT, keep=None) -> dict[str, int]   # id (sec-N, tab-N, fig-N) → số trang
prepare(src) -> (meta, thân HTML, mục lục)             # SystemExit nếu lỗi cấu trúc
strip_comments / typography / decimal_commas / label_captions / link_mentions / sequence_errors
pdf_objects / pdf_pages / pdf_dests / pdf_fonts        # chỉ cho PDF do Chrome sinh
```

## Test
`tests/test_build_pdf.py` — hàm thuần (không cần pandoc/Chrome). Dàn trang phải xem bằng mắt sau khi build.

## Hạn chế
- PDF không giống byte giữa các lần build (ngày tạo); nội dung và số trang giống nhau trên cùng máy. Máy khác font /
  phiên bản Chrome → ngắt trang có thể khác.
- `typography` đổi `0{,}5` → MathML "0,5"; công thức không được dùng dấu chấm thập phân.
- Tiêu đề hình bên trong PNG thí nghiệm vẫn như `plots.py` sinh.
