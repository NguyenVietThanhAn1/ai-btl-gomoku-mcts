# p64_strength — `gameai/experiments/p64_strength.py`

**Trạng thái:** 🔄 đang làm  ·  **Task:** P6.4 B5 (D-36)  ·  **Cập nhật:** 2026-11-18

## Mục đích
Đo sức mạnh AB Khó mới của chế độ chơi GUI (15×15) so với AB Vừa mới (= Khó cũ, E1) và MCTS Khó (E3 5000 iter), cho
từng `top_k` thử: (16, 12, 8) và (12, 8, 6). **Số minh họa GUI — chỉ ghi DECISIONS (D-36) / PROGRESS, không vào report,
không ghi `results/`.**

## Public API / cách chạy
```
python -m gameai.experiments.p64_strength --quick        # 4 khai cuộc (8 ván) / ô, file p64strength_quick_*
python -m gameai.experiments.p64_strength                # 20 khai cuộc (40 ván) / ô
  [--pairs N] [--workers 3] [--topk k16_12_8 k12_8_6] [--opponents ab_vua mcts_kho] [--out DIR] [--base-seed 0]
```
- Ô = `<top_k>_vs_<đối thủ>`; A = AB Khó mới (`hard_spec(top_k)` = `presets.AB15_HARD` đổi `top_k`), B = đối thủ.
- `make_opening(pair_seed, taken)` / `make_openings(n, base_seed)`: khai cuộc tất định theo seed — 2–4 nước luân phiên
  trong `candidate_moves` (quanh tâm), ván chưa kết thúc, người sắp đi **không** có nước thắng ngay
  (`has_immediate_win`), và **đôi một khác nhau**. Mỗi khai cuộc 2 ván đổi bên (`AX` = A cầm X, `BX`).
- `play_one(task)`, `run_cell(...)` (resume: bỏ ván đã có; spec khác file → dừng), `summarize(rows)` (điểm A thắng 1 / hòa 0,5,
  W/D/L, Wilson, điểm theo bên, `distinct_openings`, `duplicate_games` = số ván trùng chuỗi nước, `errors`).
- Output (mặc định `local_out/p64/`, gitignore; `--out` trong `results/` bị từ chối): `p64strength[_quick]_<ô>.csv`
  (mỗi ván: khai cuộc, chuỗi nước, kết quả, thời gian/nước A và B, `a_depth_mean`, spec, commit) và `..._summary.csv`.

## Điều kiện & lưu ý
- Agent theo thời gian rất nhạy tải CPU → ít worker (mặc định 3); ghi nguồn điện/bench khi báo số. Thắng-thua phụ thuộc
  tốc độ máy ở thời điểm chạy: **chỉ minh họa**.
- AB Vừa (E1) tất định, AB Khó gần tất định (hết giờ giữa chừng làm kết quả phụ thuộc thời gian) → khai cuộc ngẫu nhiên có
  seed để 20 ván cùng bên không lặp lại một ván; số ván trùng chuỗi nước được báo cùng điểm.
- Điểm Wilson coi hòa = 0,5 (xấp xỉ).

## Test
`tests/test_p64_strength.py`: khai cuộc hợp lệ/đôi một khác nhau/tất định/không thắng ngay, `has_immediate_win`,
`hard_spec` chỉ đổi `top_k`, `summarize` (trùng chuỗi, khai cuộc phân biệt, theo bên), `run_cell` (cặp đổi bên, resume, spec
khác), `--out` trong `results/` bị từ chối.
