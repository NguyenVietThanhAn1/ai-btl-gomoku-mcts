# plots - `gameai/experiments/plots.py`

> Mục tiêu của file này: agent/thành viên khác dùng được module **mà không cần đọc code**.
> Cập nhật cùng lúc với code.

**Trạng thái:** ✅ ổn định  ·  **Task:** P7.1, P7.2  ·  **Cập nhật:** 2026-11-18

## Mục đích
Sinh lại **mọi bảng/hình báo cáo k-in-row (E1-E6)** từ `results/raw` (không vẽ/gõ tay, không chạy search/ván nào)
và sinh `results/tables/summary_kinrow.md` - số chính mỗi E + bản đồ hình/bảng → mục 5 báo cáo. Nguồn cho P7.2.
Từ P8.5 (D-39) sinh lại cả bảng/hình **E7 cờ tướng** (`e7_xiangqi.build_tables`: `e7_matches`, `e7_ordering`,
`e7_branching`, `e7_scores.png`) và `results/tables/summary_xiangqi.md` (bảng E7 cho mục 5.7, neo `src-table`).

## Cách chạy
```
python -m gameai.experiments.plots           # ghi đè results/tables/*.csv, results/figures/*.png, summary_kinrow.md
python -m gameai.experiments.plots --check   # sinh vào thư mục tạm, so byte từng CSV **và `summary_kinrow.md`** với bản ĐÃ COMMIT (git show HEAD:…)
```
`--check` in `giống byte / khác / mới (chưa commit)`; exit 1 nếu có bảng hoặc summary khác. Summary được so vì `report/report.md` lấy nó làm nguồn (`src: summary_kinrow.md#…`, `src-table`); `check_outputs(new_dir, fig_dir, names, ref_dir, ref)` sinh summary vào `new_dir` rồi so cả bảng lẫn summary, dòng tổng đếm bảng + 2 summary (`summary_kinrow.md`, `summary_xiangqi.md`). CRLF/LF được chuẩn hóa trước khi so.
Thời gian ~1 phút (đọc raw E3/E5 lớn).

## Public API
- `regenerate(raw_dir, table_dir, fig_dir) -> (bảng, hình)`: E2-E6 + cơ chế E6 + E7 (`e7.build_tables`).
- `write_summary_xiangqi(table_dir) -> Path`, `section_e7(td)`: `summary_xiangqi.md` (5 bảng `### Bảng E7 - …`:
  ordering, các trận chốt trước, khám phá d3/d4, tìm kiếm MCTS vs AB, độ phân nhánh).
- `e2_tables`, `e3_tables`, `e4_tables(raw_dir, table_dir)`: bảng từ raw, **cùng hàm tóm tắt** như script gốc
  (`common.summarize`, `e2.summarize_*`, `e3.write_table`, `e4.summarize_roots / example_rows / score_ci`).
  E5/E6 dùng thẳng `e5_rollout.build_tables`, `e6_tactics.build_tables`, `e6_mechanism.build_table`; hình dùng
  `make_figures` của từng E, `e4.plot_match`, `e6_mechanism.make_figure`.
- **Tái dùng raw E3 ghim tag (2026-11-18):** `regenerate` truyền `reuse_check=pinned_reuse` cho `e5.build_tables` và
  `e6.build_tables` (tham số thêm, mặc định `e3_reusable`): `pinned_reuse` = `e3_reusable` với `diff_empty` so code
  với tag `PINNED_TAG = "kinrow-final"` thay vì HEAD → sinh lại bảng không phụ thuộc việc sau tag có sửa
  `agents/`, `heuristics/`… (P6.4, mặc định tắt). Lý do: không ghim thì mọi file mới trong các thư mục đó làm
  `--check` ném lỗi (E5 coi "code đổi", bỏ hàng E3). `pinned_tag_exists()` cho test.
- `compare(new_dir, ref_dir, names, ref=committed_bytes) -> [(tên, lý do)]`.
- `write_summary_md(table_dir, fig_dir) -> Path`; `REPORT_MAP` (mục, nội dung, E, hình, bảng); `SECTIONS[E]`;
  định dạng `vn(x, d)` (dấu phẩy thập phân; số nguyên ≥ 10 000 nhóm nghìn bằng khoảng trắng; số âm dùng "−" U+2212,
  giá trị làm tròn thành 0 không mang dấu), `ci(lo, hi, d)` = `[lo; hi]` với **luật làm tròn D-30**: nếu làm tròn tới d
  chữ số đổi kết luận chứa / không chứa 0 (dung sai 1e-9) hoặc 0,5, hay biến biên ≠ 0 thành 0 → thêm một chữ số cho
  cả hai biên (vd. `[0,004; 0,156]`, `[0,241; 0,499]`);
  `_one(rows, **kw)` = đúng 1 dòng khớp, không thì `KeyError` (không đoán).
- **Số trong hình kiểu VN (P7.2):** `vn`, `vn_tick`, `vn_figure`, `ratio_axis` nằm ở [figfmt.py](figfmt.md); `plots` chỉ
  import `vn`, `EPS` (re-export `plots.vn`). Mọi hàm vẽ E3-E6 gọi `vn_figure(fig)` ngay trước `tight_layout`/`savefig`
  (tick cùng số chữ số trên một trục, trục log chỉ major có nhãn) và `ratio_axis(ax)` ở trục tỷ lệ (không tick > 1).
- **Bảng cho báo cáo trong summary (P7.2, D-30):** mỗi bảng có tiêu đề `### Bảng E… - …` riêng, duy nhất (`_table`) -
  đây là neo `<!-- src-table: summary_kinrow.md#<tiêu đề> -->` mà `report_check` so byte với bảng chép trong
  `report/report.md`. Gồm: E1 nút/thời gian; E2 W/D/L; E3 win rate vs Greedy + **W/D/L** (hàng iter × cột c, `_wdl_rows`)
  cho 3×3 vs Random, 3×3 vs Minimax, 15×15 vs Greedy, 15×15 vs AB2; E4 ví dụ gốc 3×3 (trace) + **ví dụ 15×15**
  (`example = sensitivity`, thế đầu tiên, có W/N/W/N tham chiếu 20 000 iter). Chỉ đổi summary, không đổi CSV.

## Nguồn của từng bảng
| E | Nguồn | Ghi chú |
|---|---|---|
| E1 | **không có raw** | `e1_*.csv` là kết quả đo trực tiếp (giá trị, nút, thời gian) → chỉ kiểm tồn tại |
| E2 | `raw/e2_{iter}_vs_{opp}.csv` (+`_moves`), `raw/e2_exhaustive{,_mistakes}.csv` | mistakes: ép int các cột số trước khi tóm tắt (giữ thứ tự sắp xếp) |
| E3 | `raw/e3_{part}_c{c}_i{iter}.csv` | pilot AB2 = **10 cặp đầu** (`pair_seed < 10`) của file AB2 cùng (c, 5000): file đó được chạy tiếp tới 25 cặp ở bước ab2 |
| E4 | `raw/e4_roots_{3x3,15x15}.csv`, `raw/e4_match_3x3_i*.csv` | |
| E5, E6 | raw E5/E6 (+E3 tái dùng) | hàm `build_tables` sẵn có |

**Bảng đo trực tiếp** (`MEASURED`, không sinh lại; bảng khác đọc chúng): `e1_*`, `e5_bench`, `e6_bench`, `e6_sanity`,
`e6_cost_check`, `e6_positions_summary` (`e5_rates` ← `e5_bench`; `e6_choice` ← `e6_sanity` + `e6_positions_summary`).
`--check` copy chúng vào thư mục tạm trước khi sinh.

## Bản đồ hình/bảng → mục 5 báo cáo
| Mục | E | Hình | Bảng chính |
|---|---|---|---|
| 5.1 Minimax vs AB | E1 | - | `e1_summary` (bảng nút), `e1_nodes`, `e1_positions` |
| 5.2 MCTS 3×3 không thua | E2 | - | `e2_play` (W/D/L), `e2_exhaustive{,_by_role}` |
| 5.3 Hằng số c | E3 | `e3_3x3`, `e3_greedy`, `e3_ab2` (iter-win rate, mỗi c một đường) | `e3_3x3_{random,minimax}`, `e3_greedy`, `e3_ab2{,_pilot}` (W/D/L 15×15) |
| 5.4 N vs W/N | E4 | `e4_match` | `e4_roots_examples` (W, N, W/N ở gốc), `e4_roots_summary`, `e4_match` |
| 5.5 Rollout | E5 | `e5_iter`, `e5_time` | `e5_paired`, `e5_h2h`, `e5_greedy`, `e5_mref`, `e5_ab2`, `e5_bench`, `e5_rates` |
| 5.6 check_tactics | E6 | `e6_choice`, `e6_match`, `e6_mechanism` | `e6_choice`, `e6_match`, `e6_paired`, `e6_mechanism`, `e6_cost_check`, `e6_time`, `e6_tactic_rate` |
| 5.7 Cờ tướng | E7 | `e7_scores` | `e7_ordering`, `e7_matches`, `e7_branching` (+ `summary_xiangqi.md`); `e7_term_check` đo trực tiếp |

## Kết quả kiểm (2026-11-18, sau commit `1fac6f7`)
`--check`: 25 bảng + `summary_kinrow.md` sinh lại, **26 giống byte** với bản đã commit, 0 khác, 0 mới (9 hình sinh lại). Lịch sử: 2026-11-17 (sau `e98dc49`) là 25 bảng, 24 giống byte, 1 mới (`e6_mechanism.csv`), chưa so summary.

## Phụ thuộc
`experiments/{common,e2_never_lose,e3_c_sweep,e4_final_move,e5_rollout,e6_tactics,e6_mechanism,e7_xiangqi}.py`, matplotlib (Agg), `git`.

## Test
`tests/test_plots.py`: `test_tables_do_not_depend_on_head` (giả lập `git_diff_empty(target="HEAD")` → False, bảng E5/E6 vẫn giống byte); `vn`/`ci` (gồm luật làm tròn D-30, dấu "−"; tick hình: `tests/test_figfmt.py`); `_one` báo lỗi khi 0 hoặc ≥ 2 dòng; `compare` (giống sau chuẩn hóa CRLF / khác / mới); `check_outputs` (hai summary giống / lệch một chữ → báo đúng tên + dòng / mới); `summary_xiangqi.md` từ CSV (5 tiêu đề không trùng, d3/d4 chỉ ở bảng khám phá, W/D/L khớp, không gạch dài);
lọc 10 cặp đầu + moves tương ứng; tóm tắt mistakes E2 từ chuỗi = từ int (gồm thứ tự); `summary_kinrow.md` sinh được từ
bảng thật, chứa số lấy từ CSV (mẫu E1/E2/E6), mọi file được nhắc tới tồn tại. P7.2: tiêu đề `###` không trùng; W/D/L E3 khớp CSV, W + D + L = n; ví dụ E4 15×15 có cột tham chiếu. Chạy: `python -m pytest tests/test_plots.py -q`.

## Hạn chế / TODO
- E1 và các bảng đo trực tiếp không kiểm được bằng sinh lại (chỉ kiểm tồn tại).
- `e5_time.png`: tiêu đề panel dưới-giữa từng tràn sang panel phải - đã sửa ở P7.2 (`e5_rollout.make_figures` dùng tên ngắn); chỉ PNG đổi, `--check` 25/25 CSV giống byte.
