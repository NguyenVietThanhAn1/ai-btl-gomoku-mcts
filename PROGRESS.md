# PROGRESS — BTL AI Bài 1

> Single source of truth cho tiến độ. Cập nhật **cuối mỗi task / mỗi phiên** (wrap-up: `docs/WORKFLOW.md` §2).
> Ký hiệu: ⬜ chưa làm · 🔄 đang làm · ✅ xong · ⛔ bị chặn
> Định nghĩa task: xem `PLAN.md`.

## Đang ở đâu (đọc mục này trước tiên)

> Mỗi người chỉ sửa khối của mình (D-27, D-31, D-32).

### An

- **Task hiện tại:** P8.1 🔄 (luật cờ tướng + perft, làm thẳng trên `develop`, D-32). P6.4 ✅ 2026-11-21 (spec-reviewer PASS, An chơi thử 5 ván OK, B3 bỏ — D-36). Thứ tự D-35: `P8.1–P8.4 (+P6.2)` → bổ sung báo cáo cờ tướng → P7.3 (PDF) → P7.4 (video).
- **Việc đang dở:** P8.1 — chưa code (plan An đã duyệt 2026-11-21: `games/xiangqi.py` + `.md`, `experiments/p81_perft.py` → `results/tables/p81_perft.csv` (chỉ file này), test). Dừng báo An sau khi perft D1–3 chạy, trước `xiangqi.md` + spec-reviewer.
- **Bước tiếp theo:** P8.1 → P8.2 → P8.3 → P6.2 → P8.4 → bổ sung báo cáo cờ tướng → P7.3/P7.4 (D-34/D-35). **Còn nợ:** `report/report.md` Phụ lục B cần sửa sau P8 (mapping mức AB 15×15 + bảng thời gian/nước GUI, D-36). Nguồn số liệu báo cáo: `results/tables/summary_kinrow.md`; ảnh GUI: `report/figures/gui/`.
- **Cảnh báo / blocker:** số liệu k-in-row khóa ở tag `kinrow-final`; mọi sửa agent phải giữ `tests/test_regression_kinrow.py` xanh.

### Thành viên 2

- **Task hiện tại:**
- **Việc đang dở:**
- **Bước tiếp theo:**
- **Cảnh báo / blocker:**

## Bảng trạng thái

| ID | Task | Trạng thái | Owner | Cập nhật | Ghi chú |
|---|---|---|---|---|---|
| P0.1 | Repo, venv, skeleton | ✅ | An | 2026-10-28 | spec-reviewer PASS |
| P1.1 | core/game.py interface | ✅ | An | 2026-10-28 | spec-reviewer PASS; quyết định ở D-5 |
| P1.2 | games/kinrow.py | ✅ | An | 2026-10-28 | spec-reviewer PASS |
| P2.1 | Agent base + Random | ✅ | An | 2026-10-28 | spec-reviewer PASS |
| P2.2 | Heuristic eval k-in-row | ✅ | An | 2026-10-28 | spec-reviewer PASS; quyết định ở D-8 |
| P2.3 | Minimax | ✅ | An | 2026-11-04 | spec-reviewer PASS |
| P2.4 | Alpha-Beta | ✅ | An | 2026-11-04 | spec-reviewer PASS; quyết định ở D-9 |
| P2.5 | Greedy agent | ✅ | An | 2026-11-04 | spec-reviewer PASS |
| P3.1 | MCTS-UCT (+ RandomRollout, HeavyRollout bản đúng) | ✅ | An | 2026-11-10 | spec-reviewer PASS; phạm vi/quyết định ở D-11 |
| P3.2 | Tăng tốc HeavyRollout (+ test tương đương) | ✅ | An | 2026-11-10 | spec-reviewer PASS; D-12; phần chọn tham số tách sang P3.3 |
| P4.1 | Arena + runner song song/CSV/resume | ✅ | An | 2026-11-10 | spec-reviewer PASS; D-13; gộp phần runner của P4.2 cũ |
| P3.3 | Quét sơ bộ T / rollout_limit / scale (heavy) | ✅ | An | 2026-11-10 | spec-reviewer PASS; chọn h300 (sơ bộ); D-12, D-14 |
| P4.2 | Cờ dòng lệnh chung (`--quick`, …) | ✅ | An | 2026-11-10 | `--quick` trong `add_runner_args`; cột `*_search_*` ở `summarize` (D-15); phần runner ở P4.1 (D-13) |
| P4.3 | CLI | ✂ (cắt) | An | 2026-11-17 | thay bằng preset + cờ dòng lệnh của GUI (D-28) |
| E1 | Nodes Minimax vs AB | ✅ | An | 2026-11-10 | full 59 s; D-17; `e1_*.csv` |
| E2 | 3×3 never lose | ✅ | An | 2026-11-10 | spec-reviewer PASS; full xong; D-16 |
| E3 | c sweep | ✅ | An | 2026-11-11 | spec-reviewer PASS; D-18; full 226 phút; AB2 qua cổng (2/20) |
| E4 | N vs W/N | ✅ | An | 2026-11-11 | spec-reviewer PASS; D-19; full 174 s; bỏ đối đầu 15×15 |
| E5 | Random vs heuristic rollout | ✅ | An | 2026-11-11 | spec-reviewer PASS; D-20; full 79 phút; AB2 không qua cổng (0/20) |
| E6 | Tác dụng check_tactics | ✅ | An | 2026-11-17 | spec-reviewer PASS; D-21 (thiết kế lại); full 24 phút, AC |
| P6.1 | GUI: khung + view k-in-row | ✅ | An | 2026-11-17 | D-28; spec-reviewer PASS; autoplay headless 4 chế độ × bàn; GUI thay bởi P6.3 (An chơi thử OK) |
| P6.3 | GUI: game chơi được hoàn chỉnh | ✅ | An | 2026-11-17 | D-29; spec-reviewer PASS; An chơi thử bằng chuột OK |
| P6.4 | GUI: AI "Rất khó" 15×15 (ID, top-k, TT, VCF) | ✅ | An | 2026-11-21 | D-35/D-36; B3 bỏ; An chơi thử 5 ván OK; không đổi results/ |
| P6.2 | GUI: view cờ tướng | ⬜ | An | | sau P8.3 (D-26) |
| P7.1 | Plots/tables | ✅ | An | 2026-11-17 | D-26; `plots --check` 24/24 bảng giống byte; cơ chế E6 kiểm chứng (D-21) |
| P7.2 | report.md | ✅ | An | 2026-11-18 | D-30; spec-reviewer PASS; report_check 0 lỗi; `plots --check` 26/26 |
| P7.3 | Xuất report.pdf (D-34; thay docx) | ⬜ | An | | sau P8 + bổ sung báo cáo cờ tướng (D-35) |
| P7.4 | Video demo (script + quay) | ⬜ | An | | sau P7.3 (D-35); có cảnh cờ tướng |
| P8.0 | Xiangqi design D-22 + golden k-in-row | ✅ | An | 2026-11-17 | tag `kinrow-final`, branch `xiangqi`; golden 12 ván / 123 nước |
| P8.1 | Xiangqi rules + perft | ⬜ | An | | |
| P8.2 | Xiangqi eval + AB | ⬜ | An | | |
| P8.3 | Xiangqi MCTS | ⬜ | An | | |
| P8.4 | Xiangqi experiments | ⬜ | An | | |
| B2 | Bài 2 (Bonus) | ⬜ | | | chưa chốt phạm vi — chờ An xác nhận yêu cầu với giảng viên (PLAN §0) |

## Kết quả thí nghiệm đã có

- **E1:** giá trị gốc AB = Minimax ở 6/6 thế 3×3 (cả 3 biến thể) và 5/5 thế 15×15 depth 2; nước đi `ab` = Minimax, `ab_order`/`ab_order_tt` giống hệt 3/6 nhưng tối ưu 6/6 (hòa giá trị). Nút gộp 3×3 vs Minimax: −96,13 % (ab), −99,60 % (+ordering), −99,76 % (+TT); bàn trống 549 946 → 20 866 → 1 856 → 990. 15×15 depth 2: 46 825 → 21 612 (−53,85 %) → 1 416 (−96,98 %), nhưng thời gian ordering 0,265 s vs 0,247 s (chậm hơn 7,5 %); depth 3: 553 574 → 48 504 nút (−91,24 %), 5,46 → 1,26 s. `results/tables/e1_{nodes,summary,positions}.csv`.

- **E5:** 15×15, c = 1.4 + tactics. **Cùng thời gian (công bằng):** đối đầu h300 vs rand 0,90 [0,786; 0,957] (0,5 s; iteration thực tế 1 322 / 1 398) và 1,00 [0,929; 1] (2 s; 4 006 / 5 680); vs Greedy h300 0,62 / rand 0,00 (0,5 s), 0,86 / 0,10 (2 s); vs mref 0,98 / 0,50 (0,5 s), 1,00 / 0,92 (2 s). **Cùng iteration:** đối đầu 0,96 / 0,90 / 0,98 (250 / 1000 / 5000); vs Greedy rand ≤ 0,08 ở mọi iter, h300 0,48 (1000) → 0,92 (5000, E3); vs mref rand 0,20 / 0,50 / 0,88, h300 0,74 / 0,90 / 1,00. Paired (h300 − rand) vs Greedy 0,5 s +0,62 [0,484; 0,756], 2 s +0,76; vs mref 0,5 s +0,48, 2 s +0,08 [0,004; 0,156]. AB2: rand_i5000 0/20 → không qua cổng (h300 E3 0,22). mref hợp lệ (25/50). Benchmark rand/h300 = 1,50× iter/s. Cờ tốc độ 15/33 (không loại dữ liệu). `results/tables/e5_*.csv`, `figures/e5_{iter,time}.png`.
- **E4:** 3×3 (4 298 thế ≥ 2 nước): max_n ≠ max_wn ở 1,3–4,4 % thế; trong các thế đó tỉ lệ giữ giá trị trò chơi max_n / max_wn = 0,606 / 0,809 (10 iter), 0,948 / 0,928 (100), 1,000 / 0,982 (250), 1 / 1 (1000) → max_n chỉ hơn ở vùng giữa. 15×15 h300 c = 1.4: 0/150 search khác (W/N lớn nhất = 1,0 ở 80–100 %, max_wn phá hòa theo N); c = 0.5: 3/150. Đối đầu 3×3 max_n vs max_wn: score 0,485–0,510, mọi CI chứa 0,5. `results/tables/e4_{roots_summary,roots_examples,match}.csv`, `figures/e4_match.png`.
- **E3:** 3×3 vs Random win 0,915–0,980, vs Minimax non-loss 0,70–0,77 (100 iter) → 1,00 (≥ 2500) — mọi c chồng CI ở mọi iter. 15×15 vs Greedy: giao cắt — 1000 iter c=0.5 0,62 [0,482; 0,741] vs c=2.0 0,22 [0,128; 0,352] (tách); 5000 iter c=2.0 0,96 [0,865; 0,989], c=1.4 0,92, c=1.0 0,88, c=0.5 0,82 (chồng). AB2: pilot c=2.0 2/20 → qua cổng; tốt nhất c=1.0/5000 0,36 [0,241; 0,499], mọi c chồng. Hình `results/figures/e3_{3x3,greedy,ab2}.png`; bảng `results/tables/e3_{3x3_random,3x3_minimax,greedy,ab2_pilot,ab2}.csv`.
- **E2:** (b) vét cạn 0 nhánh thua trên 10 seed × 2 vai ở 5000 iter (5674 nhánh); 1000 iter 7/5713 thua; 100 iter 279/6247. (a) 5000 iter 0 thua/100 ván vs Minimax, Random, MCTS. `results/tables/e2_*.csv`.
- **E6:** tắt tactics, chặn four đúng (trọng số pool) rand 0,03 → 0,38, h300 0,50 → 0,14 → 0,48 (100 → 1000 → 5000 iter); bật 1,00. Win rate tắt → bật vs Greedy +0,38 (1000), +0,62 (5000); vs mref +0,04 (CI chứa 0). Cơ chế chữ U (chạy lại cây, khớp raw 100 %): 100 iter một phần, 1000 khớp cơ chế (W/N nước sai 0,90, không phải ~0,6), 5000 khớp (ô thắng đối thủ đã mở 0,20 → 0,97). `results/tables/e6_*.csv`, `figures/e6_{choice,match,mechanism}.png`.
- **Tổng hợp cho báo cáo:** `results/tables/summary_kinrow.md` (sinh tự động, bản đồ hình/bảng → mục 5).
<!-- Mỗi thí nghiệm chạy xong: 1–3 dòng số liệu chính + đường dẫn file CSV/hình. -->
- **P3.3 (sơ bộ — không phải số liệu E5):** 7 cấu hình × {Greedy, AB2, mrand} × 20 ván, 0,5 s/nước, tactics bật. Thắng vs mrand: h100 / h300 / h100c10 / h1000c10 19/20, h1000 / h300c10 16/20, rand 9/20 (Wilson [0,258; 0,658], hợp lệ). Vs Greedy cao nhất 8/20 (h300, h100c10), vs AB2 ≤ 2/20. Chọn **h300** theo luật D-14. `results/tables/p33_sweep_prelim.csv`, `p33_choice_prelim.csv`, `p33_scale_prelim.csv`.

## Session log

> Mỗi người ghi log trong khối của mình, log mới nhất ở đầu khối; không sửa khối người khác (D-32).

### An

#### 2026-11-21 — Đóng P6.4 (D-36)
- An chơi thử 5 ván 15×15 mức Khó (AB): "khá ổn", không lỗi. Bỏ B3 (MCTS Khó = `time_limit` + VCF) vì vượt timebox ~1,5 ngày (D-35); MCTS Khó giữ nguyên. spec-reviewer P6.4 **PASS** (0 blocker/major; minor `alphabeta.md` "sắp tới" → "đã có" đã sửa). P6.4 ✅.
- Sửa `PLAN.md` §P8 cho khớp D-32 (làm thẳng trên `develop`, bỏ branch `xiangqi`). An cho phép tạo MỚI `results/tables/p81_perft.csv` (chỉ file này) cho P8.1.

#### 2026-11-18 — P6.4 B1 + B4 (D-36): AB Khó mới 15×15, mapping dịch mức
- B1 xong (3 commit local, chờ precheck + An duyệt push): `AlphaBetaAgent` `root_hook`, `top_k`, `time_limit` (ID), `tt_mode="deep"` + 30 test; `kinrow_vcf`. An đổi thiết kế B4: không thêm "Rất khó" — dịch mức AB 15×15 (Vừa = Khó cũ E1, Khó = `AB15_HARD`); D-36. Demo giữ cấu hình thí nghiệm (`AB2` tra qua `EXPERIMENT_SPECS`).
- Đo GUI (D-36): AB Khó 15×15 trung bình 1,55 s (vs người ngẫu nhiên) / 2,30 s (vs AB2), tối đa 2,41 s; FPS khi nghĩ 25,8 (khung tệ nhất 22,7–24,4), MCTS Khó 25,7 (14,5–16,7). `local_out/p64/` (gitignore), không ghi đè `p63_*`.
- **Việc cần làm sau P8:** `report/report.md` **Phụ lục B cần sửa** (mapping mức độ khó AB 15×15 + bảng thời gian/nước GUI) ở đợt cập nhật report sau P8; hiện chưa sửa (An chốt). Ảnh Setup/Demo trong `report/figures/gui/` cũng sẽ lệch nhãn (chụp lại ở P7.3/P7.4).
- **B5 xong (2026-11-18):** `--quick` cả 2 `top_k` → An chốt (16,12,8). Full (20 khai cuộc × 2 ván, commit `b295df5`): vs AB Vừa mới 36/0/4 = **0,90** [0,77; 0,96] (X 0,95 / O 0,85), vs MCTS Khó 36/0/4 = **0,90** [0,77; 0,96] (X 0,90 / O 0,90); 20 khai cuộc phân biệt, 0 ván trùng chuỗi nước, 0 lỗi; AB Khó 1,52–1,68 s/nước TB, max 2,42 s. **Đạt ngưỡng** (≥ 0,8 / ≥ 0,5). Chi tiết + bảng quick: D-36. CSV ở `local_out/p64/` (gitignore).
- **Dừng chờ An chơi thử 5 ván 15×15 mức Khó (AB)**, rồi mới đóng P6.4 (spec-reviewer, ✅). B3 (MCTS Khó = `time_limit` + VCF) làm cuối, timebox ~1,5 ngày — chưa làm.

#### 2026-11-18 — Sự cố: push 139a5f7 với 2 test E5 đỏ; sửa `fix: e5 guard tests pinned to kinrow-final`
- Push `139a5f7` (chỉ thêm `heuristics/kinrow_vcf.*`) làm đỏ `test_real_e3_files_reusable_now` và `test_estimate_full_from_fake_quick` (E5): `e3_reusable` so `git diff <commit trong raw> HEAD` trên `gameai/{agents,games,heuristics,core}` nên mọi file mới ở đó là "code đổi" (guard đúng, test phụ thuộc HEAD sai). Tôi đã push vì lấy `$?` của `| tail` thay cho pytest → AGENTS.md thêm luật không pipe pytest/ruff khi cần exit code.
- Sửa: `git_diff_empty(..., target="HEAD")` (mặc định giữ nguyên); test raw thật đổi tên `..._at_kinrow_final` ghim `target="kinrow-final"` (skip chỉ khi thiếu raw/tag); `test_estimate_full_from_fake_quick` (e5) monkeypatch `e3_reusable` bỏ kiểm git, giữ kiểm raw. Test cùng tên ở `test_e3_c_sweep` không dùng git → không đổi. `e3_reusable`, `e5_rollout` logic, `results/` không đổi. Ghi chú: mọi commit sau đổi `agents/` vẫn hợp lệ với test này.
- **Phát hiện tiếp:** `plots --check` cũng đỏ từ `139a5f7` (cùng nguyên nhân: `e5/e6.build_tables` dùng `e3_reusable` so HEAD). Sửa `fix: plots reuse check pinned to kinrow-final`: `plots.regenerate` truyền `reuse_check=pinned_reuse` (ghim tag) cho `e5.build_tables` và `e6.build_tables` (e6 thêm tham số `reuse_check`/`on_source`, mặc định cũ); test `test_tables_do_not_depend_on_head`; `plots --check` 26/26 giống byte. Thêm `python -m gameai.tools.precheck` (pytest + ruff check + ruff format --check + report_check + plots --check, exit thật); AGENTS/WORKFLOW/README: trước mỗi push chạy precheck, EXIT phải 0.

#### 2026-11-18 — D-35: đổi thứ tự (P8 trước P7.3/P7.4), mở P6.4
- An duyệt plan P6.4 + 4 chỉnh: (1) B5 đánh giá từ khai cuộc ngẫu nhiên có seed, mỗi khai cuộc 2 ván đổi bên, ghi số khai cuộc phân biệt + số ván trùng chuỗi nước vào D-36; (2) ngưỡng ≥ 0,8 vs AB Khó, ≥ 0,5 vs MCTS Khó + An tự chơi 5 ván trước khi đóng, không đạt → chỉnh 1 vòng rồi dừng; (3) timebox ~1,5 ngày, B3 (MCTS Rất khó) làm cuối, bỏ nếu quá; (4) `_Timeout` không ghi TT nút dở dang + test cắt rồi search lại = TT rỗng. Quyết: Q1 có (An báo Thành viên 2 trước khi sửa `agents/`), Q2 3×3 không có Rất khó, Q4 không VCT, Q5 ảnh Setup để nguyên (chụp lại ở P7.3/P7.4), Q6 CSV gitignore.
- Sửa: `docs/DECISIONS.md` (D-35), `PLAN.md` (P6.4, P7.3/P7.4, thứ tự P8 + §4), `PROGRESS.md`. `report/report.md` không đổi (chỉ nhắc "D-30" làm hướng tiếp theo, không nêu thứ tự).

#### 2026-11-18 — P7.2 ✅ xong: help.png sinh lại, AGENTS PDF, PR mốc Bài 1
- `help.png` (Hình B.8) sinh lại bằng `python -m gameai.gui.screenshots --only help` (headless, theme mặc định, tắt animation): 1280×720, dòng "Phân tích…" có "tỷ lệ thắng"; chỉ file này đổi (các ảnh GUI khác giữ nguyên). Lưu ý: `--help` của script lỗi `UnicodeEncodeError` trên console cp1252 — chạy với `PYTHONIOENCODING=utf-8`.
- AGENTS.md "Sản phẩm nộp": ".docx" → "PDF (D-34)". `report_check.md` và D-1 giữ nguyên (mô tả lịch sử).
- P7.2 ✅ (Done khi: report_check 0 lỗi, `plots --check` 26/26 giống byte, pytest + ruff xanh, spec-reviewer PASS). Mở PR `develop` → `master` (mốc "Bài 1: code + thí nghiệm + báo cáo"); An merge.

#### 2026-11-18 — P7.2 spec-reviewer PASS + xử lý 3 minor; D-34 (nộp PDF)
- **spec-reviewer P7.2: PASS** (không blocker/major; report_check 0 lỗi, `plots --check` 26/26 giống byte, pytest + ruff xanh; ~40 khẳng định định lượng mục 5–6 khớp CSV). 3 minor, đã xử lý: (1) PROGRESS dòng "Việc đang dở"/log lỗi thời → cập nhật + log `1fac6f7` (`docs: tỷ lệ in experiment docs`, đổi "tỉ lệ" trong 6 file `experiments/*.md`; commit đã push); (2) `plots.md` mục "Kết quả kiểm" → "26 giống byte, 0 khác, 0 mới" (2026-11-18, sau `1fac6f7`); (3) Bảng 2 (E1) nhãn hiển thị "3x3"/"15x15" → "3×3"/"15×15": đổi trong `section_e1` (`plots.py`, `r["board"].replace("x", "×")`), sinh lại summary (đổi đúng 10 dòng nhãn của Bảng E1, không dòng nào khác), sync 10 dòng Bảng 2 trong `report.md`. Giá trị `board` trong CSV và selector `board=3x3` / `board=15x15` trong comment `src` không đổi. Bảng khác hiển thị "3x3": không còn (grep summary/report: chỉ còn tên file `e3_3x3*` và selector).
- **D-34:** bản nộp là PDF (không cần `report.docx`); P7.3 = xuất PDF, hoãn tới khi An yêu cầu. Sửa `PLAN.md` (§0 bảng, dòng Giao diện/Báo cáo, cây thư mục, P7.3), `PROGRESS.md` (bảng P7.3, "Bước tiếp theo"). Chưa sửa: AGENTS.md "Sản phẩm nộp" (còn ".docx"), `report_check.md` (nhắc "docx"), D-1 — chờ An đồng ý.

#### 2026-11-18 — P7.2 `plots --check` so summary + "tỷ lệ" trong GUI
- `plots --check` so byte thêm `results/tables/summary_kinrow.md` với bản đã commit (report dùng nó làm `src`): hàm `check_outputs(new_dir, fig_dir, names, ref_dir, ref)` sinh summary vào thư mục tạm rồi so cả 25 bảng + summary (dòng tổng "26 giống byte"). Test `test_check_outputs_compares_summary` (giống / lệch một chữ "tỷ lệ"↔"tỉ lệ" → báo đúng tên + dòng / mới). `plots.md` cập nhật. Lý do: lần đổi "tỉ lệ" → "tỷ lệ" ở `plots.py` làm đổi summary mà `--check` không báo.
- GUI: chữ **hiển thị** trên giao diện — `gameai/gui/scenes.py:477` (màn Hướng dẫn, thẻ "Trong ván": "W/N là tỷ lệ thắng ước lượng") → đổi. Ảnh cần chụp lại (chưa chụp, An làm): **`report/figures/gui/help.png`** (Hình B.8 trong report). Các ảnh GUI khác không chứa chữ này (chỉ màn Hướng dẫn dùng `HELP_CARDS`). Comment/doc đổi cho thống nhất: `gameai/gui/brand.md`, `gameai/gui/icons.md`, `tests/test_gui_polish.py`. Không đổi DECISIONS/PLAN/PROGRESS (ghi chép lịch sử). "tỉ lệ" trong `gameai/experiments/*.md` (common, e3, e4, e5, p33, figfmt; 13 chỗ) đã đổi ở `1fac6f7` (chỉ còn chuỗi cố ý trong `tests/test_plots.py`).

#### 2026-11-18 — P7.2 dấu thập phân VN trong hình
- Module mới `gameai/experiments/figfmt.py` (+ `figfmt.md`, `tests/test_figfmt.py`): `vn` (chuyển từ `plots`, `plots.vn` vẫn dùng được), `vn_tick`, `vn_figure(fig)` (gọi trước `tight_layout` ở mọi hàm vẽ E3–E6), `ratio_axis(ax)`. Import ở đầu file trong `plots` và `e3/e4/e5/e6_*` (không còn import trong hàm; figfmt không import `plots`, không vòng).
- Tick: phẩy thập phân, "−", **mọi tick một trục cùng số chữ số suy từ bước tick** (bước 0,05 → `0,80 … 1,00`; bước 0,2 → `0 0,2 … 1`); trục log chỉ major (1, 2, 5 × 10^k) có nhãn, hết `10^3`. Trục tỷ lệ: không tick > 1 (`ratio_axis`). Số nguyên không nhóm nghìn dưới 10 000 (khớp report).
- `e5_time`: panel dưới-trái/giữa (x = iteration thực tế) đổi sang trục tuyến tính; panel cột iteration thực tế đổi sang trục tuyến tính từ 0 (cột trên log làm sai tỷ lệ chiều dài). `e6_choice`: legend 2 cột theo rollout (random trái, h300 phải; "chọn đúng" rồi "không mất thắng"), "bật tactics (sanity)" riêng ở cuối (figsize 11×5,8).
- "tỉ lệ" → "tỷ lệ" trong mọi `gameai/experiments/*.py` (common, e3, e4, e5, plots: 12 chỗ; docstring, nhãn trục, tiêu đề hình, chú thích hình, 1 dòng summary). Bảng CSV không đổi (`plots --check` 25/25 giống byte); `summary_kinrow.md` đổi đúng 1 dòng (E5 benchmark: "tỉ lệ rand/h300" → "tỷ lệ rand/h300"; số 1,50 giữ nguyên). Còn "tỉ lệ" trong các file `.md` module/DECISIONS/PROGRESS/PLAN (chưa đổi).
- Hình đổi so với bản `5d1ea03` trước amend (cả 9 hình đổi so với `43be113`): `e3_{3x3,greedy,ab2}`, `e4_match`, `e5_{iter,time}`, `e6_choice`; `e6_match`, `e6_mechanism` giữ nguyên byte. Đã xem bằng mắt `e5_time`, `e6_choice`, `e3_3x3`.

#### 2026-11-18 — P7.2 sửa đợt (c) theo review (An duyệt đợt (c))
- 6.6: bỏ "vừa quá một nửa" (0,50 mà CI chứa 0,5); giữ khẳng định ở 5000 iteration; câu riêng "mức cao nhất mọi ngân sách: h300 100 iteration 0,503 [0,40; 0,61], khoảng chứa 0,5" — src thẳng `e6_choice.csv` (bootstrap, stratum all). `report_check`: số chữ số của biên CI lấy theo biên trong report (trước đây theo `x`) để cho phép `x` 3 chữ số + biên 2 chữ số; thêm test.
- Văn phong 5.3 ("-->;"), 6.1 ("được so với", bỏ "ở cùng số nút" lặp). AGENTS: số D-xx lấy sau khi đồng bộ (fetch + rebase); thêm D-33 (đồng bộ fetch + rebase, tham chiếu D-32, không sửa D-32).
- Kiểm: report_check 0 lỗi, plots --check, pytest, ruff xanh; đồng bộ fetch + rebase rồi push `develop` (An yêu cầu).

#### 2026-11-18 — P7.2 đợt (c): mục 6 + Tóm tắt (dừng chờ An duyệt)
- **Lỗi 5.3** (phát hiện khi viết 6.3): câu "cặp duy nhất có hai khoảng tin cậy tách nhau" sai — `e3_greedy.csv` có 4 cặp tách (1000 và 500 iter: c = 0,5 vs 2,0; 250 iter: c = 1,4 vs 0,5 và vs 1,0). Sửa riêng, commit `P7.2: fix 5.3 CI-separation claim` (chỉ hunk 5.3, `git apply --cached`).
- Mục 6 (6.1–6.8) + Tóm tắt 198 từ theo dàn ý An duyệt + 5 chỉnh; chỉnh sau duyệt: 6.6 N trung vị ô chặn = 1 (`e6_mechanism.median_n_correct`), viết lại 500–2500 rõ X/O, 6.3 thêm "4 cặp tách trong 36 phép so sánh không hiệu chỉnh".
- **Rà từ định lượng** (duy nhất/mọi/không … nào/luôn/đều/chỉ) ở Tóm tắt + mục 5–6: 90 câu; đối chiếu CSV các câu có số liệu. Sửa 4 chỗ: 6.6 "không cấu hình nào chặn quá một nửa" sai ở h300 100 iter (0,5029) → giới hạn ở 5000 iter; "mọi thế đã thử" (Tóm tắt, 6.1) → chỉ thế có so với Minimax (độ sâu 3 không chạy Minimax); 6.1 "cùng một cây" → cùng số nút, giá trị, nước đi; 6.1 nước khác Minimax chỉ trên 3×3.
- **Ký tự điều khiển:** dòng 588 có TAB/BEL (`\tfrac`, `\approx` bị escape khi chèn bằng script) → sửa; PROGRESS dòng log đợt (b) có lỗi cùng loại (`\times` → TAB) → sửa. `report_check` thêm lỗi ký tự điều khiển + test. Bài học: heredoc của Bash tool gộp `\\` thành `\` — chuỗi có dấu `\` phải ghi bằng Edit/Write, không qua heredoc.
- Workflow (commit riêng): đồng bộ chuẩn của agent = `git fetch origin` + `git rebase origin/develop` (AGENTS, WORKFLOW, README, SETUP); giữ `pull.rebase true` cho người gõ tay. Lý do: 2/3 lần `git pull --rebase` báo FETCH_HEAD trùng dòng.

#### 2026-11-18 — P7.2 sửa mục 5 theo review (commit "P7.2: section 5 review fixes")
- Nguồn gốc diff `plots.py` chưa commit (`vn` dấu "−", `ci` luật làm tròn): do **phiên trước** (transcript `8ecf8477`, 11:31–12:45 cùng ngày, file sửa lần cuối 12:45:28) tạo, không phải phiên này (phiên này bắt đầu 12:45:53, file không bị sửa trong plan mode). Phiên này giữ nguyên code đó, thêm test + doc.
- `git pull --rebase` báo "Cannot rebase onto multiple branches": FETCH_HEAD có 2 dòng `develop` trùng (không not-for-merge); xử lý `git fetch origin` + `git rebase --autostash origin/develop` (đã trùng origin).
- Luật làm tròn CI ghi vào D-30 (P7.2): không làm tròn biên nếu đổi kết luận chứa 0 / 0,5 hay biến biên ≠ 0 thành 0,00 → thêm một chữ số; số âm "−"; "tỷ lệ". `report_check`: biên theo `plots.ci`, lỗi riêng "D-30" khi vi phạm. Summary sinh lại: 10 dòng đổi (E5 mref 2 s `[0,004; 0,156]`, 2 Wilson `[0,004; 0,105]`, E3 AB2 `[0,241; 0,499]`, dấu "−").
- `report.md` mục 5: Bảng 10/14/15/17 đồng bộ summary; 5.2 thêm W/D/L vs MCTS 0/100/0; 5.3 "c có ước lượng điểm cao nhất" (3 chỗ) + `[0,241; 0,499]`; 5.4 "năm con có N lớn nhất ở gốc", "mọi lần tìm kiếm (1,00)"; 5.5 `[0,004; 0,156]`, "tỷ lệ 1,50"; 5.6 `[−0,10; 0,18]`.
- Kiểm: report_check 0 lỗi, plots --check, pytest, ruff. Bước tiếp: viết đợt (c) mục 6 + Tóm tắt theo dàn ý An đã duyệt (5 chỉnh), dừng chờ duyệt. Sau (c): dấu thập phân trong hình (commit riêng).

#### 2026-11-18 — P7.2 đợt (b) (dừng chờ An duyệt)
- Sửa (a) theo An: caption hình kiểu pandoc `![Hình n. …](…)` (bỏ dòng **Hình** đậm), dấu phẩy thập phân trong văn xuôi (E2: c = √2 ≈ 1,41 — `e2.mcts_spec` dùng mặc định `MCTSAgent`), câu thời gian GUI nêu bench 0,827× vs 0,996× (không gõ % chênh tự tính), "tối đa $15 \times 15 = 225$ nước". Quy tắc: không đặt số đo trong code fence.
- `plots.py`: tiêu đề cột c kiểu VN; bảng summary mới — E2 vét cạn (theo vai), E4 3×3 thống kê + 15×15 + đối đầu (tách bên đi trước), E5 cùng thời gian / cùng iteration (+ bench rand/h300 = 1,50, kiểm tra hợp lệ mref), E6 chọn đúng / so cặp / chi phí / nước đi thẳng (cột nguồn ván bật E3/E5/E6). `plots --check` 25/25 CSV giống byte.
- `report_check`: caption hình trong alt (cấm dòng **Hình**, thiếu alt báo lỗi, `Hình B.n` không đếm); một `src` phủ `x [lo; hi]` (CSV 3 cột hoặc neo summary) hoặc khoảng `a–b` (neo summary); `const: D-xx | tok …` chỉ miễn token liệt kê, token phải có trong văn bản D-xx. 14 test.
- `report.md` mục 5 (5.1–5.6): 18 bảng `src-table` (Bảng 2–19), 8 hình (Hình 1–8), chỉ mô tả kết quả. `report_check` 0 lỗi (146 số có nguồn, 55 dòng const, 2 dòng ví dụ tay). Mục 5 thêm ~2 500 từ văn xuôi (~4 600 kể cả bảng); cả báo cáo ~7 300 từ không tính bảng. pytest xanh, ruff sạch.
- Hình `e6_mechanism.png` để dành cho mục 6 (cơ chế = giải thích). Chú giải trong các hình matplotlib vẫn dấu chấm (c = 0.5) — chưa sửa.

#### 2026-11-18 — P7.2 đợt (a) (dừng chờ An duyệt)
- An chốt thứ tự D-30 (Bài 1 trước cờ tướng); PLAN §4/P8/P7.2 + PROGRESS sửa; branch `feat/P7.2` từ `develop`. An duyệt plan + 6 chỉnh (src-table so byte, neo theo heading không theo dòng, A(s) = mọi ô trống / candidate là tỉa nhánh ở mục 3, ví dụ E4 15×15 có tham chiếu, tương thích pandoc không crossref, GUI timing đúng file D-29 + ghi bật/tắt animation; thêm Silver 2017).
- Bước 1: `e5_time.png` hết tràn tiêu đề (`e5_rollout.make_figures`, tên ngắn); `summary_kinrow.md` mỗi bảng có `### Bảng …` riêng, thêm W/D/L E3 (3×3 vs Random/Minimax, 15×15 vs Greedy/AB2) và ví dụ E4 15×15 (thế 3, 250 iter, c = 0.5, tham chiếu 20 000 iter); `plots --check` **25/25 CSV giống byte**. `p72_env.py` → `results/tables/p72_env.csv` (Python 3.13.14, thư viện, OS; ghi lúc viết báo cáo).
- `report_check.py` (+`.md`, 9 test): `src:` CSV (lọc 1 hàng, định dạng VN theo số chữ số của token) / `src: summary#heading`, `src-table:` so byte, `const: D-xx`, `example: file.md` (ví dụ tính tay, đếm riêng), bỏ khối ```, số trần (thập phân / ≥ 100 / %), ảnh tồn tại, caption Hình n./Bảng n. liên tiếp, Tóm tắt ≤ 200 từ.
- `report/report.md` đợt (a): Tóm tắt (placeholder), 1 Giới thiệu (RQ1–RQ6 ↔ đề ý 1–5 + E6), 2 Phát biểu bài toán, 3.0 tập ứng viên (tỉa nhánh xấp xỉ), 3.1–3.3, 3.4 placeholder, 4 Thiết lập (Bảng 1), Phụ lục A/B (ảnh GUI, thời gian p63anim bật / p63 tắt animation), 10 tài liệu tham khảo. `report_check` 0 lỗi (15 số có nguồn, 14 dòng const, 2 dòng ví dụ tay); ~5 000 từ. Full pytest xanh (1 xfail chủ ý), ruff sạch.
- Ghi chú: pandoc **chưa cài** trên máy (cần cho P7.3). Ví dụ E4 15×15: ô 97 và 202 cùng tham chiếu 90/213 — đã kiểm raw, là hai dòng khác nhau trùng số, không phải lỗi tra cứu.
- Tiếp theo (sau khi An duyệt): đợt (b) mục 5 (bảng `src-table` từ summary, hình `../results/figures/`), đợt (c) mục 6 + Tóm tắt, spec-reviewer.

#### 2026-11-17 — P6.3 xong, mốc k-in-row hoàn chỉnh
- An chơi thử GUI bằng chuột trên cửa sổ thật: ổn → P6.3 ✅.
- Git: merge `--no-ff` `feat/P6.3` → `develop` (pytest + ruff xanh trên develop, push), `develop` → `master` (mốc "k-in-row hoàn chỉnh": thí nghiệm + GUI, push); xóa `feat/P6.1`, `feat/P6.3` local.

#### 2026-11-17 — P6.3 phiên 3c (hoàn tất, chờ An chơi thử)
- An duyệt ảnh 3b + 2 điểm: (1) hover ô có nhãn overlay → ẩn nhãn ô đó khi vẽ quân mờ (`KInRowView.hover_move`); (2) mọi số cấu hình hiển thị lấy từ `AgentSpec` — phát hiện và bỏ 3 chỗ gõ tay: "h300" cố định + `c` mặc định 1.41 trong `side_label` (nay: `rollout_tag` từ `temperature`, c từ mặc định `MCTSAgent` qua `inspect` = √2 → "1.41", E3 "1.4"), tiêu đề 3 preset (nay `preset_title`), nguồn Demo "E2/E3" (nay `DemoScene.sources` tra ngược `find_level` → "E2", "E3", "E3 · E3/E5").
- Test: +2 trong `tests/test_gui_polish.py` (ẩn/hiện nhãn khi hover; số trong nhãn/tiêu đề = spec). Full suite xanh (1 xfail chủ ý), golden xanh, ruff sạch.
- Autoplay headless (animation bật, vẽ mỗi frame, mức Vừa): 18 tổ hợp = 2 bàn × {người vs MCTS/AB × 2 bên, AI vs AI 4 cặp MCTS/AB, 2 người} → **18/18 hết ván, 0 lỗi**, modal kết thúc mở; 3×3 AI vs AI hòa cả 4 cặp; 15×15 dài nhất 26 nước AI vs AI (13 s).
- spec-reviewer: **PASS** (không lỗi chặn); đã bù góp ý doc (Phụ thuộc / Hạn chế cho anim, icons, brand, render; `logo_surface`). Ảnh `report/figures/gui/*.png` chụp lại.

#### 2026-11-17 — P6.3 phiên 3b (theme tối hoàn thiện, animation, đo lại; chờ duyệt ảnh)
- An chọn theme **tối**; 4 chỉnh thêm (overlay badge trên ô có quân, overlay 3×3 nhạt, Đen/Trắng + ●/○ ở 15×15, bảng Phân tích đủ lề) — ghi D-29.
- Mới: `gui/anim.py` (+`.md`: Tween theo dt, cờ tắt), `tests/conftest.py` (animation tắt cho mọi test), `tests/test_gui_polish.py` (12 test: tween, cache không tăng khi chạy trọn animation đặt quân + hover qua 60 frame, modal / đường thắng / crossfade, hover dùng tint, overlay badge + 3×3 nhạt, Đen/Trắng, bảng Phân tích trong card, modal không che bàn, Disclosure, tooltip Setup, thời gian người với clock giả).
- Làm lại: Setup (card, "Đen · đi trước", tóm tắt "Đối thủ: MCTS · Khó" + ⓘ, seed trong "Tùy chọn nâng cao"), Demo (card + nhãn "CẤU HÌNH THÍ NGHIỆM · E2/E3"), Help (card + chip phím, gói dòng; bỏ glyph ← → mà font không có), modal 200 px trên panel (fade + slide, bỏ dòng trùng tiêu đề); widget `Disclosure`, `wrap_text`, hover tween; SceneManager crossfade + `tick(dt)`; `GameController(clock=...)`; `p63_gui_timing` cột `animations`, `--no-anim`, file `p63anim_*`; `pygame_app --no-anim`.
- Đo (AC, Balanced, bench 0,827× E5 — máy chậm hơn lần gốc ~17 %): MCTS Khó 15×15 2,05 / 2,51 s (gốc 1,85 / 2,38; +10,8 % / +5,3 %) → dưới 15 %, giữ. D-29.
- Full suite xanh (1 xfail chủ ý), golden xanh, ruff sạch. Ảnh: `report/figures/gui/{home,setup,play15,play3,modal,review,demo,help}.png`.

#### 2026-11-17 — P6.3 phiên 3a (giao diện sản phẩm MoveMind, chờ chọn theme)
- An đổi hướng phiên 3 (D-29 "Phiên 3" + 4 chỉnh khi duyệt: cache sprite không phình theo animation, cache xóa khi `pygame.quit`, chỉ đánh bóng theme được chọn, `set_icon`). Commit `a79c7b8` (D-29/PLAN/PROGRESS).
- Mới: `gui/assets/fonts/` (Be Vietnam Pro 4 độ đậm + `OFL.txt` + README nguồn/license, tải từ google/fonts), `gui/render.py` (sprite 4× + smoothscale, `lru_cache` có maxsize, xóa khi quit; quân gradient numpy, X/O nét bo, bóng mờ, vạch đầu tròn, vân gỗ sinh bằng code), `gui/icons.py` (13 icon vẽ bằng code), `gui/brand.py` (`APP_NAME = "MoveMind"`, logo, wordmark, icon cửa sổ), `gui/screenshots.py` (ảnh headless), `.md` mỗi file.
- Làm lại: `widgets.py` (Theme DARK/WARM, 4 cỡ chữ + lưới 8 px, Button có icon / ghost, IconButton, Tooltip, mọi hình qua `render`), `view.get_font` (font đóng gói theo độ đậm, fallback Segoe UI → Arial), `kinrow_view.py` (lớp tĩnh cache: bóng + khung + gỗ + lưới + nhãn; quân sprite; nước cuối một màu = vòng/khung; đường thắng vạch nối tâm có `win_progress`; overlay top-8 theo hạng), `play_scene.py` (thẻ có avatar quân, tên ngắn "MCTS · Khó" + ⓘ tooltip chi tiết/nguồn, Demo hiện "Cấu hình thí nghiệm · E3"; nút icon; card lịch sử + Phân tích; modal đặt trên panel, chỉ làm mờ panel), Home (wordmark + 4 nút icon + bàn 9×9 minh họa; bỏ "Minimax…"/"BTL…"), nhãn trò "Caro 3×3" / "Caro 15×15 · 5 quân thắng"; `pygame_app` caption + `set_icon` + `--theme`.
- Test: `tests/test_gui_style.py` 10 test (token, mép mềm + cache, quit → init vẽ lại, icon, tên/caption/icon cửa sổ, Home không chữ kỹ thuật, nhãn trò, cache không tăng qua 40 frame có hover, tooltip nguồn, screenshots); test font đổi sang "ưu tiên font đóng gói" + "thiếu file → font hệ thống" (D-29). Full suite xanh (1 xfail chủ ý), golden xanh, ruff sạch.
- Ảnh 2 phương án (Home, Play 15×15 có Phân tích + W/N + quân mờ, Play 3×3): `report/figures/gui/style/{dark,warm}/`.

#### 2026-11-17 — P6.3 phiên 2/3 (UI, chờ duyệt ảnh)
- Mới: `gui/widgets.py` (theme tối kiểu chess.com; Button, Toggle, SegmentedControl, Stepper, Modal, ScrollList theo cột), `gui/scene.py` (Scene, SceneManager), `gui/scenes.py` (Home, Setup, Demo, Help), `gui/play_scene.py` (AppState chuyển từ pygame_app; thẻ 2 người chơi, lịch sử, Đi lại / Ván mới / Đầu hàng / Menu, Phân tích + W/N, modal kết thúc, xem lại), `.md` mỗi file.
- Sửa: `pygame_app.py` = chủ SceneManager (không `--preset` → Home; có → vào thẳng ván; API `App.ctrl/view/state/handle_key/handle_click` giữ cho test P6.1 + `p63_gui_timing`); `view.py` hook `preview` / `draw_ghost` / `winning_cells` (có mặc định, không phá P6.2); `kinrow_view.py` nhãn tọa độ (a–c / A–O, hàng 1.. từ trên — khớp lịch sử; 3×3 `move_label` đổi `B2` → `b2`), quân mờ khi hover, nước cuối nền vàng; `presets.find_level` / `source_of`.
- 4 chỉnh của An đều có: undo khóa khi AI nghĩ (nút disabled), nhãn tọa độ, Esc theo màn, Setup AI vs AI có độ trễ + nút "X/O đầu hàng" ở 2 người, không có Đầu hàng ở AI vs AI (thay bằng Tạm dừng / Tiếp tục).
- Lỗi tìm được: `get_font` cache `Font` qua `pygame.quit()` → access violation ở test sau `run()`; sửa bằng xóa cache qua `pygame.register_quit` (đăng ký lại mỗi chu kỳ init vì pygame bỏ danh sách sau mỗi lần quit).
- Test: `tests/test_gui_scenes.py` 15 test (chuyển màn bằng click, Setup → AgentSpec + nguồn, Demo giữ spec, nút ván, undo khóa khi AI nghĩ, modal kết thúc / Bạn thắng / Bạn thua / đường thắng / Chơi lại, xem lại không đổi ván thật, quân mờ, widget, `run`). Full suite xanh (1 xfail chủ ý), golden xanh, ruff sạch. CLI headless: preset 3 (50 iter) và 3×3 `--swap` autoplay hết ván; không preset → Home.
- Ảnh headless (scratchpad, không commit): Home, Setup người vs AI / AI vs AI, ván 15×15 có Phân tích + W/N + quân mờ, modal 3×3, xem lại, 2 người 15×15 đường thắng.

#### 2026-11-17 — P6.3 phiên 1/3 (xong) — đo lại thời gian
- An: chuyển script đo vào repo → `gameai/experiments/p63_gui_timing.{py,md}` (+ `tests/test_p63_gui_timing.py`), CSV `results/tables/p63_gui_{timing,runinfo}.csv` + `p63_bench.csv`, cột `note` = minh họa GUI; dừng nếu không AC. `git branch -u origin/develop develop`.
- Đo cắm sạc (D-21: AC, Balanced, máy rảnh, bench 0,996× E5), 130 s: MCTS Khó 15×15 trung bình 1,85–2,38 s/nước, tối đa 3,60 → đạt luật, giữ cấu hình; bảng đủ ở D-29. Bỏ số đo trên pin.
- xfail duy nhất: `tests/test_mcts.py::test_15x15_block_without_tactics_is_unreliable` — lý do đã nằm trong `reason=` (MCTS thuần 1000 iter rollout random không chặn được four 15×15; D-11, E6).

#### 2026-11-17 — P6.3 phiên 1/3 (dừng chờ đo lại thời gian) — số pin, đã thay bằng đo lại ở trên
- Git: `develop` merge `--no-ff` `feat/P6.1` (local, `5747e08`, chưa push), tạo `feat/P6.3`. D-29 + PLAN P6.3 (commit `a953986`); An duyệt plan + 4 chỉnh (undo khóa khi AI nghĩ, nhãn tọa độ, Esc theo màn, độ trễ AI vs AI + nút đầu hàng theo chế độ).
- Code: `gui/controller.py` (`undo`/`can_undo`, `resign`/`resign_side`/`can_resign`, `outcome`, `side_time`, `position_at`, thời gian nghĩ của người, bỏ kết quả AI khi ván đã dừng), `gui/presets.py` (`DIFFICULTY` 12 ô, `Level`, 3 spec AB riêng, `side_label` AB), `gui/game_config.py` mới. `.md` cập nhật. Không sửa `agents/`, `games/`, `heuristics/`.
- Test: +9 test controller, `tests/test_gui_config.py` mới (20 case); full suite xanh (1 xfail chủ ý), golden xanh, ruff sạch.
- Đo thời gian/nước (script scratchpad `time_levels.py`: App trên Surface headless 30 fps, người = nước ngẫu nhiên trong candidate có seed; 3×3 5 ván/mức; 15×15 3 ván + 1 ván vs AB2/mức). 3×3 (mean / max s): MCTS 0,004 / 0,013 · 0,036 / 0,065 · 0,143 / 0,243; AB 0,000 · 0,000 · 0,005 / 0,020. 15×15 **trên pin, không dùng làm số chốt**: MCTS Dễ 0,31 / 0,52, Vừa 0,92–1,25 / 1,86, Khó 4,65–5,63 / 9,33; AB Dễ 0,003, Vừa 0,05–0,08 / 0,14, Khó 0,25–0,34 / 0,52. Kiểm chéo không vẽ (controller, seed 0) MCTS Khó 14,5 s/nước → chậm do pin, không do GUI.

#### 2026-11-17 — Setup git + P6.1 (xong)
- Git: `.gitignore` giữ `!results/*_full.log`; bỏ track 77 file quick (`git rm --cached`, còn trên đĩa); track `results/e3_full.log`; D-27 cập nhật. Commit `13f4f94` trên `develop`, merge `--no-ff` vào `master` (`51dfbb8`, mốc tài liệu), push cả hai. Tạo `feat/P6.1` từ `develop`.
- P6.1 (D-28): `gui/presets.py`, `gui/controller.py`, `gui/view.py`, `gui/kinrow_view.py`, `gui/pygame_app.py` (+ `.md` mỗi file). Preset 15×15 dùng h300 5000 iter (bổ sung của An). Không sửa `agents/`, `games/`, `heuristics/`.
- Test: `tests/test_gui_controller.py` 26 test (controller headless, view, font tiếng Việt + đúng font hệ thống, App trên Surface, AI vs AI 15×15 h300 50 iter vs AB2); full suite xanh (golden xanh), ruff sạch.
- Autoplay headless (`SDL_VIDEODRIVER=dummy`, người = nước ngẫu nhiên có seed): 3×3 người vs MCTS seed 1 (O thắng, 6 nước) và đổi bên seed 2 (X = MCTS thắng, 5 nước); 15×15 người vs h300 5000 seed 3 (MCTS thắng, 10 nước, 10,6 s); 15×15 h300 5000 vs AB2 delay 0 seed 0 (**AB2 thắng**, 26 nước, 24,3 s — khớp E3: h300 5000 vs AB2 chỉ 0,22). 3×3 AI vs AI: test controller. Không lỗi.
- Đo ngoài GUI: h300 5000 iter ≈ 2,1 s/nước (thế 5 quân); AB2 ≈ 0,01 s.
- spec-reviewer: **PASS**; đã sửa 3 góp ý nhỏ (test font đúng font hệ thống, test 15×15 hết ván, ghi chú overlay chỉ sau nước AI).
- Chưa làm: chơi thử bằng chuột trên cửa sổ thật (cần An).

#### 2026-11-17 — P7.1 (xong)
- Đổi thứ tự (An, D-26): `xiangqi` fast-forward vào master; P7.1 → P6.1 → P8.1…; tách P6.1 / P6.2. Commit `e98dc49`.
- `experiments/plots.py` (+`.md`): sinh lại bảng/hình E2–E6 từ raw bằng đúng hàm tóm tắt của từng E (E1 + bench/sanity/cost/positions_summary là bảng đo trực tiếp). `--check` so với bản đã commit: **24/24 bảng giống byte**, 0 khác; chạy ghi đè: mọi PNG cũ cũng giống byte. Sinh `results/tables/summary_kinrow.md` (số chính mỗi E + bản đồ → mục 5.1–5.6 + bảng md cho báo cáo).
- Cơ chế E6: dự đoán ghi vào D-21 trước khi chạy (yêu cầu An: bảng tách nhóm correct = 1 / 0, dự đoán áp cho nhóm chọn sai). `experiments/e6_mechanism.py` (+`.md`) chạy lại 900 cây block (rand + h300) — `CODE_PATHS` không đổi so với tag, **khớp `e6_choice.csv` 100 %**, 589 s, AC → `raw/e6_mechanism.csv`, `tables/e6_mechanism.csv`, `figures/e6_mechanism.png`. Kết luận: 100 iter một phần, 1000 iter khớp cơ chế / sai độ lớn, 5000 iter khớp (`e6_tactics.md`, D-21).
- Test: `tests/test_plots.py`, `tests/test_e6_mechanism.py` (11 test); full suite xanh, ruff sạch. Đã xem 9 hình; `e5_time.png` có tiêu đề panel dưới-giữa tràn sang phải (có từ E5, chưa sửa).

#### 2026-11-17 — P8.0 (xong)
- Lập plan P8 (An duyệt + 4 bổ sung: hạn chế TT/lặp thế, kiểm tỉ lệ ván phân thắng thua trước khi fit scale, 50 ván/điểm E7 c/d (≥ 20 nếu quá đắt), đánh dấu lõi / ✂).
- Git: tag annotated `kinrow-final` tại `aa8e3d5`, branch `xiangqi`. File quick chưa track giữ nguyên.
- Golden hồi quy: `tests/kinrow_golden_cases.py` → `tests/golden/kinrow_golden.json`, sinh khi `git diff kinrow-final -- gameai` rỗng; 12 ván / 123 nước (5 cấu hình, 3×3 + 15×15, AB / MCTS / Greedy / Random); `tests/test_regression_kinrow.py` ~4 s.
- PLAN: viết lại P8 (P8.0–P8.4, lõi / ✂), P6 cho cả hai trò sau P8.3, thứ tự §4. DECISIONS: D-22 (thiết kế game, kết thúc, hạn chế; đặt chỗ D-23/24/25).

#### 2026-11-17 — E6 (xong)
- Sau quick (An quyết, D-21): ghi `power`/`battery_pct` mọi bước vào `e6_runinfo.csv`; bench ngắn so `e5_bench`; phần (c) chỉ khi AC; bỏ đối đầu h300 tắt vs bật 5000; lấy mẫu phân tầng 15 thế/tầng `n_candidates`/loại, tỷ lệ chung theo trọng số pool + bootstrap phân tầng; loại 2 thêm tầng `n_mine`. Commit `d8f09af`. Xóa `e6quick_*` lần 1 (pin, thiết kế cũ).
- Quick lần 2 (AC) 88 s, ước tính 23 phút → chạy full theo luật (≤ 100 phút): 1 433 s, AC, `git_dirty = 0`, sanity 90/90.
- Kết quả: chặn four khi tắt tactics rand 0,03 → 0,38, h300 0,50 → 0,14 → 0,48; thắng ngay rand → 1,00 từ 2 500 iter, h300 0,27–0,39 (chọn thắng chắc khác); vs Greedy bật − tắt +0,38 / +0,62; vs mref +0,04 (không khác); h300 bật thắng h300 tắt 34/50; overhead `check_tactics` ~7 % (rand 1000 iter). Sửa hình sau full (legend), không đổi dữ liệu.

#### 2026-11-17 — E6 (quick, dừng trước full)
- PLAN E6 gốc kẹt sàn (E5: rand bật vs Greedy ≤ 0,08, vs AB2 0/20) → An chọn thiết kế lại, ghi D-21 trước khi code: (a) bộ thế thật từ ván E3/E5 (loại 1 chặn four 1 ô, loại 2 thắng ngay), tắt tactics theo iter {100…5000} × rand/h300 × 10 seed, checkpoint trong một cây; bật = sanity; tầng `n_candidates`; loại 2 thêm "không mất thắng" (phụ); (b) randoff vs mref, h300 tắt vs bật, h300 tắt vs Greedy (bản bật tái dùng E3/E5), bỏ AB2; (c) chi phí.
- Không sửa code agent/game (giữ tái dùng E3/E5). Commit `6e86acc`.
- Quick 724 s trên pin: sanity 8/8, tái dùng E3/E5 ok, ước tính full ~191 phút (phóng to do pin). Chi tiết D-21.

#### 2026-11-11 — E5 (xong)
- Trước full (An duyệt): commit riêng `.claude/settings.json` (`50e4099`); D-20 sửa luật cờ tốc độ theo nhóm giai đoạn ván ply 0–9 / 10–19 / ≥ 20 so với benchmark cùng nhóm (`method = phase`; dự phòng `mixed` ghi rõ trộn giai đoạn), rand là chỉ báo tải, cờ không loại dữ liệu; benchmark 7 thế chạy ở đầu full (commit `ec3b8d5`, 26 test E5).
- Full `ec3b8d5`, `git_dirty = 0`: 4 733 s (bench ~46 s, iteration + pilot ~33 phút, time ~45 phút), 1 270 ván normal, distinct = n. 7 điểm h300 tái dùng E3. Pilot AB2 rand 0/20 → dừng. Kết quả chính: "Kết quả thí nghiệm đã có" + `e5_rollout.md`.
- Cờ tốc độ 15/33: h300 nhóm 10–19 nhanh hơn benchmark +25…+56 % ở mọi điểm (thế benchmark là playout ngẫu nhiên, ít đe dọa); rand chậm hơn đều −7…−27 % ở mọi điểm → không thấy tải ở riêng điểm nào.

#### 2026-11-11 — E5 (đang dở: chờ duyệt full)
- D-20 chốt trước khi chạy (commit `07791c1`), gồm 5 điểm sửa của An: seed mref tách riêng (`derive_seed(seed_B, "mref")`); thứ tự iter → time, runinfo ghi CPU + workers, phần time cần máy rảnh; tỉ lệ iteration/giây đo từ benchmark (không ghi "~2×"); bảng paired báo khoảng cặp + độc lập; "Giải thích cho báo cáo" dẫn c10 của P3.3 (không cải thiện nhất quán, LL evaluate −0,566 vs −0,693). Thêm cờ lệch tốc độ > 20 % ở phần time (`e5_rates.csv`). PLAN dòng E5 sửa theo D-20.
- `experiments/e5_rollout.{py,md}`, `tests/test_e5_rollout.py` (24 case). Full suite xanh (1 xfail chủ ý), ruff sạch.
- `--quick` 300 s: 44 ván normal, distinct = n, 4 điểm E3 tái dùng được, rand_i1000 vs mref 1/2 (hợp lệ). Bench `results/tables/e5_bench.csv`: rand 3 721, h300 2 840 iter/s (1,31×). `git_dirty = 1` do `.claude/settings.json`. File `e5quick_*` không commit.
- spec-reviewer: FAIL 1 lỗi (dòng in ở `estimate_full` sau khi sửa, chuỗi bị gọi như hàm — quick đã chạy bằng code trước đó nên không ảnh hưởng) + 2 lệch số trong `.md` → đã sửa, test xanh.

#### 2026-11-11 — E4 (xong)
- Full (commit `71344d6`): roots 164 s (3×3 42 s, 15×15 120 s gồm 2 tham chiếu 20 000 iter), match 3×3 10 s, 1 000 ván normal, `git_dirty = 0`. Thêm cột theo yêu cầu An: `max_n_N_tie_rate`, `max_wn_is_1_rate`, `n_wn1_{median,max}`.
- Kết quả chính: xem "Kết quả thí nghiệm đã có". Điểm khác với diễn giải dự kiến: W/N = 1,0 ở 15×15 không phải "ít nhiễu" — tham chiếu 20 000 iter cho chính các con đó W/N 0,25–0,47 (ghi D-19 + `.md`).
- spec-reviewer PASS; đã sửa các điểm nhỏ nó nêu (mục Public API/Phụ thuộc, dùng thế `trace` pos 435 trong `.md`, test hằng số D-19 + NaN). 13 hàm test (15 case) trong `tests/test_e4_final_move.py`; full suite xanh (1 xfail chủ ý); ruff sạch.

#### 2026-11-11 — E4 (đang dở: chờ duyệt full)
- D-19 chốt trước khi chạy (commit `906374d`), bổ sung sau thăm dò theo An duyệt (commit `a6f8cc8`): "tối ưu" = giữ giá trị trò chơi (`e2_never_lose.solve`, không dùng thang `WIN − ply`); 3×3 iter {10, 20, 50, 100, 250, 1000}, ví dụ ở iter 100; 15×15 iter {50, 250, 1000}, thêm c = 0.5 làm độ nhạy; **bỏ đối đầu 15×15**; đối đầu 3×3 iter {10, 20, 50, 100, 250}, 200 ván/điểm, độ đo chính score.
- Thăm dò (không ghi vào results): 15×15 max_n = max_wn ở 0/30 thế (c = 1.4, iter 50–1000; cả rollout random, c = 2.0); chẩn đoán = cơ chế thật, không phải bug (mọi con N = 1 → hai luật phá hòa chọn cùng con 1/1; W/N bão hòa ở 1,0; UCT dồn lượt thăm vào con hoàn hảo). 3×3: khi hai tiêu chí khác nhau, max_wn **không** tệ hơn max_n. Chi tiết: D-19.
- `experiments/e4_final_move.{py,md}`, `tests/test_e4_final_move.py` (13 test). Full suite xanh (1 xfail chủ ý), ruff sạch.
- `--quick` 16,9 s: mọi ván normal, 0 lỗi, `git_dirty = 0`. Ước tính full: roots 3×3 ~1,3 phút, roots 15×15 ~5,5 phút (gồm tham chiếu 20 000 iter, cận trên 6 thế), match 3×3 ~0,3 phút tuần tự (ước tính có thể thấp do overhead tiến trình). File `e4quick_*` không commit.

#### 2026-11-11 — E3 (full xong)
- Full nền (commit `544ece9`, 4 worker): 8 800 ván, mọi ván normal, 0 lỗi, `git_dirty = 0`. Thời gian thực 226,3 phút: 3×3 16,7, Greedy 78,6 (ước tính quick 41 — thấp), pilot 8,3, AB2 122,7 (gồm ~29 phút máy dừng giữa 2 ván ở c=1.0/2500; iteration budget nên kết quả không đổi). Pilot c=2.0 2/20 → qua cổng D-18 → chạy AB2 full không hỏi lại (An đã duyệt trước).
- Sửa lỗi vẽ: cận Wilson ở p = 1 lệch ~1e-16 → `yerr` âm làm `plot` crash sau khi dữ liệu đã ghi đủ; cắt err ở 0 + test mới. Legend chuyển xuống hàng riêng dưới tiêu đề (hình 1 panel bị đè tiêu đề).
- Test: 23 trong `tests/test_e3_c_sweep.py`; ruff sạch. Kết quả + diễn giải: `gameai/experiments/e3_c_sweep.md` mục "Kết quả full".
- Lưu ý cho báo cáo: CI Wilson độc lập từng điểm; chỉ 15×15 vs Greedy ở 500–1000 iter có cặp c tách CI (0.5 vs 2.0). `distinct_games` 3×3 vs Minimax chỉ 51–94/100. c tốt vs Greedy (2.0) không tốt nhất vs AB2.

#### 2026-11-10 — E3 (đang dở: chờ duyệt full)
- Full suite trước task (sau sửa E1): 306 test, 305 passed + 1 xfail chủ ý.
- Đã làm: D-18 (lưới, 3×3 vs Random 200 ván + vs Minimax có seed/cache 100 ván, 15×15 h300 + tactics vs Greedy 50 ván, AB2 pilot **sau** Greedy với c tốt nhất ở 5000 iter + cổng ≥ 2/20, ghi chú Wilson độc lập từng điểm); PLAN dòng E3. `experiments/e3_c_sweep.{py,md}` (`CachedMinimaxAgent`, `choose_pilot_c`, `gate_passes`, `run_part`, `estimate_full`, `plot_panels`). Commit `36e9b68` trước quick.
- Test: 328 full suite (327 passed + 1 xfail chủ ý); 22 mới trong `tests/test_e3_c_sweep.py`; ruff sạch.
- `--quick` 310 s, mọi ván normal, `git_dirty = 0`. Ước tính full 4 worker: 3x3 ~3–10 phút, greedy ~41 phút, ab2 pilot ~9 phút, ab2 full ~2 h (ván vs AB2 dài 50–83 nước, ~94 s/ván). Chi tiết: `gameai/experiments/e3_c_sweep.md` mục Quick. File `e3quick_*` không commit.
- Hình: legend chung một hàng phía trên (không đè đường ở 1,0), trần trục y 1,03; bảng màu qua validator dataviz.

#### 2026-11-10 — E1 (xong)
- Đã làm: `experiments/e1_nodes.{py,md}` — 3×3 (bàn trống + 5 thế, Minimax / AB / +ordering / +ordering+TT), 15×15 (5 thế cố định, AB depth 2, 3 × có/không ordering; Minimax chỉ depth 2; thêm `ab_evalonly` tách tác dụng `delta_eval`). Kiểm giá trị + nước đi + `move_optimal`; báo % nút và % thời gian, gộp và trung bình theo thế. `--quick` 5 s; full 58,7 s (không cần hỏi trước khi chạy: < 2 phút). P4.3 hoãn, gộp với P6 (ghi ở bảng + PLAN + D-17).
- Test: full suite pass (1 xfail chủ ý); 4 test mới trong `tests/test_e1_nodes.py`; ruff sạch.
- File đổi: `gameai/experiments/e1_nodes.{py,md}`, `tests/test_e1_nodes.py`, `results/tables/e1_{nodes,summary,positions}.csv`, `PLAN.md`, `docs/DECISIONS.md` (D-17), `PROGRESS.md`.
- Lưu ý: 5 thế mỗi bàn **lồng nhau** (cùng playout seed 0) và chỉ 5 thế → không có CI. Ordering giảm nút nhưng ở 15×15 depth 2 không giảm thời gian (chi phí `move_score`); depth 3 mới có lợi. Nước của `ab_order*` khác Minimax khi hòa giá trị là hợp lệ (xem `move_optimal`).

#### 2026-11-10 — E2 (xong)
- Full: (a) 543 s, (b) 290 s. Vét cạn: 0 nhánh thua trên 10 seed × 2 vai ở 5000 iter (5674 nhánh); 1000 iter còn 7/5713 (2/20 run, MCTS=O); luật mở rộng 10000/20000 không kích hoạt. Sai chủ yếu ở vai O, nước đáp đầu. Sửa `mcts.md` ("1000 iter đủ" chỉ đúng với ván đấu). Chi tiết: `gameai/experiments/e2_never_lose.md`.

#### 2026-11-10 — P4.2
- Đã làm: `add_runner_args` thêm `--quick` (chỉ đăng ký cờ; script tự định nghĩa quick + file riêng); `p33_heavy_sweep` bỏ khai `--quick` trùng. `summarize(rows, moves=None)` thêm `{a,b}_search_moves`, `{a,b}_search_iterations_per_move` (bỏ nước tactic thắng/chặn ngay; restrict vẫn tính), cột cũ giữ nguyên (D-15). Không đổi schema CSV, không chạy lại p33. Ghi cảnh báo AB2/E3/E5 vào "Cảnh báo".
- Kiểm trên dữ liệu p33 có sẵn: h300 vs Greedy 664 → 880 it/nước (123 nước search), vs mrand 805 → 968 (212 nước).
- Test: full suite pass (1 xfail chủ ý); 4 test mới/sửa trong `tests/test_experiments_common.py`; ruff sạch. spec-reviewer PASS (đã siết 1 test yếu).
- File đổi: `gameai/experiments/{common.py,common.md,p33_heavy_sweep.py}`, `tests/test_experiments_common.py`, `docs/DECISIONS.md` (D-15), `PROGRESS.md`.

#### 2026-11-10 — P3.3 (chạy full, xong)
- Đã làm: luật chọn D-14 (nhóm chốt trước khi chạy) cài trong `choose_config` → `results/tables/p33_choice_prelim.csv`; commit `217aabd`, chạy full 4 worker: 21 match, 420 ván, 11 phút 27 s, mọi ván `normal`, `git_dirty = 0`, `distinct_games` = 20/20 ở cả 21 ô (không cần `random_opening`).
- Kết quả (sơ bộ — không phải E5), thắng/20 vs mrand · Greedy · AB2 (không có hòa): rand 9 · 0 · 0; h100 19 · 6 · 2; h300 19 · 8 · 0; h1000 16 · 2 · 0; h100c10 19 · 8 · 2; h300c10 16 · 4 · 0; h1000c10 19 · 5 · 1. Kiểm tra hợp lệ rand vs mrand 9/20, Wilson [0,258; 0,658] ∋ 0,5. Bốn cấu hình hòa nhất vs mrand (19/20, Wilson [0,764; 0,991]), cả 6 cấu hình heavy chồng CI → phá hòa: Greedy 0,40 (h300 = h100c10) → không cắt → **h300**.
- Lưu ý: `a_iterations_per_move` tính cả nước đi thẳng nhờ tactics (0 iteration): rand vs greedy 897 trên 102 nước, 1 040 trên 88 nước có search (`p33_rand_vs_greedy_moves.csv`). So cùng nước (seed 0–1, 14 nước có search) quick 1 worker / quick 4 worker / full: 1 464 / 1 264 / 1 273 → full không bị tải thêm so với quick 4 worker. Vs AB2 gần sàn (≤ 2/20) → mrand là đối thủ phân biệt được cấu hình.
- Test: 290 full suite (289 passed + 1 xfail chủ ý), 23 trong `tests/test_p33_heavy_sweep.py` (thêm 4 test luật chọn); ruff sạch. spec-reviewer PASS (đã sửa 1 số không truy được trong `p33_heavy_sweep.md`).
- File đổi: `gameai/experiments/p33_heavy_sweep.{py,md}`, `tests/test_p33_heavy_sweep.py`, `gameai/agents/rollout.md`, `docs/DECISIONS.md` (D-14 luật chọn), `PROGRESS.md`, `results/raw/p33_*_vs_*.csv` (+ `_moves.csv`), `results/tables/p33_{sweep,choice}_prelim.csv`. File `p33quick_*` không commit.

#### 2026-11-10 — P3.3
- Đã làm: `experiments/p33_heavy_sweep.{py,md}` — `calibrate` (mỗi T một scale, mọi thế dọc rollout heavy sau khai cuộc 4–20 quân, seed 50 000–50 199, lưới D-12 + mở rộng khi chạm biên) và `sweep` (7 cấu hình × Greedy / AB2, 0,5 s/nước, `--quick` = 1 seed + kiểm tra worker 1 vs 4). D-12 bổ sung 5 điểm. Commit `4d6a8d9` trước khi chạy (`git_dirty = False`).
- Test: 286 full suite (285 passed + 1 xfail chủ ý); 19 mới trong `tests/test_p33_heavy_sweep.py` (gồm khớp `value_fn` của MCTS với σ(eval_P1/scale) đã fit ở cả lượt X và O — không lệch dấu); ruff sạch.
- Hiệu chỉnh (`results/tables/p33_scale_prelim.csv`, 9 343 thế, 1,9 s): T=100 → scale 500 (LL 300/500/1000: −0,6045 / **−0,5590** / −0,5686, 1 554 thế); T=300 → 500 (−0,5855 / **−0,5657** / −0,5835, 1 962 thế); T=1000 → 1000 (500/1000/2000: −0,6862 / **−0,6619** / −0,6670, 5 827 thế). Không chạm biên, không mở rộng lưới. LL gần log 0,5 = −0,693 (nhất là T=1000) → eval dự đoán yếu kết quả rollout.
- `--quick` (`results/tables/p33quick_sweep_prelim.csv`, không commit; 1 phút 27 s tổng): 7 cấu hình × 2 đối thủ × 2 ván = 28 ván, **MCTS thua cả 28** (termination normal, không lỗi), ván trung bình 9,5–27,5 nước; MCTS không chặn four (`check_tactics=False`). Iteration/nước: rand ~1 530, h100 ~1 100, h300 ~860–935, h1000 ~530–720, cấu hình c10 1 200–1 800. Ước tính full: vs Greedy 140 ván ~7 phút tuần tự / ~2 phút 4 worker; vs AB2 140 ván ~8 / ~2 phút. Kiểm tra worker (rand vs greedy, 4 ván): 1 worker 1 106 it/nước, 4 worker 1 282 (+15,9%) → 4 worker không làm giảm iteration.
- File đổi: `gameai/experiments/p33_heavy_sweep.{py,md}`, `tests/test_p33_heavy_sweep.py`, `gameai/agents/rollout.md`, `gameai/heuristics/kinrow_rollout.md`, `docs/DECISIONS.md`, `PROGRESS.md`, `results/raw/p33_calib_positions.csv`, `results/tables/p33_scale_prelim.csv`.
- Còn dở: chờ quyết định về floor effect rồi chạy full; chọn cấu hình cho E5; spec-reviewer.
- **Tiếp (cùng ngày) — D-14:** sanity check (script tạm, không lưu; 3 thế 15×15 có four của O, tactics tắt, h100 iteration cố định, 5 seed): 2000 iteration chặn 0/5 ở cả 3 thế (ô chặn chiếm 1–3% N gốc); 5000 iteration chặn 5/5 ở 2 thế ~58 candidate (3–5% N), 0/5 ở thế chéo ~100 candidate; 20 000 (seed 0) chặn ở cả 3, ô chặn W/N 0,39–0,75, cao nhất. Không phải bug: nước sai chỉ bị bác bỏ sau khi nút con mở rộng tới nước thắng của O. Iteration/nước ở 0,5 s (thế four kín): rand 1 682, h100 1 104, h300 867, h1000 389. → D-14: `check_tactics=True` cho mọi MCTS 15×15 (P3.3, E3, E5), chỉ E6 so bật/tắt; thêm đối thủ `mrand`. PLAN + doc cập nhật; xóa file `p33quick_*` cũ (chưa commit, config cũ).
- `--quick` lần 2 (42 ván, 3 phút 23 s, `results/tables/p33quick_sweep_prelim.csv`, không commit): MCTS thắng/hòa/thua — vs Greedy 4/0/10 (h300c10 2/2, h100 1/2, h100c10 1/2, còn lại 0), vs AB2 1/0/13 (chỉ h100 1/2), vs mrand 11/0/3 (rand 0/2, h300c10 1/2, còn lại 2/2). Độ dài ván TB (trung bình các cấu hình): 17,2 / 16,4 / 23,1 nước. Ước tính full: Greedy ~8 phút tuần tự / ~2 phút 4 worker; AB2 ~8 / ~2; mrand ~24 / ~6. Kiểm tra worker: 1 worker 1 256 it/nước, 4 worker 1 124 (−10,5%, dưới ngưỡng 15%).

#### 2026-11-10 — P4.1
- Đã làm: D-11 (làm rõ "Done P3 — thắng ngay") được nhóm duyệt. `agents/registry.py` — `AgentSpec`/`GameSpec` (params JSON, pickle được) + `make_agent`/`make_game`. `arena.py` — `play_game` (time do arena đo + bản sao stats mỗi nước; exception / nước sai / mutate game → thua), `derive_seed` (sha256), `random_opening_moves`, `play_seeded_game` (agent mới mỗi ván), `play_match`. `experiments/common.py` — `run_match` (song song, mặc định 4 worker, ghi ván + `*_moves.csv` ngay khi xong, resume: dòng cắt dở, moves mồ côi, `config_hash`, `git_commit`/`git_dirty` + `allow_code_change`), `summarize` (Wilson cho win rate và non-loss, score, `distinct_games`, tách A=X / A=O), `write_summary`, `add_runner_args`. PLAN: gộp runner vào P4.1, P4.2 chỉ còn cờ dòng lệnh. DECISIONS: D-13.
- Test: 267 test full suite (266 passed + 1 xfail chủ ý); 57 mới trong `tests/test_arena.py` + `tests/test_experiments_common.py` (~40 s, có spawn tiến trình), agent lỗi giả ở `tests/arena_helpers.py`; ruff sạch. Đột biến: 11 đột biến (không đổi lượt, seed bỏ tag, đảo người thắng khi lỗi, bỏ kiểm mutate, không xóa moves mồ côi, không bỏ dòng cắt dở, distinct bỏ vai, không bỏ ván đã xong, bỏ kiểm commit, đổi seed A/B, `FIRST_EXCEPTION`) đều bị test bắt.
- File đổi: `gameai/arena.{py,md}`, `gameai/agents/registry.{py,md}`, `gameai/experiments/common.{py,md}`, `tests/test_arena.py`, `tests/test_experiments_common.py`, `tests/arena_helpers.py`, `PLAN.md`, `docs/DECISIONS.md`, `PROGRESS.md`.
- Lưu ý: phát hiện khi kill thật: bản đầu dùng `wait(FIRST_EXCEPTION)` nên chế độ song song chỉ ghi khi **cả batch** xong; đã sửa sang `FIRST_COMPLETED` và thêm test. Đã kill thật một lần giữa batch 15×15 (2 worker): 4 ván giữ nguyên, chạy lại chỉ chơi 16 ván còn thiếu. `git_dirty` không tính file chưa track và không phân biệt hai trạng thái dirty khác nhau cùng commit → commit trước khi chạy dài. Script thí nghiệm phải gọi `run_match` trong `if __name__ == "__main__":`. Đo thử (không phải số liệu): MCTS heavy_kinrow 0,05 s/nước vs Greedy 15×15 thắng 12/80.

#### 2026-11-10 — P3.2
- Đã làm: profile `HeavyRollout` (~80% ở `kinrow_eval._scan`, chấm lại mọi candidate mỗi bước). `heuristics/kinrow_rollout.py` — `KInRowHeavyRollout(T)`: giữ số quân mỗi cửa sổ + (delta, win, block) mỗi ô × mỗi bên, chỉ cập nhật cửa sổ qua ô vừa đặt; tự đồng bộ theo tiền tố `move_history` (gỡ/áp nước). `KInRow.move_history` (property chỉ đọc). `experiments/p32_heavy_speed.py` đo tốc độ. Thêm mục "So sánh với Minimax: thắng ngay hay thắng chắc" vào `mcts.md` (tư liệu báo cáo, thuộc D-11). PLAN: tách P3.2 / P3.3 (quét tham số, sau P4.1). DECISIONS: D-12.
- Test: 210 test full suite, 209 passed + 1 xfail chủ ý; 27 mới trong `tests/test_kinrow_rollout.py` (~2 s) + 1 trong `tests/test_kinrow.py`; ruff sạch. 4 đột biến (ngưỡng chặn, bỏ góc nhìn O, không gỡ khi đồng bộ, bỏ kiểm tiền tố) đều bị test bắt.
- Kết quả đo (`results/tables/p32_heavy_speed.csv`, `p32_mcts_iterations.csv` — số đo phát triển, không phải E5): 300/300 rollout giống hệt bản chuẩn; nhanh hơn 7,1–10,9×/rollout (khai cuộc 6 nước), 4,1–8,4× (20 nước). MCTS 0,5 s/nước, T=100: 387–577 iteration (bản chuẩn 53–76, random 535–637).
- File đổi: `gameai/heuristics/kinrow_rollout.{py,md}`, `gameai/experiments/p32_heavy_speed.{py,md}`, `gameai/games/kinrow.{py,md}`, `gameai/agents/{rollout,mcts}.md`, `gameai/heuristics/kinrow_eval.md`, `tests/test_kinrow_rollout.py`, `tests/test_kinrow.py`, `results/raw/p32_heavy_speed.csv`, `results/tables/p32_{heavy_speed,mcts_iterations}.csv`, `PLAN.md`, `docs/DECISIONS.md`, `PROGRESS.md`.
- Lưu ý: rollout heavy rất ngắn ở T nhỏ (T=100: 9,4 nước sau khai cuộc 6, 5,1 sau 20) → `rollout_limit=10` gần như không tác dụng ở T=100. Console Windows cp1252 không in được tiếng Việt → script in ASCII. Đối tượng `KInRowHeavyRollout` có trạng thái: mỗi agent/tiến trình một object.

#### 2026-11-10 — P3.1
- Đã làm: `agents/mcts.py` — `MCTSAgent` (UCT, `iterations` và/hoặc `time_limit`, `final_move` max_n/max_wn, `rollout_limit` + `value_fn`, `check_tactics` mặc định tắt, seed riêng), `Node`, `uct`, `select_child`, `backpropagate` (chỗ lật góc nhìn duy nhất), `last_root_stats()`, `root`. `agents/rollout.py` — `RandomRollout`, `HeavyRollout` (softmax trên `score_fn`, T=100, chưa tối ưu), `make_policy`, `sigmoid_value`. PLAN: phạm vi P3.1/P3.2, đối thủ chuẩn 15×15 (Greedy + AB depth 2), thêm E6. DECISIONS: D-10, D-11.
- Test: 182 test, 181 passed + 1 xfail chủ ý (full suite ~2 phút gồm `slow`); 59 mới trong `tests/test_mcts.py` + `tests/test_rollout.py` (~5 s không tính `slow`, ~23 s cả `slow`); ruff sạch. Đã thử 4 đột biến lật dấu (backprop lật toàn cục / viết cứng P1 / đảo 1−r từ lá / lật trong UCT) → đều bị test bắt.
- File đổi: `gameai/agents/{mcts,rollout}.{py,md}`, `tests/test_{mcts,rollout}.py`, `gameai/heuristics/kinrow_eval.md`, `PLAN.md`, `docs/DECISIONS.md`, `PROGRESS.md`.
- Lưu ý: tốc độ 3×3 1000 iter ≈ 19 ms; 15×15 ≈ 0,32–0,40 ms/iter (cây sâu ~2 ở 1000 iter). Tắt tactics: 15×15 chặn four 0/10 seed ở 1000 iter, 2/10 ở 5000 (số đo phát triển — báo cáo lấy từ E6). 20 ván vs Minimax 3×3 tắt tactics: 1000 iter đủ, 0 thua. MCTS không phân biệt thắng ngay / thắng chắc (thế `. . X / X O X / . O .`) → làm rõ Done P3 ở D-11, chờ nhóm duyệt. `check_tactics` tốn O(b²) (~80 ms với 148 candidate). Heavy trên 15×15 phải có `rollout_limit` cho tới khi P3.2 tăng tốc.

#### 2026-11-04 — P2.5
- Đã làm: `agents/greedy.py` — `GreedyAgent(score_fn, seed=None, use_candidates=True)`: argmax `score_fn` trên candidate (1-ply), tie-break `random.Random(seed)` chỉ khi hòa điểm; stats `nodes` (= số nước chấm), `iterations`, `time`, `value`.
- Test: 123 passed full suite (~59 s); 11 mới trong `tests/test_greedy.py`; ruff sạch.
- File đổi: `gameai/agents/greedy.{py,md}`, `tests/test_greedy.py`, `PROGRESS.md`.
- Lưu ý: dùng `GreedyAgent(move_score, seed=s)`. `use_candidates` mặc định True (RandomAgent mặc định False). Sau khi X đi giữa bàn, mọi candidate của O cùng điểm 20 → khai cuộc của Greedy gần như ngẫu nhiên. Greedy thắng Random(candidate) trong 9–10 nước ở mọi seed đã thử. `MoveFn` import từ `alphabeta.py` (có thể dời sang `base.py` sau).

#### 2026-11-04 — P2.4
- Đã làm: `agents/alphabeta.py` — `AlphaBetaAgent` (cùng tham số Minimax + `order_fn`, `delta_fn`, `use_tt`), fail-soft, TT có cờ EXACT/LOWER/UPPER, khóa `(key, độ sâu còn lại)`, điểm thắng lưu theo khoảng cách; `search()` trả (move, value); stats thêm `cutoffs`, `tt_hits`. D-9 trong DECISIONS (gồm cả `WIN_SCORE` chung từ P2.3).
- Test: 112 passed full suite (~86 s; 111 với `-m "not slow"`), 16 mới trong `tests/test_alphabeta.py`; ruff sạch. Bàn trống 3×3: AB 20 866 nút, ordering+TT 990 (Minimax 549 946) — đo thử, chưa phải số liệu E1.
- File đổi: `gameai/agents/alphabeta.{py,md}`, `tests/test_alphabeta.py`, `docs/DECISIONS.md`, `PROGRESS.md`.
- Lưu ý: 15×15 nên dùng `AlphaBetaAgent(depth=2|3, eval_fn=evaluate, delta_fn=delta_eval, order_fn=move_score)`. Full suite ~1–1,5 phút; `test_kinrow_eval.py::test_delta_eval_matches_brute_force[15-5]` mất ~70 s (có từ P2.2) — đã đánh dấu `slow` (bỏ qua bằng `python -m pytest -m "not slow"`).

#### 2026-11-04 — P2.3
- Đã làm: `agents/minimax.py` — `MinimaxAgent(depth=None, eval_fn=None, use_candidates=True, seed=None)`, max/min tường minh theo góc nhìn người đi ở gốc, đếm nút (kể cả gốc), `root_values`/`value` để so với AB; `terminal_score` = ±(`WIN_SCORE` − ply), `WIN_SCORE = 10**12`.
- Test: 96 passed (17 mới trong `tests/test_minimax.py`); ruff sạch. Cây 3×3 đầy đủ = 549 946 nút, giá trị 0, ~1,3 s. File test chạy ~30 s.
- File đổi: `gameai/agents/minimax.{py,md}`, `tests/test_minimax.py`, `PROGRESS.md`.
- Lưu ý: seed=None → chọn nước tốt nhất đầu tiên (tất định); có seed → ngẫu nhiên trong các nước tốt nhất. Terminal dùng `WIN_SCORE` chung (không phải `win_score(k)`) để AB/minimax cùng thang điểm; AB nên import từ `minimax.py`.

#### 2026-10-28 — P2.2
- Đã làm: `heuristics/kinrow_eval.py` — eval theo cửa sổ k ô (`W[c]=10^(c-1)`), `evaluate`, `delta_eval` (= evaluate sau − trước, quét cục bộ), `move_score` (bậc WIN > BLOCK > delta). Thêm `cell_of(player)` vào `kinrow.py`.
- Test: 79 passed (23 mới trong `tests/test_kinrow_eval.py`); ruff sạch.
- File đổi: `gameai/heuristics/kinrow_eval.{py,md}`, `gameai/games/kinrow.{py,md}`, `tests/test_kinrow_eval.py`, `docs/DECISIONS.md` (D-8), `PROGRESS.md`.
- Lưu ý: delta thuần thích tạo open-four (+1915) hơn chặn four (+1143) nên greedy/ordering/rollout phải dùng `move_score`. AB (P2.4) cộng dồn `delta_eval` + terminal `WIN − depth`. Trọng số chưa tinh chỉnh.

#### 2026-10-28 — P2.1
- Đã làm: `Agent` ABC (`stats` dict, `name`, `reset_stats`, `select_move` abstract); `RandomAgent(seed, use_candidates=False)` với `random.Random` riêng.
- Test: 56 passed (9 mới trong `tests/test_random_agent.py`); ruff sạch.
- File đổi: `gameai/agents/{base,random_agent}.py` + `.md`, `tests/test_random_agent.py`, `PROGRESS.md`.
- Lưu ý: `Agent.select_move` (template method) tự reset stats rồi gọi `_select_move` — agent con chỉ override `_select_move` (D-7). Khóa stats: `nodes`, `iterations`, `time`.

#### 2026-10-28 — P1.2
- Đã làm: `KInRow(n, k, radius=2)` với board `bytearray`, thắng tăng dần (4 hướng qua nước vừa đi), `candidate_moves` giữ tăng dần bằng `_near` + `_cand` cập nhật trong `play`/`undo`, undo bằng stack, `clone` độc lập, `key=(bytes(board), player)`.
- Test: 47 passed (28 mới trong `tests/test_kinrow.py`); `ruff check` và `ruff format --check` sạch.
- File đổi: `gameai/games/kinrow.py`, `gameai/games/kinrow.md`, `tests/test_kinrow.py`, `PROGRESS.md`.
- Lưu ý: `board` lưu 0/1/2 còn người chơi là 1/-1 → eval (P2.2) phải ánh xạ `1 if p == X else 2`. Candidate trả list đã sort (tất định). Bàn trống 3×3 trả toàn bộ ô, bàn lớn trả ô giữa.

#### 2026-10-28 — P1.1
- Đã làm: `Protocol Game` (10 hàm, `@runtime_checkable`), `Move = Hashable`, `P1/P2/DRAW`, hàm `result_for(winner, player)`; `game.md` ghi hợp đồng từng hàm; D-5 trong DECISIONS.
- Test: 19 passed (12 mới trong `tests/test_game_interface.py`); `ruff check .` sạch.
- File đổi: `gameai/core/game.py`, `gameai/core/game.md`, `tests/test_game_interface.py`, `docs/DECISIONS.md`, `PROGRESS.md`.
- Lưu ý cho P1.2: alias `X = P1`, `O = P2` đặt trong `kinrow.py`, không đặt ở core. Hợp đồng chỉ được ép bằng test của từng game, Protocol không ép được.

#### 2026-10-28 — P0.1
- Đã làm: skeleton `gameai/{core,games,heuristics,agents,gui,experiments}` + `__init__.py`, `tests/`, `results/{raw,tables,figures}`, `report/` (`.gitkeep`); `tests/test_smoke.py` (import các gói).
- Test: 7 passed; `ruff check .` sạch.
- File đổi: xem commit `P0.1`.
- Lưu ý: `ruff format --check` từng báo `docs/MODULE_TEMPLATE.md` (code block trong file md) → đã thêm `extend-exclude = ["*.md"]` vào `[tool.ruff]` (commit `P0.1: exclude md from ruff`), nay sạch. pytest cảnh báo không ghi được `.pytest_cache` (WinError 5, quyền Windows) — không ảnh hưởng kết quả. Python venv là 3.13.

### Thành viên 2

<!-- Mẫu:
#### YYYY-MM-DD — <task ID>
- Đã làm: ...
- Test: N passed
- File đổi: ...
- Còn dở / lưu ý cho phiên sau: ...
-->
