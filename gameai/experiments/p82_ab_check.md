# p82_ab_check — `gameai/experiments/p82_ab_check.py`

> Đo nhanh AB cờ tướng và trận thử AB vs Random/Greedy (P8.2). **Không phải số liệu thí nghiệm** (E7 ở P8.4).

**Trạng thái:** ✅ ổn định  ·  **Task:** P8.2  ·  **Cập nhật:** 2026-11-21

## Mục đích
Đưa ra cỡ độ lớn nút/giây, hiệu quả ordering và `depth_reached` theo `time_limit` của `AlphaBetaAgent` trên cờ tướng; cung cấp helper trận thử (khai cuộc ngẫu nhiên có seed, đổi bên) cho test và cho P8.4 dùng lại.

## Public API
```python
ab_spec(depth, order="xq_mvv_lva", use_tt=False, time_limit=None, label=None) -> AgentSpec   # AB tất định, eval+delta
RANDOM, GREEDY                       # AgentSpec("random"), AgentSpec("greedy", {"score": "xq_delta"})
midgame_fens(n, seed=0, plies=(14, 36)) -> list[str]     # thế giữa ván: nước ngẫu nhiên có seed từ thế đầu
measure_ordering(fens, depth) -> rows                    # nút / giây / nút-s: none, mvv_lva, mvv_lva+tt, mvv_lva_check
measure_time_limits(fens, limits, max_depth=8) -> rows   # depth_reached trung bình theo time_limit (TT exact)
make_openings(n_pairs, base_seed=0, spec=None)           # [(pair_seed, khai cuộc 2–4 nước)], đôi một khác nhau
run_match(spec_a, spec_b, n_pairs, base_seed=0, max_plies=200) -> dict   # 2·n_pairs ván; W/D/L, score, distinct_openings, duplicate_games, errors
```
- Chạy: `python -m gameai.experiments.p82_ab_check [--out results/tables/p82_ab_speed.csv] [--skip-match] [--pairs 5] [--max-plies 200] [--base-seed 0]` (~35 s đo + ~2 s trận).
- **Khai cuộc:** mỗi `pair_seed` cho một khai cuộc 2–4 nước ngẫu nhiên hợp lệ (`arena.random_opening_moves`), mỗi khai cuộc **2 ván đổi bên** (A cầm Đỏ / Đen). AB và Greedy gần như tất định nên lặp ván giống nhau là vô nghĩa; khai cuộc tạo đa dạng. Kết quả in số khai cuộc phân biệt và số ván trùng chuỗi nước.
- CSV `results/tables/p82_ab_speed.csv` (cột `metric, config, value, unit, n_samples, note`).

## Phụ thuộc
- Dùng: `agents/registry.py`, `arena.py` (`derive_seed`, `play_game`, `random_opening_moves`), `games/xiangqi.py`, `heuristics/xiangqi_eval.py` (qua registry).
- Được dùng bởi: `tests/test_xiangqi_ab.py`.

## Thiết kế & quyết định
- Thế đo: thế khởi đầu + 8 thế giữa ván (nước ngẫu nhiên có seed 82, 14–36 ply). Thế ngẫu nhiên có thể lệch thực tế (nhiều quân đã mất) → số đo là cỡ độ lớn.
- Đo ordering ở depth 3 (tất định): giá trị gốc phải giống nhau giữa các cấu hình (ghi trong cột `note`).
- `time_limit`: TT exact, `depth` tối đa 8, không `top_k` (D-36: `deep`/`top_k` chỉ cho chế độ chơi).

## Kết quả đo (2026-11-21, một máy dev của An, Windows; không ghi trạng thái nguồn điện)
Nguồn: `results/tables/p82_ab_speed.csv`. Thời gian phụ thuộc máy/lần chạy; số nút tất định.

| Cấu hình (depth 3, 9 thế) | Nút | Giây | Nút/s |
|---|---|---|---|
| không ordering | 89 985 | 1,172 | 76 806 |
| `xq_mvv_lva` | 17 417 (−80,6 %) | 0,299 | 58 155 |
| `xq_mvv_lva` + TT exact | 17 417 | 0,274 | 63 590 |
| `xq_mvv_lva_check` | 16 277 | 0,356 (+19 % so với mvv_lva) | 45 743 |

TT exact không đổi số nút ở depth 3 (ít thế trùng cùng độ sâu còn lại). `check_bonus`: nút −6,5 % nhưng chậm hơn → **không bật** (D-23).

| `time_limit` (ID, TT exact, depth ≤ 8, 9 thế) | `depth_reached` trung bình (min–max) | thời gian dùng tối đa | nút trung bình |
|---|---|---|---|
| 0,5 s | 4,00 (4–4) | 0,501 s | 22 169 |
| 1,0 s | 4,33 (4–5) | 1,001 s | 49 767 |
| 2,0 s | 4,89 (4–5) | 2,001 s | 96 050 |

Trận thử (AB depth 2 vs đối thủ, seed 0, 5 khai cuộc × 2 ván, `max_plies` 200; số đo một lần, ngưỡng test chốt từ đó): vs Random **W/D/L = 10/0/0**; vs Greedy (`xq_delta`) **10/0/0**; 5 khai cuộc phân biệt, 0 ván trùng chuỗi nước, 0 lỗi; ~0,8 s mỗi trận (10 ván).

## Test
- Helper được kiểm trong `tests/test_xiangqi_ab.py` (trận thử, registry). Chạy: `python -m pytest tests/test_xiangqi_ab.py -q` (~7 s).

## Hạn chế / TODO
- Ván cờ ngắn (17–122 ply) vì đối thủ yếu; không đại diện cho đối đầu mạnh–mạnh (E7 ở P8.4 dùng `random_opening` + `time_limit`).
- Trận chạy tuần tự (đủ nhanh); P8.4 sẽ dùng runner song song của arena.
