"""AlphaBetaAgent: minimax với cắt tỉa alpha-beta, tùy chọn move ordering, cộng dồn delta, TT."""

from __future__ import annotations

import random
import time
from collections.abc import Callable

from gameai.agents.base import Agent
from gameai.agents.minimax import WIN_SCORE, EvalFn, terminal_score
from gameai.core.game import Game, Move

MoveFn = Callable[[Game, Move], float]

EXACT, LOWER, UPPER = 0, 1, 2
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


class AlphaBetaAgent(Agent):
    """Alpha-Beta dạng max/min tường minh (MAX = người đi ở gốc), cùng giá trị gốc với Minimax.

    - `order_fn(game, move)`: sắp nước giảm dần trước khi duyệt (vd. `kinrow_eval.move_score`).
    - `delta_fn(game, move)`: thay đổi lượng giá theo góc nhìn người đi, tính *trước* `play`
      (vd. `kinrow_eval.delta_eval`); lá = `eval_fn(gốc)` (hoặc 0) + tổng delta dọc nhánh.
    - `use_tt`: bảng chuyển vị theo `game.key()`, xóa ở đầu mỗi lần tìm.
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
    ) -> None:
        super().__init__()
        if depth is not None and depth < 1:
            raise ValueError("depth phải ≥ 1 hoặc None")
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

    def _moves(self, game: Game) -> list[Move]:
        moves = game.candidate_moves() if self.use_candidates else game.legal_moves()
        if self.order_fn is not None:
            moves = sorted(moves, key=lambda m: self.order_fn(game, m), reverse=True)
        return moves

    def search(self, game: Game) -> tuple[Move, float]:
        """Trả (nước tốt nhất, giá trị gốc theo góc nhìn người đang đi). Cập nhật `stats`."""
        assert not game.is_terminal(), "search gọi trên ván đã kết thúc"
        t0 = time.perf_counter()
        self._root = game.current_player()
        self._nodes = 1  # nút gốc
        self._cutoffs = 0
        self._tt_hits = 0
        self._tt = {}
        need_score = self.depth is not None
        base = self.eval_fn(game, self._root) if need_score and self.eval_fn else 0

        moves = game.candidate_moves() if self.use_candidates else game.legal_moves()
        if self.rng is not None:
            self.rng.shuffle(moves)  # tie-break ngẫu nhiên; sort ổn định giữ thứ tự trong nhóm bằng
        if self.order_fn is not None:
            moves.sort(key=lambda m: self.order_fn(game, m), reverse=True)

        best_move, best, alpha = moves[0], -_INF, -_INF
        for move in moves:
            score = base + self.delta_fn(game, move) if need_score and self.delta_fn else base
            game.play(move)
            v = self._alphabeta(game, 1, alpha, _INF, score)
            game.undo()
            if v > best:
                best, best_move = v, move
            alpha = max(alpha, v)

        self.stats["nodes"] = self._nodes
        self.stats["iterations"] = 0
        self.stats["time"] = time.perf_counter() - t0
        self.stats["value"] = best
        self.stats["cutoffs"] = self._cutoffs
        self.stats["tt_hits"] = self._tt_hits
        return best_move, best

    def value(self, game: Game) -> float:
        """Giá trị gốc (bằng `MinimaxAgent.value` với cùng depth/eval)."""
        return self.search(game)[1]

    def _select_move(self, game: Game) -> Move:
        return self.search(game)[0]

    def _alphabeta(self, game: Game, ply: int, alpha: float, beta: float, score: float) -> float:
        """Giá trị nút theo góc nhìn gốc (fail-soft). `score` = lượng giá cộng dồn tới nút này."""
        self._nodes += 1
        winner = game.winner()
        if winner is not None:
            return terminal_score(winner, self._root, ply)
        depth = self.depth
        if depth is not None and ply >= depth:
            if self.delta_fn is not None:
                return score
            return self.eval_fn(game, self._root) if self.eval_fn else 0

        alpha0, beta0 = alpha, beta
        key = None
        if self.use_tt:
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
        for move in self._moves(game):
            child = score + sign * delta_fn(game, move) if delta_fn else score
            game.play(move)
            v = self._alphabeta(game, ply + 1, alpha, beta, child)
            game.undo()
            if maximizing:
                if v > best:
                    best = v
                if best > alpha:
                    alpha = best
            else:
                if v < best:
                    best = v
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
            self._tt[key] = (flag, _to_tt(best, ply))
        return best
