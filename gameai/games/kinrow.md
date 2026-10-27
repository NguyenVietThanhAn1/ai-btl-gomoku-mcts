# KInRow — `gameai/games/kinrow.py`

> Mục tiêu của file này: agent/thành viên khác dùng được module **mà không cần đọc code**.
> Cập nhật cùng lúc với code.

**Trạng thái:** ✅ ổn định  ·  **Task:** P1.2  ·  **Cập nhật:** 2026-10-28

## Mục đích
Cài đặt `Game` (xem `core/game.md`) cho k-in-a-row trên bàn n×n: 3×3 k=3 (thí nghiệm E2) và
15×15 k=5 (đề ý 1–5). Một class duy nhất cho cả hai (D-2).

## Public API
```python
X = P1; O = P2                      # alias người chơi (O có noqa E741)

class KInRow:
    def __init__(self, n: int = 15, k: int = 5, radius: int = 2): ...  # ValueError nếu k > n
    n, k, radius: int
    board: bytearray                # index = r*n + c; 0 trống, 1 = X, 2 = O (KHÁC giá trị P1/P2)
    # Toàn bộ interface Game: current_player, legal_moves, candidate_moves, play, undo,
    # is_terminal, winner, clone, key, render
```
- `Move` = `int` (index `r*n + c`). X (P1) đi trước.
- `play(m)` chỉ `assert` ô trống và ván chưa kết thúc.
- `key()` = `(bytes(board), current_player)`; hashable, dùng cho transposition table.
- `render()`: chuỗi n dòng, ký tự `.` `X` `O` cách nhau bởi dấu cách.

### `candidate_moves()`
Ô trống nằm trong bán kính Chebyshev `radius` (mặc định 2) quanh bất kỳ quân đã đặt; trả về
**list đã sắp tăng dần** (tất định). Bàn trống: ô giữa `(n//2)*n + n//2`, trừ khi
`n <= 2*radius+1` (vd. 3×3) thì trả toàn bộ ô trống. Ván kết thúc: `[]`. Với 3×3 mọi quân
đều phủ cả bàn nên luôn bằng `legal_moves()`.

## Phụ thuộc
- Dùng: `core/game.py` (`P1`, `P2`, `DRAW`).
- Được dùng bởi: `heuristics/kinrow_eval.py`, mọi agent, `arena.py`, `experiments/`.

## Thiết kế & quyết định
- **Thắng tăng dần:** `_wins_at(move)` đếm quân liên tiếp cùng màu theo 4 hướng qua nước vừa đi
  (cộng hai phía) → O(k), không quét cả bàn. Dài hơn k vẫn thắng. Không "quấn" qua hàng vì dùng
  tọa độ (r, c) có kiểm tra biên.
- **Candidate tăng dần:** `_near[i]` = số quân trong bán kính quanh ô i; `_cand` = tập ô trống
  có `_near > 0`. `play`/`undo` cập nhật O(radius²) bằng bảng lân cận tiền tính (`_neighbors`,
  cache theo `(n, radius)`). `candidate_moves()` chỉ `sorted(set)`.
- **Undo:** stack `(move, winner_trước_đó)`; khôi phục board, lượt, winner, `_near`, `_cand`.
- **Hòa:** khi đủ n² nước mà không ai thắng (nước cuối thắng được ưu tiên hơn hòa).
- `clone()` sao chép board, history, `_near`, `_cand`; bảng lân cận bất biến nên dùng chung.
- Test hợp đồng `Game` (candidate ⊆ legal, không rỗng; `legal=[]` khi kết thúc; clone độc lập;
  key gồm lượt; undo khôi phục winner) nằm trong `tests/test_kinrow.py`.

## Test
- File: `tests/test_kinrow.py` — thắng ngang/dọc/2 chéo (3×3), thắng ở giữa đoạn, thắng của O,
  sát mép/góc 15×15, 4 quân không thắng, không quấn hàng, hòa 3×3, undo (kể cả sau hòa/thắng và
  về bàn trống), clone độc lập, key, candidate (bàn trống, 3×3, bán kính 5×5, góc, so với brute
  force, random playout + undo hết).
- Chạy riêng: `python -m pytest tests/test_kinrow.py -q`

## Hạn chế / TODO
- `board` dùng 0/1/2 còn người chơi là 1/-1: code ngoài (eval) cần ánh xạ `1 if p == X else 2`.
- Chưa có hash Zobrist; `key()` tạo `bytes` mỗi lần gọi (đủ cho 3×3; xem lại ở P2.4 nếu chậm).
