# Quét sơ bộ tham số heavy rollout — `gameai/experiments/p33_heavy_sweep.py`

> Mục tiêu của file này: agent/thành viên khác dùng được module **mà không cần đọc code**.
> Cập nhật cùng lúc với code.

**Trạng thái:** 🔄 script xong, mới chạy hiệu chỉnh + `--quick`  ·  **Task:** P3.3 (D-12, D-14)  ·  **Cập nhật:** 2026-11-10

## Mục đích
Chọn T, `rollout_limit` và `scale` của `sigmoid_value` cho heavy rollout trước E5. Kết quả là **số liệu sơ
bộ, không phải số liệu E5** (tên bảng có hậu tố `_prelim`).

## Cách chạy
```
python -m gameai.experiments.p33_heavy_sweep calibrate              # hiệu chỉnh scale (tất định, < vài phút)
python -m gameai.experiments.p33_heavy_sweep sweep --quick          # 1 seed × 2 ván/match + kiểm tra worker
python -m gameai.experiments.p33_heavy_sweep sweep [--workers 4] [--allow-code-change]   # full
python -m gameai.experiments.p33_heavy_sweep all ...                # calibrate rồi sweep
```
Commit trước khi chạy sweep (cột `git_commit` / `git_dirty`, xem `common.md`).

## Public API (dùng trong test / script khác)
```python
TEMPERATURES = (100, 300, 1000); SCALES = (100, 200, 300, 500, 1000, 2000, 5000)
CALIB_SEEDS = range(50_000, 50_200); OPENING_RANGE = (4, 20); TIME_LIMIT = 0.5; ROLLOUT_LIMIT = 10
BASE_SEED = 0; N_PAIRS = 10; QUICK_PAIRS = 1; MAX_GRID_EXTENSIONS = 4
OPPONENTS: dict[str, AgentSpec]   # "greedy", "ab2" (chuẩn D-10), "mrand" (MCTS random 0,5 s + tactics, D-14)
def calibration_samples(temperature, seed) -> list[dict]   # mọi thế chưa kết thúc của 1 rollout
def generate_calibration(seeds=CALIB_SEEDS, temperatures=TEMPERATURES) -> list[dict]
def mean_loglik(samples: Iterable[(eval, z)], scale) -> float
def fit_scale_grid(samples, scales=SCALES, max_extensions=4) -> (dict[scale, ll], best_scale)
def fit_scales(rows, scales=SCALES) -> list[dict]     # bảng SCALE_COLUMNS
def chosen_scales(table) -> dict[T, scale]
def describe_fit(table) -> list[str]                  # scale chọn + ll của nó và 2 scale kề bên
def calibrate(raw=CALIB_RAW, table=SCALE_TABLE) -> dict[T, scale]
def sweep_configs(scales: dict[T, scale]) -> list[AgentSpec]    # 7 cấu hình; thiếu scale → KeyError
def match_path(config, opponent, quick) -> Path; def summary_path(quick) -> Path
def sweep(quick, workers, allow_code_change) -> None
def worker_check(spec, workers, allow_code_change) -> None
def choose_config(summary, configs) -> list[dict]     # luật chọn D-14, cột CHOICE_COLUMNS
def describe_choice(choice) -> list[str]; def choice_path(quick) -> Path
```

### Bước 1 — hiệu chỉnh `scale` (mỗi T một scale)
- Với mỗi T và seed s ∈ [50 000, 50 199]: `rng = Random(derive_seed(s, "calib-T<T>"))`, bàn 15×15 k=5,
  khai cuộc `rng.randint(4, 20)` quân bằng `arena.random_opening_moves`, rồi `KInRowHeavyRollout(T)` tới hết
  ván với cùng `rng`. Ghi **mọi thế chưa kết thúc** từ sau khai cuộc: `eval_p1 = evaluate(g, P1)`, nhãn
  `z = result_for(winner, P1)` ∈ {1, 0,5, 0}.
- Chọn scale trên lưới theo mean log-likelihood. Tốt nhất ở **biên** lưới → thêm biên dưới ÷ 2 hoặc biên trên
  × 2 (vd. 50, hay 10 000, 20 000) và fit lại, tối đa 4 lần; vẫn ở biên → cột `at_edge = 1` + in `WARNING`.
- File: `results/raw/p33_calib_positions.csv` (`temperature, seed, opening_len, ply, to_move, eval_p1, z`;
  có sẵn → dùng lại, không ghi đè) và `results/tables/p33_scale_prelim.csv` (`temperature, scale,
  n_positions, n_rollouts, mean_loglik, chosen, extended, at_edge`).

### Bước 2 — quét
- Đọc scale từ `p33_scale_prelim.csv` (thiếu → dừng, yêu cầu `calibrate`).
- 7 cấu hình MCTS, chung `iterations=None`, `time_limit=0.5`, **`check_tactics=True` (D-14)**, `c` /
  `final_move` mặc định: `rand`; `h100`, `h300`, `h1000` (`heavy_kinrow`, không cắt); `h100c10`, `h300c10`, `h1000c10`
  (`rollout_limit=10`, `value_scale` = scale của đúng T).
- × 3 đối thủ (`greedy`, `ab2`, `mrand`) = 21 match, mỗi match `run_match(n_pairs=10, base_seed=0,
  random_opening=0)` = 20 ván → **420 ván** full (140 mỗi đối thủ). `rand` vs `mrand` là cùng một agent →
  kiểm tra ~50% (sai lệch lớn = có vấn đề ở lượt / seed / tải). Iteration mỗi ván: cột `a_iterations_*` của file ván.
- File full: `results/raw/p33_<cfg>_vs_<opp>.csv` (+ `_moves.csv`), bảng `results/tables/p33_sweep_prelim.csv`
  (`summarize`, gồm `distinct_games`, `a_iterations_per_move`).
- `--quick`: `n_pairs=1` (42 ván), file `p33quick_*` (không trộn với full, không commit). In ước tính full
  theo đối thủ: Σ thời gian ván (`a_time_sum + b_time_sum`) × 10, tuần tự và ÷ số worker (xấp xỉ).
  Sau đó **kiểm tra worker**: `rand` vs `greedy`, 2 seed × 2 lượt, chạy với 1 và `--workers` tiến trình
  (`p33quick_wcheck_rand_vs_greedy_w<k>.csv`), so `a_iterations_per_move`; giảm > 15% → in cảnh báo.

### Bước 3 — chọn cấu hình (D-14, tự chạy cuối `sweep`)
- Chỉ xét 6 cấu hình heavy (`rand` là mốc). `best` = score vs `mrand` cao nhất; tập ứng viên = `best` + các
  cấu hình có Wilson 95% (win rate) vs `mrand` chồng với `best`; xếp hạng: score vs Greedy giảm dần → không
  cắt trước → iteration/nước (TB 3 đối thủ) giảm dần; hạng 1 = `chosen`.
- Hợp lệ khi Wilson của `rand` vs `mrand` chứa 0,5; không → `valid = 0`, không chọn, in `INVALID`.
- File: `results/tables/p33_choice_prelim.csv` (`p33quick_choice_prelim.csv` khi quick): `config, temperature,
  rollout_limit, value_scale, score_mrand, win_mrand, win_lo_mrand, win_hi_mrand, score_greedy, score_ab2,
  iterations_per_move, best, in_overlap, rank, chosen, valid, validity_note`.

## Phụ thuộc
- Dùng: `experiments/common.py`, `agents/registry.py`, `arena.py` (`derive_seed`, `random_opening_moves`),
  `heuristics/kinrow_rollout.py`, `heuristics/kinrow_eval.py` (`evaluate`), `core/game.py`.
- Được dùng bởi: E5 (lấy cấu hình heavy đã chọn), báo cáo (cách chọn tham số).

## Thiết kế & quyết định (D-12)
- **Seed tách biệt:** hiệu chỉnh 50 000–50 199, quét 0–9 (có test).
- **Mỗi T một scale:** `value_fn` ước lượng xác suất P1 thắng *rollout heavy với T đó*, nên phụ thuộc T.
- **Mọi thế dọc rollout** làm mẫu (các mẫu cùng ván tương quan, nhưng chỉ fit 1 tham số); chỉ lấy thế ở
  nước thứ 10 thì T=100 gần như không có mẫu (rollout trung bình ~9 nước).
- **Khớp fit ↔ chạy:** MCTS dùng `sigmoid_value(evaluate, scale)(g) = σ(evaluate(g, P1)/scale)` làm z (điểm
  P1) khi cắt rollout — đúng công thức và đúng góc nhìn của nhãn khi fit (test kiểm cả lượt X và O).
- **`check_tactics=True` (D-14):** `--quick` đầu tiên với tactics tắt thua 28/28 (MCTS 0,5 s ~1 100 iteration
  không chặn được four; sanity check: cần ~5 000 iteration với ~58 candidate, ~20 000 với ~100) → mọi ô 0%.
  `mrand` thêm làm đối thủ không bị thua sàn.
- Ván quét `random_opening = 0` như chuẩn D-10; đa dạng nhờ seed đối thủ + MCTS theo thời gian. Kiểm
  `distinct_games`; nếu < 15/20 thì báo nhóm, **không** tự bật `random_opening`.

## Giải thích cho báo cáo
**Bản chất.** Khi cắt rollout sau L nước, MCTS cần ước lượng xác suất P1 thắng từ thế đó. Ta dùng
p = σ(eval/scale), với `eval` là hàm lượng giá heuristic (thang tùy ý). `scale` đổi thang điểm sang xác suất,
được chọn sao cho p khớp nhất với kết quả thực của chính rollout heavy: hồi quy logistic một tham số, không
hệ số chặn (eval = 0 ↔ p = 0,5).

**Công thức.** Với mẫu (e_i, z_i), z_i ∈ {0, ½, 1} là kết quả cho P1:
```
LL(scale) = (1/n) Σ_i [ z_i·log σ(e_i/scale) + (1 − z_i)·log(1 − σ(e_i/scale)) ]
scale* = argmax LL trên lưới {100, 200, 300, 500, 1000, 2000, 5000} (mở rộng nếu chạm biên)
```
**Ví dụ trace tay.** Hai mẫu (e = 300, z = 1), (e = −300, z = 0). scale = 100: σ(3) = 0,953 → LL =
log 0,953 = −0,049. scale = 1000: σ(0,3) = 0,574 → LL = −0,554. Mẫu "dễ" ủng hộ scale nhỏ (tự tin); khi có
mẫu ngược chiều (e = 300 nhưng z = 0: scale 100 → log(1 − 0,953) = −3,05) scale lớn hơn được ưu tiên.

**Chọn T / rollout_limit.** Các cấu hình đấu cùng 0,5 s/nước với Greedy và AlphaBeta depth 2; chọn theo tỉ lệ
thắng (kèm Wilson 95%) — số liệu sơ bộ, E5 chạy lại với thiết lập đầy đủ.

## Test
- `tests/test_p33_heavy_sweep.py`: công thức LL, không tràn số, nhãn hòa; fit tìm lại scale thật (500); mở
  rộng lưới ở biên dưới / trên và giới hạn số lần (`at_edge`, `WARNING`); fit theo từng T; dữ liệu hiệu
  chỉnh tất định, dựng lại được, mọi thế chưa kết thúc, `eval_p1` đúng; seed tách biệt; **value_fn của MCTS
  (dựng qua registry) = σ(eval_p1/scale), là xác suất P1 ở cả lượt X và O**; `_simulate` cắt trả đúng z đó;
  7 cấu hình đúng tham số, dựng được; đối thủ; tên file; luật chọn (thắng rõ, chồng CI → Greedy, rồi không
  cắt, rồi iteration; `rand` không được chọn; `rand` vs `mrand` không chứa 0,5 → không chọn).
- Chạy: `python -m pytest tests/test_p33_heavy_sweep.py -q` (~5 s).

## Hạn chế / TODO
- Chưa chạy full sweep; chưa chọn cấu hình cho E5.
- Ước tính thời gian từ `--quick` (2 ván/match) chỉ là xấp xỉ; độ dài ván thay đổi nhiều.
