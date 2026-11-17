"""Controller GUI: trạng thái ván, lượt, AI chạy trong thread, hàng đợi kết quả (không pygame)."""

from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass, field
from typing import Any

from gameai.agents.base import Agent
from gameai.agents.registry import AgentSpec, make_agent, make_game
from gameai.arena import derive_seed
from gameai.core.game import DRAW, P1, P2, Game, Move
from gameai.gui.presets import Preset

SIDE_TAG = {P1: "X", P2: "O"}
TACTIC_SHORTCUT = (1, 2)  # mcts.TACTIC_WIN, TACTIC_BLOCK: đi thẳng, không có cây


@dataclass
class MoveInfo:
    """Một nước đã đi trong ván (của người hoặc AI)."""

    move: Move
    player: int
    by_ai: bool
    time: float = 0.0  # giây: AI = quanh select_move trong thread; người = từ lúc tới lượt
    iterations: int | None = None
    nodes: int | None = None
    tactic: int = 0  # 1/2 = đi thẳng nhờ tactics (không có root_stats)
    root_stats: list[tuple[Move, float, int, float]] = field(default_factory=list)

    @property
    def is_tactic(self) -> bool:
        return self.tactic in TACTIC_SHORTCUT


@dataclass
class AIResult:
    """Kết quả thread AI gửi về; chỉ áp dụng nếu `game_id` và `ply` còn khớp."""

    game_id: int
    ply: int
    player: int
    move: Move | None
    stats: dict[str, Any]
    root_stats: list[tuple[Move, float, int, float]]
    time: float
    error: str | None = None


def _think(agent: Agent, game: Game, game_id: int, ply: int, out: queue.Queue) -> None:
    """Thân thread: tìm nước trên bản clone, gửi kết quả vào hàng đợi."""
    player = game.current_player()
    t0 = time.perf_counter()
    try:
        move = agent.select_move(game)
        root = agent.last_root_stats() if hasattr(agent, "last_root_stats") else []
        out.put(AIResult(game_id, ply, player, move, dict(agent.stats), list(root),
                         time.perf_counter() - t0))  # fmt: skip
    except Exception as exc:  # noqa: BLE001 — lỗi agent hiện lên GUI, không làm sập app
        out.put(AIResult(game_id, ply, player, None, {}, [], time.perf_counter() - t0,
                         f"{type(exc).__name__}: {exc}"))  # fmt: skip


class GameController:
    """Điều phối một ván: người đi qua `submit_human_move`, AI nghĩ trong thread trên `clone()`."""

    def __init__(self, preset: Preset, seed: int = 0, delay: float | None = None) -> None:
        self.preset = preset
        self.seed = seed
        self.delay = preset.delay if delay is None else delay
        self.paused = False
        self.game_id = 0
        self._results: queue.Queue[AIResult] = queue.Queue()
        self.new_game()

    # ------------------------------------------------------------ ván
    def new_game(self, preset: Preset | None = None, seed: int | None = None) -> None:
        """Bắt đầu ván mới; kết quả AI của ván cũ (nếu còn đang nghĩ) sẽ bị bỏ."""
        if preset is not None:
            self.preset = preset
        if seed is not None:
            self.seed = seed
        self.game_id += 1
        self.game: Game = make_game(self.preset.game)
        self.specs: dict[int, AgentSpec | None] = {P1: self.preset.x, P2: self.preset.o}
        self._make_agents()
        self.history: list[MoveInfo] = []
        self.error: str | None = None
        self.resigned: int | None = None  # bên đã đầu hàng
        self.thinking = False
        self._last_move_at = time.monotonic()

    def _make_agents(self) -> None:
        """Agent mới cho mỗi bên AI (seed suy từ `seed` + bên)."""
        self.agents: dict[int, Agent | None] = {
            p: None if s is None else make_agent(s, derive_seed(self.seed, SIDE_TAG[p]))
            for p, s in self.specs.items()
        }

    @property
    def ply(self) -> int:
        return len(self.history)

    @property
    def last(self) -> MoveInfo | None:
        return self.history[-1] if self.history else None

    @property
    def last_ai(self) -> MoveInfo | None:
        for info in reversed(self.history):
            if info.by_ai:
                return info
        return None

    @property
    def over(self) -> bool:
        return self.error is not None or self.resigned is not None or self.game.is_terminal()

    @property
    def winner(self) -> int | None:
        """Người thắng theo luật trên bàn (= `game.winner()`, không tính đầu hàng)."""
        return self.game.winner()

    @property
    def outcome(self) -> int | None:
        """Kết quả ván có tính đầu hàng: P1/P2/DRAW; None nếu chưa xong hoặc dừng vì lỗi."""
        if self.resigned is not None:
            return -self.resigned
        return self.game.winner()

    @property
    def human_sides(self) -> list[int]:
        return [p for p in (P1, P2) if self.agents[p] is None]

    def is_human_turn(self) -> bool:
        return not self.over and self.agents[self.game.current_player()] is None

    def is_ai_turn(self) -> bool:
        return not self.over and self.agents[self.game.current_player()] is not None

    @property
    def ai_vs_ai(self) -> bool:
        return all(a is not None for a in self.agents.values())

    # ------------------------------------------------------------ nước đi
    def submit_human_move(self, move: Move) -> bool:
        """Người đi `move`. False (không đổi gì) nếu sai lượt / AI đang nghĩ / nước không hợp lệ."""
        if self.thinking or not self.is_human_turn() or move not in self.game.legal_moves():
            return False
        spent = time.monotonic() - self._last_move_at
        self._apply(MoveInfo(move, self.game.current_player(), by_ai=False, time=spent))
        return True

    # ------------------------------------------------------------ đi lại / đầu hàng
    @property
    def can_undo(self) -> bool:
        """Có người, AI không đang nghĩ, chưa đầu hàng / lỗi, còn ít nhất 1 nước của người."""
        if self.ai_vs_ai or self.thinking or self.resigned is not None or self.error is not None:
            return False
        return any(not m.by_ai for m in self.history)

    def undo(self) -> bool:
        """Lùi tới khi bỏ được đúng 1 nước của người (người vs AI: 2 ply; 2 người: 1 ply).

        Khóa khi AI đang nghĩ (không hủy được thread). `game_id += 1` + agent mới → kết quả
        thread cũ (nếu còn) bị bỏ và thread mới không dùng chung agent có trạng thái.
        """
        if not self.can_undo:
            return False
        while True:
            info = self.history.pop()
            self.game.undo()
            if not info.by_ai:
                break
        self.game_id += 1
        self._make_agents()
        self._last_move_at = time.monotonic()
        return True

    @property
    def can_resign(self) -> bool:
        return not self.over and not self.ai_vs_ai

    def resign_side(self) -> int | None:
        """Bên sẽ đầu hàng khi bấm nút: người vs AI = người; 2 người = bên đang tới lượt."""
        if not self.can_resign:
            return None
        humans = self.human_sides
        return humans[0] if len(humans) == 1 else self.game.current_player()

    def resign(self, player: int | None = None) -> bool:
        """`player` (mặc định `resign_side()`) đầu hàng; kết quả AI đang nghĩ bị bỏ."""
        side = self.resign_side() if player is None else player
        if side is None or not self.can_resign or self.agents[side] is not None:
            return False
        self.resigned = side
        self.game_id += 1
        self.thinking = False
        return True

    def update(self, now: float | None = None) -> None:
        """Gọi mỗi frame: nhận kết quả AI, rồi khởi thread AI nếu tới lượt AI."""
        now = time.monotonic() if now is None else now
        while True:
            try:
                res = self._results.get_nowait()
            except queue.Empty:
                break
            self._receive(res)
        if self.is_ai_turn() and not self.thinking and not self.paused:
            if now - self._last_move_at >= self.delay:
                self._start_ai()

    def _start_ai(self) -> None:
        agent = self.agents[self.game.current_player()]
        assert agent is not None
        self.thinking = True
        threading.Thread(
            target=_think,
            args=(agent, self.game.clone(), self.game_id, self.ply, self._results),
            daemon=True,
        ).start()

    def _receive(self, res: AIResult) -> None:
        if res.game_id != self.game_id or res.ply != self.ply or self.over:
            return  # kết quả của ván cũ / lượt cũ / ván đã dừng → bỏ
        self.thinking = False
        if res.error is not None:
            self.error = f"AI lỗi: {res.error}"
            return
        if res.move not in self.game.legal_moves():
            self.error = f"AI đi nước không hợp lệ: {res.move!r}"
            return
        st = res.stats
        info = MoveInfo(res.move, res.player, by_ai=True, time=res.time,
                        iterations=st.get("iterations"), nodes=st.get("nodes"),
                        tactic=int(st.get("tactic", 0)), root_stats=res.root_stats)  # fmt: skip
        self._apply(info)

    def _apply(self, info: MoveInfo) -> None:
        assert not self.thinking, "không mutate ván khi AI đang nghĩ"
        self.game.play(info.move)
        self.history.append(info)
        self._last_move_at = time.monotonic()

    # ------------------------------------------------------------ tiện ích
    def result_text(self) -> str | None:
        """'X thắng' / 'O thắng' / 'Hòa' / 'X đầu hàng — O thắng' / lỗi; None nếu chưa kết thúc."""
        if self.error is not None:
            return self.error
        if self.resigned is not None:
            return f"{SIDE_TAG[self.resigned]} đầu hàng — {SIDE_TAG[-self.resigned]} thắng"
        w = self.game.winner()
        if w is None:
            return None
        return "Hòa" if w == DRAW else f"{SIDE_TAG[w]} thắng"

    def side_time(self, player: int) -> float:
        """Tổng giây đã dùng của một bên (các nước trong lịch sử)."""
        return sum(m.time for m in self.history if m.player == player)

    def position_at(self, ply: int) -> Game:
        """Thế sau `ply` nước đầu (0 … `self.ply`): ván mới + đi lại; không đụng `self.game`."""
        if not 0 <= ply <= self.ply:
            raise ValueError(f"ply ngoài khoảng 0..{self.ply}: {ply}")
        game = make_game(self.preset.game)
        for info in self.history[:ply]:
            game.play(info.move)
        return game

    def run_until_idle(self, timeout: float = 60.0, poll: float = 0.002) -> None:
        """Gọi `update` tới khi ván hết / tới lượt người / đang pause (cho test, autoplay)."""
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            self.update()
            if self.over or (not self.thinking and (self.is_human_turn() or self.paused)):
                return
            time.sleep(poll)
        raise TimeoutError("AI chưa xong trong thời gian chờ")
