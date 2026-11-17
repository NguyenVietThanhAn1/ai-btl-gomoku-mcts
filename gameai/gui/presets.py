"""Preset cấu hình GUI: game + hai bên (AgentSpec hoặc người), dùng cùng spec với thí nghiệm."""

from __future__ import annotations

from dataclasses import dataclass, replace

from gameai.agents.registry import AgentSpec, GameSpec
from gameai.experiments.e2_never_lose import mcts_spec as e2_mcts_spec
from gameai.experiments.e3_c_sweep import AB2, GAME3, GAME15
from gameai.experiments.e3_c_sweep import mcts_spec as e3_mcts_spec

HUMAN = None  # bên do người chơi


@dataclass(frozen=True)
class Preset:
    """Một chế độ chơi. `x` đi trước (P1), `o` đi sau; `None` = người."""

    key: str
    title: str
    game: GameSpec
    x: AgentSpec | None
    o: AgentSpec | None
    delay: float = 0.0  # giây chờ tối thiểu trước mỗi nước AI

    @property
    def has_human(self) -> bool:
        return self.x is None or self.o is None


MCTS_3X3 = e2_mcts_spec(1000)  # E2: 1000 iter, c = √2, tactics tắt (D-16)
MCTS_H300 = e3_mcts_spec(15, 1.4, 5000)  # E3: h300 + tactics (D-14), 5000 iter

PRESETS: dict[str, Preset] = {
    p.key: p
    for p in (
        Preset("3x3_human_mcts", "3×3: người vs MCTS 1000", GAME3, HUMAN, MCTS_3X3),
        Preset("15_human_h300", "15×15: người vs MCTS h300", GAME15, HUMAN, MCTS_H300),
        Preset("15_h300_vs_ab2", "15×15: MCTS h300 vs Alpha-Beta d2", GAME15, MCTS_H300, AB2, 0.5),
    )
}
PRESET_ORDER: list[str] = list(PRESETS)


def swap_sides(preset: Preset) -> Preset:
    """Đổi bên: ai cầm X thì cầm O và ngược lại."""
    return replace(preset, x=preset.o, o=preset.x)


def with_iterations(preset: Preset, iterations: int) -> Preset:
    """Đổi `iterations` của mọi bên MCTS (spec mới, label giữ nguyên)."""
    if iterations < 1:
        raise ValueError("iterations phải ≥ 1")

    def fix(spec: AgentSpec | None) -> AgentSpec | None:
        if spec is None or spec.kind != "mcts":
            return spec
        return replace(spec, params={**spec.params, "iterations": iterations})

    return replace(preset, x=fix(preset.x), o=fix(preset.o))


def mcts_iterations(preset: Preset) -> int | None:
    """Iteration của bên MCTS đầu tiên (None nếu không có MCTS)."""
    for spec in (preset.x, preset.o):
        if spec is not None and spec.kind == "mcts":
            return spec.params.get("iterations")
    return None


def side_label(spec: AgentSpec | None) -> str:
    """Nhãn hiển thị của một bên."""
    if spec is None:
        return "Người"
    if spec.kind == "mcts":
        p = spec.params
        roll = "h300" if p.get("rollout") == "heavy_kinrow" else "random"
        tac = ", tactics" if p.get("check_tactics") else ""
        return f"MCTS {roll} {p.get('iterations')} iter, c={p.get('c', 1.41):g}{tac}"
    if spec.kind == "alphabeta":
        return f"Alpha-Beta depth {spec.params.get('depth')}"
    return spec.name
