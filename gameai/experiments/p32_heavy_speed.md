# p32_heavy_speed — `gameai/experiments/p32_heavy_speed.py`

> Mục tiêu của file này: agent/thành viên khác dùng được module **mà không cần đọc code**.
> Cập nhật cùng lúc với code.

**Trạng thái:** ✅ ổn định  ·  **Task:** P3.2 (D-12)  ·  **Cập nhật:** 2026-11-10

## Mục đích
Đo tốc độ rollout 15×15 của random, `HeavyRollout(move_score, T)` (bản chuẩn) và `KInRowHeavyRollout(T)`
(bản tăng dần), kiểm chuỗi nước của hai bản heavy có giống hệt không, và đo số iteration MCTS trong cùng
`time_limit`. Số đo phát triển (P3.2), **không phải số liệu E5**.

## Cách chạy
```
python -m gameai.experiments.p32_heavy_speed            # full: 50 rollout/ô, ~25 s, ghi results/
python -m gameai.experiments.p32_heavy_speed --quick    # 5 rollout/ô, chỉ in, không ghi file (~3 s)
python -m gameai.experiments.p32_heavy_speed --n 100    # đổi số rollout/ô
```

## Thiết lập
- T ∈ {100, 300, 1000}; khai cuộc 6 hoặc 20 nước ngẫu nhiên trên candidate (thế thứ i: seed `i`).
- Rollout thứ i dùng `random.Random(1000 + i)` cho **cả** bản chuẩn và bản nhanh, từ cùng thế cờ (clone).
- Một object policy dùng lại qua mọi rollout (giống trong MCTS).
- MCTS: `MCTSAgent(time_limit=0,5, rollout_policy=..., seed=1000+i)`, rollout tới hết ván, 3 thế/ô.

## Output
- `results/raw/p32_heavy_speed.csv` — mỗi rollout một dòng: `policy, temperature, opening_moves,
  opening_seed, rng_seed, plies, seconds, identical_to_ref` (1/0, chỉ với `heavy_kinrow`).
- `results/tables/p32_heavy_speed.csv` — theo (policy, T, khai cuộc): `n_rollouts, mean_plies, us_per_ply,
  ms_per_rollout, speedup_vs_ref, identical_to_ref` (k/n), `python, machine`.
- `results/tables/p32_mcts_iterations.csv` — `mean_iterations` và `plies_per_iter` mỗi nước.
- Ghi đè khi chạy lại; số đo thời gian phụ thuộc máy và tải.

## Phụ thuộc
- Dùng: `games/kinrow.py`, `agents/rollout.py`, `agents/mcts.py`, `heuristics/kinrow_eval.py`,
  `heuristics/kinrow_rollout.py`.

## Hạn chế
- Chạy tuần tự một tiến trình; không có cờ `--workers`.
- In ra console bằng ASCII (console Windows cp1252 không in được tiếng Việt).
