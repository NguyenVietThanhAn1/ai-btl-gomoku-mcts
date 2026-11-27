# Kiểm nhãn kết thúc E7 — `gameai/experiments/e7_term_check.py`

> Mục tiêu của file này: agent/thành viên khác dùng được module **mà không cần đọc code**.
> Cập nhật cùng lúc với code.

**Trạng thái:** ✅ ổn định  ·  **Task:** P8.4 (D-25)  ·  **Cập nhật:** 2026-11-26

## Mục đích
Kiểm **độc lập** nhãn `mate` / `stalemate` mà `e7_xiangqi.classify_game` gán cho ván E7 (bí nước chiếm phần lớn ván
phân thắng thua, vd. c4 44/94 → cần chắc không phải lỗi luật). Thế cuối được kiểm bằng một bộ sinh nước viết riêng từ
FEN, không dùng code `gameai/games/xiangqi.py`.

## Chạy
```
python -m gameai.experiments.e7_term_check          # in perft, 10 ván + FEN thế cuối, "khớp 10/10"
```
Cờ: `--raw-dir` (mặc định `results/raw`), `--out` (mặc định `results/tables/e7_term_check.csv`).
Mã thoát 0 khi mọi ván khớp; 1 nếu perft bộ sinh độc lập sai hoặc có ván lệch. Chỉ đọc raw, không ghi vào `results/raw/`.

## Cách kiểm
1. Pool: mọi ván trong `e7_c4.csv`, `e7_a1.csv`, `e7_d1.csv` có nhãn `mate` (116 ván) / `stalemate` (78 ván).
2. Chọn `random.Random(20261126)`: 5 ván stalemate rồi 5 ván mate (`rng.sample`) — chạy lại ra đúng 10 ván cũ.
3. Mỗi ván: replay khai cuộc + nước bằng game (`make_game(game_spec)`), lấy `to_fen()` thế cuối.
4. Kiểm bằng bộ sinh độc lập trên FEN: số nước hợp lệ của bên tới lượt = 0; bên tới lượt có bị chiếu không.
5. Ván **khớp** khi đồng thời: độc lập 0 nước; `game.legal_moves()` rỗng; `game.in_check()` = chiếu độc lập;
   `winner()` = winner CSV = −(bên tới lượt); nhãn = `mate` nếu bị chiếu, `stalemate` nếu không.
6. Trước khi kiểm, tự kiểm bộ sinh độc lập: perft thế đầu depth 1 / 2 = **44 / 1 920** (giá trị chuẩn).

## Public API
```python
parse_fen(fen) -> (grid 10×9, "R" | "B")       # hàng 0 = phía Đen; chữ hoa = Đỏ; nhận H/N, E/B
pseudo_moves(grid, side) -> [((r, c), (r2, c2))]
attacked(grid, side) -> bool                    # tướng bị tấn công, gồm luật lộ mặt tướng
legal_moves(grid, side) -> [...]; perft(grid, side, depth) -> int
check_row(point, row) -> dict                   # một ván → dòng COLUMNS (ok = 1/0)
sample_games(raw_dir, seed=SEED, n_each=5) -> [(point, row)]
```

## File ra
`results/tables/e7_term_check.csv`: `point, game_id, label, ply, fen, side_to_move, indep_legal, indep_check, game_legal,
game_in_check, game_winner, csv_winner, ok`.

## Kết quả (2026-11-26, raw commit `814a612`)
perft 44 / 1 920; **10/10 khớp** (5 stalemate: a1 ×2, c4 ×3; 5 mate: c4 ×3, d1 ×2). Ghi trong D-25.

## Phụ thuộc
- Dùng: `e7_xiangqi.classify_game` (nhãn cần kiểm), `e7_xiangqi._write`, `registry.make_game` (chỉ để replay).
- Bộ sinh độc lập: luật Tướng / Sĩ (cung), Tượng (mắt, không qua sông), Mã (cản chân), Xe, Pháo (ngòi), Tốt (qua
  sông đi ngang), lộ mặt tướng — viết lại từ đầu, không chia sẻ bảng nước với `xiangqi.py`.

## Giải thích cho báo cáo
Mục 5 (E7) dùng được: "Nhãn kết thúc được kiểm độc lập trên 10 ván chọn ngẫu nhiên bằng bộ sinh nước thứ hai viết
riêng (perft thế đầu 44 / 1 920 khớp chuẩn): 10/10 thế cuối không còn nước hợp lệ và trạng thái chiếu khớp nhãn."

## Test
`tests/test_e7_term_check.py`: perft thế đầu 44 / 1 920; `sample_games` tất định theo seed (raw tạm); chiếu bí và bí nước khớp `Xiangqi`; `check_row` trên thế chiếu
bí → ok; lộ mặt tướng chặn Tướng sang cột đối diện. Chạy: `python -m pytest tests/test_e7_term_check.py -q`.

## Hạn chế / TODO
- Mẫu 10 ván (không phải toàn bộ 194); bộ sinh độc lập chậm (Python thuần, chỉ dùng cho thế cuối).
