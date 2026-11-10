"""Test P3.3: hiệu chỉnh scale (log-likelihood, mở rộng lưới, dữ liệu), cấu hình, khớp sigmoid."""

from __future__ import annotations

import math
import random

import pytest

from gameai.agents.registry import AgentSpec, make_agent
from gameai.agents.rollout import sigmoid_value
from gameai.core.game import P1, P2
from gameai.experiments import p33_heavy_sweep as p33
from gameai.games.kinrow import KInRow
from gameai.heuristics.kinrow_eval import evaluate


def _synthetic(scale: float, n: int = 4000, seed: int = 0) -> list[tuple[float, float]]:
    rng = random.Random(seed)
    out = []
    for _ in range(n):
        e = rng.uniform(-4 * scale, 4 * scale)
        p = 1 / (1 + math.exp(-e / scale))
        out.append((e, 1.0 if rng.random() < p else 0.0))
    return out


# ---------------------------------------------------------------- log-likelihood / fit


def test_mean_loglik_matches_formula():
    samples = [(300.0, 1.0), (-200.0, 0.0), (50.0, 0.5)]
    scale = 100.0
    want = 0.0
    for e, z in samples:
        p = 1 / (1 + math.exp(-e / scale))
        want += z * math.log(p) + (1 - z) * math.log(1 - p)
    assert p33.mean_loglik(samples, scale) == pytest.approx(want / 3)


def test_mean_loglik_huge_eval_no_overflow():
    ll = p33.mean_loglik([(1e12, 1.0), (-1e12, 0.0), (1e12, 0.0)], 100)
    assert math.isfinite(ll) and ll < -1e9  # nhãn trái dấu bị phạt rất nặng, không lỗi


def test_draw_label_is_valid():
    # z = 0.5 → tối ưu ở e = 0 bất kể scale
    assert p33.mean_loglik([(0.0, 0.5)], 100) == pytest.approx(math.log(0.5))


def test_fit_recovers_true_scale():
    lls, best = p33.fit_scale_grid(_synthetic(500.0), p33.SCALES)
    assert best == 500.0
    assert set(lls) == {float(s) for s in p33.SCALES}  # không ở biên → không mở rộng


@pytest.mark.parametrize(
    ("true", "expect_new"), [(25.0, {50.0, 25.0}), (16000.0, {10000.0, 20000.0})]
)
def test_grid_extends_when_best_at_edge(true, expect_new):
    lls, best = p33.fit_scale_grid(_synthetic(true, n=6000), p33.SCALES)
    assert expect_new <= set(lls)
    grid = sorted(lls)
    assert best not in (grid[0], grid[-1])
    assert best == pytest.approx(true, rel=0.5)


def test_grid_extension_is_capped_and_flagged():
    rows = [{"temperature": "100", "seed": "1", "eval_p1": str(e), "z": str(z)}
            for e, z in _synthetic(1.0, n=500)]  # fmt: skip
    table = p33.fit_scales(rows, scales=(100, 200))
    assert len(table) == 2 + p33.MAX_GRID_EXTENSIONS
    chosen = [r for r in table if r["chosen"]]
    assert len(chosen) == 1 and chosen[0]["at_edge"] == 1
    assert sum(r["extended"] for r in table) == p33.MAX_GRID_EXTENSIONS
    assert any("WARNING" in line for line in p33.describe_fit(table))


def test_fit_scales_per_temperature_and_chosen_scales():
    rows = []
    for t, s in ((100, 200.0), (300, 2000.0)):
        rows += [{"temperature": str(t), "seed": str(i % 7), "eval_p1": str(e), "z": str(z)}
                 for i, (e, z) in enumerate(_synthetic(s, n=3000, seed=t))]  # fmt: skip
    table = p33.fit_scales(rows)
    assert p33.chosen_scales(table) == {100.0: 200.0, 300.0: 2000.0}
    assert all(r["n_rollouts"] == 7 for r in table)
    lines = p33.describe_fit(table)
    assert len(lines) == 2 and "scale=200" in lines[0] and "100:" in lines[0] and "300:" in lines[0]


# ---------------------------------------------------------------- dữ liệu hiệu chỉnh


def test_calibration_deterministic_and_labels():
    a = p33.calibration_samples(1000, 50_000)
    b = p33.calibration_samples(1000, 50_000)
    assert a == b and len(a) > 0
    assert {s["z"] for s in a} <= {0.0, 0.5, 1.0} and len({s["z"] for s in a}) == 1
    lo, hi = p33.OPENING_RANGE
    assert lo <= a[0]["opening_len"] <= hi
    assert [s["ply"] for s in a] == list(range(len(a)))
    assert p33.calibration_samples(1000, 50_001) != a


def test_calibration_positions_are_nonterminal_and_eval_from_p1():
    """Dựng lại ván: mọi thế ghi chưa kết thúc, eval_p1 = evaluate(·, P1), to_move đúng."""
    t, seed = 300, 50_003
    samples = p33.calibration_samples(t, seed)
    # chạy lại cùng rng để có chuỗi nước
    from gameai.arena import derive_seed, random_opening_moves
    from gameai.heuristics.kinrow_rollout import KInRowHeavyRollout

    rng = random.Random(derive_seed(seed, f"calib-T{t}"))
    g = KInRow(15, 5)
    random_opening_moves(g, rng.randint(*p33.OPENING_RANGE), rng)
    policy = KInRowHeavyRollout(t)
    for s in samples:
        assert not g.is_terminal()
        assert s["eval_p1"] == evaluate(g, P1) and s["to_move"] == g.current_player()
        g.play(policy(g, rng))
    assert g.is_terminal()


def test_calibration_seeds_disjoint_from_sweep_seeds():
    sweep = set(range(p33.BASE_SEED, p33.BASE_SEED + p33.N_PAIRS))
    assert sweep == set(range(10))
    assert not sweep & set(p33.CALIB_SEEDS)
    assert len(p33.CALIB_SEEDS) == 200 and min(p33.CALIB_SEEDS) == 50_000


# ---------------------------------------------------------------- khớp sigmoid fit ↔ MCTS


def _position(x_moves: list[int], o_moves: list[int], to_move: int) -> KInRow:
    g = KInRow(15, 5)
    xs, os_ = list(x_moves), list(o_moves)
    while xs or os_:
        g.play(xs.pop(0) if g.current_player() == P1 else os_.pop(0))
    assert g.current_player() == to_move
    return g


def _c(r: int, c: int) -> int:
    return r * 15 + c


@pytest.mark.parametrize("to_move", [P1, P2])
@pytest.mark.parametrize("x_strong", [True, False])
def test_mcts_value_fn_matches_fit_sigmoid(to_move, x_strong):
    """value_fn mà MCTS dùng (dựng qua registry như bước quét) = σ(eval_p1/scale) đã dùng khi fit,
    là xác suất **P1** thắng bất kể lượt đi."""
    strong = [_c(7, 5), _c(7, 6), _c(7, 7)]  # three mở
    corners = [_c(0, 0), _c(14, 14), _c(0, 14), _c(14, 0)]
    # số quân: P1 đi ↔ X = O; P2 đi ↔ X = O + 1
    n_weak = 3 if to_move == P1 else (2 if x_strong else 4)
    weak = corners[:n_weak]
    g = _position(strong, weak, to_move) if x_strong else _position(weak, strong, to_move)
    e = evaluate(g, P1)
    assert (e > 0) == x_strong  # đúng chiều lợi thế
    scale = 300.0
    spec = p33.sweep_configs({100.0: 1.0, 300.0: scale, 1000.0: 1.0})[5]  # h300c10
    assert spec.name == "h300c10"
    agent = make_agent(spec, 0)
    v = agent.value_fn(g)
    want = math.exp(p33._log_sigmoid(e / scale))  # đúng công thức của mean_loglik
    assert v == pytest.approx(want, rel=1e-12)
    assert v == pytest.approx(sigmoid_value(evaluate, scale)(g), rel=1e-12)
    assert (v > 0.5) == x_strong


def test_mcts_simulate_returns_value_fn_as_p1_score():
    """Rollout bị cắt ở 0 nước → z = value_fn(g), dùng thẳng làm điểm P1 (cùng nhãn z khi fit)."""
    g = _position([_c(7, 5), _c(7, 6), _c(7, 7)], [_c(0, 0), _c(14, 14)], P2)
    agent = make_agent(AgentSpec("mcts", {"iterations": 1, "rollout": "heavy_kinrow",
                                          "rollout_limit": 0, "value_scale": 300}), 0)  # fmt: skip
    z = agent._simulate(g.clone())
    assert z == pytest.approx(sigmoid_value(evaluate, 300)(g)) and z > 0.5


# ---------------------------------------------------------------- cấu hình quét


def test_sweep_configs():
    scales = {100.0: 200.0, 300.0: 500.0, 1000.0: 2000.0}
    specs = p33.sweep_configs(scales)
    assert [s.name for s in specs] == ["rand", "h100", "h300", "h1000", "h100c10", "h300c10",
                                       "h1000c10"]  # fmt: skip
    for s in specs:
        assert s.params["time_limit"] == 0.5 and s.params["iterations"] is None
        assert s.params["check_tactics"] is False
        make_agent(s, 0)  # dựng được
    for s in specs[1:4]:
        assert s.params["rollout"] == "heavy_kinrow" and s.params["rollout_limit"] is None
        assert "value_scale" not in s.params
    for s in specs[4:]:
        t = s.params["temperature"]
        assert s.params["rollout_limit"] == 10 and s.params["value_scale"] == scales[float(t)]
    assert specs[0].params["rollout"] == "random"


def test_sweep_configs_missing_scale():
    with pytest.raises(KeyError):
        p33.sweep_configs({100.0: 200.0})


def test_opponents_and_paths():
    assert set(p33.OPPONENTS) == {"greedy", "ab2"}
    ab = p33.OPPONENTS["ab2"]
    assert ab.params == {
        "depth": 2,
        "eval": "evaluate",
        "delta": "delta_eval",
        "order": "move_score",
    }
    for o in p33.OPPONENTS.values():
        make_agent(o, 0)
    assert p33.match_path("h100c10", "ab2", False).name == "p33_h100c10_vs_ab2.csv"
    assert p33.match_path("rand", "greedy", True).name == "p33quick_rand_vs_greedy.csv"
    assert p33.summary_path(False).name == "p33_sweep_prelim.csv"
    assert p33.summary_path(True).name == "p33quick_sweep_prelim.csv"
    assert p33.worker_check_path(4).name.startswith("p33quick_")
