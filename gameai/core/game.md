# Game interface — `gameai/core/game.py`

> Mục tiêu của file này: agent/thành viên khác dùng được module **mà không cần đọc code**.
> Cập nhật cùng lúc với code.

**Trạng thái:** ✅ ổn định  ·  **Task:** P1.1  ·  **Cập nhật:** 2026-10-28

## Mục đích
Định nghĩa hợp đồng `Game` mà mọi agent (Random, Greedy, Minimax, Alpha-Beta, MCTS) chỉ dựa vào,
cùng hằng số người chơi và hàm `result_for`. Nhờ đó k-in-a-row và cờ tướng (P8) cắm vào được
mà không phải sửa agent. Không chứa luật chơi nào.

## Public API
```python
Move: TypeAlias = Hashable          # KInRow: int (index r*n+c). Cờ tướng: quyết định ở P8
P1, P2, DRAW = 1, -1, 0             # người chơi đi trước = P1; hòa = DRAW

@runtime_checkable
class Game(Protocol):
    def current_player(self) -> int            # P1 hoặc P2
    def legal_moves(self) -> list[Move]
    def candidate_moves(self) -> list[Move]
    def play(self, move: Move) -> None         # mutate tại chỗ
    def undo(self) -> None                     # hoàn tác đúng 1 nước gần nhất
    def is_terminal(self) -> bool
    def winner(self) -> int | None             # P1 / P2 / DRAW; None = chưa kết thúc
    def clone(self) -> "Game"
    def key(self) -> Hashable
    def render(self) -> str

def result_for(winner: int | None, player: int) -> float   # 1.0 thắng / 0.5 hòa / 0.0 thua
```

### Hợp đồng từng hàm (P1.2 và P8.1 phải test các điểm này)
- `legal_moves()` trả `[]` khi `is_terminal()`.
- `candidate_moves()` là **tập con** của `legal_moves()`, **không rỗng** khi chưa kết thúc.
  Mặc định (game nhỏ) bằng `legal_moves()`.
- `play(move)`: nước không hợp lệ chỉ `assert`, **không validate** ở đường nóng.
- `undo()` đảo đúng `play()` gần nhất: khôi phục bàn, `current_player()`, `winner()`, `key()`.
- `clone()` **độc lập hoàn toàn**: sửa bản clone không ảnh hưởng bản gốc.
- `key()` phải phân biệt cả **lượt đi** (`current_player`), không chỉ vị trí quân.
- `winner()` chỉ trả `None` khi chưa kết thúc; `DRAW = 0` là hòa.
- `Move` phải hashable (dùng làm khóa con của node MCTS và transposition table).
  Agent không được giả định kiểu cụ thể của `Move`.

### `result_for(winner, player)`
Hàm thuần, điểm của ván đã xong theo góc nhìn `player`. Ném `ValueError` nếu `winner is None`.
MCTS (tính `W`) và arena dùng **chung** hàm này để không sai dấu. Với `W` của node: gọi với
`player` = người vừa đi vào node.

## Phụ thuộc
- Dùng: chỉ thư viện chuẩn (`typing`, `collections.abc`).
- Được dùng bởi: `games/kinrow.py`, mọi file trong `agents/`, `arena.py`, `experiments/`.

## Thiết kế & quyết định
- Tên trung lập `P1`/`P2` trong core. **Mỗi game tự đặt alias riêng:** KInRow `X = P1`, `O = P2`;
  cờ tướng `RED = P1`, `BLACK = P2`. Alias nằm trong module của game, không nằm ở core.
- `@runtime_checkable` chỉ để **dùng trong test**. Nó chỉ kiểm tra có đủ tên hàm, không kiểm tra
  chữ ký. **Không dùng `isinstance(x, Game)` ở đường nóng.**
- `Move = Hashable` thay vì `int` để cờ tướng dùng được `(from, to)` mà không phải mã hóa.
  Xem `docs/DECISIONS.md` D-5.

## Test
- File: `tests/test_game_interface.py` — hằng số; Protocol nhận game đủ hàm và loại game thiếu hàm;
  agent giả chạy hết ván chỉ qua interface; `clone` độc lập, `undo` khôi phục `key`;
  `result_for` đủ 6 tổ hợp (thắng/thua/hòa) và lỗi khi `winner is None`.
- Chạy riêng: `python -m pytest tests/test_game_interface.py -q`

## Hạn chế / TODO
- Protocol không ép được các điều kiện hợp đồng ở trên; từng game phải tự test (P1.2, P8.1).
