# E6 — kiểm chứng cơ chế block h300 — `gameai/experiments/e6_mechanism.py`

> Mục tiêu của file này: agent/thành viên khác dùng được module **mà không cần đọc code**.
> Cập nhật cùng lúc với code.

**Trạng thái:** ✅ full xong  ·  **Task:** P7.1 (D-21, mục kiểm chứng cơ chế)  ·  **Cập nhật:** 2026-11-17

## Mục đích
Kiểm chứng giải thích "block h300 không đơn điệu 0,50 → 0,14 → 0,48" của E6 (a). `e6_choice.csv` thiếu W/N của nước
được chọn và cây con của nút sai → **chạy lại đúng các cây cũ** (không chơi ván mới) và ghi thêm các đại lượng đó.
Module riêng (không thêm bước vào `e6_tactics`) để không đổi hành vi E6; chỉ tái dùng hàm.

## Cách chạy
```
python -m gameai.experiments.e6_mechanism run [--workers 4] [--limit N]   # N task đầu để thử
python -m gameai.experiments.e6_mechanism tables                          # bảng + hình từ raw
```
`run` dừng ngay nếu (1) `git diff kinrow-final -- <CODE_PATHS>` (agents/games/heuristics/core/arena, gồm thay đổi chưa
commit) không rỗng, hoặc (2) một checkpoint lệch `e6_choice.csv` ở `move, n_correct, wn_correct, n_chosen` — task lệch
không được ghi, in 10 dòng lệch, exit 1. Resume theo `(pos_id, rollout, seed)`; file có dòng lệch → từ chối chạy tiếp.
Mỗi lần chạy ghi `raw/e6_mechanism_runinfo.csv` (power, % pin, thời gian, commit).

## Public API
- `mechanism_task(pos, rollout, seed, refs, checkpoints)` → 1 dòng/checkpoint: dựng cây như `e6_tactics.choice_task`
  (`spec_off`, `derive_seed(seed, pos_id)`, `checkpoint_moves`), so với `refs[iter]` (dòng raw cũ) → `matches_raw`.
- `root_row(root, chosen, correct)`, `matches(row, ref)`, `run(workers, limit)`, `build_table()`, `make_figure()`,
  `code_unchanged()`.

## File
- Raw `results/raw/e6_mechanism.csv` (1 dòng/(thế block, rollout, seed, iter)): `move, matches_raw, correct, n_chosen,
  wn_chosen, n_correct, wn_correct` (con đúng N lớn nhất, như raw cũ), `n_children, n_wrong, frac_wrong_zero` (tỷ lệ con
  sai có W = 0), `max_n_wrong`; **nút sai top** = con sai có (N, W) lớn nhất (= nước được chọn khi chọn sai; tính cả khi
  chọn đúng để không thiên lệch): `n_wrong_top, wn_wrong_top, children_wrong_top`, `refute_expanded` (ô thắng của đối thủ
  — ở thế block chính là ô chặn — đã là con của nút đó), `n_refute`, `wn_refute` (luôn 1: nút thắng kết thúc → kiểm tra),
  `git_commit, git_dirty`.
- Bảng `results/tables/e6_mechanism.csv`: rollout × iter × nhóm (`all`, `correct=1`, `correct=0`) — `n_pos, n_runs,
  correct_rate`, trung bình + bootstrap cụm thế (`_boot_ci`, 2 000 lần) của `frac_wrong_zero` (`fwz_lo/hi`),
  `wn_chosen`, `wn_correct`, `wn_wrong_top`, `refute_rate`; `wn_chosen_gt0`, `chosen_ge_correct`, trung vị N, 
  `ncorr_gt_maxwrong`, `median_n_refute`, `wn_wrong_top_refuted / _unrefuted`.
- Hình `results/figures/e6_mechanism.png`: (1) tỷ lệ con sai W = 0 (mọi lần chạy), (2) nhóm chọn sai: W/N nước được chọn
  vs W/N ô chặn, (3) nhóm chọn sai: tỷ lệ ô thắng của đối thủ đã mở dưới nước sai; rand và h300.

## Kết quả (2026-11-17, commit `e98dc49` + file chưa commit ngoài `CODE_PATHS`)
900 task (45 thế × 10 seed × 2), 4 500 dòng, **khớp `e6_choice.csv` 100 %**, 589 s / 4 worker, AC (59 %). Kết luận từng
bước (dự đoán ghi trước ở D-21): xem `e6_tactics.md` mục "Kiểm chứng cơ chế".

## Phụ thuộc
`e6_tactics` (`checkpoint_moves`, `spec_off`, `correct_set`, `position_game`, `load_positions`, `choice_path`,
`_boot_ci`, `power_status`, `COLORS/MARKERS`), `e5_rollout` (`CODE_PATHS`, `_append_csv`, `_write`, `_style`, `fnum`),
`agents.mcts.Node/MCTSAgent._final_child`, `arena.derive_seed`.

## Test
`tests/test_e6_mechanism.py`: khớp `choice_task` ở mọi checkpoint (rand, h300); phát hiện lệch / thiếu raw; `root_row`
trên cây dựng tay (con sai top, `frac_wrong_zero`, `refute_expanded`, `n_refute`, W/N); nhóm `correct=0/1` + trung bình
trong `build_table`. Chạy: `python -m pytest tests/test_e6_mechanism.py -q`.

## Hạn chế
- Chỉ thế block (loại 1). `refute_expanded` chỉ xét con trực tiếp của nút sai top, không xét sâu hơn.
