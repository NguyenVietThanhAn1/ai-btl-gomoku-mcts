# E3 — Ảnh hưởng của hằng số khám phá c — `gameai/experiments/e3_c_sweep.py`

> Mục tiêu của file này: agent/thành viên khác dùng được module **mà không cần đọc code**.
> Cập nhật cùng lúc với code.

**Trạng thái:** 🔄 quick xong, chờ duyệt full  ·  **Task:** E3 (D-18)  ·  **Cập nhật:** 2026-11-10

## Mục đích
Đề ý 3: c ∈ {0.5, 1.0, 1.4, 2.0} × iter ∈ {100, 250, 500, 1000, 2500, 5000}, đồ thị iteration – tỉ lệ thắng,
mỗi c một đường, kèm Wilson 95 %. Ngân sách **iteration** (không `time_limit`) → kết quả không phụ thuộc tải máy.

| Phần (`part`) | MCTS | Đối thủ | Ván/điểm | Độ đo chính |
|---|---|---|---|---|
| `3x3_random` | rollout random, `check_tactics=False` | Random | 200 | win rate (+ non-loss) |
| `3x3_minimax` | như trên | `CachedMinimaxAgent` (Minimax có seed, cache theo key) | 100 | non-loss |
| `greedy` | h300 (`heavy_kinrow`, T=300, không cắt), `check_tactics=True` | `GreedyAgent(move_score)` | 50 | win rate |
| `ab2` | như trên | AB depth 2 (D-10) | pilot 20 → (qua cổng) 50, iter {2500, 5000} | win rate |

Mọi điểm dùng `base_seed = 0` → các c chơi **cùng seed** (thiết kế cặp). Nhãn MCTS `c<c>_i<iter>`.

## Cách chạy
```
python -m gameai.experiments.e3_c_sweep all --quick      # 3x3 + greedy + ab2-pilot + hình + ước tính
python -m gameai.experiments.e3_c_sweep 3x3              # full từng phần, resume được
python -m gameai.experiments.e3_c_sweep greedy
python -m gameai.experiments.e3_c_sweep ab2-pilot        # SAU greedy (đọc bảng greedy để chọn c)
python -m gameai.experiments.e3_c_sweep ab2 [--force]    # chỉ chạy nếu pilot qua cổng
python -m gameai.experiments.e3_c_sweep plot             # vẽ lại từ bảng
```
Cờ chung: `--workers` (4), `--allow-code-change`. `all` **không** gồm `ab2` (cần đọc kết quả cổng).
Quick ghi `e3quick_*`: 3×3 đủ lưới × 2 cặp; greedy c ∈ {0.5, 2.0} × iter ∈ {100, 1000, 5000} × 1 cặp; ab2-pilot
1 cặp (không áp luật cổng); `results/tables/e3quick_estimate.csv` = ước tính thời gian full.

## Luật D-18 (chốt trước khi chạy)
- **c của pilot** — `choose_pilot_c(greedy_table, 5000)`: c có win rate vs Greedy (dòng `all`) cao nhất ở 5000 iter;
  hòa → 1.4 nếu trong nhóm hòa, không thì c gần 1.4 nhất.
- **Cổng** — `gate_passes(wins)`: pilot 20 ván, thắng ≥ 2 → chạy `ab2` (iter {2500, 5000} × 4 c × 50 ván; điểm pilot
  resume từ 20 lên 50 ván); ≤ 1 → bỏ AB2, báo cáo dùng pilot làm bằng chứng floor effect.

## API
- `mcts_spec(board, c, iterations) -> AgentSpec`; `label_for(c, it)`; `points(part, quick)` (iter thấp trước);
  `raw_path(part, c, it, quick)`; `PARTS: dict[str, Part]`.
- `run_part(part_name, quick, workers, allow_code_change, pts=None, n_pairs=None, table_name=None, raw_dir, table_dir)`
  → bảng dạng dài; `run_3x3`, `run_pilot`, `run_ab2(..., force)`.
- `choose_pilot_c`, `gate_passes` (luật D-18).
- `CachedMinimaxAgent(seed)`: Minimax `depth=None`; danh sách nước có giá trị tốt nhất (`root_values`, thang
  `WIN − ply` như E2) nhớ trong `_MINIMAX_CACHE` theo `game.key()` (mỗi tiến trình một bản), chọn ngẫu nhiên bằng
  `random.Random(seed)` riêng. `stats`: `nodes` (0 khi trúng cache), `iterations` 0, `time`, `cache_hit`.
  Dùng qua registry: `AgentSpec("gameai.experiments.e3_c_sweep:CachedMinimaxAgent")`.
- `fit_cost(rows) -> (a, b)` (sec/ván = a + b·iter, bình phương tối thiểu trên giờ CPU/ván = `a_time_sum + b_time_sum`),
  `estimate_full()` → `e3quick_estimate.csv` (`seq_minutes`, `est_4w_minutes` = tuần tự / 3,5).
- `plot_panels(panels, path, title)`, `make_figures(quick)`.

## File
- Raw: `results/raw/e3_<part>_c<c>_i<iter>.csv` (+ `_moves`), schema runner (`common.md`).
- Bảng: `results/tables/e3_{3x3_random,3x3_minimax,greedy,ab2_pilot,ab2}.csv` = `part, c, iterations` +
  `SUMMARY_COLUMNS` (3 dòng/điểm: `all`, `A=X`, `A=O`). Iteration/nước báo cáo lấy `a_search_iterations_per_move` (D-15).
- Hình: `results/figures/e3_3x3.png` (3 panel: thắng vs Random, không thua vs Random, không thua vs Minimax),
  `e3_greedy.png`, `e3_ab2.png` (nếu chạy). Trục x log, 1 đường/c (màu + marker riêng, cố định theo c), thanh lỗi Wilson.
  Bảng màu: 4 slot đầu của bảng phân loại mặc định của skill dataviz, đã qua validator (CVD ΔE ≥ 9,1); hai màu
  tương phản < 3:1 nên có marker riêng + bảng CSV đi kèm.

## Quick (2026-11-10, commit `36e9b68`, không commit file `e3quick_*` — không phải số liệu báo cáo)
Tổng 310 s, 4 worker; mọi ván `normal`, `git_dirty = 0`, `distinct_games` = n ở mọi điểm.
- 3x3_random 45 s (96 ván), 3x3_minimax 79 s (96 ván), greedy 71 s (12 ván), ab2-pilot 112 s (2 ván, c = 2.0 chọn
  theo luật từ bảng greedy quick).
- Ván 15×15 ở 5000 iter: vs Greedy 17–22 nước, MCTS 2,2–2,7 s/nước; **vs AB2 50 và 83 nước** (MCTS trụ lâu rồi thua),
  MCTS 2,6–3,0 s/nước, AB2 ~0,07 s/nước → ~94 s/ván, đắt hơn ước tính trong plan (~25 s).
- Ước tính full (`e3quick_estimate.csv`, fit a + b·iter; 4 worker = tuần tự / 3,5) và hiệu chỉnh:

| Phần | Ván | Fit tuần tự | Fit 4 worker | Ghi chú |
|---|---|---|---|---|
| 3x3_random | 4 800 | 4,8 phút | 1,4 phút | + ~1,8 s khởi động pool/điểm → ~2–3 phút |
| 3x3_minimax | 2 400 | 32,5 phút | 9,3 phút | cận trên: a = 0,72 s/ván là cache lạnh (quick 4 ván/điểm) |
| greedy | 1 200 | 143,6 phút | 41 phút | |
| ab2 pilot | 20 | 31,3 phút | 8,9 phút | |
| ab2 full | 380 | 595 phút | 170 phút | quá cao: fit chỉ có điểm 5000 (b = 0); tỉ lệ theo iter → ~440 phút tuần tự, **~2 h** 4 worker |

## Phụ thuộc
`experiments/common.py` (`run_match`, `summarize`, `read_rows`, `moves_path_for`, `add_runner_args`),
`agents/registry.py`, `agents/minimax.py`, matplotlib (Agg).

## Giải thích cho báo cáo
**Vai trò của c.** Ở bước chọn, MCTS-UCT đi xuống con có điểm UCT lớn nhất:
`UCT(con) = W/N + c · √(ln N_p / N)`. Số hạng đầu là **khai thác** (tỉ lệ thắng ước lượng, góc nhìn người vừa đi vào
con), số hạng sau là **khám phá** (lớn khi con ít được thăm so với cha). c nhỏ → tập trung sớm vào nước đang tốt nhất
(nhanh hội tụ nhưng dễ bỏ sót nước tốt bị ước lượng thấp lúc đầu); c lớn → rải iteration đều hơn (ít bỏ sót nhưng
cây nông, ước lượng nước tốt nhất chậm chính xác). c = √2 ≈ 1,4 là giá trị lý thuyết của UCB1 khi thưởng trong [0, 1].

**Vì sao c tốt phụ thuộc bài toán.** Thang của W/N do rollout quyết định: rollout random trên 3×3 cho W/N trải rộng,
còn rollout heavy (h300) trên 15×15 cho kết quả ít nhiễu hơn và hệ số nhánh lớn (~50–150 candidate), nên cùng một c
cho mức cân bằng khám phá/khai thác khác nhau. Vì vậy E3 đo riêng 3×3 (rollout random) và 15×15 (h300) — không
suy c tốt của bàn này sang bàn kia.

**Thiết kế ván và cách đọc khoảng tin cậy.** Mỗi điểm (c, iter) chơi 2·n ván đổi lượt; mọi c dùng **cùng** dãy seed.
Thanh lỗi trên hình là **Wilson 95 % tính độc lập cho từng điểm** (công thức ở `common.md`) — nó không dùng thông tin
"cùng seed" giữa các c. Do đó: (1) hai khoảng chồng nhau **không** chứng tỏ hai c như nhau; (2) hai khoảng tách nhau là
dấu hiệu khác biệt nhưng chưa phải kiểm định cặp. Báo cáo chỉ nêu xu hướng chung (vd. "c nhỏ tốt hơn ở iteration
thấp") một cách thận trọng; kết luận "c₁ tốt hơn c₂" cần phép so sánh cặp theo seed riêng.

**Đối thủ.** 3×3 vs Random đo khả năng tận dụng sai lầm (win rate); vs Minimax hoàn hảo chỉ có thể hòa hoặc thua nên
đo non-loss. 15×15 vs Greedy (1-ply, rẻ). AB depth 2 chỉ chạy ở iteration cao nếu pilot cho thấy MCTS ra khỏi sàn 0 %
(P3.3: ở ~0,5 s/nước ≤ 2/20) — ở sàn mọi đường c trùng nhau, không đo được ảnh hưởng của c.

## Test
`tests/test_e3_c_sweep.py`: spec 3×3/15×15 (tactics, h300, không `time_limit`), nhãn duy nhất + quick ⊂ full, cỡ lưới và
số ván, `choose_pilot_c` (max rõ, hòa có 1.4, hòa không có 1.4, đọc chuỗi CSV, thiếu điểm → lỗi), `gate_passes`
(0, 1, 2, 20), `CachedMinimaxAgent` (dựng qua registry, cache hit, nước tối ưu, chặn, ngẫu nhiên trong nước tối ưu),
`run_part` end-to-end (`workers=1`, 2 điểm, cột bảng), `fit_cost`, `estimate_full` (dữ liệu giả), `plot_panels` ra PNG.
Chạy: `python -m pytest tests/test_e3_c_sweep.py -q`.

## Hạn chế / TODO
- Cache Minimax theo tiến trình; mỗi `run_match` mở pool mới nên cache dựng lại mỗi điểm (rẻ: < vài giây).
- Ước tính 4 worker = tuần tự / 3,5 (thô).
