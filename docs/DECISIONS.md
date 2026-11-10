# DECISIONS — nhật ký quyết định thiết kế

> Mỗi quyết định ảnh hưởng tới nhiều module / interface / thiết lập thí nghiệm: thêm 1 mục. Không xóa mục cũ; nếu đổi ý thì thêm mục mới "thay thế D-x".

### D-1 (2026-10-28) — Phạm vi & công nghệ
- Python 3.11+, pygame GUI, pytest, báo cáo .docx.
- Bàn 5-in-a-row: **15×15**; 3×3 dùng cho kiểm chứng "không bao giờ thua".
- Cờ tướng làm phase cuối (P8), interface `Game` thiết kế chung từ đầu.
- Lý do: theo trả lời của nhóm khi lập kế hoạch.

### D-2 (2026-10-28) — Một class `KInRow(n, k)` cho cả 3×3 và 15×15
- Tránh 2 code path; mọi agent/thí nghiệm chạy trên cả hai bàn.

### D-3 (2026-10-28) — `candidate_moves` bán kính 2 cho bàn lớn
- MCTS/alpha-beta trên 225 ô là quá rộng với Python thuần; giới hạn ô gần quân đã đặt là kỹ thuật chuẩn của Gomoku AI. Phải nêu trong báo cáo mục 3.

### D-4 (2026-10-28) — Đối thủ cố định cho thí nghiệm 15×15 là `GreedyAgent`
- Rẻ, có seed, đủ mạnh để tỷ lệ thắng của MCTS tăng dần theo iteration (đồ thị có ý nghĩa). Nếu MCTS thắng 100% ngay từ 100 iter → đổi sang AlphaBeta depth 2 và ghi mục mới.

### D-5 (2026-10-28) — Chi tiết interface `Game` (P1.1)
- `Move = Hashable`: KInRow dùng `int` (index `r*n+c`); cờ tướng chọn tuple hay int mã hóa ở P8. Agent không giả định kiểu cụ thể.
- Hằng số trung lập trong core: `P1 = 1`, `P2 = -1`, `DRAW = 0`. Alias theo game: KInRow `X=P1, O=P2`; cờ tướng `RED=P1, BLACK=P2`.
- `@runtime_checkable` chỉ dùng trong test, không dùng `isinstance` ở đường nóng.
- Hợp đồng bổ sung: `legal_moves()=[]` khi kết thúc; `candidate_moves()` ⊆ `legal_moves()` và không rỗng khi chưa kết thúc; `play()` chỉ assert; `clone()` độc lập; `key()` gồm cả lượt đi.
- `result_for(winner, player) -> 1.0/0.5/0.0` đặt trong `core/game.py`; MCTS và arena dùng chung để không sai dấu `W`.

### D-6 (2026-10-28) — Sản phẩm nộp: báo cáo + video demo, không vấn đáp
- Mục "Giải thích để vấn đáp" trong module doc đổi thành "Giải thích cho báo cáo" (nguyên liệu cho mục 3 báo cáo).
- Thêm P7.4 video demo; GUI (P6.1) cần chế độ AI vs AI có độ trễ và overlay thống kê MCTS để quay.

### D-7 (2026-10-28) — `Agent.select_move` là template method
- `select_move(game)` (không abstract) gọi `reset_stats()` rồi `_select_move(game)` (abstract); agent con chỉ override `_select_move`.
- Lý do: ép `stats` không cộng dồn giữa các lượt ở một chỗ, tránh việc từng agent (P2.3+) quên gọi `reset_stats()`. Chữ ký công khai `select_move(game) -> Move` không đổi.
- Agent con vẫn được ghi `self.stats[...]` trong `_select_move`; nếu cần cộng dồn qua nhiều lượt thì tự giữ biến riêng.

### D-8 (2026-10-28) — Heuristic k-in-row theo cửa sổ (P2.2)
- Eval = Σ điểm mọi cửa sổ k ô liên tiếp (4 hướng), `W[c] = 10^(c-1)` cho cửa sổ chỉ có `c` quân một bên; WIN = 10·10^k. Pattern (open-four, four, open-three, …) tự phân cấp, không cần bảng pattern. PLAN không có "Done khi" riêng cho P2.2 → tiêu chí là bộ test `tests/test_kinrow_eval.py`.
- Tách hai hàm: `delta_eval` (đúng bằng `evaluate` sau − trước, để AB cộng dồn) và `move_score` (ưu tiên chiến thuật cho greedy/ordering/rollout) với bậc **WIN > BLOCK (= WIN/10) > delta**. Lý do: delta thuần cho nước tạo open-four (+1915) cao hơn nước chặn four (+1143) nên thua ngay.
- Alpha-Beta (P2.4) cộng dồn `delta_eval` dọc nhánh (O(k²)/nút) thay vì gọi `evaluate` toàn bàn ở lá; terminal dùng `WIN − depth` để ưu tiên thắng nhanh.
- Thêm `cell_of(player)` vào `kinrow.py` (không đổi interface `Game`).

### D-9 (2026-11-04) — Minimax/Alpha-Beta: thang điểm và tùy chọn (P2.3, P2.4)
- Terminal dùng chung `terminal_score` = ±(`WIN_SCORE` − ply), `WIN_SCORE = 10**12` (trong `agents/minimax.py`), thay vì `win_score(k)` như ghi chú D-8 → Minimax và Alpha-Beta cùng thang điểm cho mọi game, thắng thật luôn trội hơn mọi heuristic.
- `AlphaBetaAgent` nhận hàm qua tham số (`eval_fn`, `delta_fn`, `order_fn`) thay vì import `kinrow_eval` → không phụ thuộc game, dùng lại được cho cờ tướng (P8).
- TT chỉ dùng lại entry có **cùng** độ sâu còn lại (không phải `≥`) để giá trị gốc luôn bằng Minimax cùng depth (cần cho E1 "best move giống nhau?"). Điểm thắng/thua lưu theo khoảng cách từ nút.
- Tie-break có seed: xáo thứ tự nước ở gốc rồi sort ổn định theo `order_fn`; không chọn đều tuyệt đối (AB không biết giá trị chính xác của các nước không tốt nhất).

### D-10 (2026-11-10) — Đối thủ chuẩn 15×15: Greedy **và** AlphaBeta depth 2 (bổ sung D-4)
- Thí nghiệm so sánh cấu hình MCTS trên 15×15 (E3, E5) dùng cả `GreedyAgent(move_score)` và `AlphaBetaAgent(depth=2, eval_fn=evaluate, delta_fn=delta_eval, order_fn=move_score)` làm đối thủ chuẩn ngay từ đầu, thay vì chỉ đổi sang AB khi đã thấy MCTS thắng 100% Greedy như D-4.
- Lý do: tránh ceiling effect. Khi tỷ lệ thắng bão hòa gần 100% thì các đường c / rollout không phân biệt được nhau; AB depth 2 thấy được phản ứng của đối thủ nên khó hơn Greedy, nhưng vẫn rẻ (có `delta_fn` + ordering).
- Theo yêu cầu của nhóm khi lập kế hoạch P3.1.

### D-11 (2026-11-10) — Thiết kế MCTS và phạm vi P3.1/P3.2
- **Phạm vi:** P3.1 làm cả `agents/rollout.py` (`RandomRollout`, `HeavyRollout` bản đúng chưa tối ưu, `sigmoid_value`). P3.2 đổi thành "tăng tốc heavy + chọn tham số". Lý do: đo nhanh 15×15 (sau 6 nước) — rollout random 0,35 ms (trung bình 91 nước), chấm `move_score` trên ~100 candidate 0,5 ms/bước → heavy chơi tới hết ~45 ms/rollout, không dùng được cho thí nghiệm nếu không cắt/tối ưu; nhưng cần có bản đúng sớm để làm chuẩn so sánh.
- **Heavy:** lấy mẫu theo softmax((s − max)/T) trên `score_fn` (k-in-row: `move_score`), T mặc định 100. Bậc WIN/BLOCK cách delta thường ~10^5 nên thắng ngay / chặn ngay tự được chọn với xác suất ≈ 1, không cần ngưỡng riêng của k-in-row. Loại ε-greedy: đo được rollout chỉ dài 5,8 nước, bên đi trước trong rollout gần như luôn thắng → tín hiệu lệch.
- **Rollout bị cắt** (`rollout_limit`): z = `value_fn(g)` (xác suất P1 thắng) nếu có, ngược lại 0,5. Mặc định `rollout_limit=None` cho cả hai policy; thí nghiệm dùng heavy tự đặt giới hạn.
- **Góc nhìn:** backprop là chỗ lật duy nhất: `W += z if player_just_moved == P1 else 1 − z`, `z = result_for(winner, P1)` (D-5). Selection và chọn nước cuối không lật.
- **`check_tactics`** (mặc định tắt để E6 đo được tác dụng): thắng ngay → đi luôn; tập nước an toàn S (sau đó đối thủ không thắng ngay, tính bằng play/undo nên dùng được cho cờ tướng): |S| = 1 → đi luôn; S = ∅ hoặc S = mọi nước → search bình thường; còn lại → search chỉ trên S. Chi phí O(b²), xấu nhất ~80 ms với 148 candidate; tính vào `time` và `time_limit`.
- **Ngân sách:** `iterations` và/hoặc `time_limit`, dừng khi chạm cái nào trước; luôn chạy ít nhất 1 iteration. Chỉ ngân sách iteration mới tái lập được theo seed.
- **`stats["nodes"]`** = số node của cây (kể cả gốc) — độ đo "số nút" của đề cho MCTS. `stats["value"]` = W/N của nước chọn (∈ [0, 1], khác thang AB).
- Thêm thí nghiệm **E6** (tác dụng `check_tactics`) vào PLAN để báo cáo có số liệu trong `results/`.
- **Làm rõ "Done P3 — luôn đi nước thắng ngay"** (phát hiện khi test; **đã duyệt 2026-11-10**, khi lập kế hoạch P4.1 — không thêm ưu tiên thắng ngay vào thuật toán): MCTS thuần không chiết khấu độ sâu. Ở 3×3 `. . X / X O X / . O .` (O đi), O thắng ngay ở 1 nhưng đi 8 cũng thắng chắc (3 đường dọa) → cả hai có W/N = 1 chính xác, N bằng nhau, tie-break có thể chọn 8. Bộ test vị trí vì vậy kiểm "có nước thắng → chọn nước **thắng chắc** theo Minimax" (không bỏ thắng); thế phải chặn vẫn đòi đúng ô chặn; test thắng ngay "chặt" giữ cho các thế mà thắng ngay là nước thắng duy nhất. Không đổi thuật toán để ép "thắng ngay" (khác: ưu tiên con kết thúc thắng khi chọn nước cuối — có thể thêm nếu nhóm muốn, nhưng sẽ chồng lên `check_tactics` mà E6 đo).

### D-12 (2026-11-10) — Tăng tốc heavy rollout (P3.2) và tách bước chọn tham số (P3.3)
- **Profile** (15×15): ~80% thời gian của `HeavyRollout(move_score)` ở `kinrow_eval._scan`, vì mỗi bước chấm lại mọi candidate. Không dùng "chỉ dò thắng/chặn quanh 2 nước cuối": softmax cần delta của mọi candidate (bỏ đi là đổi policy), và đe dọa có thể nằm xa 2 nước cuối vì nước trong cây UCT được mở rộng ngẫu nhiên.
- **Chọn cách (A) tăng dần, tương đương từng bit:** `KInRowHeavyRollout` trong `heuristics/kinrow_rollout.py` (phụ thuộc cấu trúc cửa sổ của k-in-row) giữ số quân mỗi cửa sổ và (delta, win, block) mỗi ô × mỗi bên, chỉ cập nhật các cửa sổ qua ô vừa đặt. `HeavyRollout` giữ làm bản chuẩn; `make_policy` không đổi, thí nghiệm truyền object. Test chứng minh: cùng điểm từng bước, cùng chuỗi nước, MCTS cùng cây. Đo: 300/300 rollout giống hệt, nhanh hơn 4,1–10,9×/rollout (`results/tables/p32_heavy_speed.csv`).
- **Đồng bộ trạng thái:** thêm property chỉ đọc `KInRow.move_history` (không thuộc `Game` protocol); policy so tiền tố lịch sử, gỡ nước thừa, áp nước mới. Không sửa `mcts.py`.
- **Phát hiện:** heavy ở T ≤ 300 cho rollout rất ngắn (T=100: ~9 nước sau khai cuộc 6 nước, ~5 sau 20 nước) → `rollout_limit=10` gần như không có tác dụng ở T=100; vẫn giữ trong lưới để thấy điều đó bằng số liệu.
- **Tách task:** phần quét tham số thành **P3.3, làm sau P4.1** (dùng Arena, không viết vòng lặp chơi tạm). Thiết lập đã duyệt: lưới T ∈ {100, 300, 1000} × {không cắt; cắt 10 + `sigmoid_value`} + random; cùng `time_limit` 0,5 s/nước; đối thủ Greedy **và** AlphaBeta depth 2; 20 ván (10 seed × 2 lượt)/cấu hình/đối thủ; 4 worker (máy lẫn nhân P/E, ngân sách thời gian nhạy với tải) và ghi số iteration mỗi ván; kết quả đánh dấu sơ bộ, không phải E5.
- **`scale` của `sigmoid_value`:** hồi quy logistic (một tham số, chọn trên lưới {100, 200, 300, 500, 1000, 2000, 5000} theo log-likelihood) giữa `evaluate(·, P1)` của các thế cờ và kết quả ván. **Tập seed tách biệt với bước quét:** dữ liệu hiệu chỉnh sinh từ seed **50 000–50 199** (khai cuộc + rollout), bước quét P3.3 dùng seed **0–9** cho ván và đối thủ; hai khoảng không giao nhau.
- **Bổ sung khi làm P3.3 (2026-11-10, nhóm chọn):** (1) **mỗi T một `scale`** (value_fn ước lượng xác suất P1 thắng rollout heavy với chính T đó); (2) mẫu hiệu chỉnh = **mọi thế chưa kết thúc dọc rollout**, khai cuộc ngẫu nhiên 4–20 quân (`random_opening_moves`), nhãn z theo P1; (3) scale tốt nhất chạm **biên lưới** → mở rộng (biên dưới ÷2 / biên trên ×2, tối đa 4 lần) và fit lại, báo LL của scale chọn cạnh scale kề bên; (4) ván quét `random_opening = 0` như chuẩn D-10 — nếu `distinct_games` < 15/20 thì báo nhóm, không tự bật; (5) `--quick` kiểm tra tải: `rand` vs Greedy với 1 và 4 worker, iteration/nước giảm > 15% → đề xuất giảm worker cho full. Có test chứng minh `value_fn` MCTS dùng = σ(evaluate(·, P1)/scale) đã fit, đúng góc nhìn P1 ở cả lượt X và O. Script: `experiments/p33_heavy_sweep.py`.

### D-15 (2026-11-10) — Cột iteration/nước chỉ tính nước có search (P4.2)
- **Vấn đề:** với `check_tactics=True` (D-14) nước thắng/chặn ngay không search (0 iteration) nhưng vẫn nằm trong mẫu số của `*_iterations_per_move` → số bị kéo xuống (P3.3: rand vs Greedy 897 trên 102 nước, 1 040 trên 88 nước có search).
- **Quyết định:** `summarize(rows, moves=None)` thêm `{a,b}_search_moves` và `{a,b}_search_iterations_per_move` — chỉ tính nước có `tactic` ∉ {1, 2} và có `iterations`; nước `restrict` (3) vẫn search nên tính. Cột cũ giữ nguyên (tính mọi nước). Cần dòng của `*_moves.csv`; không truyền → nan. Không đổi schema file ván/moves → file P3.3 dùng lại được, **không chạy lại** (vd. h300 vs Greedy: 664 → 880 trên 123 nước có search; vs mrand: 805 → 968 trên 212 nước).
- **Báo cáo (E3, E5)** lấy iteration/nước từ cột `search`. `p33_choice_prelim.csv` (luật D-14, tiêu chí thứ ba) vẫn dùng cột cũ như đã chạy; không ảnh hưởng chọn h300 vì tiêu chí đó không được dùng để phá hòa.
- **`--quick`:** `add_runner_args` đăng ký cờ chung; ý nghĩa và tên file quick do từng script quyết định.

### D-14 (2026-11-10) — MCTS 15×15 trong thí nghiệm luôn bật `check_tactics`; thêm đối thủ `mrand` (P3.3)
- **Lý do:** `--quick` đầu tiên của P3.3 (thiết lập D-12, `check_tactics=False`, 0,5 s/nước): **MCTS thua 28/28 ván** ở cả 7 cấu hình, cả vs Greedy lẫn vs AB depth 2 (ván 9,5–27,5 nước, không lỗi agent) → mọi cấu hình 0%, không phân biệt được tham số.
- **Sanity check (không phải bug):** 3 thế 15×15 có four của O (X đi), tactics tắt, h100 iteration cố định, 5 seed: 2000 iteration chặn 0/5 ở cả 3 thế; 5000 chặn 5/5 ở hai thế ~58 candidate, 0/5 ở thế chéo ~100 candidate (20 000 iteration: chặn, seed 0). Ô chặn luôn có W/N cao nhất khi đủ lượt thăm (0,70–0,76) → lan ngược đúng góc nhìn. Nguyên nhân: nước X không chặn chỉ bị "bác bỏ" sau khi nút con của nó mở rộng tới nước thắng của O (lần lượt qua ~58–100 nước chưa thử), trong khi rollout heavy cho X tự chặn → W/N của nước sai vẫn ~0,6. Ở 0,5 s/nước h100 chỉ có ~1 100 iteration (rand ~1 700, h300 ~870, h1000 ~390).
- **Quyết định:** mọi thí nghiệm MCTS trên 15×15 (P3.3, E3, E5) dùng `check_tactics=True` cho **mọi** cấu hình MCTS. **E6 là nơi duy nhất so bật/tắt.** 3×3 (E2, E3 3×3, E4) giữ theo PLAN.
- **Đối thủ thứ ba `mrand`:** MCTS rollout random, `time_limit` 0,5 s, `check_tactics=True` — đối thủ cùng loại để tránh floor effect nếu Greedy / AB2 vẫn quá mạnh. Cặp `rand` vs `mrand` giữ làm kiểm tra (~50%).
- Ảnh hưởng: phần "check_tactics=False" của P3.3 trong D-12 bị thay thế.
- **Luật chọn cấu hình heavy của P3.3** (nhóm chốt **trước** khi chạy full, cài trong `p33_heavy_sweep.choose_config`, output `results/tables/p33_choice_prelim.csv`):
  - Đối thủ quyết định chính: **`mrand`**. Greedy / AB2 để tham khảo và phá hòa.
  - Chỉ chọn trong 6 cấu hình **heavy**; `rand` là mốc so sánh, không được chọn.
  - `best` = cấu hình có score (W + 0,5D)/n vs `mrand` cao nhất (bằng nhau → cấu hình đứng trước trong danh sách). Tập ứng viên = `best` + mọi cấu hình có khoảng **Wilson 95% của win rate** vs `mrand` chồng với của `best` (score không có CI; hòa hiếm ở 15×15). Trong tập, xét lần lượt: score vs Greedy cao hơn → không cắt rollout (không phụ thuộc `scale`) → nhiều iteration/nước hơn (trung bình `a_iterations_per_move` qua 3 đối thủ).
  - **Kiểm tra hợp lệ:** khoảng Wilson của win rate `rand` vs `mrand` phải chứa 0,5; không chứa → không chọn (`chosen = 0`, `valid = 0`), báo nhóm trước.
  - Báo cáo kèm `distinct_games` từng ô; < 15/20 thì báo nhóm, không tự bật `random_opening`. Kết quả là **sơ bộ — không phải số liệu E5**.

### D-13 (2026-11-10) — Arena và runner thí nghiệm (P4.1)
- **Phạm vi:** gộp phần chạy song song, CSV, resume (P4.2 cũ) vào P4.1 vì P3.3 cần ngay; P4.2 chỉ còn cờ dòng lệnh chung. Code: `agents/registry.py`, `arena.py`, `experiments/common.py`.
- **Agent mới mỗi ván:** worker nhận `AgentSpec(kind, params, label)` (tham số kiểu JSON, pickle được trên Windows/spawn), dựng agent bằng `make_agent(spec, seed)` cho từng ván → không còn TT/cây/rng của ván trước. Game cũng qua `GameSpec` + `make_game`.
- **Seed:** ván thứ i có `pair_seed = base_seed + i` (khớp quy ước "seed 0–9" của D-12); seed agent = `derive_seed(pair_seed, "A"/"B")` (sha256, không phụ thuộc `PYTHONHASHSEED`). Mỗi `pair_seed` chơi 2 ván: A cầm X rồi B cầm X, cùng seed agent và cùng khai cuộc. `game_id = "<pair_seed>-AX" / "<pair_seed>-BX"`.
- **Khai cuộc ngẫu nhiên:** `random_opening` (số quân, mặc định 0 = tắt), chọn ngẫu nhiên trong `candidate_moves()` (k-in-row: quanh tâm), không được kết thúc ván, sinh tất định từ `derive_seed(pair_seed, "opening")`. Mặc định tắt; cảnh báo trong `arena.md`: hai agent tất định → mọi ván trùng nhau.
- **Dữ liệu:** file ván (1 dòng/ván, cột cố định, tổng/trung bình stats mỗi bên) + `*_moves.csv` (1 dòng/nước, gồm `stats` của agent; `stats["time"]` ghi là `agent_time`). Cột `time` chính do arena đo quanh `select_move`. Không lấy trung bình `value` (thang AB và MCTS khác nhau).
- **Ghi và resume:** chỉ tiến trình chính ghi; ghi moves rồi mới ghi dòng ván, `flush` + `fsync`. Resume: bỏ phần sau dòng xuống cuối cùng (dòng cắt dở), bỏ dòng moves của ván chưa có trong file ván, bỏ qua `game_id` đã xong. Header, `config_hash` (game, spec A/B, `max_moves`, `random_opening`, `base_seed` — không gồm số ván để chạy thêm được) khác → lỗi. `git_commit` + `git_dirty` khác → lỗi trừ khi `allow_code_change=True` (cờ `--allow-code-change`).
- **Lỗi:** lỗi khi **dựng** agent/game (sai config) → dừng cả batch (kiểm trước ở tiến trình chính). Lỗi khi **chơi** (exception, nước không hợp lệ, agent làm đổi `game.key()`) → agent đó thua, ghi `termination` + `error`, batch chạy tiếp. Không có timeout cứng; ghi `time_max`.
- **`max_moves`** (mặc định `None`): đếm nước do agent đi (không tính khai cuộc); chạm → hòa, `termination = max_moves`.
- **Tổng hợp:** số chính là win rate W/n kèm Wilson 95%, thêm non-loss (W+D)/n kèm Wilson; score (W + 0,5D)/n không có CI (không phải tỉ lệ nhị thức). Tách tổng / A cầm X / A cầm O. Cột `distinct_games` (số chuỗi nước khác nhau, gồm khai cuộc) để phát hiện ván trùng làm CI hẹp giả.
- **Worker** mặc định 4 (máy lẫn nhân P/E; ngân sách thời gian nhạy với tải); `workers` được ghi vào CSV. `workers=1` chạy trong tiến trình (debug/test).

### D-16 (2026-11-10) — Thiết kế E2 (MCTS 3×3 không thua)
- **Vét cạn:** seed MCTS tại mỗi nút = `derive_seed(base_seed, repr(game.key()))` (key gồm cả lượt đi) → nước MCTS chỉ phụ thuộc thế cờ, nhớ theo `key`; đối thủ thử mọi nước. 10 `base_seed` × 2 vai. Báo số nhánh (lá), số nhánh thua, một chuỗi thua ví dụ.
- **Iteration ∈ {100, 250, 1000, 5000} cho cả (a) và (b)** để thấy ngưỡng; `check_tactics=False` (D-14). PLAN E2 ghi (1000, 5000) → mở rộng theo yêu cầu của An.
- **(a) Minimax có seed** (`depth=None`, ngẫu nhiên trong các nước tốt nhất) ngay từ đầu; quick cho `distinct_games` 10/10 nên không cần `random_opening`. 100 ván/cặp (50 seed × 2 lượt). Đối thủ MCTS = cùng iter, seed khác (`derive_seed` "A"/"B").
- **Quick (không phải số liệu báo cáo):** vét cạn thua 54/1239 (100 iter), 16/1187 (250), 3/1132 (1000), 0/1133 (5000) → "1000 iter đủ" trong `mcts.md` chỉ đúng với ván đấu, chưa với vét cạn; cập nhật sau khi chạy full.
- **Luật định trước khi chạy full (An, 2026-11-10):** (1) Nếu (b) ở 5000 iter còn nhánh thua ở **bất kỳ** seed nào → chạy thêm (b) với 10000 và 20000 iter **cho đúng các seed đó** (cả hai vai), báo ngưỡng; không đổi thiết lập khác (cài trong `run_extension`, tự chạy cuối bước `exhaustive`/`all`; file `e2_exhaustive_ext*`). (2) Báo cáo đúng phạm vi: "0 nhánh thua trên N seed × 2 vai ở X iter", **không** viết "chứng minh mọi seed". (3) Báo thêm: bảng (b) theo từng mức iter — số seed (trên 10) có 0 nhánh thua, riêng MCTS là X và là O (`e2_exhaustive_by_role.csv`); các thế gây thua gom lại theo **nước sai đầu tiên** của MCTS (nước làm giá trị minimax của MCTS tụt khỏi hòa; phân loại tâm/góc/cạnh và loại ô đối thủ vừa đi; `e2_exhaustive_mistakes.csv`, chi tiết ở `results/raw/e2_exhaustive_mistakes.csv`).

### D-17 (2026-11-10) — Thiết kế E1 (Minimax vs Alpha-Beta)
- **3×3:** Minimax, AB, AB+ordering, AB+ordering+TT trên bàn trống + 5 thế sau 2–6 nước; kiểm giá trị gốc (phải bằng) và nước đi. Vì ordering đổi thứ tự duyệt, nước giống hệt Minimax không đảm bảo khi hòa giá trị → thêm `move_optimal` (giá trị minimax của nước chọn = giá trị gốc, từ `root_values`) và báo cả hai.
- **15×15:** 5 thế cố định (playout ngẫu nhiên trên `candidate_moves`, seed nhỏ nhất ≥ 0 cho ván chưa kết thúc; sau 6/10/14/18/22 nước; chuỗi nước ghi ở `e1_positions.csv`; thế lồng nhau vì cùng seed). AB depth 2, 3 × {không ordering, ordering}, cấu hình chuẩn `eval=evaluate, delta=delta_eval`. Minimax thuần chỉ depth 2 (eval ở lá), bỏ các thế còn lại nếu một thế > 60 s (không xảy ra, 0,5–2,2 s). Minimax depth 3 không chạy.
- **`ab_evalonly` (depth 2):** AB không delta, không ordering — để so thời gian với Minimax mà không lẫn tác dụng của `delta_eval` (nút bằng `ab`, thời gian khác ~15×).
- **Báo cáo tiết kiệm:** % nút và % thời gian, so với Minimax (nếu có) và so với `ab` (cho ordering/TT); cả **gộp** (1 − Σx/Σref) và **trung bình theo thế** vì thế bàn trống chi phối số gộp ở 3×3. Thời gian = trung vị 3 lần, chạy tuần tự.
- **P4.3 (CLI) hoãn**, gộp với P6 (GUI) theo yêu cầu của An (2026-11-10); E1 không dùng CLI/arena.
