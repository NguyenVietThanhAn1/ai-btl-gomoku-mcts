# PLAN — BTL Trí tuệ nhân tạo, Bài 1

> File này định nghĩa **việc cần làm** (task ID, phạm vi, tiêu chí hoàn thành).
> **Trạng thái** của từng task chỉ được ghi ở `PROGRESS.md` (single source of truth) — không đánh dấu tiến độ ở đây.
> Khi đổi phạm vi/thiết kế: sửa file này + ghi lý do vào `docs/DECISIONS.md`.

## 0. Đề bài (tóm tắt)

Trò chơi k-in-a-row (Tic-Tac-Toe tổng quát, **5 quân thẳng hàng thắng**):

| # | Yêu cầu đề | Task tương ứng |
|---|---|---|
| 1 | MiniMax + cắt tỉa Alpha-Beta | P2 |
| 2 | MCTS + UCT; kiểm chứng trên Tic-Tac-Toe 3×3 thuật toán **không bao giờ thua** | P3, E2 |
| 3 | Thực nghiệm c ∈ {0.5, 1.0, 1.4, 2.0}; đồ thị iteration – tỷ lệ thắng (mỗi c một đường) | E3 |
| 4 | Phân tích: vì sao chọn nước theo **N lớn nhất** thay vì W/N lớn nhất | E4 + báo cáo |
| — | Sản phẩm nộp: báo cáo .docx + **video demo** (không vấn đáp) | P7 |
| 5 | Thay rollout ngẫu nhiên bằng heuristic, đo cải thiện; liên hệ value network | E5 |
| 6 | (*) Mở rộng Cờ tướng → điều kiện điểm > 9 | P8 |

Công thức: `UCT(i) = W_i/N_i + c·sqrt(ln N_p / N_i)`.
Thiết lập thực nghiệm theo đề: ≥ 50 ván/cấu hình, **đổi lượt đi trước**, iteration ∈ {100 … 5000}, độ đo: tỷ lệ thắng, số nút, thời gian.

Khung báo cáo bắt buộc: Tóm tắt (≤200 từ) · 1 Giới thiệu · 2 Phát biểu bài toán · 3 Phương pháp (3.1–3.4) · 4 Thiết lập thực nghiệm · 5 Kết quả · 6 Thảo luận.

### Bài 2 (Bonus) — chưa chốt phạm vi
Chưa có phạm vi/task. **Chờ An xác nhận yêu cầu với giảng viên**; khi có thì thêm task ID + tiêu chí vào đây và ghi DECISIONS. Trạng thái ở PROGRESS (dòng `B2`, ⬜).

## 1. Quyết định đã chốt

- Ngôn ngữ: **Python 3.11+**, thuần Python + numpy/matplotlib/pandas; GUI **pygame**; test **pytest**.
- Bàn: một class `KInRow(n, k)` dùng cho cả **3×3 (k=3)** và **15×15 (k=5)**. Mặc định demo/thí nghiệm chính: 15×15, k=5.
- Giao diện: CLI + GUI pygame đơn giản. Báo cáo: `.docx` (viết `report/report.md` → convert sang docx).
- Cờ tướng làm ở **phase cuối**, nhưng interface `Game` thiết kế từ đầu để cắm vào không phải sửa agent.
- Làm nhóm (hiện 1 người) → mỗi module độc lập, có file `.md` riêng, task có cột Owner trong PROGRESS.

## 2. Kiến trúc

```
btl/
├── CLAUDE.md  PLAN.md  PROGRESS.md  README.md  requirements.txt  pyproject.toml
├── docs/            DECISIONS.md, MODULE_TEMPLATE.md, SETUP.md
├── gameai/
│   ├── core/        game.py            # interface Game + kiểu Move/Player
│   ├── games/       kinrow.py          # KInRow(n,k): 3x3 và 15x15
│   │                xiangqi.py         # (P8) cờ tướng (D-22)
│   ├── heuristics/  kinrow_eval.py     # hàm lượng giá pattern (open-3, open-4, ...)
│   ├── agents/      base.py random_agent.py greedy.py minimax.py alphabeta.py mcts.py rollout.py
│   ├── arena.py                        # chơi 1 ván / 1 match, đổi lượt, seed
│   ├── cli.py                          # chơi trong terminal, chạy match
│   ├── gui/         pygame_app.py
│   └── experiments/ common.py e1_nodes.py e2_never_lose.py e3_c_sweep.py e4_root_stats.py e5_rollout.py plots.py
├── tests/           test_<module>.py
├── results/         raw/*.csv (chỉ script ghi)  tables/  figures/
└── report/          report.md  report.docx
```

Quy ước: mỗi file `X.py` có **`X.md` nằm cạnh** (theo `docs/MODULE_TEMPLATE.md`). Agent đọc `.md` trước, chỉ mở `.py` khi cần sửa.

### Interface `Game` (hợp đồng chung — mọi agent chỉ dùng các hàm này)

```python
class Game(Protocol):
    def current_player(self) -> int            # +1 / -1
    def legal_moves(self) -> list[Move]
    def candidate_moves(self) -> list[Move]    # tập con có ích (vd. ô gần quân đã đặt); mặc định = legal_moves
    def play(self, move) -> None               # mutate in place
    def undo(self) -> None                     # cho minimax/alphabeta
    def is_terminal(self) -> bool
    def winner(self) -> int | None             # +1/-1, 0 = hòa, None = chưa kết thúc
    def clone(self) -> "Game"                  # cho MCTS rollout
    def key(self) -> Hashable                  # cho transposition table (tùy chọn)
    def render(self) -> str
```

## 3. Các phase & task

Mỗi task: **mục tiêu → output → Done khi (acceptance)**. Một task = một phiên `/next-task`.

### P0 — Setup
- **P0.1** Khởi tạo repo: git, `.venv`, `requirements.txt`, `pyproject.toml` (pytest + ruff), skeleton thư mục + `__init__.py`.
  Done khi: `python -m pytest` chạy được (0 test cũng được), `ruff check .` sạch.

### P1 — Game engine
- **P1.1** `core/game.py`: Protocol `Game`, hằng số player, kiểu `Move`.
- **P1.2** `games/kinrow.py`: `KInRow(n, k)`, board 1 chiều (`list`/`bytearray`, index = r*n+c).
  - Kiểm tra thắng **tăng dần**: chỉ quét 4 hướng qua nước vừa đi → O(k).
  - `candidate_moves()`: ô trống trong bán kính `radius` (mặc định 2) quanh quân đã đặt; bàn trống → ô giữa. Với 3×3 trả về toàn bộ ô trống.
  - `undo()` bằng stack nước đi.
  Done khi: test thắng ngang/dọc/2 chéo, sát mép, không thắng khi chỉ 4 quân, hòa 3×3, undo khôi phục đúng trạng thái + `winner`.

### P2 — Minimax + Alpha-Beta (đề ý 1)
- **P2.1** `agents/base.py` (`Agent.select_move(game) -> Move`, có `stats` dict) + `random_agent.py`.
- **P2.2** `heuristics/kinrow_eval.py`: lượng giá theo pattern trên các đoạn dài k (five, open-four, four, open-three, …), đối xứng cho 2 bên. Dùng chung cho alpha-beta, greedy agent, rollout heuristic.
- **P2.3** `agents/minimax.py`: minimax thuần, depth-limited (depth=None → tìm đến terminal), **đếm số nút**.
- **P2.4** `agents/alphabeta.py`: alpha-beta, cùng chữ ký, đếm nút, tùy chọn **move ordering** (theo heuristic) và transposition table.
- **P2.5** `agents/greedy.py`: 1-ply theo heuristic, tie-break ngẫu nhiên có seed → đối thủ rẻ cho thí nghiệm 15×15.
  Done P2 khi: trên 3×3 alpha-beta cho **cùng giá trị** với minimax ở mọi trạng thái test; minimax-vs-minimax 3×3 luôn hòa; alpha-beta 15×15 depth 2 thắng ngay nếu có nước thắng, chặn nếu đối thủ có four.

### P3 — MCTS-UCT (đề ý 2, 4, 5)
- **P3.1** `agents/mcts.py` + `agents/rollout.py` (D-11): Node(move, parent, children, untried, W, N, player_just_moved); 4 bước select (UCT) → expand → simulate → backprop.
  - W tính theo góc nhìn **người vừa đi vào node**; thắng = 1, hòa = 0.5, thua = 0. Lật góc nhìn duy nhất ở backprop.
  - Tham số: `c` (√2), `iterations` và/hoặc `time_limit` (dừng khi chạm cái nào trước), `rollout_policy ∈ {"random", "heavy"}` hoặc object, `score_fn` (cho heavy), `rollout_limit` (None = chơi tới hết) + `value_fn` (chấm khi bị cắt, None → 0.5), `final_move ∈ {"max_n", "max_wn"}` (để làm E4), `check_tactics` (mặc định tắt), `seed`.
  - `last_root_stats()` → list (move, W, N, W/N) cho E4. `stats`: `iterations`, `nodes` (= số node cây), `time`, `value`, `max_depth`, `rollout_plies`, `tactic`.
  - Expand/rollout dùng `candidate_moves()` để 15×15 chạy được.
  - `rollout.py`: `RandomRollout`, `HeavyRollout(score_fn, temperature)` bản đúng chưa tối ưu: chấm mọi candidate, lấy mẫu theo softmax((s − max)/T) → thắng ngay > chặn thua ngay tự trội nhờ bậc WIN/BLOCK của `move_score`; `sigmoid_value(eval_fn, scale)` làm `value_fn`.
- **P3.2** Tăng tốc heavy rollout (D-12): `heuristics/kinrow_rollout.py` — `KInRowHeavyRollout(T)` cập nhật điểm `move_score` tăng dần theo cửa sổ, **cùng chuỗi nước** với `HeavyRollout(move_score, T)` khi cùng rng (bản chuẩn giữ lại); `KInRow.move_history` (chỉ đọc) để đồng bộ. Đo tốc độ bằng `experiments/p32_heavy_speed.py`.
  Done P3.2 khi: test chứng minh tương đương (điểm từng bước = `move_score`, cùng chuỗi nước, MCTS cùng cây khi cùng seed + iteration); số đo tốc độ trong `results/`.
- **P3.3** (làm **sau P4.1**, dùng Arena — không viết vòng lặp chơi tạm) Quét sơ bộ chọn tham số heavy trước E5 (D-12): lưới T ∈ {100, 300, 1000} × {`rollout_limit=None`; `rollout_limit=10` + `sigmoid_value(evaluate, scale)`} + mốc random; mọi cấu hình **cùng `time_limit` = 0,5 s/nước**, `check_tactics=True` (D-14); đối thủ `GreedyAgent(move_score)`, `AlphaBetaAgent` depth 2 (D-10) **và** `mrand` (MCTS random 0,5 s, tactics bật — D-14); 20 ván/cấu hình/đối thủ (10 seed × 2 lượt); 4 worker; ghi số iteration mỗi ván. `scale` hiệu chỉnh trước bằng hồi quy logistic trên tập seed tách biệt (D-12). `--quick` trước, báo thời gian ước tính (~25 phút tuần tự vs Greedy, +35–45 phút vs AB), hỏi trước khi chạy full. Output `results/raw/p33_*.csv`, `results/tables/p33_*_prelim.csv`, đánh dấu **sơ bộ — không phải số liệu E5**.
  Done P3 khi: MCTS 3×3 (1000 iter) luôn đi nước thắng ngay / chặn thua ngay trong bộ test vị trí; 20 ván vs minimax 3×3 không thua ván nào.
  (Làm rõ ở D-11: "thắng ngay" được kiểm là "nước thắng chắc theo Minimax" vì MCTS không chiết khấu độ sâu; chặn vẫn phải đúng ô. Hai tiêu chí kiểm với `check_tactics=False`.)

### P4 — Arena, CLI, khung thí nghiệm
- **P4.1** (D-13, gộp phần runner của P4.2 cũ) `agents/registry.py`: `AgentSpec`/`GameSpec` (tham số kiểu JSON, pickle được) + `make_agent(spec, seed)` / `make_game(spec)`. `arena.py`: `play_game(game, agent_x, agent_o, max_moves) -> GameRecord` (winner, số nước, chuỗi nước, thời gian do arena đo + `stats` từng nước, lỗi agent → xử thua), `play_seeded_game` (agent **mới** mỗi ván, seed suy tất định từ `pair_seed`, tùy chọn `random_opening`), `play_match(..., n_pairs)` (mỗi seed 2 ván, đổi lượt). `experiments/common.py`: `run_match` chạy song song `ProcessPoolExecutor` (`workers`, mặc định 4), mỗi ván ghi **1 dòng CSV ngay khi xong** + file `*_moves.csv`, chạy tiếp được nếu bị ngắt (kiểm `config_hash`, `git_commit`), `summarize` (W/D/L, win rate + non-loss kèm Wilson 95%, score, số chuỗi nước khác nhau; tách lượt X/O).
  Done P4.1 khi: test cùng seed cùng kết quả (ngân sách iteration, kể cả song song = tuần tự), đổi lượt đúng, resume đúng (dòng cắt dở, không lặp ván), CSV đủ cột, agent lỗi bị xử thua mà batch không sập.
- **P4.2** Cờ dòng lệnh chung cho script thí nghiệm: `--quick` (ít ván/ít iteration để smoke test), `--workers`, `--allow-code-change`.
- **P4.3** (✂ cắt 2026-11-17, thay bằng preset + cờ dòng lệnh GUI — D-28; trước đó hoãn, gộp với P6) `cli.py`: `python -m gameai.cli play --board 15 --k 5 --ai mcts --iters 2000` và `match ...`.
  Done P4 khi: 1 match quick chạy end-to-end ra CSV; ngắt giữa chừng chạy lại không lặp ván đã xong.

### P5 — Thí nghiệm (dữ liệu cho mục 5 báo cáo)
Trước khi chạy full: chạy `--quick`, ghi **thời gian ước tính** vào PROGRESS, rồi mới chạy full (có thể chạy nền).

| ID | Câu hỏi | Thiết lập | Output |
|---|---|---|---|
| **E1** | Alpha-Beta tiết kiệm bao nhiêu nút? (D-17) | 3×3: Minimax vs AB (không ordering / ordering / ordering+TT), từ bàn trống + 5 thế giữa ván, kiểm giá trị **và** nước đi. 15×15: AB depth 2, 3 trên 5 thế cố định, có/không ordering; Minimax thuần chỉ depth 2 | `tables/e1_{nodes,summary,positions}.csv`: nodes, time, % tiết kiệm, giá trị/nước giống? |
| **E2** | MCTS 3×3 có bao giờ thua? | (a) MCTS(1000, 5000 iter) vs Minimax hoàn hảo, vs Random, vs MCTS — mỗi cặp ≥100 ván đổi lượt. (b) **Kiểm chứng vét cạn**: duyệt mọi chuỗi nước của đối thủ (MCTS seed cố định đi 1 nhánh, đối thủ thử mọi nước) → 0 nhánh thua | bảng W/D/L; số nhánh đã kiểm |
| **E3** | Ảnh hưởng của c (D-18) | c ∈ {0.5, 1.0, 1.4, 2.0} × iter ∈ {100, 250, 500, 1000, 2500, 5000}; ≥50 ván/điểm, đổi lượt. 3×3 rollout random vs Random 200 ván/điểm (win rate chính, kèm non-loss) và vs Minimax có seed (cache theo key) 100 ván/điểm (non-loss). 15×15 MCTS h300 + tactics vs Greedy, 50 ván/điểm. AB depth 2 (sau Greedy): pilot c tốt nhất vs Greedy ở 5000 iter, 20 ván; ≥ 2/20 thắng → chạy iter {2500, 5000}, không thì bỏ (D-18) | `figures/e3_*.png`: 1 đường/c, kèm khoảng tin cậy 95% |
| **E4** | N vs W/N (D-19) | (1) Root stats: 3×3 mọi thế ≥ 2 nước × iter {10, 20, 50, 100, 250, 1000}, c = 1.4, so nước max_n / max_wn / max_lcb với giá trị trò chơi; 15×15 h300 + tactics, 10 thế × 5 seed × iter {50, 250, 1000}, c = 1.4 + độ nhạy c = 0.5, ví dụ có tham chiếu 20 000 iter + cột chẩn đoán. (2) Đối đầu max_n vs max_wn chỉ 3×3, iter {10, 20, 50, 100, 250}, 200 ván/điểm, độ đo chính score (15×15 bỏ: hai tiêu chí không khác nhau) | `tables/e4_roots_{summary,examples}.csv`, `tables/e4_match.csv`, `figures/e4_match.png` |
| **E5** | Rollout heuristic tốt hơn bao nhiêu? (D-20) | 15×15, `rand` vs `h300` (c = 1.4, tactics). Cùng iteration (Greedy {100…5000}; đối đầu, mref {250, 1000, 5000}; 4 worker) **và** cùng thời gian {0,5; 2} s/nước (2 worker, kết luận chính). Đối thủ: đối đầu trực tiếp, Greedy, `mref` (MCTS random 1000 iter, seed tách riêng); AB2 chỉ 5000 iter có cổng pilot ≥ 2/20. Tái dùng E3 cho h300 khi spec + code khớp. 50 ván/điểm; bảng cặp + độc lập; benchmark iteration/giây | `tables/e5_{h2h,greedy,mref,ab2,paired,validity,rates,bench}.csv`, `figures/e5_{iter,time}.png`; nhận xét liên hệ value network |
| **E6** | Kiểm tra "thắng ngay / chặn ngay" trước khi search giúp bao nhiêu? | **Thiết kế lại theo D-21.** MCTS `check_tactics` bật vs tắt, cùng iteration: (a) bộ thế 15×15 trích từ ván E3/E5 (loại 1: đối thủ có four 1 ô chặn; loại 2: mình thắng ngay), tắt tactics: tỷ lệ chọn đúng theo iter {100…5000}, rand và h300, 10 seed/thế, 15 thế/tầng `n_candidates`/loại; bật: sanity 100 %; (b) `randoff_i1000` vs mref, h300 tắt vs bật (1000), h300 tắt vs Greedy (1000, 5000; bản bật từ E3) — bỏ AB2; (c) thời gian `check_tactics`, % nước đi thẳng, thời gian/nước | `tables/e6_{choice,match,paired,cost_check,tactic_rate,time}.csv` + `e6_choice.png`, `e6_match.png` |

**MCTS 15×15 (D-14):** mọi cấu hình MCTS trong thí nghiệm 15×15 (P3.3, E3, E5 — gồm `mref`) bật `check_tactics=True`; chỉ E6 so bật/tắt.

**Đối thủ chuẩn 15×15 (D-10):** dùng **cả hai** đối thủ cố định khi so sánh các cấu hình MCTS:
`GreedyAgent(move_score, seed=s)` (rẻ) và `AlphaBetaAgent(depth=2, eval_fn=evaluate, delta_fn=delta_eval, order_fn=move_score, seed=s)`
(mạnh hơn vì thấy phản ứng của đối thủ). Lý do: tránh ceiling effect. Nếu MCTS thắng gần 100% Greedy ở iteration cao thì các đường
c / rollout / final_move chồng lên nhau, không phân biệt được. Bắt buộc có `eval_fn` (thiếu thì lá depth 2 = 0). Seed của đối thủ
đổi theo ván để các ván không trùng nhau.

Ghi chú hiệu năng 15×15: nếu 5000 iter quá chậm, giảm số ván ở mức iteration cao hoặc dùng time budget — **ghi rõ vào báo cáo**, không âm thầm đổi thiết lập.

### P6 — GUI pygame (tách theo D-26; gộp ✂ P4.3 CLI)
- **P6.1** (sau P7.1, trước P8.1) `gui/pygame_app.py`: khung GUI + **một lớp view cho mỗi game** + view k-in-row.
  K-in-row: chọn bàn 3×3/15×15, chọn AI (alphabeta/mcts + tham số), người vs AI, AI vs AI; hiện nước cuối, thông báo thắng/hòa; AI chạy không treo cửa sổ (thread hoặc chia nhỏ iteration). Phục vụ quay video: chế độ AI vs AI có độ trễ chỉnh được giữa các nước; tùy chọn bật overlay hiện N (và W/N) của các nước ứng viên ở gốc MCTS.
  Bổ sung của An (D-28): tách `controller` (test headless) / `GameView` (input là máy trạng thái cho P6.2), AI trong thread trên `clone()` + hủy theo id ván, preset = `AgentSpec` của E2/E3 (15×15: h300 5000 iter), seed chỉnh được, phím `S` đổi bên, cửa sổ 1280×720 cố định, 30 fps, font tiếng Việt.
  Done khi: chơi hết 1 ván mỗi chế độ (người vs AI, AI vs AI) × (3×3, 15×15) không lỗi; test controller xanh; ruff sạch.
- **P6.2** (sau P8.3) view cờ tướng trên khung P6.1: bấm quân → tô sáng nước hợp lệ → bấm ô đích; báo chiếu / chiếu bí /
  hòa. Cờ tướng chơi được là **lõi**; ✂ overlay N/W/N cho cờ tướng. Done khi: chơi hết 1 ván mỗi chế độ cờ tướng không lỗi.
- **P6.3** (sau P6.1, An thêm; D-29) Nâng GUI thành game chơi được hoàn chỉnh kiểu chess.com: scene manager + widget tự viết
  (Home / Setup / Play / modal Kết thúc / Xem lại / Demo / Hướng dẫn); chế độ người vs AI, AI vs AI, 2 người cùng máy; loại AI
  MCTS / Alpha-Beta × Dễ/Vừa/Khó ánh xạ sang `AgentSpec` (bảng D-29, panel ghi nguồn cấu hình); controller thêm undo / đầu hàng /
  `position_at`; nhãn tọa độ quanh bàn; tô đường thắng, quân mờ khi hover. Không sửa `agents/`, `games/`, `heuristics/`;
  giữ cờ dòng lệnh + phím tắt P6.1. ✂ âm thanh, animation, đồng hồ đếm ngược, gợi ý nước, Hướng dẫn chi tiết.
  Done khi: test headless (click nút → đổi scene, cấu hình → AgentSpec, undo khóa khi AI nghĩ + bỏ kết quả cũ, modal kết thúc,
  xem lại không đổi ván thật) xanh; golden k-in-row xanh; autoplay mọi chế độ × bàn không lỗi; thời gian/nước mức Khó ≤ ~5 s;
  ruff sạch; spec-reviewer PASS.
  **Phiên 3 (An đổi hướng, D-29): giao diện sản phẩm "MoveMind".** 3a: Theme (2 bảng màu) + font đóng gói + sprite khử răng
  cưa + icon + bàn gỗ; làm lại Home và Play → ảnh 2 phương án trong `report/figures/gui/style/`, An chọn. 3b: Setup / Demo /
  Help / modal / xem lại theo Theme, animation (cờ tắt cho test), overlay top-8, đường thắng vạch nối tâm, modal trên panel,
  đo lại thời gian (animation bật, chậm > 15 % → báo An), ảnh `report/figures/gui/`. 3c: autoplay mọi chế độ × bàn × AI, `.md`,
  spec-reviewer, commit. Done thêm: Home không còn chữ kỹ thuật, nhãn trò không "k=", Demo vẫn hiện "cấu hình thí nghiệm",
  mọi test GUI chạy với animation tắt, ảnh màn hình sinh bằng script.

### P7 — Báo cáo & video demo
- **P7.1** `experiments/plots.py` sinh toàn bộ hình/bảng từ `results/raw` (không vẽ tay).
- **P7.2** `report/report.md` đúng khung đề; số liệu lấy từ `results/tables`.
- **P7.3** Convert sang `report.docx`, kiểm tra hình/bảng hiển thị đúng.
- **P7.4** Video demo (3–5 phút): `report/video_script.md` gồm kịch bản từng cảnh + lệnh chạy chính xác. Cảnh gợi ý: (1) 3×3 người vs MCTS — MCTS không thua; (2) 15×15 người vs MCTS với overlay N; (3) 15×15 MCTS vs Alpha-Beta (AI vs AI); (4) đồ thị E3/E5 và kết luận; (5) cờ tướng nếu xong P8. Quay bằng OBS hoặc Xbox Game Bar (Win+Alt+R).

### P8 — (*) Cờ tướng — **bắt buộc** (đề: điều kiện điểm > 9)
Làm trên branch `xiangqi` (tạo lại từ master khi bắt đầu P8.1, D-26); số liệu k-in-row khóa ở tag `kinrow-final` (`aa8e3d5`). **Thứ tự (D-26):** `P8.0 → P7.1 → P6.1 → P8.1 → P8.2 → P8.3 → P6.2 → P8.4 → P7.2–P7.4`. Thiết kế: D-22.

**Ràng buộc:** không đổi hành vi mặc định của agents / arena / k-in-row. Phải sửa agent → thêm tham số có mặc định giữ nguyên
hành vi cũ + test hồi quy `tests/test_regression_kinrow.py` (golden chụp từ tag: cùng chuỗi nước + cùng stats) phải xanh.

**Lõi** (không được cắt): perft độ sâu 1–3, AB cờ tướng, MCTS cắt + eval, E7 (c) và (d), GUI cờ tướng chơi được.
**Cắt được nếu thiếu giờ** (đánh dấu ✂): perft độ sâu 4, CLI P4.3, overlay N/W/N cho cờ tướng, E7 (a).

- **P8.0** Thiết kế D-22 + golden hồi quy k-in-row (`tests/kinrow_golden_cases.py` → `tests/golden/kinrow_golden.json`).
  Done khi: D-22 được duyệt, golden sinh từ code bằng tag, test golden xanh trên branch.
- **P8.1** `games/xiangqi.py` + `xiangqi.md`: luật theo D-22, FEN, ICCS, Zobrist. Script `experiments/p81_perft.py` → `results/tables/p81_perft.csv`.
  Done khi:
  - perft độ sâu 1–3 khớp giá trị chuẩn ở thế khởi đầu (44 / 1 920 / 79 666) và các thế 2–11 của chessprogramming.org
    "Chinese Chess Perft Results" (URL + ngày truy cập + người đóng góp ghi trong `xiangqi.md`). ✂ Độ sâu 4 (3 290 240): test `slow`.
  - Test riêng từng loại quân: cản chân mã (8 hướng), cản mắt tượng, tượng không qua sông, sĩ/tướng trong cung, xe, pháo ăn
    qua đúng 1 ngòi, tốt chưa qua sông chỉ tiến / qua sông thêm đi ngang / không lùi; lộ mặt tướng; không tự chiếu; hết nước
    (chiếu bí, bí nước) = thua; lặp thế lần 3 → hòa; `max_plies` → hòa; hợp đồng `Game` (undo khôi phục key/winner/lượt,
    clone độc lập, candidate ⊆ legal); key tăng dần = key tính lại từ đầu.
  - Đo nút/giây perft, thời gian `legal_moves()` / `winner()`; ghi vào `xiangqi.md` + CSV. Nếu MCTS ước tính < ~200 iter/s →
    tối đa 1 phiên tối ưu trước khi sang P8.2.
- **P8.2** `heuristics/xiangqi_eval.py` + `.md`: `evaluate` (vật chất + PST), `delta_eval`, `mvv_lva` (ordering ăn quân giá
  trị cao bằng quân giá trị thấp trước). Dùng lại `AlphaBetaAgent`; thêm `time_limit` + iterative deepening (D-23); registry:
  `GameSpec("xiangqi")`, `FUNCTIONS` thêm `xq_evaluate`, `xq_delta`, `xq_mvv_lva`.
  Done khi: `delta_eval` = hiệu `evaluate` trên thế ngẫu nhiên; AB (eval và delta) cùng giá trị gốc với Minimax depth 2 trên
  ≥ 10 thế; ordering ít nút hơn; AB ăn quân cho không, thoát chiếu, chiếu bí 1 nước; test ID (time_limit nhỏ vẫn trả nước
  depth 1, giờ dư = depth cố định); golden k-in-row xanh.
- **P8.3** MCTS cờ tướng: dùng nguyên `MCTSAgent` với `rollout_limit` + `sigmoid_value(xq_evaluate, scale)` (rollout ngẫu
  nhiên tới hết ván gần như vô dụng → cắt + lượng giá, đúng tinh thần value network; ghi vào báo cáo 3.4). Hiệu chỉnh `scale`
  kiểu D-12 (logistic, lưới, mở rộng biên, seed tách biệt) trên nhãn kết quả ván tự đấu AB depth 1 có `random_opening`.
  **Trước khi fit:** báo tỉ lệ ván phân thắng thua của nhãn; < ~30 % → đổi nguồn nhãn (AB depth 2, hoặc nhãn theo chênh lệch
  vật chất sau L nước) và ghi D-24. Đo chi phí `check_tactics` (ms/nước, % nước đi thẳng) → quyết định bật/tắt trong E7 (D-24).
  Done khi: MCTS ăn quân cho không và thoát chiếu bí 1 nước (khi bật tactics; tắt thì ghi tỉ lệ); iteration/s + bảng scale
  trong `results/`.
- **P6.2** GUI cờ tướng — xem mục P6 (làm sau P8.3).
- **P8.4** E7 `experiments/e7_xiangqi.py` + `.md` (thiết kế chi tiết D-25):
  - ✂ (a) AB depth 1/2 cố định vs Random.
  - (b) AB ordering: số nút, depth cố định (tất định): không ordering / MVV-LVA / + TT, depth 2–4, thế khởi đầu + ~10 thế
    giữa ván; kiểm giá trị gốc giống nhau.
  - (c) MCTS rollout random (tới hết, chặn bởi `max_plies`) vs cắt L nước + eval, cùng `time_limit`: đối đầu + vs Random.
  - (d) MCTS (tốt nhất ở c) vs AB `time_limit`, cùng s/nước.
  - Phần theo thời gian: `random_opening` vài nước; cắm sạc, máy rảnh, ghi power + bench như D-21. Mục tiêu **50 ván/điểm**
    cho (c), (d) như đề; quick cho thấy quá đắt → ≥ 20 ván, ghi lý do vào D-25 + báo cáo. `--quick` trước, báo thời gian ước
    tính, hỏi trước khi chạy full.

## 4. Thứ tự & phân việc (khi nhóm có thêm người)

`P0 → P1 → P2 → P3 → P4 → P5` (xong, tag `kinrow-final`) `→ P8.0 → P7.1 → P6.1 → P8.1 → P8.2 → P8.3 → P6.2 → P8.4 → P7.2–P7.4` (D-26: làm nốt k-in-row trước)

Chia việc gợi ý khi có thêm người: A = P2 + E1; B = P3 + E2–E5; C = P6 GUI + P8; báo cáo chia theo mục. Ranh giới giữa các phần là interface `Game`/`Agent` — không sửa interface khi chưa ghi vào DECISIONS.md.

## 5. Definition of Done (áp dụng mọi task)

1. Code chạy, `python -m pytest` xanh, `ruff check .` sạch.
2. Có test cho hành vi mới.
3. File `.md` cạnh mỗi module mới/đổi đã cập nhật (API, quyết định, trạng thái).
4. `PROGRESS.md` cập nhật: trạng thái task, việc dở, bước tiếp theo.
5. Git commit theo task ID: `P3.1: MCTS-UCT core`.
