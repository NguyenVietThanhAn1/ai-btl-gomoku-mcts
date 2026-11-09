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
- **Làm rõ "Done P3 — luôn đi nước thắng ngay"** (phát hiện khi test, chờ nhóm duyệt): MCTS thuần không chiết khấu độ sâu. Ở 3×3 `. . X / X O X / . O .` (O đi), O thắng ngay ở 1 nhưng đi 8 cũng thắng chắc (3 đường dọa) → cả hai có W/N = 1 chính xác, N bằng nhau, tie-break có thể chọn 8. Bộ test vị trí vì vậy kiểm "có nước thắng → chọn nước **thắng chắc** theo Minimax" (không bỏ thắng); thế phải chặn vẫn đòi đúng ô chặn; test thắng ngay "chặt" giữ cho các thế mà thắng ngay là nước thắng duy nhất. Không đổi thuật toán để ép "thắng ngay" (khác: ưu tiên con kết thúc thắng khi chọn nước cuối — có thể thêm nếu nhóm muốn, nhưng sẽ chồng lên `check_tactics` mà E6 đo).
