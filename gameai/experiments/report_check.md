# report_check — `gameai/experiments/report_check.py`

**Trạng thái:** ✅ ổn định · **Task:** P7.2 · **Cập nhật:** 2026-11-18

## Mục đích
Đối chiếu **mọi số** trong `report/report.md` với nguồn trong `results/` (CLAUDE.md: "không bịa số liệu"; D-30). Chạy trước
mỗi commit báo cáo và ở bước kiểm cuối P7.2.

## Cách chạy
```
python -m gameai.experiments.report_check              # report/report.md
python -m gameai.experiments.report_check FILE.md
```
In từng lỗi `L<dòng>: …` + dòng tổng `N số có nguồn, M bảng src-table, Tóm tắt W từ, K lỗi`; exit 1 nếu có lỗi.

## Cú pháp nguồn trong report (comment HTML — pandoc bỏ qua khi sang docx)
| Comment | Ý nghĩa / kiểm gì |
|---|---|
| `0,92 <!-- src: results/tables/e3_greedy.csv \| part=greedy,c=1.4,iterations=5000,split=all \| win_rate -->` | Lọc **đúng 1 hàng** (so chuỗi, như `plots._one`; `-` = không lọc); văn bản ngay trước comment phải **kết thúc bằng** giá trị định dạng `plots.vn` với số chữ số thập phân của token (cho phép ` %` sau số). Nhóm nghìn theo token (5000 / 5 000 đều được nếu giá trị khớp). |
| `… \| wins/draws/losses -->` | Ghép cột bằng `/` → so nguyên văn `46/0/4`. |
| `0,62 [0,48; 0,74] <!-- src: … \| … \| win_rate,win_lo,win_hi -->` | Cột `x,lo,hi` → so nguyên văn `x [lo; hi]` (số chữ số thập phân theo token cuối). Một comment phủ cả ba số. |
| `… \| win_rate \| x100 -->` | Biến đổi: `x100` (tỷ lệ → %), `abs` (bỏ dấu). |
| `… \| cpu -->` | Giá trị không phải số → so chuỗi (tên CPU, phiên bản Python từ `p72_env.csv`). |
| `0,62 <!-- src: summary_kinrow.md#E5 -->` | Token số cuối trước comment phải có **nguyên văn** trong mục có tiêu đề **bắt đầu bằng** `E5` (tới tiêu đề cùng cấp/cao hơn kế tiếp); neo phải khớp đúng 1 tiêu đề. Không neo theo số dòng. |
| `0,62 [0,48; 0,76] <!-- src: summary_kinrow.md#E5 -->`, `0,915–0,980 <!-- src: …#E3 -->` | Nếu văn bản trước comment kết thúc bằng `x [lo; hi]` hoặc khoảng `a–b`, **cả chuỗi** phải có nguyên văn trong mục; một comment phủ mọi số trong chuỗi. |
| `<!-- src-table: summary_kinrow.md#Bảng E3 — W/D/L của MCTS, 3×3 vs Random -->` | Khối bảng md ngay sau comment phải **giống byte** khối bảng đầu tiên của mục đó. Số trong bảng không bị quét "số trần". |
| `<!-- const: D-18 -->` | Mọi số trên dòng là hằng số thiết kế (lưới c, số ván, iteration); mọi `D-xx` phải là tiêu đề trong `docs/DECISIONS.md`. |
| `… <!-- const: D-18 \| 1000 5000 2,0 -->` | **Dạng liệt kê (ưu tiên trong câu có cả số đo):** chỉ các token liệt kê được miễn (so sau khi bỏ khoảng trắng: `20000` miễn `20 000`); mỗi token phải có **giá trị** xuất hiện trong văn bản mục D-xx đã nêu (dấu chấm hay phẩy đều được). Số đo khác trên dòng vẫn phải có `src`. |
| `<!-- example: gameai/agents/mcts.md -->` | Số trên dòng thuộc **ví dụ tính tay** chép từ mục "Giải thích cho báo cáo" của file `.md` đó (không phải số đo); file phải tồn tại. Đếm riêng ở dòng tổng để người duyệt thấy. |

Tên trần `summary_kinrow.md` → `results/tables/`; nguồn phải nằm trong `results/` (raw hoặc tables).

## Quy tắc "số trần"
Khối code ``` (pseudocode, trace) bỏ qua hoàn toàn — **quy tắc viết: không đặt số đo từ `results/` trong khối code** (An, 2026-11-18). Số **bắt buộc có nguồn**: có phẩy thập phân, hoặc ≥ 100, hoặc theo sau là `%`. Bỏ qua: dòng tiêu đề, code `` `…` ``,
công thức `$…$`, comment, đích link/ảnh, bảng `src-table`, mục "Tài liệu tham khảo", token dính chữ/dấu chấm (E3, h300,
D-18, P7.2, 3×3 vẫn là số < 100 nên không bị báo). Số nhỏ không thập phân (k = 5, 15×15, 4 bước) không cần nguồn.

## Kiểm thêm
- Ảnh `![…](đường dẫn)` tồn tại (tương đối thư mục của file report).
- Caption hình = **alt text kiểu pandoc** `![Hình n. Mô tả.](đường dẫn)` (một caption trong docx); dòng `**Hình …**` in đậm bị
  báo lỗi (caption đôi); ảnh không có alt bắt đầu bằng "Hình " bị báo lỗi. Bảng: dòng `**Bảng n.** …` ngay trên bảng.
  `Hình n.` / `Bảng n.` đánh số liên tiếp từ 1 (pandoc không có crossref — D-30); phụ lục dùng `Hình B.n.` (không đếm).
- Tóm tắt (mục có tiêu đề bắt đầu "Tóm tắt", bỏ comment) ≤ 200 từ (tách theo khoảng trắng).

## Public API
`check_text(text, decisions=None, base=REPORT.parent) -> (list[Issue], số từ Tóm tắt)`, `csv_value(path, filt, col)`,
`find_section(text, anchor)`, `expected_text(raw, before, transforms)`, `abstract_words(text)`, `main(argv)`.

## Phụ thuộc
`experiments/plots.vn` (cùng định dạng với summary). Được dùng bởi: kiểm P7.2 / P7.3.

## Test
`tests/test_report_check.py` (ROOT giả trong tmp): khớp / lệch CSV, lọc 0 hoặc ≥ 2 hàng, `x100`, nhóm nghìn, W/D/L, chuỗi,
không khớp một phần (10,92 ≠ 0,92), neo summary đúng / sai / không tồn tại, bảng giống byte / khác, số trần (3 lỗi đúng
chỗ), const D-xx có / không, khối ``` và `example:` (file có / không / thiếu), code + công thức + link bỏ qua, ảnh thiếu, caption hình trong alt + nhảy số + thiếu alt + dòng **Hình** bị cấm, Hình B.n không đếm, khoảng `x [lo; hi]` (CSV 3 cột, neo summary), khoảng `a–b`, const liệt kê token (miễn đúng token, token phải có trong D-xx), Tóm tắt > 200 từ, mục Tài liệu
tham khảo bỏ qua.

## Hạn chế
- Chỉ kiểm số **có trong comment nguồn** đúng là số trong nguồn — không kiểm diễn giải (vd. "tách CI") có đúng không.
- Số nhỏ không thập phân (< 100) không bắt buộc nguồn → số ván hòa/thắng nhỏ trong câu văn nên vẫn gắn `src` chủ động.
