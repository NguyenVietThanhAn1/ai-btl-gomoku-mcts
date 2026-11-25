"""AlphaBetaAgent: minimax với cắt tỉa alpha-beta, tùy chọn move ordering, cộng dồn delta, TT."""

from __future__ import annotations

import math
import random
import time
from collections.abc import Callable, Sequence

from gameai.agents.base import Agent
from gameai.agents.minimax import WIN_SCORE, EvalFn, terminal_score
from gameai.core.game import Game, Move

MoveFn = Callable[[Game, Move], float]
# Hook ở gốc: (nước đi ngay | None, tập nước cho gốc | None). Vd. `kinrow_vcf.make_root_hook`.
RootHook = Callable[[Game], tuple[Move | None, list[Move] | None]]

EXACT, LOWER, UPPER = 0, 1, 2
TT_MODES = ("exact", "deep")
TT_MAX_ENTRIES = 2_000_000  # tt_mode="deep": đầy thì xóa hết (đơn giản, tránh phình RAM)
_CHECK_MASK = 31  # kiểm thời gian mỗi 32 nút (mỗi nút 15×15 có ordering tốn cỡ ms)
_INF = float("inf")
_MATE = WIN_SCORE // 2  # |v| > _MATE ⇒ điểm thắng/thua thật (phụ thuộc ply)


def _to_tt(v: float, ply: int) -> float:
    """Điểm thắng/thua → khoảng cách tính từ nút hiện tại (độc lập với ply của nút)."""
    if v > _MATE:
        return v + ply
    if v < -_MATE:
        return v - ply
    return v


def _from_tt(v: float, ply: int) -> float:
    if v > _MATE:
        return v - ply
    if v < -_MATE:
        return v + ply
    return v


class _Timeout(Exception):
    """Hết `time_limit` giữa chừng một vòng ID — vòng dở dang bị bỏ, không ghi TT nút dở dang."""


def _norm_top_k(top_k: int | Sequence[int] | None) -> tuple[int, ...] | None:
    """None → None; int → (k,); dãy → tuple. Mọi k phải là số nguyên ≥ 1."""
    if top_k is None:
        return None
    if isinstance(top_k, (int, float)):
        ks: tuple = (top_k,)
    else:
        ks = tuple(top_k)
    if not ks or any(not isinstance(k, int) or isinstance(k, bool) or k < 1 for k in ks):
        raise ValueError("top_k phải là int ≥ 1 hoặc dãy int ≥ 1")
    return ks


class AlphaBetaAgent(Agent):
    """Alpha-Beta dạng max/min tường minh (MAX = người đi ở gốc), cùng giá trị gốc với Minimax.

    - `order_fn(game, move)`: sắp nước giảm dần trước khi duyệt (vd. `kinrow_eval.move_score`).
    - `delta_fn(game, move)`: thay đổi lượng giá theo góc nhìn người đi, tính *trước* `play`
      (vd. `kinrow_eval.delta_eval`); lá = `eval_fn(gốc)` (hoặc 0) + tổng delta dọc nhánh.
    - `use_tt`: bảng chuyển vị theo `game.key()`, xóa ở đầu mỗi lần tìm.
    - `top_k` (P6.4, mặc định None = tắt): sau khi sắp theo `order_fn`, chỉ duyệt k nước đầu —
      **cắt tỉa xấp xỉ** (mất tính đúng của giá trị minimax). `int` = mọi ply; dãy = k theo ply
      (gốc = ply 0).
    - `root_hook` (P6.4, mặc định None): gọi ở gốc trước khi tìm; trả nước đi ngay hoặc tập nước
      cho gốc.
    - `time_limit` (P6.4, giây, mặc định None = tắt): iterative deepening độ sâu 1, 2, … tới
      `depth` (= độ sâu tối đa, bắt buộc có); trả nước của **độ sâu hoàn tất gần nhất** (độ sâu 1
      luôn xong).
    - `tt_mode` (P6.4): "exact" (mặc định, như cũ) hoặc "deep" (cần `use_tt` và `depth`): khóa TT
      chỉ theo thế, dùng lại entry có độ sâu còn lại ≥ cần, nước tốt nhất của entry đi trước.
    """

    def __init__(
        self,
        depth: int | None = None,
        eval_fn: EvalFn | None = None,
        use_candidates: bool = True,
        seed: int | None = None,
        order_fn: MoveFn | None = None,
        delta_fn: MoveFn | None = None,
        use_tt: bool = False,
        top_k: int | Sequence[int] | None = None,
        root_hook: RootHook | None = None,
        time_limit: float | None = None,
        tt_mode: str = "exact",
    ) -> None:
        super().__init__()
        if depth is not None and depth < 1:
            raise ValueError("depth phải ≥ 1 hoặc None")
        if time_limit is not None:
            if time_limit <= 0:
                raise ValueError("time_limit phải > 0")
            if depth is None:
                raise ValueError("time_limit cần depth (độ sâu tối đa của iterative deepening)")
        if tt_mode not in TT_MODES:
            raise ValueError(f"tt_mode phải thuộc {TT_MODES}")
        if tt_mode == "deep" and (not use_tt or depth is None):
            raise ValueError('tt_mode="deep" cần use_tt=True và depth')
        self.time_limit = time_limit
        self.tt_mode = tt_mode
        self._deep = tt_mode == "deep"
        self._clock = time.perf_counter  # tiêm được trong test
        self._deadline: float | None = None
        self._depth_now: int | None = depth
        self._preserve_tt = False  # chỉ dùng trong test: không xóa TT ở đầu `search`
        self._top_k = _norm_top_k(top_k)
        if self._top_k is not None and order_fn is None:
            raise ValueError("top_k cần order_fn (chọn k nước đầu theo điểm sắp xếp)")
        self.root_hook = root_hook
        self.depth = depth
        self.eval_fn = eval_fn
        self.use_candidates = use_candidates
        self.rng = random.Random(seed) if seed is not None else None
        self.order_fn = order_fn
        self.delta_fn = delta_fn
        self.use_tt = use_tt
        self._tt: dict = {}
        self._nodes = 0
        self._cutoffs = 0
        self._tt_hits = 0
        self._root = 0

    def _moves(self, game: Game, ply: int = 1) -> list[Move]:
        moves = game.candidate_moves() if self.use_candidates else game.legal_moves()
        if self.order_fn is not None:
            moves = sorted(moves, key=lambda m: self.order_fn(game, m), reverse=True)
        if self._top_k is not None:
            moves = moves[: self._top_k[min(ply, len(self._top_k) - 1)]]
        return moves

    def search(self, game: Game) -> tuple[Move, float]:
        """Trả (nước tốt nhất, giá trị gốc theo góc nhìn người đang đi). Cập nhật `stats`."""
        assert not game.is_terminal(), "search gọi trên ván đã kết thúc"
        t0 = self._clock()
        self._root = game.current_player()
        self._nodes = 1  # nút gốc
        self._cutoffs = 0
        self._tt_hits = 0
        if not self._preserve_tt:
            self._tt = {}
        hook_moves: list[Move] | None = None
        if self.root_hook is not None:
            forced, hook_moves = self.root_hook(game)
            if forced is not None:  # đi ngay, không tìm (value = NaN như MCTS đi tắt)
                self._write_stats(t0, math.nan)
                self.stats["root_hook"] = 1
                return forced, math.nan
        need_score = self.depth is not None
        base = self.eval_fn(game, self._root) if need_score and self.eval_fn else 0

        moves = game.candidate_moves() if self.use_candidates else game.legal_moves()
        if self.rng is not None:
            self.rng.shuffle(moves)  # tie-break ngẫu nhiên; sort ổn định giữ thứ tự trong nhóm bằng
        if hook_moves:  # giữ thứ tự gốc; rỗng sau giao → dùng nguyên tập hook trả về
            allowed = set(hook_moves)
            moves = [m for m in moves if m in allowed] or list(hook_moves)
        if self.order_fn is not None:
            moves.sort(key=lambda m: self.order_fn(game, m), reverse=True)
        if self._top_k is not None:
            moves = moves[: self._top_k[0]]

        if self.time_limit is None:
            self._depth_now, self._deadline = self.depth, None
            best_move, best = self._root_search(game, moves, base)
            self._write_stats(t0, best)
            return best_move, best
        return self._iterative(game, moves, base, t0)

    def _root_search(self, game: Game, moves: list[Move], base: float) -> tuple[Move, float]:
        """Một lần duyệt gốc ở độ sâu `self._depth_now` (thứ tự `moves` giữ nguyên)."""
        need_score = self._depth_now is not None
        best_move, best, alpha = moves[0], -_INF, -_INF
        for move in moves:
            score = base + self.delta_fn(game, move) if need_score and self.delta_fn else base
            game.play(move)
            v = self._alphabeta(game, 1, alpha, _INF, score)
            game.undo()
            if v > best:
                best, best_move = v, move
            alpha = max(alpha, v)
        return best_move, best

    def _iterative(
        self, game: Game, moves: list[Move], base: float, t0: float
    ) -> tuple[Move, float]:
        """Iterative deepening tới `depth` hoặc hết `time_limit`; vòng dở dang bị bỏ.

        Gốc giữ nguyên thứ tự `moves` ở mọi vòng nên khi không `top_k` và không hết giờ, kết quả
        trùng AB depth cố định (cùng nước, cùng giá trị) ở chế độ TT "exact"."""
        assert self.depth is not None and self.time_limit is not None
        work = game.clone()  # bị hủy nếu hết giờ giữa chừng (không cần undo)
        deadline = t0 + self.time_limit
        best_move, best, reached, timed_out = moves[0], 0.0, 0, False
        for d in range(1, self.depth + 1):
            self._depth_now = d
            self._deadline = None if d == 1 else deadline  # độ sâu 1 luôn hoàn tất
            try:
                best_move, best = self._root_search(work, moves, base)
            except _Timeout:
                timed_out = True
                break
            finally:
                self._deadline = None
            reached = d
            if self._clock() >= deadline:
                break
        self._write_stats(t0, best)
        self.stats["depth_reached"] = reached
        self.stats["timed_out"] = int(timed_out or reached < self.depth)
        self.stats["tt_size"] = len(self._tt)
        return best_move, best

    def _write_stats(self, t0: float, value: float) -> None:
        self.stats["nodes"] = self._nodes
        self.stats["iterations"] = 0
        self.stats["time"] = self._clock() - t0
        self.stats["value"] = value
        self.stats["cutoffs"] = self._cutoffs
        self.stats["tt_hits"] = self._tt_hits

    def value(self, game: Game) -> float:
        """Giá trị gốc (bằng `MinimaxAgent.value` với cùng depth/eval)."""
        return self.search(game)[1]

    def _select_move(self, game: Game) -> Move:
        return self.search(game)[0]

    def _alphabeta(self, game: Game, ply: int, alpha: float, beta: float, score: float) -> float:
        """Giá trị nút theo góc nhìn gốc (fail-soft). `score` = lượng giá cộng dồn tới nút này."""
        self._nodes += 1
        if self._deadline is not None and not self._nodes & _CHECK_MASK:
            if self._clock() >= self._deadline:
                raise _Timeout
        winner = game.winner()
        if winner is not None:
            return terminal_score(winner, self._root, ply)
        depth = self._depth_now
        if depth is not None and ply >= depth:
            if self.delta_fn is not None:
                return score
            return self.eval_fn(game, self._root) if self.eval_fn else 0

        alpha0, beta0 = alpha, beta
        key = None
        tt_move = None
        if self.use_tt and self._deep:
            key = game.key()
            rem = depth - ply
            entry = self._tt.get(key)
            if entry is not None:
                flag, tv, erem, tt_move = entry
                if erem >= rem:  # entry từ tìm kiếm sâu ≥ cần → dùng được
                    self._tt_hits += 1
                    tv = _from_tt(tv, ply)
                    if flag == EXACT:
                        return tv
                    if flag == LOWER:
                        alpha = max(alpha, tv)
                    else:
                        beta = min(beta, tv)
                    if alpha >= beta:
                        return tv
        elif self.use_tt:
            # depth=None: mọi nút có "độ sâu còn lại" vô hạn; có depth: chỉ dùng lại khi bằng nhau
            # để giá trị trùng khớp Minimax cùng depth.
            key = (game.key(), None if depth is None else depth - ply)
            entry = self._tt.get(key)
            if entry is not None:
                self._tt_hits += 1
                flag, tv = entry
                tv = _from_tt(tv, ply)
                if flag == EXACT:
                    return tv
                if flag == LOWER:
                    alpha = max(alpha, tv)
                else:
                    beta = min(beta, tv)
                if alpha >= beta:
                    return tv

        maximizing = game.current_player() == self._root
        sign = 1 if maximizing else -1
        delta_fn = self.delta_fn if depth is not None else None
        best = -_INF if maximizing else _INF
        best_move = None
        moves = self._moves(game, ply)
        if tt_move is not None and tt_move in moves:  # nước tốt nhất đã biết đi trước
            moves.remove(tt_move)
            moves.insert(0, tt_move)
        for move in moves:
            child = score + sign * delta_fn(game, move) if delta_fn else score
            game.play(move)
            v = self._alphabeta(game, ply + 1, alpha, beta, child)
            game.undo()
            if maximizing:
                if v > best:
                    best, best_move = v, move
                if best > alpha:
                    alpha = best
            else:
                if v < best:
                    best, best_move = v, move
                if best < beta:
                    beta = best
            if alpha >= beta:
                self._cutoffs += 1
                break

        if key is not None:
            if best <= alpha0:
                flag = UPPER
            elif best >= beta0:
                flag = LOWER
            else:
                flag = EXACT
            if self._deep:
                old = self._tt.get(key)
                if old is None or rem >= old[2]:  # thay entry nông hơn (độ sâu ưu tiên)
                    if len(self._tt) >= TT_MAX_ENTRIES:
                        self._tt.clear()
                    self._tt[key] = (flag, _to_tt(best, ply), rem, best_move)
            else:
                self._tt[key] = (flag, _to_tt(best, ply))
        return best
