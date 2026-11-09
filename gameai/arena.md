# Arena — `gameai/arena.py`

> Mục tiêu của file này: agent/thành viên khác dùng được module **mà không cần đọc code**.
> Cập nhật cùng lúc với code.

**Trạng thái:** ✅ ổn định  ·  **Task:** P4.1 (D-13)  ·  **Cập nhật:** 2026-11-10

## Mục đích
Chơi một ván / một match giữa hai agent: đổi lượt, seed tất định, agent mới mỗi ván, ghi thời gian +
`stats` từng nước, xử lý agent lỗi. Chạy song song + ghi CSV + resume: xem `experiments/common.md`.

## Public API
```python
ERROR_TERMINATIONS = ("exception", "illegal_move", "mutated_game")

@dataclass
class MoveRecord:  ply: int; player: int; move: Move | None; time: float; stats: dict; side: str  # "A"/"B"
@dataclass
class GameRecord:
    winner: int                    # P1 / P2 / DRAW
    termination: str               # normal | max_moves | exception | illegal_move | mutated_game
    moves: list[MoveRecord]; opening: tuple[Move, ...]; error: str; error_player: int | None
    n_moves: int                   # property: số nước do agent đi (không tính khai cuộc)
    move_sequence: tuple           # property

def play_game(game, agent_x, agent_o, max_moves=None, opening=()) -> GameRecord
def derive_seed(pair_seed: int, tag: str) -> int
def random_opening_moves(game, n: int, rng: random.Random) -> list[Move]

@dataclass
class MatchGame:  game_id: str; pair_seed: int; a_is_x: bool; seed_a: int; seed_b: int; record: GameRecord
    a_player: int; result_a: float  # properties; result_a: thắng 1 / hòa 0.5 / thua 0
def game_id_for(pair_seed: int, a_is_x: bool) -> str               # "<seed>-AX" / "<seed>-BX"
def match_tasks(n_pairs: int, base_seed: int = 0) -> list[tuple[int, bool]]
def play_seeded_game(game_spec, spec_a, spec_b, pair_seed, a_is_x,
                     max_moves=None, random_opening=0) -> MatchGame
def play_match(game_spec, spec_a, spec_b, n_pairs, base_seed=0,
               max_moves=None, random_opening=0) -> list[MatchGame]  # tuần tự, trong bộ nhớ
```
- `play_game`: chơi từ trạng thái hiện tại của `game` (mutate). `agent_x` đi cho P1, `agent_o` cho P2.
  `time` mỗi nước do arena đo quanh `select_move` (perf_counter); `stats` là **bản sao** `agent.stats`.
  `max_moves` đếm nước do agent đi; chạm → hòa, `termination = "max_moves"`.
- **Agent lỗi → thua ngay:** ném exception (`move = None`, `error = "<Type>: <msg>"`, một dòng, ≤ 300 ký tự),
  trả nước không thuộc `legal_moves()` (`illegal_move`), hoặc làm `game.key()` khác đi (`mutated_game`).
  `winner = -player`, `error_player = player`; nước lỗi vẫn có `MoveRecord`.
- `play_seeded_game`: dựng game + hai agent **mới** từ spec (`agents/registry.md`). Seed agent A/B =
  `derive_seed(pair_seed, "A"/"B")`, giống nhau ở hai ván của cùng `pair_seed`. `random_opening > 0` → đặt
  chừng đó quân bằng `random_opening_moves` với rng `derive_seed(pair_seed, "opening")` (hai ván của một seed
  cùng khai cuộc). Lỗi khi **dựng** agent/game (hoặc khai cuộc không đặt được) được ném ra, không xử thua.
- `match_tasks` / `play_match`: ván thứ i có `pair_seed = base_seed + i`, mỗi seed 2 ván (A cầm X rồi B cầm X).
- `random_opening_moves`: luân phiên hai bên, chọn đều trong `candidate_moves()` (k-in-row: quanh quân đã có,
  bàn trống → tâm), bỏ nước làm ván kết thúc. Với 15×15, quân đầu luôn là tâm (`random_opening=1` không tạo
  khác biệt).

## Phụ thuộc
- Dùng: `agents/registry.py` (`AgentSpec`, `GameSpec`, `make_agent`, `make_game`), `core/game.py`
  (`P1`, `P2`, `DRAW`, `result_for`), `agents/base.py`.
- Được dùng bởi: `experiments/common.py` (`run_match`), sắp tới CLI (P4.3), GUI (P6.1), P3.3, E1–E6.

## Thiết kế & quyết định (D-13)
- **Agent mới mỗi ván** (qua spec, không truyền object) → không còn TT / cây / rng của ván trước; cùng
  `pair_seed` + `a_is_x` + ngân sách iteration → cùng ván (có test).
- **Seed** suy bằng sha256 (`"<pair_seed>:<tag>"` → 63 bit), không dùng `hash()` (phụ thuộc
  `PYTHONHASHSEED`). Quy ước "seed 0–9" của D-12 = `pair_seed`.
- **Đổi lượt có cặp:** cùng seed agent và cùng khai cuộc ở hai ván → khác biệt chỉ do lượt đi.
- **Cảnh báo ván trùng:** game không có yếu tố ngẫu nhiên. Nếu cả hai agent tất định (Minimax/AB không seed,
  hoặc `seeded: false`) và `random_opening = 0` thì mọi ván cùng lượt **giống hệt nhau** → n ván chỉ là 1 mẫu,
  khoảng tin cậy hẹp giả. Kiểm cột `distinct_games` của `summarize`; cần đa dạng thì bật `random_opening`.
- Kiểm `move in legal_moves()` và `game.key()` mỗi nước: O(n²) cho 15×15, nhỏ so với thời gian agent.
- Không có timeout cứng (không ngắt được agent trong cùng tiến trình); xem `time_max` trong CSV.

## Test
- `tests/test_arena.py` (cả registry): kết quả ván thường / thắng / hòa; stats là bản sao; `max_moves` → hòa;
  exception / nước sai / mutate → thua + ghi lỗi; chơi từ thế có sẵn; `game_id` + seed; ánh xạ A/B và
  `result_a`; cùng seed cùng ván (MCTS iteration); agent mới mỗi ván; mỗi agent dùng đúng seed của mình;
  khai cuộc tất định, quanh tâm, không kết thúc ván, hai ván cùng seed cùng khai cuộc; lỗi dựng agent ném ra;
  `play_match` đổi lượt. Agent lỗi giả ở `tests/arena_helpers.py`.
- Chạy: `python -m pytest tests/test_arena.py -q` (~10 s).

## Hạn chế / TODO
- Không có timeout cứng mỗi nước.
- `random_opening` chọn đều trong candidate, không theo "khai cuộc cân bằng" nào.
