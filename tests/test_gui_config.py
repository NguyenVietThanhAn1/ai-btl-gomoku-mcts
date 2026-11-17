"""P6.3: bảng độ khó (D-29) và GameConfig → Preset."""

from __future__ import annotations

import pytest

from gameai.agents.registry import AgentSpec, make_agent
from gameai.core.game import P1, P2
from gameai.experiments import e1_nodes, e2_never_lose, e3_c_sweep
from gameai.gui.game_config import AIChoice, GameConfig, build_preset
from gameai.gui.presets import DIFFICULTY, LEVELS, OWN_CONFIG, PRESETS, level_for, side_label

EXPECTED_EXPERIMENT = {
    (3, "mcts", "easy"): (e2_never_lose.mcts_spec(100), "E2"),
    (3, "mcts", "medium"): (e2_never_lose.mcts_spec(1000), "E2"),
    (3, "mcts", "hard"): (e2_never_lose.mcts_spec(5000), "E2"),
    (3, "alphabeta", "hard"): (e1_nodes.VARIANTS_3["ab_order_tt"], "E1"),
    (15, "mcts", "easy"): (e3_c_sweep.mcts_spec(15, 1.4, 250), "E3"),
    (15, "mcts", "medium"): (e3_c_sweep.mcts_spec(15, 1.4, 1000), "E3"),
    (15, "mcts", "hard"): (e3_c_sweep.mcts_spec(15, 1.4, 5000), "E3"),
    (15, "alphabeta", "medium"): (e3_c_sweep.AB2, "E3/E5"),
    (15, "alphabeta", "hard"): (e1_nodes.variants_15(3)["ab_order"], "E1"),
}
EXPECTED_OWN = {
    (3, "alphabeta", "easy"): {"depth": 1, "eval": "evaluate"},
    (3, "alphabeta", "medium"): {"depth": 2, "eval": "evaluate"},
    (15, "alphabeta", "easy"): {"depth": 1, "eval": "evaluate", "delta": "delta_eval",
                                "order": "move_score"},
}  # fmt: skip


def test_difficulty_table_complete_and_matches_experiments():
    keys = {(b, k, lv) for b in (3, 15) for k in ("mcts", "alphabeta") for lv in LEVELS}
    assert set(DIFFICULTY) == keys == set(EXPECTED_EXPERIMENT) | set(EXPECTED_OWN)
    for key, (spec, source) in EXPECTED_EXPERIMENT.items():
        lv = level_for(*key)
        assert lv.spec == spec and lv.source == source
        assert lv.source_text == f"cấu hình {source}"
    for key, params in EXPECTED_OWN.items():
        lv = level_for(*key)
        assert lv.spec.kind == "alphabeta" and lv.spec.params == params
        assert lv.source is None and lv.source_text == OWN_CONFIG
    for lv in DIFFICULTY.values():
        make_agent(lv.spec, 0)


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


def test_xiangqi_not_playable_yet():
    with pytest.raises(ValueError):
        build_preset(GameConfig("xiangqi"))


def test_side_label_alphabeta():
    assert side_label(e3_c_sweep.AB2) == "Alpha-Beta depth 2, ordering"
    assert side_label(e1_nodes.VARIANTS_3["ab_order_tt"]) == "Alpha-Beta đầy đủ, ordering, TT"
    assert side_label(AgentSpec("alphabeta", {"depth": 1})) == "Alpha-Beta depth 1"
