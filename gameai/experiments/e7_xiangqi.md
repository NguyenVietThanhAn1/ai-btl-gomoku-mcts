# E7 cờ tướng — `gameai/experiments/e7_xiangqi.py`

> Mục tiêu của file này: agent/thành viên khác dùng được module **mà không cần đọc code**.
> Cập nhật cùng lúc với code.

**Trạng thái:** 🟡 full xong (2026-11-26, kết quả D-25)  ·  **Task:** P8.4 (D-25)  ·  **Cập nhật:** 2026-11-26

## Mục đích
Thí nghiệm E7 cờ tướng (thiết kế D-25): (a) AB depth 1/2 vs Random, (b) move ordering của AB (số nút, tất định),
(c) MCTS rollout ngẫu nhiên tới hết ván vs cắt L ply + eval (kèm kiểm lại L = 0 vs L = 10 với tactics bật, D-24),
(d) MCTS tốt nhất ở (c) vs Alpha-Beta cùng giây/nước.

## Chạy
```
python -m gameai.experiments.e7_xiangqi all --quick          # 4 ván/điểm, file e7quick_*, + wcheck + ước tính
python -m gameai.experiments.e7_xiangqi b                    # từng phần (chạy tiếp được sau khi ngắt)
python -m gameai.experiments.e7_xiangqi c                    # c1..c4 (1 worker) rồi in kết luận luật c4
python -m gameai.experiments.e7_xiangqi d                    # cần c1 + c4 đủ ván; L0 mạnh hơn rõ → DỪNG (mã 3)
python -m gameai.experiments.e7_xiangqi summary              # dựng lại bảng + hình từ raw
```
Phần: `bench, b, c, c1..c4, d, d1, d2, a, a1, a2, wcheck, summary, all`. Cờ: `--quick`, `--workers` (mặc định 1, D-25),
`--pairs` (mặc định 25; quick 2), `--allow-code-change`, `--allow-battery` (full mặc định từ chối khi chạy pin, D-21),
`--skip-bench`, `--raw-dir/--table-dir/--fig-dir/--log`.
`all` = b → c → luật c4 → d → a → summary (quick thêm `wcheck` và ước tính). Mọi dòng in ra được append vào
`results/e7_full.log` (quick: `results/e7quick.log`), mỗi lần gọi có dòng đầu ghi giờ, nguồn điện, commit.

## Cấu hình (D-25)
| Điểm | A | B |
|---|---|---|
| c1 | MCTS `Lend` (rollout tới hết, chặn `max_plies`) | MCTS `L10` |
| c2 | MCTS `Lend` | Random |
| c3 | MCTS `L10` | Random |
| c4 | MCTS `L0` (chấm eval ngay ở lá) | MCTS `L10` |
| d1 / d2 | MCTS tốt nhất ở (c), 1 s / 2,5 s | AB `ab_t1` / `ab_t2.5` |
| a1 / a2 | AB depth 1 / 2 cố định | Random |

- MCTS: `xq_mcts_spec(time_limit=1 s, rollout_limit=L, tactics=True)` (c = √2, σ(`xq_evaluate`/2000)). Nhãn `mcts_L<L>`
  (+ `_t<t>` nếu t ≠ 1 s).
- AB (d) theo D-23, không theo GUI: `ab_spec(12, use_tt=True, time_limit=t)` + `tt_mode="exact"`, không `top_k`
  (iterative deepening, trả nước của độ sâu hoàn tất gần nhất).
- Ván: `GameSpec("xiangqi", {"max_plies": 200})`, khai cuộc ngẫu nhiên 4 ply (`random_opening=4`), `base_seed = 7000`,
  mỗi khai cuộc 2 ván đổi bên (`common.run_match`), 25 khai cuộc = 50 ván/điểm.
- File moves ghi thêm cột `depth_reached` (`extra_move_stats`, chỉ AB có `time_limit` mới có giá trị).

## Luật chốt trước (D-25)
- `l_verdict(score, n)` cho c4 (A = L0): Wilson cận dưới > 0,5 → `L0_stronger` (full: **DỪNG trước (d)**, báo An);
  cận trên < 0,5 → `L10_stronger`; còn lại `tie` (giữ L = 10).
- `best_rollout(c1, c4)`: mặc định `L10`; `Lend` (c1) / `L0` (c4) thay nếu thắng L10 với Wilson cận dưới > 0,5; cả hai → điểm cao hơn.
- `wcheck`: iter/s trung vị của MCTS ở c3 với 1 worker vs `WCHECK_WORKERS` = 3 (file riêng `c3_w1`, `c3_w3`); giảm > 15 %
  (`WORKER_DROP_LIMIT`) → khuyến nghị full **1 worker**, ngược lại 3 (`e7quick_workers.csv`, cột `recommend`; ước tính
  dùng số này). Quick 2026-11-25: giảm 25 % → **full chạy 1 worker** (2 worker chưa đo, không dùng), ~5,6 h qua đêm.

## Public API (dùng trong test / script khác)
```python
mcts(rollout: int | None, t=1.0) -> AgentSpec; ab_time(t) -> AgentSpec; d_specs(best) -> {point: (A, B)}
FIXED_POINTS: dict[str, tuple[AgentSpec, AgentSpec]]   # c1..c4, a1, a2
classify_game(row) -> (term, ply)     # term ∈ mate | stalemate | repetition | max_plies | error (replay từ CSV)
side_game_stats(moves, side) -> dict  # 1 ván, 1 bên: iter/s (nước có search), độ sâu cây, ply rollout/iter, depth_reached
summarize_point(point, rows, moves) -> 3 dòng (all, A=Đỏ, A=Đen) theo MATCH_COLUMNS
l_verdict(score, n) -> str; best_rollout(c1, c4) -> "L10" | "Lend" | "L0"
run_ordering(quick, raw_dir, fens=None, depths=(2,3,4)) -> rows; ordering_table(rows) -> rows
```

## File ra
- Raw: `results/raw/e7_<điểm>.csv` + `_moves.csv` (schema `common`, + `depth_reached`), `e7_ordering.csv` (mỗi
  (thế, depth, cấu hình) một dòng: nút, giây, giá trị gốc, nước, `value_match` so với `none`), `e7_runinfo.csv` (mỗi
  phần: workers, power, pin %, bench/`e5_bench`, giờ, commit, dirty). Quick: tiền tố `e7quick_` (gitignore).
- Bảng: `results/tables/e7_matches.csv` (`MATCH_COLUMNS`: W/D/L, điểm + Wilson 95 %, `distinct_games`, `term_*`, ply TB/
  trung vị, mỗi bên `s_per_move_mean/max`, `iter_per_s_mean/median/cv`, `tree_depth_mean`, `rollout_plies_per_iter`,
  `nodes_per_move`, `depth_reached_mean/min/max`, workers, commit); `e7_ordering.csv` (theo depth × cấu hình: tổng nút,
  giây, nút/s, tỉ lệ so với `none`, số thế khớp/lệch giá trị). Quick thêm `e7quick_workers.csv`, `e7quick_estimate.csv`.
- Hình: `results/figures/e7_scores.png` — điểm A + Wilson 95 % mỗi điểm, đường 0,5.

## Định nghĩa số đo
- **Điểm** = (W + 0,5·D)/n theo góc nhìn A; **Wilson 95 % trên điểm** (`p83_mcts_check.wilson_score`, như lmatch).
- **Lý do kết thúc:** replay khai cuộc + nước tới thế cuối; thắng/thua và bên thua đang bị chiếu → chiếu bí, không → bí nước;
  hòa với ply < `max_plies` → lặp thế 3 lần, = `max_plies` → giới hạn nước; `termination ≠ normal` → lỗi. Replay kiểm
  `winner` khớp CSV (lệch → `ValueError`).
- **iter/s một ván** = Σ iterations / Σ `agent_time` trên các nước có search (bỏ tactic 1/2 đi thẳng, D-15); bảng báo
  trung bình, trung vị và CV (độ lệch chuẩn / trung bình) giữa các ván — CV lớn → nhiễu tải máy.
- **Độ sâu cây MCTS** = `max_depth` TB trên nước có search; **ply rollout/iter** = Σ `rollout_plies` / Σ iterations
  (stats sẵn có của `MCTSAgent`, không sửa agent).
- **s/nước** = thời gian arena đo (gồm cả tactics); AB: `depth_reached` của iterative deepening.
- (b) dựng thế từ FEN → không có lịch sử lặp nên TT không gặp vấn đề lặp thế (D-22). `value_match = 0` được đếm, không giấu.

## Phụ thuộc
- Dùng: `common.run_match` (+ `extra_move_stats`), `p82_ab_check` (`ab_spec`, `RANDOM`, `midgame_fens`),
  `p83_mcts_check` (`xq_mcts_spec`, `wilson_score`), `e5_rollout.bench`, `e6_tactics.power_status`, `figfmt`.
- Không sửa `gameai/agents/`; không ghi đè raw của thí nghiệm khác.

## Giải thích cho báo cáo
- **Vì sao cắt rollout (3.4).** Rollout ngẫu nhiên tới hết ván cờ tướng rất dài (TB ~269 ply, 107/150 ván hòa vì
  `max_plies`/lặp thế, `xiangqi.md`) → mỗi iteration đắt (~60 ván/s) và kết quả gần như luôn là hòa 0,5, không phân biệt
  nước. Cắt sau L ply rồi chấm σ(eval/scale) giống ý tưởng value network: thay phần đuôi rollout bằng ước lượng giá trị.
  E7(c) đo trực tiếp: `Lend` vs `L10` cùng 1 s/nước, và mỗi bên vs Random làm mốc sàn.
- **Kiểm lại L (c4).** P8.3 chọn L = 10 với tactics tắt (lmatch, ngang L = 0). c4 lặp lại so sánh ở cấu hình dùng thật
  (tactics bật) với luật chốt trước ở trên.
- **Thiết kế ván đấu.** Khai cuộc ngẫu nhiên 4 ply theo seed (agent theo thời gian/AB gần tất định → không có khai cuộc
  ngẫu nhiên thì các ván trùng nhau); mỗi khai cuộc chơi 2 ván đổi bên để triệt tiêu lợi thế đi trước; cùng 25 khai cuộc ở
  mọi điểm.
- **Hạn chế thống kê.** Wilson coi điểm có hòa như tỉ lệ nhị thức và 2 ván cùng khai cuộc không độc lập → khoảng hơi hẹp
  hơn thật (như lmatch). Agent theo thời gian phụ thuộc tốc độ máy: ghi bench + nguồn điện + CV iter/s.
- **Ordering (b).** Alpha-Beta cắt nhánh nhiều hơn khi nước tốt được xét trước; MVV-LVA ưu tiên ăn quân giá trị cao bằng
  quân giá trị thấp; TT tái dùng giá trị thế đã gặp (chuyển vị). Cả ba cho **cùng giá trị gốc** (alpha-beta chính xác),
  chỉ khác số nút — bảng kiểm điều này trên 11 thế.

## Test
`tests/test_e7_xiangqi.py`: lý do kết thúc (chiếu bí, bí nước, lặp thế, `max_plies`, lỗi, replay lệch winner → lỗi);
`l_verdict` ba nhánh; `best_rollout`; spec theo D-23/D-25 (AB `tt_mode` exact, không `top_k`; MCTS tactics bật,
`Lend` = `rollout_limit None`); `side_game_stats` (bỏ nước tactic / AB 0 iteration); ordering 1 thế depth 2 cùng giá trị +
chạy lại không thêm dòng; `run_point` + resume không chơi lại + cột `depth_reached` + `summarize_point`; `part_d` chưa có
c → mã 2, L0 mạnh hơn → mã 3 không chạy (d), ngang → chạy d1, d2. Chạy: `python -m pytest tests/test_e7_xiangqi.py -q`.

## Hạn chế / TODO
- Hình/bảng chưa nối vào `plots.py --check` (làm khi có số full, cùng đợt bổ sung báo cáo).
- AB trong ván thật có TT + lặp thế (D-22) — chỉ ghi nhận.
