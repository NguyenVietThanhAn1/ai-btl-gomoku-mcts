# Tổng hợp kết quả cờ tướng (E7) - nguồn cho mục 5.7 báo cáo

> **Sinh tự động** bởi `python -m gameai.experiments.plots` từ `results/tables/e7_*.csv` - không sửa tay. Số kiểu VN (dấu phẩy thập phân).

## E7 - cờ tướng: ordering, rollout, MCTS vs Alpha-Beta (mục 5.7)

Ván: 25 khai cuộc ngẫu nhiên 4 ply × 2 ván đổi bên (c4: 50 × 2), `max_plies` 200; điểm = (W + D/2)/n theo góc nhìn A; Wilson 95 % trên điểm (D-25).

### Bảng E7 - ordering của Alpha-Beta (11 thế, độ sâu cố định, `e7_ordering.csv`)

| độ sâu | cấu hình | thế | nút | giây | nút so với không ordering | giây so với không ordering | giá trị gốc khớp |
|---|---|---|---|---|---|---|---|
| 2 | không ordering | 11 | 4712 | 0,073 | 1,000 | 1,000 | 11/11 |
| 2 | MVV-LVA | 11 | 1542 | 0,046 | 0,327 | 0,630 | 11/11 |
| 2 | MVV-LVA + TT | 11 | 1542 | 0,047 | 0,327 | 0,644 | 11/11 |
| 3 | không ordering | 11 | 85 054 | 1,168 | 1,000 | 1,000 | 11/11 |
| 3 | MVV-LVA | 11 | 19 880 | 0,339 | 0,234 | 0,290 | 11/11 |
| 3 | MVV-LVA + TT | 11 | 19 880 | 0,341 | 0,234 | 0,292 | 11/11 |
| 4 | không ordering | 11 | 938 419 | 18,865 | 1,000 | 1,000 | 11/11 |
| 4 | MVV-LVA | 11 | 97 926 | 3,722 | 0,104 | 0,197 | 11/11 |
| 4 | MVV-LVA + TT | 11 | 90 165 | 3,249 | 0,096 | 0,172 | 11/11 |

### Bảng E7 - các trận chốt trước (`e7_matches.csv`)

| điểm | A | B | s/nước | ván | W/D/L của A | điểm A [Wilson 95 %] | điểm A khi cầm Đỏ / Đen | chiếu bí / bí nước / lặp thế / max_plies | ply TB |
|---|---|---|---|---|---|---|---|---|---|
| c1 | MCTS Lend | MCTS L10 | 1 | 50 | 0/0/50 | 0,00 [0,00; 0,07] | 0,00 / 0,00 | 33 / 17 / 0 / 0 | 62,4 |
| c2 | MCTS Lend | Random | 1 | 50 | 49/1/0 | 0,99 [0,91; 1,00] | 0,98 / 1,00 | 49 / 0 / 0 / 1 | 116,8 |
| c3 | MCTS L10 | Random | 1 | 50 | 50/0/0 | 1,00 [0,93; 1,00] | 1,00 / 1,00 | 40 / 10 / 0 / 0 | 49,3 |
| c4 | MCTS L0 | MCTS L10 | 1 | 100 | 52/6/42 | 0,55 [0,45; 0,64] | 0,54 / 0,56 | 50 / 44 / 0 / 6 | 80,1 |
| d1 | MCTS L10 | AB ID | 1 | 50 | 0/0/50 | 0,00 [0,00; 0,07] | 0,00 / 0,00 | 40 / 10 / 0 / 0 | 42,9 |
| d2 | MCTS L10 | AB ID | 2,5 | 50 | 0/0/50 | 0,00 [0,00; 0,07] | 0,00 / 0,00 | 43 / 7 / 0 / 0 | 41,4 |
| a1 | AB độ sâu 1 | Random | - | 50 | 50/0/0 | 1,00 [0,93; 1,00] | 1,00 / 1,00 | 26 / 24 / 0 / 0 | 54,6 |
| a2 | AB độ sâu 2 | Random | - | 50 | 50/0/0 | 1,00 [0,93; 1,00] | 1,00 / 1,00 | 38 / 12 / 0 / 0 | 59,3 |

### Bảng E7 - khám phá d3/d4, thêm sau d1/d2, không chốt trước (`e7_matches.csv`)

| điểm | A | B | s/nước | ván | W/D/L của A | điểm A [Wilson 95 %] | điểm A khi cầm Đỏ / Đen | chiếu bí / bí nước / lặp thế / max_plies | ply TB |
|---|---|---|---|---|---|---|---|---|---|
| d3 | MCTS L10 | AB độ sâu 1 | 1 | 50 | 44/2/4 | 0,90 [0,79; 0,96] | 0,90 / 0,90 | 37 / 11 / 2 / 0 | 52,6 |
| d4 | MCTS L10 | AB độ sâu 2 | 1 | 50 | 2/1/47 | 0,05 [0,02; 0,15] | 0,06 / 0,04 | 31 / 18 / 1 / 0 | 66,9 |

### Bảng E7 - tìm kiếm trong trận MCTS L10 vs AB (`e7_matches.csv`)

| điểm | AB | s/nước MCTS | s/nước AB | iter/s MCTS (trung vị) | độ sâu cây MCTS TB | nút/nước MCTS | nút/nước AB | độ sâu AB đạt TB (min-max) |
|---|---|---|---|---|---|---|---|---|
| d1 | AB ID | 0,92 | 1,001 | 1228 | 3,22 | 1162 | 49 925 | 4,51 (3-7) |
| d2 | AB ID | 2,36 | 2,501 | 1202 | 3,69 | 2898 | 112 606 | 5,09 (4-7) |
| d3 | AB độ sâu 1 | 0,95 | 0,000 | 1607 | 3,34 | 1585 | 25 | cố định |
| d4 | AB độ sâu 2 | 0,90 | 0,004 | 1415 | 3,30 | 1280 | 111 | cố định |

### Bảng E7 - độ phân nhánh và ngân sách MCTS L10 (`e7_branching.csv`)

| điểm | ván | thế | nước hợp lệ TB / trung vị | nước search của L10 | iteration/nước TB / trung vị | iteration / nước hợp lệ ở gốc TB / trung vị |
|---|---|---|---|---|---|---|
| c1 | 50 | 2919 | 31,3 / 35,0 | 1422 | 1254 / 1235 | 31,9 / 28,6 |
| c4 | 100 | 7606 | 22,7 / 23,0 | 3674 | 2057 / 1674 | 246,5 / 74,9 |
| d1 | 50 | 1945 | 28,8 / 32,0 | 884 | 1324 / 1220 | 209,4 / 69,3 |
| d2 | 50 | 1869 | 29,4 / 33,0 | 870 | 3161 / 2974 | 443,8 / 160,3 |
| d3 | 50 | 2429 | 24,4 / 25,0 | 1166 | 1846 / 1630 | 155,4 / 66,0 |
| d4 | 50 | 3146 | 29,1 / 32,0 | 1399 | 1460 / 1354 | 233,9 / 67,9 |
| all | 350 | 19 914 | 26,4 / 28,0 | - | - | - |

Nguồn: `results/tables/e7_ordering.csv`, `results/tables/e7_matches.csv`, `results/tables/e7_branching.csv`, `results/figures/e7_scores.png`
