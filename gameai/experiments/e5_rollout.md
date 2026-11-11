# E5 — Rollout random vs rollout heuristic — `gameai/experiments/e5_rollout.py`

> Mục tiêu của file này: agent/thành viên khác dùng được module **mà không cần đọc code**.
> Cập nhật cùng lúc với code.

**Trạng thái:** ✅ full xong  ·  **Task:** E5 (D-20)  ·  **Cập nhật:** 2026-11-11

## Mục đích
Đề ý 5: thay rollout ngẫu nhiên bằng rollout heuristic, đo mức cải thiện, liên hệ value network. Chỉ 15×15.
Hai cấu hình MCTS chỉ khác rollout (c = 1.4, `check_tactics=True` theo D-14, `final_move` = max_n):

| Nhãn | Rollout | Ghi chú |
|---|---|---|
| `rand_i<N>` / `rand_t<s>` | random trên `candidate_moves` | |
| `h300_i<N>` / `h300_t<s>` | `heavy_kinrow`, T = 300, không cắt (chọn ở P3.3) | |

Hai trục ngân sách (D-20):
- **Cùng iteration** (4 worker): **thiên vị h300**, vì mỗi iteration heavy đắt hơn random (tỉ lệ iteration/giây
  đo bằng benchmark đơn luồng `results/tables/e5_bench.csv` (bản full, 7 thế): rand/h300 = **1,50** theo trung vị,
  1,3–1,8 ở thế 4–16 quân, 0,97–1,0 ở thế 20–28 quân — xem mục Kết quả full).
- **Cùng thời gian** 0,5 s và 2 s/nước (2 worker, máy rảnh): **so sánh công bằng — kết luận chính dựa trên trục này**.

| Bước (`step`) | Đối thủ | Ngân sách | Ván/điểm |
|---|---|---|---|
| `h2h-iter` / `h2h-time` | A = h300 vs B = rand (cùng ngân sách) | iter {250, 1000, 5000} / t {0,5; 2} | 50 |
| `greedy-iter` / `greedy-time` | `GreedyAgent(move_score)` | iter {100, 250, 500, 1000, 2500, 5000} / t {0,5; 2} | 50 |
| `mref-iter` / `mref-time` | `mref` (MCTS random 1000 iter, seed tách riêng) | iter {250, 1000, 5000} / t {0,5; 2} | 50 |
| `ab2-pilot` → `ab2` | AB depth 2 (D-10) | iter 5000; rand pilot 20 ván, cổng ≥ 2/20 → 50 | 20 / 50 |

h300 vs Greedy (6 iter) và h300 vs AB2 (5000) **tái dùng E3** nếu thỏa điều kiện (xem dưới) — cột `source = e3`.

## Cách chạy
```
python -m gameai.experiments.e5_rollout all --quick    # bench + mọi bước 1 cặp/điểm + bảng + hình + ước tính
python -m gameai.experiments.e5_rollout all            # full: bench → iter → ab2-pilot → ab2 (qua cổng) → time
python -m gameai.experiments.e5_rollout h2h-iter       # từng bước, resume được
python -m gameai.experiments.e5_rollout ab2 [--force]  # sau ab2-pilot
python -m gameai.experiments.e5_rollout tables         # dựng lại bảng + hình từ raw
python -m gameai.experiments.e5_rollout bench          # chỉ benchmark iteration/giây đơn luồng
```
Cờ chung `--workers` (4, chỉ cho phần iteration; phần time cố định 2), `--allow-code-change`.
**Thứ tự full (D-20):** mọi phần iteration trước, 3 phần time sau cùng; khi chạy phần time máy phải rảnh.

## Public API
- `mcts_spec(rollout, iterations=None, time_limit=None) -> AgentSpec` (đúng một ngân sách; nhãn `<rollout>_i<N>` /
  `<rollout>_t<s>`); `budget_tag`.
- `MRefAgent(seed, iterations=1000, c=1.4, check_tactics=True)` — `MCTSAgent` rollout random, seed bên trong =
  `derive_seed(seed, "mref")`. `MREF` = spec qua registry (`"gameai.experiments.e5_rollout:MRefAgent"`).
- `Point(part, budget_type, budget, rollout, spec_a, spec_b, n_pairs, workers, e3_path)`; `points(step, quick)`,
  `all_points(quick)`, `raw_path(pt, quick)`.
- `e3_reusable(path, spec_a, spec_b, n_pairs, game, base_seed, diff_empty) -> (ok, reason)`; `git_diff_empty(commit)`.
- `run_point`, `run_step`, `run_pilot`, `run_ab2` (dùng `gate_passes` của E3).
- `bench(seconds=1.0, plies=(4, 8, 12, 16, 20, 24, 28), seeds=(0, 1, 2), path)`; `bench_rates(rows) -> {rollout: trung
  vị iter/s}`; `bench_phase_rates(rows) -> {(rollout, phase): trung vị}`; `phase_of(stones)`.
- `paired_diff(rows_h300, rows_rand)`, `check_validity(summary_all)`, `rate_rows(time_tables, bench_rows, time_moves)`,
  `build_tables(quick, …)`, `estimate_full(…)`, `make_figures(quick, …)`, `fnum`.

## File
- Raw: `results/raw/e5_<part>_<label_a>.csv` (+ `_moves`), schema runner (`common.md`). Thông tin máy mỗi điểm:
  `results/raw/e5_runinfo.csv` (`step, part, label_a, label_b, budget_type, budget, source, workers, n_pairs, cpu,
  logical_cpus, started, finished, wall_s, git_commit, git_dirty, note`).
- Bảng (`results/tables/`):
  - `e5_{h2h,greedy,mref,ab2}.csv` = `part, budget_type, budget, rollout, source, raw` + `SUMMARY_COLUMNS` (3 dòng/điểm).
    Iteration/nước báo cáo lấy `{a,b}_search_iterations_per_move` (D-15).
  - `e5_paired.csv` — mỗi (đối thủ, ngân sách): `n` (số game_id chung), `mean_h300, mean_rand, diff`, khoảng **cặp**
    `paired_lo/hi`, khoảng **độc lập** `indep_lo/hi`, `sd_diff`.
  - `e5_validity.csv` — `rand_i1000` vs `mref`: Wilson win rate có chứa 0,5 (`valid`), `distinct_games`.
  - `e5_rates.csv` — phần time, mỗi điểm × mỗi bên chạy theo thời gian × nhóm giai đoạn ván (`phase` ∈ 0-9, 10-19,
    >=20 theo ply): `method` (`phase` / `mixed`), `n_moves`, `iterations`, `agent_time`, `rate_iter_per_s`
    (Σ iterations / Σ agent_time), `bench_iter_per_s` (trung vị benchmark cùng rollout + nhóm), `dev_bench`, `flag`
    (lệch > 20 %), `load_indicator` (1 = rand).
  - `e5_bench.csv` — benchmark đơn luồng (không phải số liệu ván đấu): `rollout, plies, seed, iterations, agent_time, iter_per_s`.
- Hình: `results/figures/e5_iter.png` (3 panel: vs Greedy, vs mref, đối đầu — x log iteration, 1 đường/rollout, Wilson)
  và `e5_time.png` (hàng trên x = thời gian/nước; hàng dưới x = iteration thực tế/nước, panel đối đầu = cột
  iteration thực tế của từng bên).
- Quick: tiền tố `e5quick_` (không commit), `e5quick_estimate.csv` = ước tính full từng bước.

## Thiết kế & quyết định (D-20)
- **Thay AB2 bằng `mref`:** ở ngân sách thấp AB2 đẩy mọi cấu hình về sàn (P3.3 ≤ 2/20 ở 0,5 s), nên không phân biệt
  được rollout. `mref` (MCTS random 1000 iter) là đối thủ cùng loại, tính theo iteration nên không nhạy tải.
  AB2 chỉ ở 5000 iter, nơi E3 cho h300 0,22.
- **Dãy seed của mref tách riêng:** arena cấp seed bên B = `derive_seed(pair_seed, "B")`; `MRefAgent` băm tiếp
  thành `derive_seed(seed_B, "mref")` → không trùng dãy seed của agent MCTS nào khác. Kiểm tra hợp lệ:
  `rand_i1000` vs `mref` (cùng thuật toán, khác seed) phải cho Wilson chứa 0,5.
- **Tái dùng E3** khi: spec A/B (bỏ label), game, `base_seed` khớp; mọi dòng `git_dirty = 0`; đủ 50 ván (lấy
  `pair_seed` < 25); và `git diff <commit E3> HEAD -- gameai/agents gameai/games gameai/heuristics gameai/core
  gameai/arena.py` rỗng. Ngân sách iteration + cùng seed → ván tất định, chạy lại sẽ cho cùng kết quả.
  Không thỏa → điểm đó chạy vào file `e5_*`.
- **So sánh cặp:** rand và h300 vs cùng đối thủ có cùng `game_id` → cùng seed đối thủ và cùng lượt. Nhưng cây MCTS
  khác nhau nên ván diễn ra khác nhau; vì vậy khoảng cặp **có thể không hẹp hơn** khoảng độc lập — bảng báo cả hai.
- **Kiểm tra tải (phần time, luật sửa sau quick):** tốc độ phụ thuộc mạnh vào giai đoạn ván (h300 đầu ván chậm hơn
  rand 1,5–1,8×, cuối ván gần bằng), nên so **theo nhóm giai đoạn** ply 0–9 / 10–19 / ≥ 20 với benchmark cùng nhóm
  (`method = phase`, dùng `iterations` + `agent_time` từng nước trong `*_moves`). Không có dữ liệu từng nước →
  `method = mixed` (trộn giai đoạn). rand là **chỉ báo tải**; cờ chỉ ở h300 có thể do thế cờ khác nhau trong nhóm.
  Cờ chỉ để báo cáo, **không** loại dữ liệu.
- **Ước tính** (`estimate_full`): giây/ván = `a_time_sum + b_time_sum` (arena đo); điểm có trong quick dùng trung bình
  đo được, điểm iter khác fit a + b·iter theo (bước, rollout) bằng `e3_c_sweep.fit_cost`; thời gian thực = tuần tự /
  {4 worker: 3,5; 2 worker: 1,9} + 2 s khởi động pool/điểm. Quick chỉ 1 cặp/điểm → ước tính thô.

## Giải thích cho báo cáo
**Rollout là gì trong MCTS.** Sau khi mở rộng một node, MCTS cần một ước lượng giá trị của thế cờ đó. Rollout
(simulation) ước lượng bằng cách chơi tiếp tới hết ván theo một chính sách nhanh rồi lấy kết quả z ∈ {0; 0,5; 1};
trung bình W/N của nhiều rollout là ước lượng Monte Carlo của giá trị thế cờ **dưới chính sách rollout đó**.

- **Rollout random:** mỗi bước chọn đều trong `candidate_moves`. Rẻ, không thiên lệch theo một heuristic nào, nhưng ở
  gomoku 15×15 hai bên ngẫu nhiên bỏ qua đe dọa → kết quả rollout gần như không liên quan tới chất lượng thế cờ
  (phương sai lớn, giá trị "dưới chính sách ngẫu nhiên" khác xa giá trị thật).
- **Rollout heavy h300:** mỗi bước lấy mẫu theo softmax((s − max s)/T) với s = `move_score` (thắng ngay ≫ chặn thua ngay
  ≫ tạo/chặn chuỗi), T = 300. Pseudocode một rollout:
  ```
  while not terminal(g):
      C = candidate_moves(g)
      s_i = move_score(g, i) cho i ∈ C          # cập nhật tăng dần (KInRowHeavyRollout, D-12)
      p_i = exp((s_i − max s)/T) / Σ exp(...)
      g.play(sample(C, p))
  return z(g)                                   # 1 / 0,5 / 0 theo góc nhìn người cần
  ```
  Nước thắng ngay có điểm cao hơn mọi nước khác hàng bậc độ lớn nên gần như chắc được chọn; vì vậy rollout heavy
  "biết" kết thúc đe dọa và chặn four → z phản ánh thế cờ tốt hơn, đổi lại mỗi rollout đắt hơn (số iteration/giây
  thấp hơn; tỉ lệ đo ở `e5_bench.csv`).
- **Ví dụ nhỏ (trace tay, điểm minh họa).** Một thế X có 3 ứng viên với điểm s = (1 000 000 thắng ngay; 500; 0), T = 300:
  p ∝ (e⁰; e^((500 − 10⁶)/300); e^(−10⁶/300)) ≈ (1; 0; 0) → chọn nước thắng. Nếu không có nước thắng, s = (500; 200; 0):
  p ∝ (1; e^(−1); e^(−5/3)) = (1; 0,368; 0,189) → (0,643; 0,236; 0,121): ưu tiên nước tốt nhưng vẫn ngẫu nhiên.
  Rollout random cho (1/3; 1/3; 1/3) ở cả hai trường hợp.
- **Vì sao phải so cùng thời gian.** Với cùng số iteration, h300 dùng rollout đắt hơn nên được "tặng" thời gian tính
  toán; so sánh công bằng là cùng thời gian/nước, khi đó random có nhiều iteration hơn (cây sâu/rộng hơn) còn heavy
  có ước lượng mỗi lá tốt hơn. E5 báo cả hai trục, kết luận chính theo trục thời gian.

**Liên hệ value network.** Rollout chỉ là một cách ước lượng hàm giá trị v(s). Value network (AlphaGo, AlphaZero) học
trực tiếp v(s) ≈ xác suất thắng từ dữ liệu tự chơi, thay rollout bằng một lần đánh giá: ít nhiễu hơn và không
phụ thuộc chính sách rollout, nhưng chỉ tốt khi hàm học được đủ chính xác. AlphaGo (2016) trộn cả hai:
V(lá) = (1 − λ)·v_θ(s) + λ·z_rollout; AlphaZero bỏ hẳn rollout.
Bằng chứng trong dự án (P3.3, `results/tables/p33_sweep_prelim.csv`, `p33_scale_prelim.csv` — sơ bộ, 20 ván/ô):
thay phần đuôi rollout bằng một "value function" thủ công (cắt rollout sau 10 nước, chấm bằng
`sigmoid_value(evaluate, scale)`) **không cải thiện nhất quán**: vs `mrand` h300 19/20 → h300c10 16/20, h1000 16/20 →
h1000c10 19/20, h100 = h100c10 19/20; vs Greedy h300 8/20 → 4/20, h1000 2/20 → 5/20 (mọi CI chồng nhau). Hàm
`evaluate` qua sigmoid chỉ dự đoán được một phần kết quả rollout: log-likelihood trung bình −0,566/thế (T = 300,
scale 500) so với −0,693 của dự đoán hằng 0,5. Tức là một hàm giá trị thủ công yếu không thay thế được rollout;
muốn bỏ rollout như AlphaZero thì hàm giá trị phải được **học** đủ tốt.

## Kết quả full (2026-11-11, commit `ec3b8d5`)
Thời gian thực **4 733 s ≈ 79 phút** (~12:43 → 14:02): bench ~46 s, phần iteration (4 worker) + pilot AB2 ~33 phút
(12:44 → 13:17), phần time (2 worker) ~45 phút (13:17 → 14:02). 1 270 ván mới, mọi ván `normal`, 0 lỗi agent, `git_dirty = 0`, cùng commit;
`distinct_games` = n ở mọi điểm, không có hòa (trừ h300 vs AB2 của E3: 2 hòa). CPU i9-12900H, 20 luồng logic
(`results/raw/e5_runinfo.csv`). 7 điểm h300 lấy từ E3 (`source = e3`, qua điều kiện tái dùng).
Bảng: `results/tables/e5_{h2h,greedy,mref,ab2,paired,validity,rates,bench}.csv`; hình `results/figures/e5_{iter,time}.png`.
Win rate [Wilson 95 %], 50 ván/điểm (dòng `all`).

**Benchmark đơn luồng** (`e5_bench.csv`, 1 s/thế, 3 seed, trung vị iter/s rand / h300): 4 quân 3 079 / 1 718 (1,79×),
8: 3 227 / 2 409 (1,34×), 12: 3 468 / 2 000 (1,73×), 16: 3 606 / 2 196 (1,64×), 20: 4 022 / 4 153 (0,97×),
24: 4 072 / 4 169 (0,98×), 28: 4 321 / 4 332 (1,00×); chung 3 606 / 2 409 = **1,50×**.

**Đối đầu trực tiếp h300 (A) vs rand (B)** — tỉ lệ thắng của h300:

| Ngân sách | h300 thắng | iteration/nước thực tế h300 / rand |
|---|---|---|
| 250 iter | 48/50 = 0,96 [0,865; 0,989] | 250 / 250 |
| 1000 iter | 45/50 = 0,90 [0,786; 0,957] | 1000 / 1000 |
| 5000 iter | 49/50 = 0,98 [0,895; 0,996] | 5000 / 5000 |
| **0,5 s** | **45/50 = 0,90** [0,786; 0,957] | 1 322 / 1 398 |
| **2 s** | **50/50 = 1,00** [0,929; 1,000] | 4 006 / 5 680 |

**vs Greedy** (h300 iter từ E3):

| Ngân sách | rand | h300 | iteration thực tế rand / h300 |
|---|---|---|---|
| 100 / 250 / 500 iter | 0 / 0 / 0 | 0,04 / 0,02 / 0,18 | — |
| 1000 iter | 0,02 [0,004; 0,105] | 0,48 [0,348; 0,615] | — |
| 2500 iter | 0,00 [0; 0,071] | 0,90 [0,786; 0,957] | — |
| 5000 iter | 0,08 [0,032; 0,188] | 0,92 [0,812; 0,968] | — |
| **0,5 s** | **0,00** [0; 0,071] | **0,62** [0,482; 0,741] | 1 457 / 1 206 |
| **2 s** | **0,10** [0,043; 0,214] | **0,86** [0,738; 0,930] | 5 831 / 4 331 |

**vs mref** (MCTS random 1000 iter):

| Ngân sách | rand | h300 | iteration thực tế rand / h300 |
|---|---|---|---|
| 250 iter | 0,20 [0,112; 0,330] | 0,74 [0,604; 0,841] | — |
| 1000 iter | 0,50 [0,366; 0,634] | 0,90 [0,786; 0,957] | — |
| 5000 iter | 0,88 [0,762; 0,944] | 1,00 [0,929; 1,000] | — |
| **0,5 s** | **0,50** [0,366; 0,634] | **0,98** [0,895; 0,996] | 1 399 / 1 305 |
| **2 s** | **0,92** [0,812; 0,968] | **1,00** [0,929; 1,000] | 5 531 / 3 829 |

**Kiểm tra hợp lệ mref:** `rand_i1000` vs mref 25/50, Wilson [0,366; 0,634] ∋ 0,5, distinct 50/50 → `valid = 1`.

**AB2 (cổng D-20):** `rand_i5000` pilot **0/20** = 0,00 [0; 0,161] → **không qua cổng**, không chạy thêm; ghi làm bằng
chứng floor. h300 5000 iter (E3): 11/50 = 0,22 [0,128; 0,352].

**So sánh cặp** (`e5_paired.csv`, d = kết quả h300 − kết quả rand theo game_id, 50 cặp):
vs Greedy 1000 iter +0,46 (cặp [0,320; 0,600], độc lập [0,315; 0,605]); 2500 +0,90 [0,816; 0,984]; 5000 +0,84
(cặp [0,723; 0,957], độc lập [0,733; 0,947]); **0,5 s +0,62** [0,484; 0,756]; **2 s +0,76** (cặp [0,628; 0,892],
độc lập [0,632; 0,888]); 100–250 iter chứa 0. vs mref: 250 iter +0,54 [0,370; 0,710]; 1000 +0,40 [0,242; 0,558];
5000 +0,12 [0,029; 0,211]; **0,5 s +0,48** [0,340; 0,620]; **2 s +0,08** [0,004; 0,156]. AB2 (20 cặp chung): +0,15
[−0,011; 0,311]. Khoảng cặp và độc lập gần như trùng (đúng như dự kiến: chỉ chung seed đối thủ + lượt).

**Cờ tốc độ phần time** (`e5_rates.csv`, luật theo giai đoạn ván; 33 dòng, **15 cờ**, chỉ báo cáo, không loại dữ liệu):
- h300 nhóm 10–19 quân: **nhanh hơn** benchmark ở **cả 6** điểm (cờ): +45…+56 % ở 5 điểm, +25 % ở greedy 2 s. Hệ thống, không theo điểm: thế
  benchmark 12/16 quân là playout ngẫu nhiên, ít đe dọa → rollout heavy dài; trong ván thật ở 10–19 quân đã có đe
  dọa → rollout heavy kết thúc sớm. Đây là khác biệt thế cờ, không phải tải.
- h300 khác: 0–9 quân greedy 2 s −24 %; ≥ 20 quân h2h 0,5 s −24 %, mref 0,5 s −30 % (cờ).
- **rand (chỉ báo tải):** luôn chậm hơn benchmark, −7…−27 %, tăng theo giai đoạn ván (0–9: −9…−18 %, 10–19: −7…−23 %,
  ≥ 20: −24…−27 %); 6 dòng cờ: h2h 0,5 s (10–19 −20,4 %, ≥ 20 −26,6 %), h2h 2 s ≥ 20 (−27,3 %, chỉ 2 nước), mref
  0,5 s (10–19 −23,1 %, ≥ 20 −23,7 %), mref 2 s ≥ 20 (−25,6 %). Độ lệch rand tương tự giữa 0,5 s và 2 s và giữa các
  phần → giống một độ lệch đều (2 tiến trình chạy song song + thế ván thật khác thế benchmark) hơn là tải ở riêng
  một điểm; không loại trừ được việc mọi điểm time đều chậm đều ~10–25 % so với đơn luồng.

**Đọc kết quả.** Ở **cùng thời gian** (so sánh công bằng), h300 hơn rand rõ ở cả ba đối thủ: đối đầu 0,90 (0,5 s) và
1,00 (2 s); vs Greedy 0,62 so với 0,00 và 0,86 so với 0,10; vs mref 0,98 so với 0,50 (0,5 s). Ở 0,5 s hai bên có
số iteration gần bằng nhau (~1 300–1 450), nên lợi thế đến từ chất lượng ước lượng của rollout chứ không từ số
lượt. Ở 2 s rand có nhiều iteration hơn ~1,3–1,5× mà vẫn thua. Khoảng cách chỉ hẹp lại khi đối thủ yếu và ngân sách
lớn (vs mref 2 s: 0,92 so với 1,00 — gần trần). Rollout random gần như không thắng được Greedy ở mọi ngân sách thử
(≤ 0,10), còn vs AB2 ở 5000 iter là 0/20 so với 0,22 của h300.

## Quick (2026-11-11, commit `07791c1`, không commit file `e5quick_*` — không phải số liệu báo cáo)
Tổng **300 s** (bench ~25 s; phần iter 4 worker, phần time 2 worker), 44 ván, mọi ván `normal`, `distinct_games` = n
ở mọi điểm. `git_dirty = 1` ở mọi dòng — **chỉ** do `.claude/settings.json` (cấu hình Claude Code, không phải code);
cần commit/khôi phục file đó trước full. CPU: 12th Gen Intel Core i9-12900H, 20 luồng logic (nhân P + E).
- **Tái dùng E3:** cả 4 điểm (h300 vs Greedy 100/1000/5000, h300 vs AB2 5000) qua điều kiện (`ok`).
- **Kiểm tra hợp lệ:** `rand_i1000` vs mref 1/2, Wilson [0,095; 0,905] ∋ 0,5, distinct 2/2.
- **Benchmark đơn luồng** (`e5_bench.csv`, không phải số liệu ván): trung vị rand 3 721, h300 2 840 iter/s →
  rand/h300 = 1,31. Theo thế: 6 nước 3 331–3 465 vs 2 183–2 220 (1,5–1,6×); 12 nước ~3 640 vs ~1 990 (1,8×);
  18 nước ~3 830 vs ~3 530 (1,1×); 24 nước ~4 230 vs ~4 140 (1,0×).
- **Iteration thực tế trong ván (phần time):** 0,5 s: rand 1 338–1 536, h300 1 384–1 519 /nước (gần bằng nhau);
  2 s: rand 5 680–6 244, h300 3 685–4 705.
- **Cờ tốc độ (luật cũ, trước khi sửa; `e5quick_rates.csv` lúc đó có 12 dòng):** 6 dòng có cờ. rand: lệch peer ≤ 13 % (không cờ peer), lệch bench
  −16…−28 % (3 trên 6 dòng rand có cờ bench) — đều thấp hơn bench một cách đồng đều → khả năng do thế trong ván khác thế benchmark
  + chạy 2 tiến trình, chưa phải dấu hiệu tải. h300: 1 843–3 038 iter/s, cờ peer ở greedy t0,5 (+29 %), greedy t2
  (−24 %), mref t2 (−33 %) — tốc độ heavy thay đổi mạnh theo giai đoạn ván (xem benchmark) và quick chỉ 2 ván/điểm,
  nên chưa tách được tải khỏi giai đoạn ván.
- **Ước tính full** (`e5quick_estimate.csv`, thời gian thực): h2h-iter 6,7 phút, greedy-iter 3,3 (h300 tái dùng),
  mref-iter 14,8, ab2-pilot 0,8 (+ ab2 1,2 nếu qua cổng), h2h-time 15,6, greedy-time 12,4, mref-time 19,0 →
  **tổng ~73 phút** (~74 với ab2), thấp hơn ước tính kế hoạch (~2,4 h) vì h300 rẻ hơn dự kiến và ván ngắn.
  Quick 1 cặp/điểm → ước tính thô (E3: phần Greedy thực tế gần gấp đôi ước tính quick).

## Phụ thuộc
`experiments/common.py` (`run_match`, `summarize`, `read_rows`, `moves_path_for`, `add_runner_args`, `git_info`),
`experiments/e3_c_sweep.py` (`GREEDY`, `AB2`, `gate_passes`, `fit_cost`), `experiments/e1_nodes.py` (`make_position`),
`agents/registry.py`, `agents/mcts.py`, `arena.py` (`derive_seed`), matplotlib (Agg), `git`.

## Test
`tests/test_e5_rollout.py` (26 case): spec rand/h300 chỉ khác rollout, tactics bật; spec time không có ngân sách
iteration; spec h300 = spec E3 (cả trong raw E3); phần time 2 worker; lưới + quick ⊂ full + quick có điểm
`rand_i1000` vs mref; đường dẫn raw duy nhất; chỉ h300 iter Greedy/AB2 có ứng viên E3; `MRefAgent` qua registry chơi
giống `MCTSAgent(seed=derive_seed(seed, "mref"))`; `e3_reusable` (ok, code đổi, thiếu ván, spec/dirty/base_seed/game
lệch, bỏ qua label, file thật E3 hiện dùng được); `paired_diff` dữ liệu tay; `check_validity`; cổng AB2; `phase_of` + `bench_phase_rates`; `rate_rows`
(theo nhóm giai đoạn: bỏ tactic/0 iteration, ngưỡng > 20 %, `load_indicator`; nhánh `mixed` khi thiếu moves); `bench` nhỏ; `build_tables` + `make_figures` end-to-end; `run_point` ghi runinfo; `estimate_full`.
Chạy: `python -m pytest tests/test_e5_rollout.py -q`.

## Hạn chế / TODO
- Ước tính 2/4 worker là hệ số thô; quick 1 cặp/điểm nên độ dài ván ước lượng nhiễu.
- `e5_runinfo.csv` ghi nối (append): chạy lại một điểm đã xong sẽ thêm dòng mới (dòng cũ giữ làm lịch sử).
