# kinrow_vcf — `gameai/heuristics/kinrow_vcf.py`

**Trạng thái:** 🔄 đang làm (B2 xong, chưa gắn vào agent)  ·  **Task:** P6.4 (D-35/D-36)  ·  **Cập nhật:** 2026-11-18

## Mục đích
VCF (Victory by Continuous Fours — chuỗi nước "four" ép thắng) cho `KInRow(n, k)`, và một **hook ở gốc** để
`AlphaBetaAgent` / `MCTSAgent` "Rất khó" (chỉ GUI) dùng: tự thắng bằng VCF, chặn VCF của đối thủ. Không dùng cho
thí nghiệm E1–E6 (agent mặc định không gọi module này).

## Public API
```python
RootHook = Callable[[KInRow], tuple[int | None, list[int] | None]]

def completion_cells(game, move, stone) -> set[int]      # ô hoàn thành k nếu đặt `move` (không mutate)
def win_cells(game, stone) -> list[int]                  # ô (trong candidate_moves) mà stone thắng ngay
def vcf_search(game, attacker, max_depth, deadline=None) -> tuple[int | None, bool]  # (nước đầu, hết giờ?)
def find_vcf(game, attacker, max_depth, deadline=None) -> int | None
def make_root_hook(vcf_depth=8, vcf_time=0.3) -> RootHook
```
- **"Four"** của `stone` sau khi đặt `move`: một cửa sổ k ô qua `move` không có quân địch, đúng k−2 quân của `stone`
  (ngoài `move`) và đúng 1 ô trống khác = **ô hoàn thành**. Đối thủ buộc phải chặn đúng ô đó. Hai ô hoàn thành khác
  nhau (four mở / double-four) ⇒ thắng.
- `find_vcf`: nước đầu của chuỗi ≤ `max_depth` four liên tiếp (đối thủ chỉ có nước chặn) kết thúc bằng thắng; thắng
  ngay trả luôn (không tốn độ sâu). `attacker` không cần là người đi (dùng bản sao, đổi lượt nội bộ `_player`).
  Hết `deadline` (`time.perf_counter()`) → `(None, True)`. Không đụng `game`.
- `make_root_hook`: `hook(game) → (move, None)` đi ngay; `(None, danh sách)` giới hạn nước ở gốc; `(None, None)`
  không giới hạn. Thứ tự: (1) mình thắng ngay / có VCF → nước đó; (2) đối thủ có ≥ 2 ô thắng → (None, None), đúng 1
  → ô đó; (3) đối thủ (nếu được đi) có VCF → thử từng ứng viên trong `candidate_moves`, giữ nước khiến đối thủ
  **hết** VCF (1 nước → đi ngay; nhiều → danh sách đã sắp; 0 → (None, None)). `vcf_time` là tổng cho cả ba bước;
  hết giờ ở bước nào cũng → (None, None).

## Phụ thuộc
- Dùng: `games/kinrow.py` (`KInRow`, `cell_of`, `_DIRS`, `_wins_at`, `_player` — nội bộ, cùng repo).
- Sẽ được dùng bởi (P6.4, bước sau): `agents/alphabeta.py`, `agents/mcts.py` (tham số `root_hook`), registry
  (`vcf_depth`, `vcf_time`).

## Thiết kế & quyết định
- Quét cửa sổ qua `move` (4 hướng × k cửa sổ) — không play/undo để phát hiện four; play/undo chỉ để đi nước + chặn.
- Ứng viên tấn công và ô thắng lấy từ `candidate_moves()` (bán kính `radius` ≥ 2); ô chặn của đối thủ có thể nằm
  ngoài tập này (vẫn `play` được). Với k = 5, mọi ô thắng / ô four nằm trong bán kính 2 của một quân.
- Khi đối thủ đang có đúng 1 ô thắng, chỉ four **đồng thời chiếm ô đó** mới hợp lệ; ≥ 2 ô ⇒ không có VCF.
- Hết giờ = "không biết", không coi là "không có VCF": phòng thủ bỏ giới hạn thay vì cắt nhầm nước.
- Chưa làm VCT (chuỗi open-three) — ngoài phạm vi (An, Q4).

## Giải thích cho báo cáo
Không đưa vào báo cáo (tính năng chế độ chơi GUI, D-35). Ý tưởng: tìm kiếm tối thiểu chỉ qua các nước ép
(four) có nhánh phản ứng duy nhất nên rất sâu mà rẻ; tương tự threat-space search trong Gomoku.

## Test
- `tests/test_kinrow_vcf.py`: ô hoàn thành; chuỗi 2 four (tìm được, `max_depth=1` thì không); replay chuỗi tới khi
  thắng; open-three = VCF độ sâu 1; thắng ngay; four chết; đối thủ có ô thắng; attacker không phải người đi;
  deadline; hook (tự thắng, chặn bắt buộc, phòng thủ — đối chiếu từng ứng viên, không giới hạn khi hết giờ);
  k = 4; **đối chiếu bản ngây thơ** (đối thủ trả lời mọi ô) trên 120 thế ngẫu nhiên 7×7 k=4, độ sâu 3.
- Chạy: `python -m pytest tests/test_kinrow_vcf.py -q`

## Hạn chế / TODO
- Độ trễ hook trên 30 thế ngẫu nhiên 15×15 giữa ván: trung bình 13 ms, tối đa 176 ms (máy dev, 2026-11-18).
- Phòng thủ thử mọi ứng viên × VCF của đối thủ → có thể chạm `vcf_time` ở thế phức tạp (khi đó không giới hạn gốc).
