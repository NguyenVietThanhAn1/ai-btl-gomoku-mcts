# xiangqi — `gameai/games/xiangqi.py`

> Cờ tướng (Xiangqi) 9×10 cài `Game` (cùng hợp đồng với `KInRow`). Thiết kế: D-22.

**Trạng thái:** ✅ ổn định  ·  **Task:** P8.1  ·  **Cập nhật:** 2026-11-21

## Mục đích
Luật cờ tướng đầy đủ để AB/MCTS (P8.2, P8.3), GUI (P6.2) và thí nghiệm E7 (P8.4) dùng qua interface `Game`. Đúng luật được kiểm bằng **perft** so với số chuẩn bên ngoài (mục Test).

## Public API
```python
RED = P1; BLACK = P2                       # Đỏ đi trước
K, A, B, N, R, C, P = 1..7                 # tướng, sĩ, tượng, mã, xe, pháo, tốt; Đỏ dương, Đen âm, 0 = trống
START_FEN: str

class Xiangqi:
    def __init__(self, fen: str = START_FEN, max_plies: int = 300): ...
    @classmethod
    def from_fen(cls, fen, max_plies=300) -> Xiangqi
    def to_fen(self) -> str                 # "<bàn> w|b - - 0 <số nước>", chữ E/H cho tượng/mã
    # Game: current_player, legal_moves, candidate_moves (= legal_moves), play, undo,
    #       is_terminal, winner, clone, key, render
    def in_check(self) -> bool              # bên sắp đi đang bị chiếu
    ply: int                                # số nước đã đi từ lúc nạp FEN
    move_history: tuple[int, ...]

def move_to_iccs(move: int) -> str          # 25*90+22 -> "h2e2" (file a–i, rank 0–9; rank 0 = hàng cuối Đỏ)
def iccs_to_move(text: str) -> int          # ValueError nếu sai định dạng
def sq_to_iccs(sq: int) -> str
def perft(game: Xiangqi, depth: int) -> int
```
- **Bàn:** `board: list[int]` 90 ô, `sq = rank*9 + file`. **Nước:** `int = from*90 + to` (hashable, CSV ghi int).
- FEN nhận cả `n/b` và `h/e` (mã/tượng); FEN cần đúng 10 hàng, mỗi bên đúng 1 tướng (không thì `ValueError`).
- `play(move)` chỉ nhận nước hợp lệ (assert nhẹ: đúng quân của bên đi, không ăn quân mình; **không** kiểm đầy đủ — lấy nước từ `legal_moves()`).
- `legal_moves()` trả list mới mỗi lần; **cache theo ply** (xóa khi `play`/`undo`) nên mỗi nút sinh nước 1 lần. Ván đã kết thúc → `[]`.
- Không ghi `stats` (không phải agent).

## Phụ thuộc
- Dùng: `core/game.py` (`P1`, `P2`, `DRAW`). Được dùng bởi: `experiments/p81_perft.py`, `tests/test_xiangqi*.py`; sau này P8.2/P8.3/P6.2.

## Thiết kế & quyết định
- **Hình nước tính trước lúc import** theo ô (không mailbox có viền): mã = (đích, ô chân); tượng = (đích, ô mắt) chỉ trong nửa sân mình; sĩ/tướng = đích trong cung; tốt theo bên + đã qua sông (Đỏ rank ≥ 5, Đen rank ≤ 4); xe/pháo = 4 tia theo thứ tự xa dần. Có thêm bảng ngược (ô nào mã/tốt tấn công được ô này) để dò chiếu.
- **Hợp lệ:** sinh nước giả hợp lệ → đi → kiểm tướng mình bị tấn công (dò ngược từ ô tướng: tia xe, **tướng đối mặt** coi như tia xe, pháo = đúng 1 ngòi, mã ngược theo chân, tốt) → hoàn tác. Nước tạo thế hai tướng đối mặt không có quân giữa bị loại; quân đứng một mình giữa hai tướng bị "ghim" ở cột đó.
- **Zobrist:** bảng 64-bit `[14 quân][90 ô]` + khóa lượt, seed hằng số (`random.Random(20261117)`) → `key()` (int, gồm lượt) tái lập giữa các lần chạy; cập nhật tăng dần trong `play/undo`; test so với `_compute_key()`.
- **Kết thúc (`winner()`):** (1) bên sắp đi **hết nước hợp lệ** (chiếu bí *hoặc* bí nước) → bên đó **thua**; (2) key hiện tại xuất hiện **lần thứ 3** → hòa; (3) `ply ≥ max_plies` (mặc định 300) → hòa. Thứ tự ưu tiên 1 > 2 > 3 (chiếu bí ở ply cuối vẫn là thua). `winner()` dùng `_has_legal_move()` dừng ở nước hợp lệ đầu tiên khi chưa có cache — để `MCTSAgent._tactics` (gọi `winner()` sau mỗi cặp nước) không phải sinh đủ nước.
- **Đếm lặp:** `_counts: dict[key → số lần]` cập nhật trong `play/undo`; `clone()` copy list + stack + dict (O(ply)).
- **`perft`** là hàm riêng, chỉ dùng luật đi nước: bỏ qua lặp thế, `max_plies`, và không đụng cache/đếm lặp; trả game về đúng trạng thái cũ.

## Giải thích cho báo cáo (mục 3.4 Cờ tướng)
- **Biểu diễn:** bàn 90 ô, quân có dấu; nước = (ô đi, ô đến) mã hóa một số nguyên; khóa Zobrist để nhận biết thế lặp và cho bảng chuyển vị.
- **Luật khó nhất** (hay sai): cản chân mã, cản mắt tượng, tượng/tốt theo sông, pháo ăn qua đúng một ngòi, tướng không được đối mặt, không tự đặt tướng vào thế bị chiếu. Hết nước đi (kể cả chưa bị chiếu) = thua — luật cờ tướng, khác cờ vua.
- **Kiểm chứng đúng luật bằng perft:** đếm số thế lá sau `d` nước từ một thế và so với số của người khác. Khớp ở thế khởi đầu (44 / 1 920 / 79 666 / 3 290 240) và 10 thế khó (thiết kế để bắt lỗi chiếu/né chiếu) ⇒ bộ sinh nước hợp lệ đúng với tới độ sâu 4.

## Nguồn perft tham chiếu
**Nguồn chính:** trang *Chinese Chess Perft Results*, chessprogramming.org — https://www.chessprogramming.org/Chinese_Chess_Perft_Results — **truy cập 2026-11-21** (lúc đó trang ghi "temporary, read-only recovery"; FEN và số liệu chép vào `gameai/experiments/p81_perft.py`, đã đối chiếu từng ký tự với trang). Ghi công theo tác giả + ngày bài CCC (Computer Chess Club) như trang ghi:
- Thế khởi đầu: Patrice Duhamel, Nguyen Pham — bài CCC "Perft for Xiangqi & Shogi", 2013-05-25.
- Thế 2: Maksim Korzh, Nguyen Pham — bài CCC "Chinese chess Xiangqi perft results", 2021-01-27.
- Thế 3–4 (trung cuộc) và 5–11 (thế nhiều nước chiếu/né chiếu, thiết kế để thử bộ sinh nước lười): Nguyen Pham — bài CCC "New Xiangqi (Chinese chess) Perft results", 2026-01-11.
- Trang nói số đếm tính ở **nút lá**; không nêu quy ước lặp/chiếu dai — perft chỉ đếm nước hợp lệ. (D-22 ghi nhầm "thế 2–11 của Korzh & Pham"; ghi công đúng như trên.)

## Test
- `tests/test_xiangqi.py` (51 test): từng loại quân (cản chân mã 4 hướng × cả quân mình/địch, cản mắt tượng, tượng không qua sông, sĩ/tướng trong cung, xe, pháo 0/1/2 ngòi và không ăn kề, tốt trước/sau sông cả hai bên), tướng đối mặt (ghim quân giữa, tướng không bước vào cột đối mặt), tự chiếu, phải giải chiếu, chiếu bằng pháo/mã/tốt, chiếu bí và bí nước = thua (cả hai bên), lặp lần 3 → hòa (lần 2 chưa), `max_plies` → hòa, chiếu bí ưu tiên hơn `max_plies`, hợp đồng `Game` (play/undo khôi phục key/winner/lượt/FEN, clone độc lập, candidate ⊆ legal), 8 ván ngẫu nhiên × 120 ply (key tăng dần = tính lại, không tự chiếu, không lộ mặt, vị trí tướng đúng, hoàn tác hết về FEN đầu), so legal với kiểm thủ công từng nước giả hợp lệ, FEN/ICCS round-trip + từ chối đầu vào sai.
- `tests/test_xiangqi_perft.py`: perft D1–3 cả 11 thế (mặc định, ~1 s); D4 11 thế đánh dấu `slow` (`python -m pytest tests/test_xiangqi_perft.py -m slow`, ~12 s); perft không đổi trạng thái; bỏ qua lặp/`max_plies`; CSV đã commit khớp số chuẩn.
- Chạy riêng: `python -m pytest tests/test_xiangqi.py tests/test_xiangqi_perft.py -q`.
- Script: `python -m gameai.experiments.p81_perft [--max-depth 4] [--out …]` → `results/tables/p81_perft.csv` (cột `position, depth, nodes, expected, ok, seconds, nodes_per_sec`); thoát mã 1 nếu có số lệch. Hiện **44/44** (11 thế × D1–4) khớp.

## Tốc độ
**Đo trên một máy** (máy dev của An, Windows, Python 3.13, cắm sạc, 2026-11-21) nên **phụ thuộc tốc độ máy**; chỉ dùng làm cỡ độ lớn. Nguồn số: `results/tables/p81_speed.csv` (cột `metric, value, unit, n_samples, note`) và `results/tables/p81_perft.csv`, đều do `python -m gameai.experiments.p81_perft` sinh; thời gian thay đổi giữa các lần chạy.
- **Cách tính nút/giây của perft:** `nodes_per_sec = nodes / seconds`, `nodes` = số **thế lá** ở độ sâu `d`, đo bằng `time.perf_counter()` quanh `perft()` (không tính nạp FEN). Perft **có bulk counting ở lá**: ở độ sâu 1 chỉ sinh nước hợp lệ rồi lấy `len(...)`, **không** `play`/`undo` từng nước lá. Vì vậy chỉ khoảng 1/40 số nút thực sự được đi/hoàn tác, và n/s **không** so trực tiếp được với perft không bulk counting.
- Perft (`p81_speed.csv`): thế khởi đầu D4 = **715 000** nút lá/s (3 290 240 nút); tổng cả 44 phép đo = **656 000** nút lá/s.
- `legal_moves()` (không cache, thế giữa ván ngẫu nhiên): **59,2 µs/lần**. `winner()` (không cache, bên đi còn nước, dừng ở nước hợp lệ đầu tiên): **8,8 µs/lần**.
- Rollout ngẫu nhiên đến hết ván (`play` + `winner` mỗi ply, 150 ván, seed cố định): **63,4 ván/s** = 17 033 ply/s; ván trung bình 268,7 ply, 107/150 ván hòa (chạm `max_plies = 300` hoặc lặp thế).
- **Ước tính MCTS:** rollout đến cuối ván ≈ 60 ván/s, **< 200 iter/s**. Rollout **cắt** `L` ply cho cận trên ≈ 17 000/`L` lần/s (L = 30 → ~570/s, chưa tính eval và duyệt cây). Quyết định có tối ưu hay không (rollout cắt + eval) đưa ra ở đầu P8.3, sau khi có eval thật.

## Hạn chế / TODO
- **Không có luật chiếu dai / đuổi dai** (luật cờ tướng châu Á xử thua bên chiếu dai) → bên đang thua có thể cầm hòa bằng chiếu dai (thế lặp lần 3 = hòa). Không có luật 60 nước không ăn quân, không có hòa do thiếu quân. Ghi vào báo cáo, không sửa (D-22).
- **TT + lặp thế:** `key()` không chứa lịch sử nhưng kết quả của thế phụ thuộc lịch sử (lặp lần 3 → hòa), nên giá trị lưu trong bảng chuyển vị của AB có thể sai khi cùng thế đạt qua lịch sử khác (graph history interaction). Không sửa, chỉ ghi nhận (D-22).
- `play` không kiểm đầy đủ tính hợp lệ của nước (chỉ assert nhẹ) — gọi với nước lấy từ `legal_moves()`.
- Perft độ sâu ≥ 5 chưa chạy (D5 ~133 triệu nút, ước ~3 phút với bulk counting).
