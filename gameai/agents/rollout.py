"""Rollout policy cho MCTS (chọn nước trong pha mô phỏng) và `value_fn` khi cắt rollout."""

from __future__ import annotations

import math
import random
from collections.abc import Callable

from gameai.agents.alphabeta import MoveFn
from gameai.agents.minimax import EvalFn
from gameai.core.game import P1, Game, Move

RolloutPolicy = Callable[[Game, random.Random], Move]
ValueFn = Callable[[Game], float]  # xác suất P1 thắng, trong [0, 1]


class RandomRollout:
    """Chọn đều ngẫu nhiên trong `candidate_moves()`."""

    name = "random"

    def __call__(self, game: Game, rng: random.Random) -> Move:
        return rng.choice(game.candidate_moves())


class HeavyRollout:
    """Lấy mẫu theo softmax((score − max) / T) trên `score_fn(game, move)` của mọi candidate.

    Với `kinrow_eval.move_score`, bậc WIN / BLOCK lớn hơn delta thường ~10^5 nên thắng ngay rồi
    chặn thua ngay được chọn với xác suất ≈ 1; còn lại nghiêng về nước có delta cao. Bản đúng, chưa
    tối ưu: chấm mọi candidate ở mỗi bước (~0,5 ms/bước trên 15×15) — tăng tốc ở P3.2.
    """

    name = "heavy"

    def __init__(self, score_fn: MoveFn, temperature: float = 100.0) -> None:
        if temperature <= 0:
            raise ValueError("temperature phải > 0")
        self.score_fn = score_fn
        self.temperature = temperature

    def __call__(self, game: Game, rng: random.Random) -> Move:
        moves = game.candidate_moves()
        score_fn = self.score_fn
        scores = [score_fn(game, m) for m in moves]
        top = max(scores)
        t = self.temperature
        weights = [math.exp((s - top) / t) for s in scores]  # nước tốt nhất có trọng số 1
        return rng.choices(moves, weights=weights)[0]


def make_policy(policy: str | RolloutPolicy, score_fn: MoveFn | None = None) -> RolloutPolicy:
    """`"random"` → `RandomRollout()`; `"heavy"` → `HeavyRollout(score_fn)`; callable → giữ
    nguyên."""
    if callable(policy):
        return policy
    if policy == "random":
        return RandomRollout()
    if policy == "heavy":
        if score_fn is None:
            raise ValueError('rollout_policy="heavy" cần score_fn (vd. kinrow_eval.move_score)')
        return HeavyRollout(score_fn)
    raise ValueError(f"rollout_policy không hợp lệ: {policy!r}")


def sigmoid_value(eval_fn: EvalFn, scale: float) -> ValueFn:
    """`value_fn(g) = 1 / (1 + exp(−eval_fn(g, P1) / scale))`: xác suất P1 thắng từ lượng giá."""
    if scale <= 0:
        raise ValueError("scale phải > 0")

    def value(game: Game) -> float:
        x = eval_fn(game, P1) / scale
        if x >= 0:
            return 1.0 / (1.0 + math.exp(-x))
        e = math.exp(x)  # tránh tràn số khi x rất âm
        return e / (1.0 + e)

    return value
