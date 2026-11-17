# plots — `gameai/experiments/plots.py`

> Mục tiêu của file này: agent/thành viên khác dùng được module **mà không cần đọc code**.
> Cập nhật cùng lúc với code.

**Trạng thái:** ✅ ổn định  ·  **Task:** P7.1  ·  **Cập nhật:** 2026-11-17

## Mục đích
Sinh lại **mọi bảng/hình báo cáo k-in-row (E1–E6)** từ `results/raw` (không vẽ/gõ tay, không chạy search/ván nào)
và sinh `results/tables/summary_kinrow.md` — số chính mỗi E + bản đồ hình/bảng → mục 5 báo cáo. Nguồn cho P7.2.

## Cách chạy
```
python -m gameai.experiments.plots           # ghi đè results/tables/*.csv, results/figures/*.png, summary_kinrow.md
python -m gameai.experiments.plots --check   # sinh vào thư mục tạm, so byte từng CSV với bản ĐÃ COMMIT (git show HEAD:…)
```
`--check` in `giống byte / khác / mới (chưa commit)`; exit 1 nếu có bảng khác. CRLF/LF được chuẩn hóa trước khi so.
Thời gian ~1 phút (đọc raw E3/E5 lớn).

## Public API
- `regenerate(raw_dir, table_dir, fig_dir) -> (bảng, hình)`: E2–E6 + cơ chế E6.
- `e2_tables`, `e3_tables`, `e4_tables(raw_dir, table_dir)`: bảng từ raw, **cùng hàm tóm tắt** như script gốc
  (`common.summarize`, `e2.summarize_*`, `e3.write_table`, `e4.summarize_roots / example_rows / score_ci`).
  E5/E6 dùng thẳng `e5_rollout.build_tables`, `e6_tactics.build_tables`, `e6_mechanism.build_table`; hình dùng
  `make_figures` của từng E, `e4.plot_match`, `e6_mechanism.make_figure`.
- `compare(new_dir, ref_dir, names, ref=committed_bytes) -> [(tên, lý do)]`.
- `write_summary_md(table_dir, fig_dir) -> Path`; `REPORT_MAP` (mục, nội dung, E, hình, bảng); `SECTIONS[E]`;
  định dạng `vn(x, d)` (dấu phẩy thập phân; số nguyên ≥ 10 000 nhóm nghìn bằng khoảng trắng), `ci(lo, hi)`;
  `_one(rows, **kw)` = đúng 1 dòng khớp, không thì `KeyError` (không đoán).

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
| 5.1 Minimax vs AB | E1 | — | `e1_summary` (bảng nút), `e1_nodes`, `e1_positions` |
| 5.2 MCTS 3×3 không thua | E2 | — | `e2_play` (W/D/L), `e2_exhaustive{,_by_role}` |
| 5.3 Hằng số c | E3 | `e3_3x3`, `e3_greedy`, `e3_ab2` (iter–win rate, mỗi c một đường) | `e3_3x3_{random,minimax}`, `e3_greedy`, `e3_ab2{,_pilot}` (W/D/L 15×15) |
| 5.4 N vs W/N | E4 | `e4_match` | `e4_roots_examples` (W, N, W/N ở gốc), `e4_roots_summary`, `e4_match` |
| 5.5 Rollout | E5 | `e5_iter`, `e5_time` | `e5_paired`, `e5_h2h`, `e5_greedy`, `e5_mref`, `e5_ab2`, `e5_bench`, `e5_rates` |
| 5.6 check_tactics | E6 | `e6_choice`, `e6_match`, `e6_mechanism` | `e6_choice`, `e6_match`, `e6_paired`, `e6_mechanism`, `e6_cost_check`, `e6_time`, `e6_tactic_rate` |

## Kết quả kiểm (2026-11-17, sau commit `e98dc49`)
`--check`: 25 bảng sinh lại, **24 giống byte** với bản đã commit, 0 khác, 1 mới (`e6_mechanism.csv`). Chạy ghi đè:
`git status` chỉ có 3 file mới (`e6_mechanism.{csv,png}`, `summary_kinrow.md`) — **mọi PNG cũ cũng giống byte**.

## Phụ thuộc
`experiments/{common,e2_never_lose,e3_c_sweep,e4_final_move,e5_rollout,e6_tactics,e6_mechanism}.py`, matplotlib (Agg), `git`.

## Test
`tests/test_plots.py`: `vn`/`ci`; `_one` báo lỗi khi 0 hoặc ≥ 2 dòng; `compare` (giống sau chuẩn hóa CRLF / khác / mới);
lọc 10 cặp đầu + moves tương ứng; tóm tắt mistakes E2 từ chuỗi = từ int (gồm thứ tự); `summary_kinrow.md` sinh được từ
bảng thật, chứa số lấy từ CSV (mẫu E1/E2/E6), mọi file được nhắc tới tồn tại. Chạy: `python -m pytest tests/test_plots.py -q`.

## Hạn chế / TODO
- E1 và các bảng đo trực tiếp không kiểm được bằng sinh lại (chỉ kiểm tồn tại).
- `e5_time.png`: tiêu đề panel dưới-giữa hơi tràn sang panel phải (có từ E5, không sửa ở P7.1 để hình giữ nguyên byte) — sửa ở P7.2/P7.3 nếu dùng hình này.
