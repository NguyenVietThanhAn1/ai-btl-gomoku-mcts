"""Preset cấu hình GUI: game + hai bên (AgentSpec hoặc người), dùng cùng spec với thí nghiệm."""

from __future__ import annotations

import inspect
from dataclasses import dataclass, replace

from gameai.agents.mcts import MCTSAgent
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
        Preset("3x3_human_mcts", "", GAME3, HUMAN, MCTS_3X3),
        Preset("15_human_h300", "", GAME15, HUMAN, MCTS_H300),
        Preset("15_h300_vs_ab2", "", GAME15, MCTS_H300, AB2, 0.5),
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
# D-36: Khó mới của AB 15×15 = iterative deepening theo thời gian + top-k + TT sâu + VCF ở gốc.
# `top_k` tạm (16, 12, 8), chưa chốt (B5). `vcf_time` ghi ở đây, không hard-code trong agent.
AB15_HARD = AgentSpec(
    "alphabeta",
    {"depth": 12, "eval": "evaluate", "delta": "delta_eval", "order": "move_score",
     "use_tt": True, "tt_mode": "deep", "time_limit": 2.4, "top_k": [16, 12, 8],
     "vcf_depth": 8, "vcf_time": 0.3},
    label="play_ab15_hard",
)  # fmt: skip

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
    (15, "alphabeta", "medium"): Level(variants_15(3)["ab_order"], "E1"),  # Khó cũ (D-29), D-36
    (15, "alphabeta", "hard"): Level(AB15_HARD, None),
}

# Spec thí nghiệm không còn là mức độ khó nhưng vẫn dùng ở Demo (D-36): (bàn, spec, nguồn).
EXPERIMENT_SPECS: list[tuple[int, AgentSpec, str]] = [(15, AB2, "E3/E5")]


def level_for(board: int, ai_kind: str, level: str) -> Level:
    """Mức độ khó của (bàn 3 / 15, loại AI, mức); KeyError nếu không có."""
    return DIFFICULTY[(board, ai_kind, level)]


def find_level(spec: AgentSpec | None, board: int) -> tuple[str, Level] | None:
    """Tra ngược trong DIFFICULTY: (mức, Level) của `spec` trên bàn `board`; None nếu không có."""
    for (b, _kind, level), lv in DIFFICULTY.items():
        if b == board and lv.spec == spec:
            return level, lv
    return None


def experiment_source(spec: AgentSpec | None, board: int) -> str | None:
    """Nguồn thí nghiệm của spec chỉ dùng ở Demo (không phải mức độ khó): 'E3/E5' hoặc None."""
    for b, s, source in EXPERIMENT_SPECS:
        if b == board and s == spec:
            return source
    return None


def source_of(spec: AgentSpec | None, board: int) -> str | None:
    """Nhãn nguồn của spec: "cấu hình E3" / cấu hình riêng / None (người hoặc spec lạ)."""
    found = find_level(spec, board)
    return None if found is None else found[1].source_text


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


MCTS_DEFAULTS = {
    name: prm.default
    for name, prm in inspect.signature(MCTSAgent.__init__).parameters.items()
    if prm.default is not inspect.Parameter.empty
}  # mặc định thật của MCTSAgent (c = √2, iterations = 1000, ...) — không gõ tay


def mcts_param(spec: AgentSpec, name: str):
    """Tham số MCTS hiệu lực: trong spec, không có thì mặc định của `MCTSAgent`."""
    return spec.params.get(name, MCTS_DEFAULTS.get(name))


def rollout_tag(spec: AgentSpec) -> str:
    """'random' | 'h300' (heavy + temperature trong spec) | 'heavy'."""
    roll = spec.params.get("rollout", "random")
    if roll in ("heavy", "heavy_kinrow"):
        temp = spec.params.get("temperature")
        return f"h{temp:g}" if temp is not None else "heavy"
    return str(roll)


def budget_text(spec: AgentSpec) -> str:
    """'5000 iter' hoặc '0.5 s/nước' (từ spec)."""
    iters, tl = mcts_param(spec, "iterations"), mcts_param(spec, "time_limit")
    return f"{iters} iter" if iters is not None else f"{tl:g} s/nước"


def side_label(spec: AgentSpec | None) -> str:
    """Nhãn hiển thị đầy đủ của một bên — mọi số lấy từ spec / mặc định của agent."""
    if spec is None:
        return "Người"
    if spec.kind == "mcts":
        tac = ", tactics" if mcts_param(spec, "check_tactics") else ""
        return f"MCTS {rollout_tag(spec)} {budget_text(spec)}, c={mcts_param(spec, 'c'):.3g}{tac}"
    if spec.kind == "alphabeta":
        p = spec.params
        depth = p.get("depth")
        limit = p.get("time_limit")
        if limit is not None:  # iterative deepening (D-36): depth = độ sâu tối đa
            text = f"Alpha-Beta ID ≤{depth}, {limit:g} s/nước"
        else:
            text = "Alpha-Beta " + ("đầy đủ" if depth is None else f"depth {depth}")
        text += ", ordering" if p.get("order") else ""
        if p.get("top_k"):
            ks = p["top_k"]
            text += ", top-" + (str(ks) if isinstance(ks, int) else "/".join(map(str, ks)))
        text += ", TT" if p.get("use_tt") else ""
        text += f", VCF {p['vcf_depth']}" if p.get("vcf_depth") else ""
        return text
    return spec.name


def short_label(spec: AgentSpec | None) -> str:
    """Nhãn ngắn cho tiêu đề preset: 'người', 'MCTS h300 5000', 'Alpha-Beta d2'."""
    if spec is None:
        return "người"
    if spec.kind == "mcts":
        iters = mcts_param(spec, "iterations")
        return f"MCTS {rollout_tag(spec)}" + (f" {iters}" if iters is not None else "")
    if spec.kind == "alphabeta":
        depth = spec.params.get("depth")
        return "Alpha-Beta " + ("đầy đủ" if depth is None else f"d{depth}")
    return spec.name


def preset_title(game: GameSpec, x: AgentSpec | None, o: AgentSpec | None) -> str:
    n = game.params.get("n", 15)
    return f"{n}×{n}: {short_label(x)} vs {short_label(o)}"


# Tiêu đề preset suy từ spec (không gõ số tay) — gán sau khi có preset_title.
PRESETS.update({k: replace(p, title=preset_title(p.game, p.x, p.o)) for k, p in PRESETS.items()})
