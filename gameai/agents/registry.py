"""Dựng agent / game từ mô tả kiểu JSON (`AgentSpec`, `GameSpec`) cho arena/thí nghiệm (D-13).

Spec pickle được (chạy được qua `ProcessPoolExecutor` trên Windows/spawn) và băm được (config hash
cho resume). Mỗi lần `make_agent` trả một agent **mới** (không mang TT / cây / rng của ván trước).
"""

from __future__ import annotations

import importlib
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from gameai.agents.alphabeta import AlphaBetaAgent
from gameai.agents.base import Agent
from gameai.agents.greedy import GreedyAgent
from gameai.agents.mcts import MCTSAgent
from gameai.agents.minimax import MinimaxAgent
from gameai.agents.random_agent import RandomAgent
from gameai.agents.rollout import sigmoid_value
from gameai.core.game import Game
from gameai.games.kinrow import KInRow
from gameai.heuristics import kinrow_eval
from gameai.heuristics.kinrow_rollout import KInRowHeavyRollout

# Hàm heuristic gọi được theo tên trong params (k-in-row; P8 thêm hàm cờ tướng vào đây).
FUNCTIONS: dict[str, Callable[..., Any]] = {
    "move_score": kinrow_eval.move_score,
    "evaluate": kinrow_eval.evaluate,
    "delta_eval": kinrow_eval.delta_eval,
}


@dataclass(frozen=True)
class AgentSpec:
    """Mô tả agent: `kind` (tên trong registry hoặc "module:Class"), `params` (JSON), `label`."""

    kind: str
    params: dict[str, Any] = field(default_factory=dict)
    label: str | None = None

    @property
    def name(self) -> str:
        return self.label or self.kind

    def to_dict(self) -> dict[str, Any]:
        """Dạng dict chuẩn; `TypeError` nếu params không phải JSON."""
        d = {"kind": self.kind, "params": dict(self.params), "label": self.label}
        json.dumps(d)
        return d


@dataclass(frozen=True)
class GameSpec:
    """Mô tả game: `kind` ("kinrow" hoặc "module:Class") và `params` (JSON)."""

    kind: str = "kinrow"
    params: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = {"kind": self.kind, "params": dict(self.params)}
        json.dumps(d)
        return d


def _fn(name: str | None) -> Callable[..., Any] | None:
    if name is None:
        return None
    if name not in FUNCTIONS:
        raise ValueError(f"hàm không có trong registry: {name!r} (có: {sorted(FUNCTIONS)})")
    return FUNCTIONS[name]


def _import(path: str) -> Any:
    module, _, attr = path.partition(":")
    if not module or not attr:
        raise ValueError(f"kind không hợp lệ: {path!r}")
    return getattr(importlib.import_module(module), attr)


def _build_mcts(p: dict[str, Any], seed: int | None) -> Agent:
    rollout = p.pop("rollout", "random")
    temperature = p.pop("temperature", 100.0)
    score_fn = _fn(p.pop("score", "move_score"))
    value_scale = p.pop("value_scale", None)
    value_eval = _fn(p.pop("value_eval", "evaluate"))
    if rollout == "random":
        policy: Any = "random"
    elif rollout == "heavy":
        from gameai.agents.rollout import HeavyRollout

        policy = HeavyRollout(score_fn, temperature)
    elif rollout == "heavy_kinrow":
        policy = KInRowHeavyRollout(temperature)
    else:
        raise ValueError(f"rollout không hợp lệ: {rollout!r}")
    value_fn = sigmoid_value(value_eval, value_scale) if value_scale is not None else None
    return MCTSAgent(rollout_policy=policy, value_fn=value_fn, seed=seed, **p)


def _build_greedy(p: dict[str, Any], seed: int | None) -> Agent:
    return GreedyAgent(_fn(p.pop("score", "move_score")), seed=seed, **p)


def _build_minimax(p: dict[str, Any], seed: int | None) -> Agent:
    return MinimaxAgent(eval_fn=_fn(p.pop("eval", None)), seed=seed, **p)


def _build_alphabeta(p: dict[str, Any], seed: int | None) -> Agent:
    return AlphaBetaAgent(
        eval_fn=_fn(p.pop("eval", None)),
        delta_fn=_fn(p.pop("delta", None)),
        order_fn=_fn(p.pop("order", None)),
        seed=seed,
        **p,
    )


def _build_random(p: dict[str, Any], seed: int | None) -> Agent:
    return RandomAgent(seed=seed, **p)


BUILDERS: dict[str, Callable[[dict[str, Any], int | None], Agent]] = {
    "random": _build_random,
    "greedy": _build_greedy,
    "minimax": _build_minimax,
    "alphabeta": _build_alphabeta,
    "mcts": _build_mcts,
}


def make_agent(spec: AgentSpec, seed: int | None) -> Agent:
    """Dựng agent mới từ `spec` với `seed`. Sai config → `ValueError` / `TypeError`.

    Param chung `seeded` (mặc định True): False → truyền `seed=None` (agent tất định).
    """
    p = dict(spec.params)
    if not p.pop("seeded", True):
        seed = None
    if ":" in spec.kind:
        return _import(spec.kind)(seed=seed, **p)
    if spec.kind not in BUILDERS:
        raise ValueError(f"kind không có trong registry: {spec.kind!r} (có: {sorted(BUILDERS)})")
    return BUILDERS[spec.kind](p, seed)


def make_game(spec: GameSpec) -> Game:
    """Dựng ván mới (trạng thái đầu) từ `spec`."""
    if spec.kind == "kinrow":
        return KInRow(**spec.params)
    if ":" in spec.kind:
        return _import(spec.kind)(**spec.params)
    raise ValueError(f"game kind không hợp lệ: {spec.kind!r}")
