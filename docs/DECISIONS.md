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
