# Tổng hợp kết quả k-in-row (E1–E6) — nguồn cho mục 5 báo cáo

> **Sinh tự động** bởi `python -m gameai.experiments.plots` từ `results/tables/*.csv` — không sửa tay. Số kiểu VN (dấu phẩy thập phân). Khoảng [ ] là 95 %: Wilson cho tỷ lệ một điểm, khoảng cặp cho hiệu, xấp xỉ chuẩn cho score E4, bootstrap cụm thế cho E6.

## Bản đồ hình / bảng → mục 5 báo cáo

| Mục | Nội dung | E | Hình (`results/figures/`) | Bảng (`results/tables/`) |
|---|---|---|---|---|
| 5.1 | Minimax vs Alpha-Beta: số nút, thời gian, giá trị/nước | E1 | — | `e1_summary.csv`, `e1_nodes.csv`, `e1_positions.csv` |
| 5.2 | MCTS 3×3 không thua: W/D/L + vét cạn nhánh đối thủ | E2 | — | `e2_play.csv`, `e2_exhaustive.csv`, `e2_exhaustive_by_role.csv` |
| 5.3 | Hằng số c: iter – tỷ lệ thắng, mỗi c một đường; W/D/L 15×15 | E3 | `e3_3x3.png`, `e3_greedy.png`, `e3_ab2.png` | `e3_3x3_random.csv`, `e3_3x3_minimax.csv`, `e3_greedy.csv`, `e3_ab2_pilot.csv`, `e3_ab2.csv` |
| 5.4 | Chọn nước N lớn nhất vs W/N lớn nhất: W, N, W/N ở gốc; đối đầu | E4 | `e4_match.png` | `e4_roots_examples.csv`, `e4_roots_summary.csv`, `e4_match.csv` |
| 5.5 | Rollout random vs heuristic h300 (cùng iteration, cùng thời gian) | E5 | `e5_iter.png`, `e5_time.png` | `e5_paired.csv`, `e5_h2h.csv`, `e5_greedy.csv`, `e5_mref.csv`, `e5_ab2.csv`, `e5_bench.csv`, `e5_rates.csv` |
| 5.6 | Kiểm tra thắng ngay / chặn ngay (`check_tactics`) + cơ chế | E6 | `e6_choice.png`, `e6_match.png`, `e6_mechanism.png` | `e6_choice.csv`, `e6_match.csv`, `e6_paired.csv`, `e6_mechanism.csv`, `e6_cost_check.csv`, `e6_time.csv`, `e6_tactic_rate.csv` |

## E1 — Minimax vs Alpha-Beta: số nút, thời gian, giá trị/nước (mục 5.1)

- 3×3 (6 thế): giá trị gốc AB = Minimax 6/6; nút gộp 559 426 → 21 626 (−96,13 %) → 2252 (+ordering, −99,60 %) → 1318 (+TT, −99,76 %).
- 15×15 depth 2 (5 thế): 46 825 → 21 612 (−53,85 %) → 1416 (ordering, −96,98 %), nhưng thời gian ordering 0,265 s vs 0,247 s; depth 3: 553 574 → 48 504 nút, 5,46 → 1,26 s.

### Bảng E1 — số nút và thời gian (tổng trên các thế, `e1_summary.csv`)

| bàn | depth | biến thể | nút | giây | giảm nút vs Minimax | giá trị = Minimax |
|---|---|---|---|---|---|---|
| 3×3 | full | minimax | 559 426 | 1,317 | — | 6/6 |
| 3×3 | full | ab | 21 626 | 0,069 | 96,13 % | 6/6 |
| 3×3 | full | ab_order | 2252 | 0,015 | 99,60 % | 6/6 |
| 3×3 | full | ab_order_tt | 1318 | 0,009 | 99,76 % | 6/6 |
| 15×15 | 2 | minimax | 46 825 | 7,010 | — | 5/5 |
| 15×15 | 2 | ab_evalonly | 21 612 | 3,692 | 53,85 % | 5/5 |
| 15×15 | 2 | ab | 21 612 | 0,247 | 53,85 % | 5/5 |
| 15×15 | 2 | ab_order | 1416 | 0,265 | 96,98 % | 5/5 |
| 15×15 | 3 | ab | 553 574 | 5,458 | — | — |
| 15×15 | 3 | ab_order | 48 504 | 1,256 | — | — |

Nguồn: `results/tables/e1_summary.csv`, `results/tables/e1_nodes.csv`, `results/tables/e1_positions.csv`

## E2 — MCTS 3×3 không thua: W/D/L + vét cạn nhánh đối thủ (mục 5.2)

- Vét cạn (mọi chuỗi nước đối thủ): 5000 iter → 0 nhánh thua / 5674 (20 run = seed × vai); 100 iter 279/6247; 250 iter 84/5967; 1000 iter 7/5713.
- Đấu 5000 iter (100 ván/cặp, đổi lượt): vs minimax W/D/L 0/100/0, vs random W/D/L 98/2/0, vs mcts5000_opp W/D/L 0/100/0.

### Bảng E2 — W/D/L của MCTS 3×3 (`e2_play.csv`)

| MCTS | đối thủ | W/D/L | không thua [Wilson 95 %] |
|---|---|---|---|
| mcts100 | minimax | 0/73/27 | 0,73 [0,64; 0,81] |
| mcts100 | random | 92/5/3 | 0,97 [0,92; 0,99] |
| mcts100 | mcts100_opp | 22/59/19 | 0,81 [0,72; 0,87] |
| mcts250 | minimax | 0/83/17 | 0,83 [0,74; 0,89] |
| mcts250 | random | 94/5/1 | 0,99 [0,95; 1,00] |
| mcts250 | mcts250_opp | 11/77/12 | 0,88 [0,80; 0,93] |
| mcts1000 | minimax | 0/98/2 | 0,98 [0,93; 0,99] |
| mcts1000 | random | 99/1/0 | 1,00 [0,96; 1,00] |
| mcts1000 | mcts1000_opp | 1/98/1 | 0,99 [0,95; 1,00] |
| mcts5000 | minimax | 0/100/0 | 1,00 [0,96; 1,00] |
| mcts5000 | random | 98/2/0 | 1,00 [0,96; 1,00] |
| mcts5000 | mcts5000_opp | 0/100/0 | 1,00 [0,96; 1,00] |

### Bảng E2 — vét cạn mọi chuỗi nước đáp của đối thủ (`e2_exhaustive.csv`, `e2_exhaustive_by_role.csv`)

| iter | run (seed × vai) | nhánh (lá) | nhánh thua | run có thua | seed không thua, MCTS = X | seed không thua, MCTS = O |
|---|---|---|---|---|---|---|
| 100 | 20 | 6247 | 279 | 13 | 7/10 | 0/10 |
| 250 | 20 | 5967 | 84 | 10 | 10/10 | 0/10 |
| 1000 | 20 | 5713 | 7 | 2 | 10/10 | 8/10 |
| 5000 | 20 | 5674 | 0 | 0 | 10/10 | 10/10 |

Nguồn: `results/tables/e2_play.csv`, `results/tables/e2_exhaustive.csv`, `results/tables/e2_exhaustive_by_role.csv`

## E3 — Hằng số c: iter – tỷ lệ thắng, mỗi c một đường; W/D/L 15×15 (mục 5.3)

- 3×3 vs Random: thắng 0,915–0,980; vs Minimax không thua 0,70–0,77 ở 100 iter → 1,00 từ 2500 iter (mọi c).
- 15×15 vs Greedy (h300 + tactics): c = 0,5, 1000 iter 0,62 [0,48; 0,74]; c = 1,0, 1000 iter 0,46 [0,33; 0,60]; c = 1,4, 1000 iter 0,48 [0,35; 0,61]; c = 2,0, 1000 iter 0,22 [0,13; 0,35]; c = 0,5, 5000 iter 0,82 [0,69; 0,90]; c = 1,0, 5000 iter 0,88 [0,76; 0,94]; c = 1,4, 5000 iter 0,92 [0,81; 0,97]; c = 2,0, 5000 iter 0,96 [0,87; 0,99].
- AB depth 2: pilot c = 2,0 thắng 2/20; tốt nhất c = 1,0, 5000 iter 0,36 [0,241; 0,499].

### Bảng E3 — tỷ lệ thắng vs Greedy 15×15 (`e3_greedy.csv`)

| iter | c = 0,5 | c = 1,0 | c = 1,4 | c = 2,0 |
|---|---|---|---|---|
| 100 | 0,04 | 0,04 | 0,04 | 0,10 |
| 250 | 0,20 | 0,22 | 0,02 | 0,06 |
| 500 | 0,38 | 0,26 | 0,18 | 0,08 |
| 1000 | 0,62 | 0,46 | 0,48 | 0,22 |
| 2500 | 0,78 | 0,84 | 0,90 | 0,78 |
| 5000 | 0,82 | 0,88 | 0,92 | 0,96 |

### Bảng E3 — W/D/L của MCTS, 3×3 vs Random, 200 ván/điểm (`e3_3x3_random.csv`)

| iter | c = 0,5 | c = 1,0 | c = 1,4 | c = 2,0 |
|---|---|---|---|---|
| 100 | 191/9/0 | 183/17/0 | 186/11/3 | 183/14/3 |
| 250 | 187/13/0 | 187/13/0 | 189/10/1 | 190/8/2 |
| 500 | 190/10/0 | 188/12/0 | 190/9/1 | 191/9/0 |
| 1000 | 194/6/0 | 190/10/0 | 192/8/0 | 193/7/0 |
| 2500 | 196/4/0 | 188/12/0 | 193/7/0 | 193/7/0 |
| 5000 | 193/7/0 | 192/8/0 | 188/12/0 | 195/5/0 |

### Bảng E3 — W/D/L của MCTS, 3×3 vs Minimax, 100 ván/điểm (`e3_3x3_minimax.csv`)

| iter | c = 0,5 | c = 1,0 | c = 1,4 | c = 2,0 |
|---|---|---|---|---|
| 100 | 0/70/30 | 0/76/24 | 0/76/24 | 0/77/23 |
| 250 | 0/81/19 | 0/89/11 | 0/89/11 | 0/85/15 |
| 500 | 0/86/14 | 0/90/10 | 0/94/6 | 0/96/4 |
| 1000 | 0/98/2 | 0/98/2 | 0/96/4 | 0/96/4 |
| 2500 | 0/100/0 | 0/100/0 | 0/100/0 | 0/100/0 |
| 5000 | 0/100/0 | 0/100/0 | 0/100/0 | 0/100/0 |

### Bảng E3 — W/D/L của MCTS, 15×15 vs Greedy, 50 ván/điểm (`e3_greedy.csv`)

| iter | c = 0,5 | c = 1,0 | c = 1,4 | c = 2,0 |
|---|---|---|---|---|
| 100 | 2/0/48 | 2/0/48 | 2/0/48 | 5/0/45 |
| 250 | 10/0/40 | 11/0/39 | 1/0/49 | 3/0/47 |
| 500 | 19/0/31 | 13/0/37 | 9/0/41 | 4/0/46 |
| 1000 | 31/0/19 | 23/0/27 | 24/0/26 | 11/0/39 |
| 2500 | 39/0/11 | 42/0/8 | 45/0/5 | 39/0/11 |
| 5000 | 41/0/9 | 44/0/6 | 46/0/4 | 48/0/2 |

### Bảng E3 — W/D/L của MCTS, 15×15 vs AB depth 2, 50 ván/điểm (`e3_ab2.csv`)

| iter | c = 0,5 | c = 1,0 | c = 1,4 | c = 2,0 |
|---|---|---|---|---|
| 2500 | 13/2/35 | 9/0/41 | 5/0/45 | 6/0/44 |
| 5000 | 11/2/37 | 18/0/32 | 11/2/37 | 10/0/40 |

Nguồn: `results/figures/e3_3x3.png`, `results/figures/e3_greedy.png`, `results/figures/e3_ab2.png`, `results/tables/e3_3x3_random.csv`, `results/tables/e3_3x3_minimax.csv`, `results/tables/e3_greedy.csv`, `results/tables/e3_ab2_pilot.csv`, `results/tables/e3_ab2.csv`

## E4 — Chọn nước N lớn nhất vs W/N lớn nhất: W, N, W/N ở gốc; đối đầu (mục 5.4)

- 3×3: max_n ≠ max_wn ở 1,3–4,4 % thế; khi khác, tỷ lệ giữ giá trị trò chơi (max_n / max_wn) 10 iter 0,606 / 0,809, 20 iter 0,752 / 0,788, 50 iter 0,818 / 0,836, 100 iter 0,948 / 0,928, 250 iter 1,000 / 0,982, 1000 iter 1,000 / 1,000.
- 15×15: số search có max_n ≠ max_wn: c = 1,4, 50 iter 0/50, c = 1,4, 250 iter 0/50, c = 1,4, 1000 iter 0/50, c = 0,5, 50 iter 0/50, c = 0,5, 250 iter 2/50, c = 0,5, 1000 iter 1/50.
- Đối đầu 3×3 max_n vs max_wn (200 ván/điểm): score 10 iter 0,510 [0,45; 0,57], 20 iter 0,485 [0,42; 0,55], 50 iter 0,500 [0,45; 0,55], 100 iter 0,507 [0,47; 0,55], 250 iter 0,492 [0,46; 0,53].

### Bảng E4 — ví dụ gốc 3×3, 100 iter, c = 1,4 (`e4_roots_examples.csv`, giá trị trò chơi theo góc người đi ở gốc)

| ô | W | N | W/N | max N | max W/N | giá trị |
|---|---|---|---|---|---|---|
| 4 | 17,5 | 24 | 0,729 |  | ✓ | 0 |
| 8 | 3,5 | 10 | 0,350 |  |  | −1 |
| 3 | 11,0 | 18 | 0,611 |  |  | 0 |
| 0 | 18,0 | 25 | 0,720 | ✓ |  | 0 |
| 1 | 16,5 | 23 | 0,717 |  |  | 1 |

### Bảng E4 — 3×3, mọi thế ≥ 2 nước, c = 1,4: khi nào max_n ≠ max_wn (`e4_roots_summary.csv`)

| iter | số thế | max_n ≠ max_wn | giữ giá trị — max_n | giữ giá trị — max_wn |
|---|---|---|---|---|
| 10 | 4298 | 4,4 % | 0,606 | 0,809 |
| 20 | 4298 | 2,6 % | 0,752 | 0,788 |
| 50 | 4298 | 1,3 % | 0,818 | 0,836 |
| 100 | 4298 | 2,3 % | 0,948 | 0,928 |
| 250 | 4298 | 2,6 % | 1,000 | 0,982 |
| 1000 | 4298 | 2,6 % | 1,000 | 1,000 |

### Bảng E4 — 15×15 (h300 + tactics): số search có max_n ≠ max_wn (`e4_roots_summary.csv`)

| c | iter | max_n ≠ max_wn | con max_wn có W/N = 1 | max_n hòa N với con khác |
|---|---|---|---|---|
| 1,4 | 50 | 0/50 | 1,00 | 1,00 |
| 1,4 | 250 | 0/50 | 0,98 | 0,92 |
| 1,4 | 1000 | 0/50 | 0,80 | 0,76 |
| 0,5 | 50 | 0/50 | 1,00 | 1,00 |
| 0,5 | 250 | 2/50 | 0,80 | 0,70 |
| 0,5 | 1000 | 1/50 | 0,64 | 0,54 |

### Bảng E4 — đối đầu 3×3 max_n (A) vs max_wn (B), 200 ván/điểm (`e4_match.csv`)

| iter | W/D/L của max_n | score max_n [95 %] | score khi max_n đi trước | score khi max_n đi sau |
|---|---|---|---|---|
| 10 | 89/26/85 | 0,510 [0,45; 0,57] | 0,705 | 0,315 |
| 20 | 76/42/82 | 0,485 [0,42; 0,55] | 0,725 | 0,245 |
| 50 | 54/92/54 | 0,500 [0,45; 0,55] | 0,730 | 0,270 |
| 100 | 37/129/34 | 0,507 [0,47; 0,55] | 0,660 | 0,355 |
| 250 | 21/155/24 | 0,492 [0,46; 0,53] | 0,590 | 0,395 |

### Bảng E4 — ví dụ gốc 15×15, thế 3 (12 ply), 250 iter, c = 0,5, so với tham chiếu 20 000 iter (`e4_roots_examples.csv`)

| ô | W | N | W/N | max N | max W/N | W tham chiếu | N tham chiếu | W/N tham chiếu |
|---|---|---|---|---|---|---|---|---|
| 67 | 11,0 | 12 | 0,917 | ✓ |  | 185,0 | 409 | 0,452 |
| 97 | 11,0 | 11 | 1,000 |  | ✓ | 90,0 | 213 | 0,423 |
| 127 | 11,0 | 11 | 1,000 |  |  | 290,0 | 621 | 0,467 |
| 85 | 11,0 | 11 | 1,000 |  |  | 102,0 | 238 | 0,429 |
| 202 | 9,0 | 10 | 0,900 |  |  | 90,0 | 213 | 0,423 |

Nguồn: `results/figures/e4_match.png`, `results/tables/e4_roots_examples.csv`, `results/tables/e4_roots_summary.csv`, `results/tables/e4_match.csv`

## E5 — Rollout random vs heuristic h300 (cùng iteration, cùng thời gian) (mục 5.5)

- Cùng thời gian (kết luận chính): đối đầu h300 thắng rand 0,90 [0,79; 0,96] (0,5 s), 1,00 [0,93; 1,00] (2 s).
- Tỷ lệ thắng h300 vs rand (hiệu cặp): vs Greedy 0,5 s 0,62 vs 0,00, hiệu 0,62 [0,48; 0,76]; 2 s 0,86 vs 0,10, hiệu 0,76 [0,63; 0,89]; vs mref 2 s 1,00 vs 0,92, hiệu 0,08 [0,004; 0,156].
- Cùng iteration vs Greedy: 1000 iter 0,48 vs 0,02, hiệu 0,46 [0,32; 0,60]; 5000 iter 0,92 vs 0,08, hiệu 0,84 [0,72; 0,96].
- Benchmark đơn luồng (`e5_bench.csv`, trung vị): rand 3606 iter/s, h300 2409 iter/s, tỷ lệ rand/h300 = 1,50.
- Kiểm tra hợp lệ mref: rand 1000 iter vs mref thắng 25/50 [0,37; 0,63] (chứa 0,5: có).

### Bảng E5 — cùng thời gian/nước (so sánh công bằng; 2 worker)

| đối thủ | thời gian/nước | rand: thắng [Wilson 95 %] | h300: thắng [Wilson 95 %] | iteration thực tế/nước rand / h300 | hiệu cặp h300 − rand [95 %] |
|---|---|---|---|---|---|
| đối đầu (h300 vs rand) | 0,5 s | — | 0,90 [0,79; 0,96] | 1398 / 1322 | — |
| đối đầu (h300 vs rand) | 2,0 s | — | 1,00 [0,93; 1,00] | 5680 / 4006 | — |
| Greedy | 0,5 s | 0,00 [0,00; 0,07] | 0,62 [0,48; 0,74] | 1457 / 1206 | 0,62 [0,48; 0,76] |
| Greedy | 2,0 s | 0,10 [0,04; 0,21] | 0,86 [0,74; 0,93] | 5831 / 4331 | 0,76 [0,63; 0,89] |
| mref | 0,5 s | 0,50 [0,37; 0,63] | 0,98 [0,90; 1,00] | 1399 / 1305 | 0,48 [0,34; 0,62] |
| mref | 2,0 s | 0,92 [0,81; 0,97] | 1,00 [0,93; 1,00] | 5531 / 3829 | 0,08 [0,004; 0,156] |

### Bảng E5 — cùng số iteration (thiên vị h300; 4 worker)

| đối thủ | iter/nước | rand: thắng [Wilson 95 %] | h300: thắng [Wilson 95 %] | ván rand / h300 | hiệu cặp h300 − rand [95 %] |
|---|---|---|---|---|---|
| đối đầu (h300 vs rand) | 250 | — | 0,96 [0,87; 0,99] | — / 50 | — |
| đối đầu (h300 vs rand) | 1000 | — | 0,90 [0,79; 0,96] | — / 50 | — |
| đối đầu (h300 vs rand) | 5000 | — | 0,98 [0,90; 1,00] | — / 50 | — |
| Greedy | 100 | 0,00 [0,00; 0,07] | 0,04 [0,01; 0,13] | 50 / 50 | 0,04 [−0,01; 0,09] |
| Greedy | 250 | 0,00 [0,00; 0,07] | 0,02 [0,004; 0,105] | 50 / 50 | 0,02 [−0,02; 0,06] |
| Greedy | 500 | 0,00 [0,00; 0,07] | 0,18 [0,10; 0,31] | 50 / 50 | 0,18 [0,07; 0,29] |
| Greedy | 1000 | 0,02 [0,004; 0,105] | 0,48 [0,35; 0,61] | 50 / 50 | 0,46 [0,32; 0,60] |
| Greedy | 2500 | 0,00 [0,00; 0,07] | 0,90 [0,79; 0,96] | 50 / 50 | 0,90 [0,82; 0,98] |
| Greedy | 5000 | 0,08 [0,03; 0,19] | 0,92 [0,81; 0,97] | 50 / 50 | 0,84 [0,72; 0,96] |
| mref | 250 | 0,20 [0,11; 0,33] | 0,74 [0,60; 0,84] | 50 / 50 | 0,54 [0,37; 0,71] |
| mref | 1000 | 0,50 [0,37; 0,63] | 0,90 [0,79; 0,96] | 50 / 50 | 0,40 [0,24; 0,56] |
| mref | 5000 | 0,88 [0,76; 0,94] | 1,00 [0,93; 1,00] | 50 / 50 | 0,12 [0,03; 0,21] |
| AB2 | 5000 | 0,00 [0,00; 0,16] | 0,22 [0,13; 0,35] | 20 / 50 | 0,15 [−0,01; 0,31] |

Nguồn: `results/figures/e5_iter.png`, `results/figures/e5_time.png`, `results/tables/e5_paired.csv`, `results/tables/e5_h2h.csv`, `results/tables/e5_greedy.csv`, `results/tables/e5_mref.csv`, `results/tables/e5_ab2.csv`, `results/tables/e5_bench.csv`, `results/tables/e5_rates.csv`

## E6 — Kiểm tra thắng ngay / chặn ngay (`check_tactics`) + cơ chế (mục 5.6)

- Tắt tactics, chọn đúng ô chặn (trọng số pool) 100/500/1000/2500/5000 iter: rand 0,03 → 0,08 → 0,12 → 0,26 → 0,38; h300 0,50 → 0,22 → 0,14 → 0,13 → 0,48; bật tactics 1,00.
- Win rate tắt → bật (so cặp): h300 vs Greedy 1000 iter 0,10 → 0,48, hiệu 0,38 [0,23; 0,53]; 5000 iter 0,30 → 0,92, hiệu 0,62 [0,47; 0,77]; rand vs mref 0,46 → 0,50, hiệu 0,04 [−0,10; 0,18].
- Cơ chế (block, chạy lại cây): tỷ lệ con sai có W = 0 ở 100 iter h300 0,73 vs rand 0,55; nhóm chọn sai h300: W/N nước được chọn 0,31 / 0,90 / 0,70 (100 / 1000 / 5000 iter), ô thắng của đối thủ đã mở dưới nước đó 0,20 (1000) → 0,97 (5000). Kết luận: `e6_tactics.md`, D-21.

### Bảng E6 — tỷ lệ chọn đúng khi TẮT check_tactics (45 thế/loại × 10 seed; trọng số pool, bootstrap 95 %; `e6_choice.csv`)

| iter | chặn four — rand | chặn four — h300 | thắng ngay — rand | thắng ngay — h300 |
|---|---|---|---|---|
| 100 | 0,03 [0,01; 0,06] | 0,50 [0,40; 0,61] | 0,05 [0,03; 0,07] | 0,27 [0,17; 0,40] |
| 500 | 0,08 [0,05; 0,11] | 0,22 [0,12; 0,34] | 0,74 [0,66; 0,81] | 0,28 [0,17; 0,40] |
| 1000 | 0,12 [0,08; 0,16] | 0,14 [0,06; 0,24] | 0,97 [0,95; 0,99] | 0,28 [0,17; 0,40] |
| 2500 | 0,26 [0,20; 0,33] | 0,13 [0,05; 0,24] | 1,00 [1,00; 1,00] | 0,29 [0,18; 0,41] |
| 5000 | 0,38 [0,30; 0,46] | 0,48 [0,36; 0,61] | 1,00 [1,00; 1,00] | 0,39 [0,26; 0,54] |
| bật tactics | 1,00 | 1,00 | 1,00 | 1,00 |

### Bảng E6 — tỷ lệ thắng tắt → bật check_tactics, so cặp (`e6_paired.csv`)

| cấu hình | iter | ván | tắt | bật | hiệu bật − tắt [95 %] |
|---|---|---|---|---|---|
| rand vs mref | 1000 | 50 | 0,46 | 0,50 | 0,04 [−0,10; 0,18] |
| h300 vs Greedy | 1000 | 50 | 0,10 | 0,48 | 0,38 [0,23; 0,53] |
| h300 vs Greedy | 5000 | 50 | 0,30 | 0,92 | 0,62 [0,47; 0,77] |

### Bảng E6 — chi phí một lần check_tactics, đơn luồng (`e6_cost_check.csv`; overhead so với MCTS 1000 iter tắt tactics trên cùng thế)

| loại thế | số thế | ms trung vị | ms tối đa | overhead trung vị — rand | overhead trung vị — h300 |
|---|---|---|---|---|---|
| đối thủ có four (chặn) | 45 | 13,30 | 56,45 | — | — |
| mình thắng ngay | 45 | 0,15 | 0,43 | — | — |
| yên tĩnh (không tactic) | 42 | 27,36 | 98,49 | 7,3 % | 4,4 % |

### Bảng E6 — nước đi thẳng nhờ check_tactics và thời gian/nước trong ván (`e6_tactic_rate.csv`, `e6_time.csv`)

| cấu hình (bật) | ván với | nước | đi thẳng (không search) | s/nước tắt | s/nước bật | ván bật lấy từ |
|---|---|---|---|---|---|---|
| rand_i1000 | mref | 672 | 6,1 % | 0,46 | 0,44 | E5 |
| h300_i1000 | h300 tắt (đối đầu) | 274 | 17,2 % | 0,66 | 0,61 | E6 |
| h300_i1000 | Greedy | 371 | 21,3 % | 0,69 | 1,18 | E3 |
| h300_i5000 | Greedy | 491 | 31,0 % | 3,33 | 3,28 | E3 |

Nguồn: `results/figures/e6_choice.png`, `results/figures/e6_match.png`, `results/figures/e6_mechanism.png`, `results/tables/e6_choice.csv`, `results/tables/e6_match.csv`, `results/tables/e6_paired.csv`, `results/tables/e6_mechanism.csv`, `results/tables/e6_cost_check.csv`, `results/tables/e6_time.csv`, `results/tables/e6_tactic_rate.csv`
