# Runner thí nghiệm — `gameai/experiments/common.py`

> Mục tiêu của file này: agent/thành viên khác dùng được module **mà không cần đọc code**.
> Cập nhật cùng lúc với code.

**Trạng thái:** ✅ ổn định  ·  **Task:** P4.1 (D-13), P4.2 (D-15)  ·  **Cập nhật:** 2026-11-10

## Mục đích
Chạy một match A vs B song song nhiều tiến trình, ghi **mỗi ván một dòng CSV ngay khi xong**, chạy tiếp
được nếu bị ngắt, và làm bảng tổng hợp (W/D/L, tỉ lệ thắng kèm khoảng tin cậy Wilson 95%).

## Public API
```python
DEFAULT_WORKERS = 4
GAME_COLUMNS, MOVE_COLUMNS, SUMMARY_COLUMNS: list[str]
class ResumeError(ValueError)
def run_match(out_path, game_spec, spec_a, spec_b, n_pairs, base_seed=0, workers=4,
              max_moves=None, random_opening=0, record_moves=True,
              allow_code_change=False) -> list[dict[str, str]]   # mọi dòng trong file
def summarize(rows, moves=None) -> list[dict]   # 3 dòng / cặp (label_a, label_b): "all", "A=X", "A=O"
#   moves = read_rows(moves_path_for(out_path)) → thêm cột *_search_* (D-15)
def write_summary(summary, path) -> None
def wilson(k, n, z=1.96) -> tuple[float, float]       # n = 0 → (nan, nan)
def read_rows(path) -> list[dict[str, str]]
def moves_path_for(out_path) -> Path                  # "<stem>_moves.csv"
def git_info() -> tuple[str, bool]                    # (commit, dirty)
def config_hash(game_spec, spec_a, spec_b, max_moves, random_opening, base_seed) -> str
def add_runner_args(parser) -> parser                 # --quick, --workers (4), --allow-code-change
```
Dùng trong script (bắt buộc `if __name__ == "__main__":` vì Windows dùng spawn):
```python
if __name__ == "__main__":
    rows = run_match("results/raw/p33_x.csv", GameSpec("kinrow", {"n": 15, "k": 5}), MCTS_H, GREEDY,
                     n_pairs=10, base_seed=0, workers=args.workers,
                     allow_code_change=args.allow_code_change)
    write_summary(summarize(rows), "results/tables/p33_x.csv")
```
- **Cờ chung (`add_runner_args`):** `--quick` chỉ **đăng ký cờ** (`args.quick`, mặc định False); mỗi script tự
  quyết định "quick" nghĩa là gì (ít ván / ít iteration) và **phải dùng tên file riêng** (vd. tiền tố
  `<task>quick_`) để không trộn với dữ liệu full. Script không được tự khai `--quick` lần nữa (argparse
  báo trùng). `--workers`, `--allow-code-change` như trên.
- `n_pairs` cặp ván, seed `base_seed + i`, mỗi seed 2 ván đổi lượt (`arena.md`). Chạy lại với `n_pairs`
  lớn hơn → chỉ chơi thêm các ván mới.
- `workers=1` → chạy trong tiến trình (debug, test); > 1 → `ProcessPoolExecutor`. Số worker ghi vào CSV.
- Lỗi dựng agent/game → ném ra **trước khi ghi gì**; lỗi ngoài ván trong worker → dừng batch (các ván đã ghi
  vẫn còn). Agent lỗi khi chơi → thua, batch chạy tiếp (`arena.md`).

### File ván (`out_path`, 1 dòng/ván, `GAME_COLUMNS`)
`game_id, pair_seed, a_is_x (1/0), label_a, label_b, winner (1/-1/0), result_a (1.0/0.5/0.0), termination,
error_side (A/B/""), error, n_moves, opening, moves` (nước nối bằng `;`), rồi mỗi bên `a_` / `b_`:
`moves, time_sum, time_mean, time_max, nodes_sum, nodes_mean, iterations_sum, iterations_mean,
rollout_plies_sum, rollout_plies_mean, max_depth_max, cutoffs_sum, tt_hits_sum, tactic_moves` (ô trống nếu
agent không có khóa đó; `time` do arena đo), rồi meta: `seed_a, seed_b, spec_a, spec_b, game_spec` (JSON),
`max_moves, random_opening, base_seed, config_hash, git_commit, git_dirty, workers, finished_at`.

### File moves (`<stem>_moves.csv`, 1 dòng/nước, `MOVE_COLUMNS`)
`game_id, ply, side, player, move, time` (arena đo), `agent_time` (= `stats["time"]`), `nodes, iterations,
value, cutoffs, tt_hits, max_depth, rollout_plies, tactic`.

### Bảng tổng hợp (`SUMMARY_COLUMNS`)
`label_a, label_b, split, n, wins, draws, losses, win_rate, win_lo, win_hi, nonloss_rate, nonloss_lo,
nonloss_hi, score, distinct_games, mean_moves, errors, a_errors, b_errors, max_moves_draws,
{a,b}_{time,nodes,iterations}_per_move`, `{a,b}_search_moves`, `{a,b}_search_iterations_per_move`.
Thắng/hòa/thua theo góc nhìn A. Gom theo `(label_a, label_b)` →
đặt `label` khác nhau cho các cấu hình khác nhau.
- **`*_iterations_per_move` (cũ) chia cho mọi nước**, kể cả nước MCTS đi thẳng nhờ tactics (thắng/chặn ngay,
  0 iteration) → thấp hơn số iteration thật khi search. **`*_search_iterations_per_move` (D-15)** chỉ tính
  các nước có search: bỏ nước có `tactic` ∈ {1 thắng ngay, 2 chặn ngay} (mã 3 "restrict" vẫn search nên vẫn
  tính) và nước không có khóa `iterations` (ô trống). `*_search_moves` = số nước đó. Cần truyền `moves`; không
  truyền → nan. **Báo iteration/nước trong báo cáo (E3, E5) dùng cột `search`.**

## Phụ thuộc
- Dùng: `arena.py`, `agents/registry.py`; `git` (tùy chọn).
- Được dùng bởi: P3.3, E1–E6 (`experiments/*.py`), CLI `match` (P4.3).

## Thiết kế & quyết định (D-13)
- **Chỉ tiến trình chính ghi file**; nhận kết quả bằng `wait(FIRST_COMPLETED)`. Mỗi ván: ghi moves → `fsync`
  → ghi dòng ván → `fsync`. Dòng ván là dấu "ván đã xong".
- **Resume:** bỏ byte sau dòng xuống cuối cùng (dòng cắt dở) ở cả hai file; header khác schema →
  `ResumeError`; viết lại file moves bỏ dòng của ván chưa có trong file ván (mồ côi); bỏ qua `game_id` đã có.
- **Chống trộn dữ liệu:** `config_hash` (game, spec A/B, `max_moves`, `random_opening`, `base_seed`; không
  gồm `n_pairs`) khác → `ResumeError`. (`git_commit`, `git_dirty`) khác → `ResumeError`, trừ khi
  `allow_code_change=True` (cờ `--allow-code-change`); dòng mới ghi commit hiện tại.
  `git_dirty` = có thay đổi file **đã track** ngoài `results/` so với HEAD (file chưa track không tính).
  Dirty → dirty cùng commit **không** phát hiện được nội dung sửa khác nhau → nên commit trước khi chạy dài.
- **Thống kê:** số chính là win rate W/n kèm Wilson 95%; thêm non-loss (W+D)/n kèm Wilson; score không có CI.
  Không lấy trung bình `value` (thang AB khác MCTS). `distinct_games` đếm chuỗi (khai cuộc, nước); dòng
  "all" tính thêm vai A/B.
- `workers` mặc định 4: máy lẫn nhân P/E, ngân sách `time_limit` nhạy với tải → không dùng hết luồng.

## Giải thích cho báo cáo
- **Thiết kế ván đấu.** Mỗi cấu hình đấu `2·n` ván với n seed; mỗi seed chơi hai ván, mỗi bên cầm quân đi
  trước một lần, cùng seed ngẫu nhiên của agent → loại lợi thế đi trước khỏi so sánh. Agent được dựng mới mỗi
  ván nên các ván độc lập (không chia sẻ cây / bảng băm).
- **Khoảng tin cậy Wilson 95%** cho tỉ lệ thắng p̂ = k/n (z = 1,96):
  `tâm = (p̂ + z²/2n) / (1 + z²/n)`, `nửa độ rộng = z·√(p̂(1−p̂)/n + z²/4n²) / (1 + z²/n)`.
  Khác khoảng Wald p̂ ± z√(p̂(1−p̂)/n), Wilson không suy biến khi p̂ = 0 hoặc 1 (hay gặp khi một bên áp đảo)
  và luôn nằm trong [0, 1]. Ví dụ: 5/10 → [0,237; 0,763]; 10/10 → [0,722; 1] (Wald cho [1; 1]).
- Điểm (W + 0,5·D)/n không phải tỉ lệ nhị thức nên không kèm khoảng Wilson.
- Khoảng tin cậy chỉ có nghĩa khi các ván thực sự khác nhau: cột `distinct_games` cho biết số chuỗi nước
  khác nhau; nếu nhỏ hơn n thì số mẫu hiệu dụng nhỏ hơn n.

## Test
- `tests/test_experiments_common.py`: Wilson (5/10, 0/10, 10/10, n=0); đủ cột cả hai file + giá trị cột; tắt
  moves; cùng seed cùng kết quả, seed khác khác; song song = tuần tự (cả moves); **song song ghi từng ván khi
  xong**; đổi lượt + `result_a` + cột `side`; resume (chạy thêm ván, ván cũ không chơi lại, bằng chạy liền);
  resume sau ghi dở (dòng ván cắt dở + moves mồ côi + dòng moves cắt dở); đổi config / header / commit / cờ
  dirty → `ResumeError`, `allow_code_change` cho qua; agent lỗi (song song) thua, batch tiếp; lỗi dựng → dừng
  trước khi ghi; `max_moves`; `random_opening`; `summarize` (đếm, tách lượt, Wilson, `distinct_games` bắt ván
  trùng, gom theo cặp, đếm lỗi); `write_summary`; `add_runner_args`; cột `time` do arena đo (khác
  `agent_time`); lỗi trong worker ngoài ván (khai cuộc không đặt được) → dừng batch.
- `test_summarize_search_iterations_skip_direct_moves` (dữ liệu tay: tactic 1/2 bị bỏ, 3 giữ, ô trống bỏ, tách
  A=X/A=O, cột cũ không đổi), `..._without_moves_gives_nan...`, `..._real_match`; `--quick` trong
  `test_add_runner_args_defaults`.
- Đã thử kill thật một lần bằng tay (taskkill cây tiến trình) giữa batch 15×15, 2 worker, 20 ván (không có
  test tự động): 4 ván đã ghi giữ nguyên, chạy lại chơi 16 ván còn thiếu, moves khớp.
- Chạy: `python -m pytest tests/test_experiments_common.py -q` (~30 s, có spawn tiến trình).

## Hạn chế / TODO
- CLI `match`: P4.3. Chưa có cờ chung cho "số ván quick" (mỗi script tự chọn).
- Hai lần chạy **đồng thời** trên cùng file không được bảo vệ (không có file lock).
