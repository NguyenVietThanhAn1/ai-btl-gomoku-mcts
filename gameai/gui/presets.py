"""Preset cấu hình GUI: game + hai bên (AgentSpec hoặc người), dùng cùng spec với thí nghiệm."""

from __future__ import annotations

from dataclasses import dataclass, replace

from gameai.agents.registry import AgentSpec, GameSpec
from gameai.experiments.e1_nodes import VARIANTS_3, variants_15
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


# ---------------------------------------------------------------- độ khó (D-29)
LEVELS = ("easy", "medium", "hard")
LEVEL_NAMES = {"easy": "Dễ", "medium": "Vừa", "hard": "Khó"}
AI_KINDS = ("mcts", "alphabeta")
OWN_CONFIG = "cấu hình riêng của chế độ chơi, không có trong thí nghiệm"


@dataclass(frozen=True)
class Level:
    """Một mức độ khó: spec + nguồn (`"E1"`… hoặc None = cấu hình riêng)."""

    spec: AgentSpec
    source: str | None

    @property
    def source_text(self) -> str:
        return OWN_CONFIG if self.source is None else f"cấu hình {self.source}"


# Cấu hình riêng (An cho phép, D-29): chỉ dùng tham số có sẵn của AlphaBetaAgent.
AB3_D1 = AgentSpec("alphabeta", {"depth": 1, "eval": "evaluate"}, label="play_ab3_d1")
AB3_D2 = AgentSpec("alphabeta", {"depth": 2, "eval": "evaluate"}, label="play_ab3_d2")
AB15_D1 = AgentSpec("alphabeta", {"depth": 1, "eval": "evaluate", "delta": "delta_eval",
                                  "order": "move_score"}, label="play_ab15_d1")  # fmt: skip

DIFFICULTY: dict[tuple[int, str, str], Level] = {
    (3, "mcts", "easy"): Level(e2_mcts_spec(100), "E2"),
    (3, "mcts", "medium"): Level(e2_mcts_spec(1000), "E2"),
    (3, "mcts", "hard"): Level(e2_mcts_spec(5000), "E2"),
    (3, "alphabeta", "easy"): Level(AB3_D1, None),
    (3, "alphabeta", "medium"): Level(AB3_D2, None),
    (3, "alphabeta", "hard"): Level(VARIANTS_3["ab_order_tt"], "E1"),
    (15, "mcts", "easy"): Level(e3_mcts_spec(15, 1.4, 250), "E3"),
    (15, "mcts", "medium"): Level(e3_mcts_spec(15, 1.4, 1000), "E3"),
    (15, "mcts", "hard"): Level(e3_mcts_spec(15, 1.4, 5000), "E3"),
    (15, "alphabeta", "easy"): Level(AB15_D1, None),
    (15, "alphabeta", "medium"): Level(AB2, "E3/E5"),
    (15, "alphabeta", "hard"): Level(variants_15(3)["ab_order"], "E1"),
}


def level_for(board: int, ai_kind: str, level: str) -> Level:
    """Mức độ khó của (bàn 3 / 15, loại AI, mức); KeyError nếu không có."""
    return DIFFICULTY[(board, ai_kind, level)]


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
        p = spec.params
        depth = p.get("depth")
        text = "Alpha-Beta " + ("đầy đủ" if depth is None else f"depth {depth}")
        text += ", ordering" if p.get("order") else ""
        text += ", TT" if p.get("use_tt") else ""
        return text
    return spec.name
