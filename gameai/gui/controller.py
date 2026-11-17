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
    time: float = 0.0  # giây, đo quanh select_move trong thread
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
        self.agents: dict[int, Agent | None] = {
            p: None if s is None else make_agent(s, derive_seed(self.seed, SIDE_TAG[p]))
            for p, s in self.specs.items()
        }
        self.history: list[MoveInfo] = []
        self.error: str | None = None
        self.thinking = False
        self._last_move_at = time.monotonic()

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
        return self.error is not None or self.game.is_terminal()

    @property
    def winner(self) -> int | None:
        return self.game.winner()

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
        self._apply(MoveInfo(move, self.game.current_player(), by_ai=False))
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
        if res.game_id != self.game_id or res.ply != self.ply:
            return  # kết quả của ván cũ / lượt cũ → bỏ
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
        """'X thắng' / 'O thắng' / 'Hòa' / thông báo lỗi; None nếu ván chưa kết thúc."""
        if self.error is not None:
            return self.error
        w = self.game.winner()
        if w is None:
            return None
        return "Hòa" if w == DRAW else f"{SIDE_TAG[w]} thắng"

    def run_until_idle(self, timeout: float = 60.0, poll: float = 0.002) -> None:
        """Gọi `update` tới khi ván hết / tới lượt người / đang pause (cho test, autoplay)."""
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            self.update()
            if self.over or (not self.thinking and (self.is_human_turn() or self.paused)):
                return
            time.sleep(poll)
        raise TimeoutError("AI chưa xong trong thời gian chờ")
