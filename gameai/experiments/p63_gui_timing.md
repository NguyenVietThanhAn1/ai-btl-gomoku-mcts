# Đo thời gian/nước GUI — `gameai/experiments/p63_gui_timing.py`

> Mục tiêu của file này: agent/thành viên khác dùng được module **mà không cần đọc code**.
> Cập nhật cùng lúc với code.

**Trạng thái:** ✅ ổn định  ·  **Task:** P6.3 (D-29), P6.4 (D-36), P6.2 (D-37)  ·  **Cập nhật:** 2026-11-25

## Mục đích
Đo thời gian/nước của 12 mức độ khó GUI (`gui/presets.DIFFICULTY`) **qua vòng vẽ GUI thật** để kiểm luật D-29
(MCTS Khó 15×15 trung bình ≤ 5 s/nước). **Số minh họa GUI — không dùng cho báo cáo thí nghiệm** (cột `note`).

## Cách chạy
```
python -m gameai.experiments.p63_gui_timing                 # cả 3×3 và 15×15
python -m gameai.experiments.p63_gui_timing --boards 15     # chỉ 15×15 (giữ dòng 3×3 cũ trong CSV)
python -m gameai.experiments.p63_gui_timing --boards xiangqi --table-dir local_out/p62 --tag p62   # 6 mức cờ tướng (P6.2)
python -m gameai.experiments.p63_gui_timing --quick         # 1 ván/mức, file p63quick_* (không commit)
# P6.4 (D-36): bộ lọc + ghi ngoài results/ (không ghi đè p63_* / p63anim_*)
python -m gameai.experiments.p63_gui_timing --boards 15 --kinds alphabeta mcts --levels medium hard \
    --table-dir local_out/p64 --tag p64gui
```
- `--kinds` / `--levels` lọc mức; có bộ lọc hoặc `--table-dir` thì **bắt buộc** `--tag` (không bắt đầu bằng `p63`)
  hoặc `--table-dir` khác `results/tables` → không bao giờ ghi đè `p63_*` / `p63anim_*` (báo cáo trỏ vào). Bench
  tham chiếu `e5_bench.csv` vẫn đọc từ `results/tables`.
- Cột mới `fps_think` (số khung hình ÷ tổng thời gian các khung khi AI đang nghĩ) và `fps_worst` (1 / khung dài
  nhất): FPS vòng lặp chính headless (mục tiêu 30).
- Không cắm sạc → dừng (D-21); `--allow-battery` để bỏ qua (số đo khi đó không dùng được).
- Animation GUI bật mặc định → file `p63anim_*` (cột `animations = 1`); `--no-anim` → `p63_*` (bảng gốc D-29).
- Thời gian: 3×3 ~10 s; 15×15 vài phút (MCTS Khó ~2–5 s/nước chiếm phần lớn); cờ tướng ~4 phút (2 ván/mức).
- Cờ tướng (P6.2): `--boards xiangqi` (khóa trò = `presets.board_key`), `GAMES["xiangqi"]` = `max_plies`
  `XQ_TIMING_PLIES` = 60 (ván cắt ngắn, hòa khi chạm), 2 ván/mức (`--quick` 1), chỉ đối thủ người ngẫu nhiên (nước hợp lệ).
  Cột `board` = "xiangqi"; bảng xếp 3 / 15 / xiangqi (`board_order`). Kết quả: D-37.

## Điều kiện đo (D-21)
- **Cắm sạc, máy rảnh** (đóng app nặng). Ghi `power`, `battery_pct` (`e6_tactics.power_status`) và `power_plan`
  (`powercfg /getactivescheme`) vào runinfo.
- **Bench ngắn đầu mỗi lần chạy** (như E6): MCTS 1 s/thế, thế 8/16/24 quân, seed 0, rand + h300, tactics tắt
  (`e5_rollout.bench`) → `speed_vs_e5` = iter/s ÷ cùng ô trong `e5_bench.csv`; trung vị ghi vào runinfo.
  Xa 1 nhiều → máy đang chậm (pin / tải / nhiệt), đừng dùng số đo.
- Mỗi ván: `App` trên Surface headless (`SDL_VIDEODRIVER=dummy`), vẽ mỗi frame, khóa 30 fps; độ trễ AI 0.
  Thời gian = `MoveInfo.time` (quanh `select_move` trong thread AI, chịu GIL với vòng vẽ như GUI thật).
- Đối thủ: `random_human` = nước ngẫu nhiên có seed trong `candidate_moves` (3×3: 5 ván, 15×15: 3 ván; seed chẵn
  AI cầm O, lẻ AI cầm X); 15×15 thêm 1 ván AI (X) vs `e3_c_sweep.AB2` để có thế giữa ván dài hơn.
  Người ngẫu nhiên thua nhanh → thế phần lớn là đầu ván.

## Output (`results/tables/`)
| File | Nội dung |
|---|---|
| `p63_gui_timing.csv` | board, kind, level, source (E1/E2/E3/E3/E5/riêng), config, opponent, games, ai_moves, search_moves, mean_s / median_s (chỉ nước có search, bỏ tactic 1/2), max_s (mọi nước AI), power, note |
| `p63_gui_runinfo.csv` | mỗi lần chạy 1 dòng: thời điểm, wall_s, boards, cpu, power, battery_pct, power_plan, bench_speed_vs_e5, git_commit, git_dirty, note |
| `p63_bench.csv` | bench ngắn lần chạy gần nhất (cột như `e6_bench.csv`) |

## Phụ thuộc
- Dùng: `gui/presets.py` (`DIFFICULTY`, `AB2`), `gui/pygame_app.py` (`App`, `autoplay_move`), `e5_rollout`
  (`bench`, `cpu_name`, `_write`, `_append_csv`), `e6_tactics.power_status`, `common` (`git_info`, `read_rows`).

## Test
- `tests/test_p63_gui_timing.py`: `measure_level` 3×3 đủ cột + nhãn; `run` (bench giả) ghi 3 file, giữ dòng bàn khác;
  cờ tướng: `parse_board`, ván cắt ngắn, 6 mức chỉ vs người ngẫu nhiên, thứ tự bảng.

## Hạn chế / TODO
- Thời gian nước người ngẫu nhiên ≈ 0 → không đo; số ván ít (minh họa, không có CI).
