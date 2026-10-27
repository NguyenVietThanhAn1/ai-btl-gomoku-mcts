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
│   │                xiangqi/           # (P8) cờ tướng
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
- **P3.1** `agents/mcts.py`: Node(move, parent, children, untried, W, N, player_just_moved); 4 bước select (UCT) → expand → simulate → backprop.
  - W tính theo góc nhìn **người vừa đi vào node**; thắng = 1, hòa = 0.5, thua = 0.
  - Tham số: `c`, `iterations` **hoặc** `time_limit`, `rollout_policy`, `final_move ∈ {"max_n", "max_wn"}` (để làm E4), `seed`.
  - `last_root_stats()` → list (move, W, N, W/N) cho E4.
  - Expand/rollout dùng `candidate_moves()` để 15×15 chạy được.
- **P3.2** `agents/rollout.py`: `RandomRollout`, `HeuristicRollout` (thắng ngay > chặn thua ngay > chọn ngẫu nhiên có trọng số theo heuristic trên candidate moves).
  Done P3 khi: MCTS 3×3 (1000 iter) luôn đi nước thắng ngay / chặn thua ngay trong bộ test vị trí; 20 ván vs minimax 3×3 không thua ván nào.

### P4 — Arena, CLI, khung thí nghiệm
- **P4.1** `arena.py`: `play_game(game_factory, agent_x, agent_o, seed) -> GameRecord` (winner, số nước, thời gian/nước, nodes); `play_match(..., n_games, swap_first=True)`.
- **P4.2** `experiments/common.py`: chạy song song `ProcessPoolExecutor`, mỗi ván ghi **1 dòng CSV ngay khi xong** (chạy tiếp được nếu bị ngắt), seed tất định, cờ `--quick` (ít ván/ít iteration để smoke test), `--workers`.
- **P4.3** `cli.py`: `python -m gameai.cli play --board 15 --k 5 --ai mcts --iters 2000` và `match ...`.
  Done P4 khi: 1 match quick chạy end-to-end ra CSV; ngắt giữa chừng chạy lại không lặp ván đã xong.

### P5 — Thí nghiệm (dữ liệu cho mục 5 báo cáo)
Trước khi chạy full: chạy `--quick`, ghi **thời gian ước tính** vào PROGRESS, rồi mới chạy full (có thể chạy nền).

| ID | Câu hỏi | Thiết lập | Output |
|---|---|---|---|
| **E1** | Alpha-Beta tiết kiệm bao nhiêu nút? | 3×3: tìm toàn bộ từ bàn trống + 5 thế cờ giữa ván. 15×15: depth 2, 3 trên 5 thế cờ cố định, có/không move ordering | `tables/e1_nodes.csv`: nodes, time, best move giống nhau? |
| **E2** | MCTS 3×3 có bao giờ thua? | (a) MCTS(1000, 5000 iter) vs Minimax hoàn hảo, vs Random, vs MCTS — mỗi cặp ≥100 ván đổi lượt. (b) **Kiểm chứng vét cạn**: duyệt mọi chuỗi nước của đối thủ (MCTS seed cố định đi 1 nhánh, đối thủ thử mọi nước) → 0 nhánh thua | bảng W/D/L; số nhánh đã kiểm |
| **E3** | Ảnh hưởng của c | c ∈ {0.5, 1.0, 1.4, 2.0} × iter ∈ {100, 250, 500, 1000, 2500, 5000}; ≥50 ván/điểm, đổi lượt. 3×3 vs Random (đo non-loss/win rate) và 15×15 vs Greedy | `figures/e3_*.png`: 1 đường/c, kèm khoảng tin cậy 95% |
| **E4** | N vs W/N | Lấy stats gốc ở vài thế cờ; so `final_move=max_n` vs `max_wn` đối đầu nhau ≥50 ván | bảng W, N, W/N tại gốc; tỉ lệ thắng max_n vs max_wn |
| **E5** | Rollout heuristic tốt hơn bao nhiêu? | So random vs heuristic rollout ở **cùng số iteration** và **cùng thời gian/nước** (công bằng); đối đầu trực tiếp + vs Greedy | bảng + đồ thị; nhận xét liên hệ value network |

Ghi chú hiệu năng 15×15: nếu 5000 iter quá chậm, giảm số ván ở mức iteration cao hoặc dùng time budget — **ghi rõ vào báo cáo**, không âm thầm đổi thiết lập.

### P6 — GUI pygame
- **P6.1** `gui/pygame_app.py`: chọn bàn 3×3/15×15, chọn AI (alphabeta/mcts + tham số), người vs AI, AI vs AI; hiện nước cuối, thông báo thắng/hòa; AI chạy không treo cửa sổ (thread hoặc chia nhỏ iteration). Phục vụ quay video: chế độ AI vs AI có độ trễ chỉnh được giữa các nước; tùy chọn bật overlay hiện N (và W/N) của các nước ứng viên ở gốc MCTS.
  Done khi: chơi hết 1 ván mỗi chế độ không lỗi.

### P7 — Báo cáo & video demo
- **P7.1** `experiments/plots.py` sinh toàn bộ hình/bảng từ `results/raw` (không vẽ tay).
- **P7.2** `report/report.md` đúng khung đề; số liệu lấy từ `results/tables`.
- **P7.3** Convert sang `report.docx`, kiểm tra hình/bảng hiển thị đúng.
- **P7.4** Video demo (3–5 phút): `report/video_script.md` gồm kịch bản từng cảnh + lệnh chạy chính xác. Cảnh gợi ý: (1) 3×3 người vs MCTS — MCTS không thua; (2) 15×15 người vs MCTS với overlay N; (3) 15×15 MCTS vs Alpha-Beta (AI vs AI); (4) đồ thị E3/E5 và kết luận; (5) cờ tướng nếu xong P8. Quay bằng OBS hoặc Xbox Game Bar (Win+Alt+R).

### P8 — (*) Cờ tướng (sau khi P1–P7 xong)
- **P8.1** `games/xiangqi/`: biểu diễn bàn 9×10, sinh nước 7 loại quân (tướng, sĩ, tượng, xe, pháo, mã — cản chân, tốt — qua sông), **lộ mặt tướng**, chiếu, hết nước = thua; giới hạn số nước → hòa.
  Done khi: perft từ thế khởi đầu khớp giá trị chuẩn (đối chiếu nguồn, ghi nguồn vào `xiangqi.md`) + test từng loại quân.
- **P8.2** Lượng giá: vật chất + bảng vị trí. Alpha-beta (move ordering: ăn quân trước).
- **P8.3** MCTS cho cờ tướng: rollout ngẫu nhiên gần như vô dụng → rollout giới hạn độ sâu + cắt bằng hàm lượng giá (đúng tinh thần value network). Ghi nhận xét này vào báo cáo 3.4.
- **P8.4** Thí nghiệm nhỏ: alpha-beta vs random, MCTS vs alpha-beta; GUI cờ tướng nếu còn thời gian.

## 4. Thứ tự & phân việc (khi nhóm có thêm người)

`P0 → P1 → P2 → P3 → P4 → P5 (chạy nền) ∥ P6 → P7 → P8`

Chia việc gợi ý khi có thêm người: A = P2 + E1; B = P3 + E2–E5; C = P6 GUI + P8; báo cáo chia theo mục. Ranh giới giữa các phần là interface `Game`/`Agent` — không sửa interface khi chưa ghi vào DECISIONS.md.

## 5. Definition of Done (áp dụng mọi task)

1. Code chạy, `python -m pytest` xanh, `ruff check .` sạch.
2. Có test cho hành vi mới.
3. File `.md` cạnh mỗi module mới/đổi đã cập nhật (API, quyết định, trạng thái).
4. `PROGRESS.md` cập nhật: trạng thái task, việc dở, bước tiếp theo.
5. Git commit theo task ID: `P3.1: MCTS-UCT core`.
