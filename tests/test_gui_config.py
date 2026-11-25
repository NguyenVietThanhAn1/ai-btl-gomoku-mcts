"""P6.3: bảng độ khó (D-29) và GameConfig → Preset; P6.2: cờ tướng (D-37)."""

from __future__ import annotations

import pytest

from gameai.agents.registry import AgentSpec, make_agent
from gameai.core.game import P1, P2
from gameai.experiments import e1_nodes, e2_never_lose, e3_c_sweep, p82_ab_check, p83_mcts_check
from gameai.gui.game_config import AIChoice, GameConfig, build_preset
from gameai.gui.presets import (
    DIFFICULTY,
    LEVELS,
    OWN_CONFIG,
    PRESETS,
    XIANGQI,
    board_key,
    level_for,
    side_label,
)

EXPECTED_EXPERIMENT = {
    (3, "mcts", "easy"): (e2_never_lose.mcts_spec(100), "E2"),
    (3, "mcts", "medium"): (e2_never_lose.mcts_spec(1000), "E2"),
    (3, "mcts", "hard"): (e2_never_lose.mcts_spec(5000), "E2"),
    (3, "alphabeta", "hard"): (e1_nodes.VARIANTS_3["ab_order_tt"], "E1"),
    (15, "mcts", "easy"): (e3_c_sweep.mcts_spec(15, 1.4, 250), "E3"),
    (15, "mcts", "medium"): (e3_c_sweep.mcts_spec(15, 1.4, 1000), "E3"),
    (15, "mcts", "hard"): (e3_c_sweep.mcts_spec(15, 1.4, 5000), "E3"),
    (15, "alphabeta", "medium"): (e1_nodes.variants_15(3)["ab_order"], "E1"),  # Khó cũ, D-36
}
EXPECTED_OWN = {
    (3, "alphabeta", "easy"): {"depth": 1, "eval": "evaluate"},
    (3, "alphabeta", "medium"): {"depth": 2, "eval": "evaluate"},
    (15, "alphabeta", "easy"): {"depth": 1, "eval": "evaluate", "delta": "delta_eval",
                                "order": "move_score"},
    (15, "alphabeta", "hard"): {"depth": 12, "eval": "evaluate", "delta": "delta_eval",
                                "order": "move_score", "use_tt": True, "tt_mode": "deep",
                                "time_limit": 2.4, "top_k": [16, 12, 8], "vcf_depth": 8,
                                "vcf_time": 0.3},  # D-36 (top_k tạm, B5)
}  # fmt: skip
# Cờ tướng (D-37): spec sinh bằng hàm thí nghiệm P8.2/P8.3, nguồn = cấu hình riêng.
EXPECTED_XQ = {
    ("xiangqi", "mcts", "easy"): p83_mcts_check.xq_mcts_spec(time_limit=0.3, tactics=True),
    ("xiangqi", "mcts", "medium"): p83_mcts_check.xq_mcts_spec(time_limit=1.0, tactics=True),
    ("xiangqi", "mcts", "hard"): p83_mcts_check.xq_mcts_spec(time_limit=2.5, tactics=True),
    ("xiangqi", "alphabeta", "easy"): p82_ab_check.ab_spec(1),
    ("xiangqi", "alphabeta", "medium"): p82_ab_check.ab_spec(2, use_tt=True),
    ("xiangqi", "alphabeta", "hard"): p82_ab_check.ab_spec(12, use_tt=True, time_limit=2.0),
}


def test_difficulty_table_complete_and_matches_experiments():
    keys = {(b, k, lv) for b in (3, 15, "xiangqi") for k in ("mcts", "alphabeta") for lv in LEVELS}
    assert set(DIFFICULTY) == keys
    assert keys == set(EXPECTED_EXPERIMENT) | set(EXPECTED_OWN) | set(EXPECTED_XQ)
    for key, (spec, source) in EXPECTED_EXPERIMENT.items():
        lv = level_for(*key)
        assert lv.spec == spec and lv.source == source
        assert lv.source_text == f"cấu hình {source}"
    for key, params in EXPECTED_OWN.items():
        lv = level_for(*key)
        assert lv.spec.kind == "alphabeta" and lv.spec.params == params
        assert lv.source is None and lv.source_text == OWN_CONFIG
    for key, spec in EXPECTED_XQ.items():
        lv = level_for(*key)
        assert lv.spec == spec and lv.source is None and lv.source_text == OWN_CONFIG
    for lv in DIFFICULTY.values():
        make_agent(lv.spec, 0)


def test_xiangqi_levels_config():
    """MCTS: cắt rollout + eval, tactics bật, theo thời gian; AB: không top_k / TT sâu (D-23)."""
    for lv in LEVELS:
        m = level_for("xiangqi", "mcts", lv).spec.params
        assert m["check_tactics"] and m["rollout_limit"] == p83_mcts_check.XQ_MCTS_L
        assert m["time_limit"] > 0 and m["iterations"] is None
        a = level_for("xiangqi", "alphabeta", lv).spec.params
        assert "top_k" not in a and "tt_mode" not in a and a["eval"] == "xq_evaluate"
    label = side_label(level_for("xiangqi", "mcts", "medium").spec)
    assert label == f"MCTS cắt {p83_mcts_check.XQ_MCTS_L} + eval, 1 s/nước, c=1.41, tactics"
    hard_ab = side_label(level_for("xiangqi", "alphabeta", "hard").spec)
    assert hard_ab == "Alpha-Beta ID ≤12, 2 s/nước, ordering, TT"


def test_levels_still_three_and_3x3_untouched():
    assert LEVELS == ("easy", "medium", "hard")
    assert {k[2] for k in DIFFICULTY} == set(LEVELS)
    assert len([k for k in DIFFICULTY if k[0] == 3]) == 6  # 3×3: 2 loại AI × 3 mức, như D-29
    assert len([k for k in DIFFICULTY if k[0] == 15]) == 6
    assert len([k for k in DIFFICULTY if k[0] == "xiangqi"]) == 6


def test_hard_ab_15_is_new_play_config_and_old_hard_is_medium():
    hard = level_for(15, "alphabeta", "hard")
    assert hard.source is None and hard.source_text == OWN_CONFIG
    agent = make_agent(hard.spec, 0)
    assert agent.time_limit == 2.4 and agent.tt_mode == "deep" and agent.root_hook is not None
    assert level_for(15, "alphabeta", "medium").spec == e1_nodes.variants_15(3)["ab_order"]
    assert "ID ≤12, 2.4 s/nước" in side_label(hard.spec) and "VCF 8" in side_label(hard.spec)


def test_demo_presets_still_experiment_specs():
    from gameai.gui.presets import experiment_source

    assert PRESETS["15_h300_vs_ab2"].o == e3_c_sweep.AB2  # Demo giữ cấu hình thí nghiệm
    assert experiment_source(e3_c_sweep.AB2, 15) == "E3/E5"
    assert experiment_source(e3_c_sweep.AB2, 3) is None
    assert experiment_source(level_for(15, "alphabeta", "hard").spec, 15) is None


def test_p61_presets_unchanged():
    assert PRESETS["3x3_human_mcts"].o == level_for(3, "mcts", "medium").spec
    assert PRESETS["15_human_h300"].o == level_for(15, "mcts", "hard").spec


@pytest.mark.parametrize("game,board", [("3x3", 3), ("15x15", 15)])
@pytest.mark.parametrize("kind", ["mcts", "alphabeta"])
@pytest.mark.parametrize("level", LEVELS)
def test_human_vs_ai_preset(game, board, kind, level):
    for side, human in (("X", P1), ("O", P2)):
        p = build_preset(GameConfig(game, "human_ai", side, AIChoice(kind, level)))
        spec = level_for(board, kind, level).spec
        assert (p.x, p.o) == ((None, spec) if human == P1 else (spec, None))
        assert p.game.params["n"] == board


def test_random_side_deterministic_by_seed():
    sides = {s: GameConfig(side="random", seed=s).human_side() for s in range(20)}
    assert set(sides.values()) == {"X", "O"}
    assert all(GameConfig(side="random", seed=s).human_side() == v for s, v in sides.items())
    p = build_preset(GameConfig(side="random", seed=3))
    assert (p.x is None) == (sides[3] == "X")


def test_two_players_and_ai_vs_ai():
    p = build_preset(GameConfig("3x3", "two_players"))
    assert p.x is None and p.o is None
    cfg = GameConfig("15x15", "ai_ai", ai=AIChoice("mcts", "hard"),
                     ai_o=AIChoice("alphabeta", "easy"), delay=1.25)  # fmt: skip
    p = build_preset(cfg)
    assert p.x == e3_c_sweep.mcts_spec(15, 1.4, 5000)
    assert p.o == level_for(15, "alphabeta", "easy").spec
    assert p.delay == 1.25
    assert GameConfig(mode="ai_ai").human_side() is None


@pytest.mark.parametrize("kind", ["mcts", "alphabeta"])
@pytest.mark.parametrize("level", LEVELS)
def test_xiangqi_presets_all_modes(kind, level):
    spec = level_for("xiangqi", kind, level).spec
    for side, human in (("X", P1), ("O", P2)):
        cfg = GameConfig("xiangqi", "human_ai", side, AIChoice(kind, level))
        p = build_preset(cfg)
        assert p.game == XIANGQI and board_key(p.game) == "xiangqi" == cfg.board
        assert (p.x, p.o) == ((None, spec) if human == P1 else (spec, None))
        assert cfg.side_name(side) == ("Đỏ" if human == P1 else "Đen")
    p = build_preset(GameConfig("xiangqi", "ai_ai", ai=AIChoice(kind, level)))
    assert p.x == spec and p.o == level_for("xiangqi", "alphabeta", "medium").spec
    p = build_preset(GameConfig("xiangqi", "two_players"))
    assert p.x is None and p.o is None and p.game == XIANGQI


def test_board_key_and_side_names():
    from gameai.gui.presets import GAME3, GAME15

    assert (board_key(GAME3), board_key(GAME15), board_key(XIANGQI)) == (3, 15, "xiangqi")
    games = ("3x3", "15x15", "xiangqi")
    assert [GameConfig(g).side_name("X") for g in games] == ["X", "Đen", "Đỏ"]
    assert [GameConfig(g).side_name("O") for g in games] == ["O", "Trắng", "Đen"]


def test_side_label_alphabeta():
    assert side_label(e3_c_sweep.AB2) == "Alpha-Beta depth 2, ordering"
    assert side_label(e1_nodes.VARIANTS_3["ab_order_tt"]) == "Alpha-Beta đầy đủ, ordering, TT"
    assert side_label(AgentSpec("alphabeta", {"depth": 1})) == "Alpha-Beta depth 1"
