"""Arena: chơi một ván / một match giữa hai agent, đổi lượt, seed tất định (P4.1, D-13).

Phần chạy song song + CSV + resume nằm ở `experiments/common.py`.
"""

from __future__ import annotations

import hashlib
import random
import time
from dataclasses import dataclass, field
from typing import Any

from gameai.agents.base import Agent
from gameai.agents.registry import AgentSpec, GameSpec, make_agent, make_game
from gameai.core.game import DRAW, P1, P2, Game, Move, result_for

ERROR_TERMINATIONS = ("exception", "illegal_move", "mutated_game")
_ERROR_MAX_LEN = 300


@dataclass
class MoveRecord:
    """Một nước: `time` do arena đo quanh `select_move`; `stats` là bản sao `agent.stats`."""

    ply: int  # đếm từ 0, chỉ các nước do agent đi (không tính khai cuộc)
    player: int  # P1 / P2
    move: Move | None  # None nếu agent ném exception
    time: float
    stats: dict[str, Any]
    side: str = ""  # "A" / "B" (điền bởi play_seeded_game)


@dataclass
class GameRecord:
    winner: int  # P1 / P2 / DRAW
    termination: str  # normal | max_moves | exception | illegal_move | mutated_game
    moves: list[MoveRecord] = field(default_factory=list)
    opening: tuple[Move, ...] = ()
    error: str = ""
    error_player: int | None = None

    @property
    def n_moves(self) -> int:
        return len(self.moves)

    @property
    def move_sequence(self) -> tuple[Move | None, ...]:
        return tuple(m.move for m in self.moves)


def _short_error(e: BaseException) -> str:
    msg = f"{type(e).__name__}: {e}".replace("\r", " ").replace("\n", " | ")
    return msg[:_ERROR_MAX_LEN]


def play_game(
    game: Game,
    agent_x: Agent,
    agent_o: Agent,
    max_moves: int | None = None,
    opening: tuple[Move, ...] = (),
) -> GameRecord:
    """Chơi từ trạng thái hiện tại của `game` tới khi kết thúc (mutate `game`).

    `agent_x` đi cho P1, `agent_o` cho P2. Agent ném exception / trả nước không hợp lệ / làm đổi
    `game.key()` → thua ngay (`termination` tương ứng). Chạm `max_moves` (số nước do agent đi)
    → hòa.
    `opening` chỉ để ghi vào record (các nước đã có trên bàn trước khi gọi).
    """
    agents = {P1: agent_x, P2: agent_o}
    rec = GameRecord(winner=DRAW, termination="normal", opening=tuple(opening))
    while not game.is_terminal():
        if max_moves is not None and rec.n_moves >= max_moves:
            rec.termination = "max_moves"
            return rec
        player = game.current_player()
        agent = agents[player]
        key_before = game.key()
        move: Move | None = None
        error: BaseException | None = None
        t0 = time.perf_counter()
        try:
            move = agent.select_move(game)
        except Exception as e:  # noqa: BLE001 — lỗi agent không được làm sập batch
            error = e
        elapsed = time.perf_counter() - t0
        rec.moves.append(MoveRecord(rec.n_moves, player, move, elapsed, dict(agent.stats)))
        if error is not None:
            termination, msg = "exception", _short_error(error)
        elif game.key() != key_before:
            termination, msg = "mutated_game", "agent làm thay đổi game"
        elif move not in game.legal_moves():
            termination, msg = "illegal_move", f"nước không hợp lệ: {move!r}"[:_ERROR_MAX_LEN]
        else:
            game.play(move)
            continue
        rec.termination, rec.error, rec.error_player = termination, msg, player
        rec.winner = -player
        return rec
    rec.winner = game.winner()
    return rec


def derive_seed(pair_seed: int, tag: str) -> int:
    """Seed con tất định từ `pair_seed` + `tag`
    (sha256 → 63 bit, không phụ thuộc PYTHONHASHSEED).
    """
    h = hashlib.sha256(f"{pair_seed}:{tag}".encode()).digest()
    return int.from_bytes(h[:8], "big") >> 1


def random_opening_moves(game: Game, n: int, rng: random.Random) -> list[Move]:
    """Đặt `n` quân ngẫu nhiên (luân phiên hai bên) trong `candidate_moves()`; không kết thúc ván.

    k-in-row: candidate = quanh quân đã có, bàn trống → tâm, nên khai cuộc nằm quanh tâm.
    Mutate `game`; trả về các nước đã đặt. `ValueError` nếu không đặt được mà ván chưa kết thúc.
    """
    placed: list[Move] = []
    for _ in range(n):
        cands = list(game.candidate_moves())
        rng.shuffle(cands)
        for m in cands:
            game.play(m)
            if not game.is_terminal():
                placed.append(m)
                break
            game.undo()
        else:
            raise ValueError(f"không đặt được quân khai cuộc thứ {len(placed) + 1}")
    return placed


@dataclass
class MatchGame:
    """Một ván trong match: định danh, seed và record."""

    game_id: str
    pair_seed: int
    a_is_x: bool
    seed_a: int
    seed_b: int
    record: GameRecord

    @property
    def a_player(self) -> int:
        return P1 if self.a_is_x else P2

    @property
    def result_a(self) -> float:
        """Điểm của A: thắng 1, hòa 0.5, thua 0."""
        return result_for(self.record.winner, self.a_player)


def game_id_for(pair_seed: int, a_is_x: bool) -> str:
    return f"{pair_seed}-{'AX' if a_is_x else 'BX'}"


def play_seeded_game(
    game_spec: GameSpec,
    spec_a: AgentSpec,
    spec_b: AgentSpec,
    pair_seed: int,
    a_is_x: bool,
    max_moves: int | None = None,
    random_opening: int = 0,
) -> MatchGame:
    """Dựng game + hai agent **mới** từ spec, seed suy từ `pair_seed`, rồi chơi một ván.

    Seed agent: `derive_seed(pair_seed, "A"/"B")` (giống nhau ở hai ván của cùng `pair_seed`).
    Khai cuộc: `random_opening` quân từ `derive_seed(pair_seed, "opening")` (0 = tắt).
    Lỗi khi dựng agent/game được ném ra (không xử thua).
    """
    seed_a, seed_b = derive_seed(pair_seed, "A"), derive_seed(pair_seed, "B")
    game = make_game(game_spec)
    agent_a = make_agent(spec_a, seed_a)
    agent_b = make_agent(spec_b, seed_b)
    opening: list[Move] = []
    if random_opening > 0:
        rng = random.Random(derive_seed(pair_seed, "opening"))
        opening = random_opening_moves(game, random_opening, rng)
    agent_x, agent_o = (agent_a, agent_b) if a_is_x else (agent_b, agent_a)
    rec = play_game(game, agent_x, agent_o, max_moves=max_moves, opening=tuple(opening))
    a_player = P1 if a_is_x else P2
    for m in rec.moves:
        m.side = "A" if m.player == a_player else "B"
    return MatchGame(game_id_for(pair_seed, a_is_x), pair_seed, a_is_x, seed_a, seed_b, rec)


def match_tasks(n_pairs: int, base_seed: int = 0) -> list[tuple[int, bool]]:
    """Danh sách (pair_seed, a_is_x): mỗi seed 2 ván, A cầm X trước."""
    return [(base_seed + i, a_is_x) for i in range(n_pairs) for a_is_x in (True, False)]


def play_match(
    game_spec: GameSpec,
    spec_a: AgentSpec,
    spec_b: AgentSpec,
    n_pairs: int,
    base_seed: int = 0,
    max_moves: int | None = None,
    random_opening: int = 0,
) -> list[MatchGame]:
    """Chơi tuần tự `2 * n_pairs` ván trong bộ nhớ (không ghi file).

    Bản song song + CSV: `experiments.common.run_match`.
    """
    return [
        play_seeded_game(game_spec, spec_a, spec_b, s, a_is_x, max_moves, random_opening)
        for s, a_is_x in match_tasks(n_pairs, base_seed)
    ]
