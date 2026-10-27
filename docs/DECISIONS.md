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
