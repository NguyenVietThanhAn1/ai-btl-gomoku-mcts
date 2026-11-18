"""AlphaBetaAgent P6.4: iterative deepening (`time_limit`) và `tt_mode="deep"`."""

import math
import random

import pytest

from gameai.agents.alphabeta import (
    EXACT,
    LOWER,
    AlphaBetaAgent,
    _from_tt,
)
from gameai.agents.registry import AgentSpec, make_agent
from gameai.games.kinrow import KInRow
from gameai.heuristics.kinrow_eval import delta_eval, evaluate, move_score

BIG = 1e9
FNS = {"eval_fn": evaluate, "delta_fn": delta_eval, "order_fn": move_score}


def mid_game(n: int, k: int, plies: int, seed: int) -> KInRow:
    rng = random.Random(seed)
    while True:
        g = KInRow(n, k)
        for _ in range(plies):
            g.play(rng.choice(g.candidate_moves()))
            if g.is_terminal():
                break
        if not g.is_terminal():
            return g


COMBOS = [
    {"eval_fn": evaluate},
    {"eval_fn": evaluate, "order_fn": move_score},
    {"eval_fn": evaluate, "delta_fn": delta_eval, "order_fn": move_score},
    {"eval_fn": evaluate, "delta_fn": delta_eval, "order_fn": move_score, "use_tt": True},
    {"eval_fn": evaluate, "use_tt": True},
]


@pytest.mark.parametrize("opts", COMBOS)
def test_id_equals_fixed_depth_without_top_k(opts):
    """time_limit rất lớn + không top_k + tt exact ⇒ trùng AB depth cố định (nước + giá trị)."""
    for seed, plies in [(0, 6), (1, 10), (2, 14), (3, 18)]:
        g = mid_game(15, 5, plies, seed)
        for depth in (1, 2, 3):
            fixed = AlphaBetaAgent(depth=depth, **opts)
            ident = AlphaBetaAgent(depth=depth, time_limit=BIG, **opts)
            assert ident.search(g.clone()) == fixed.search(g.clone()), (opts, seed, depth)
            assert ident.stats["depth_reached"] == depth and ident.stats["timed_out"] == 0


def test_id_equals_fixed_depth_3x3_all_positions():
    rng = random.Random(7)
    for _ in range(25):
        g = KInRow(3, 3)
        for _ in range(rng.randint(0, 6)):
            g.play(rng.choice(g.legal_moves()))
            if g.is_terminal():
                break
        if g.is_terminal():
            continue
        for depth in (2, 4, 6):
            fixed = AlphaBetaAgent(depth=depth, eval_fn=evaluate, order_fn=move_score)
            ident = AlphaBetaAgent(
                depth=depth, eval_fn=evaluate, order_fn=move_score, time_limit=BIG
            )
            assert ident.search(g.clone()) == fixed.search(g.clone())


def test_id_with_seed_matches_fixed_depth_tiebreak():
    g = mid_game(15, 5, 8, 9)
    a = AlphaBetaAgent(depth=2, seed=5, **FNS)
    b = AlphaBetaAgent(depth=2, seed=5, time_limit=BIG, **FNS)
    assert a.search(g.clone()) == b.search(g.clone())


def test_time_limit_validation():
    with pytest.raises(ValueError):
        AlphaBetaAgent(depth=3, time_limit=0)
    with pytest.raises(ValueError, match="depth"):
        AlphaBetaAgent(time_limit=1.0)
    with pytest.raises(ValueError):
        AlphaBetaAgent(depth=3, tt_mode="nope")
    with pytest.raises(ValueError, match="deep"):
        AlphaBetaAgent(depth=3, tt_mode="deep")  # thiếu use_tt
    with pytest.raises(ValueError, match="deep"):
        AlphaBetaAgent(tt_mode="deep", use_tt=True)  # thiếu depth


def test_time_limit_tiny_still_returns_depth_one_move():
    g = mid_game(15, 5, 12, 1)
    a = AlphaBetaAgent(depth=8, time_limit=1e-9, top_k=(8, 6, 4), **FNS)
    move, value = a.search(g)
    assert move in g.legal_moves() and math.isfinite(value)
    assert a.stats["depth_reached"] >= 1 and a.stats["timed_out"] == 1
    assert len(g.move_history) == 12  # game y nguyên


def test_time_limit_wall_clock_respected_and_depth_grows():
    g = mid_game(15, 5, 14, 2)
    a = AlphaBetaAgent(
        depth=12, time_limit=0.3, top_k=(10, 8, 6), use_tt=True, tt_mode="deep", **FNS
    )
    move, _ = a.search(g)
    assert move in g.legal_moves()
    assert a.stats["time"] < 0.3 + 0.5  # dung sai quá hạn (kiểm mỗi 32 nút)
    assert a.stats["depth_reached"] >= 2 and a.stats["timed_out"] == 1


def test_result_is_last_completed_depth():
    """Hết giờ giữa vòng d+1 ⇒ trả đúng kết quả vòng d (đối chiếu AB depth cố định d)."""
    g = mid_game(15, 5, 12, 3)
    fixed = {d: AlphaBetaAgent(depth=d, **FNS).search(g.clone()) for d in (1, 2, 3, 4)}
    nodes_by_depth = {}
    for d in (1, 2, 3):
        a = AlphaBetaAgent(depth=d, time_limit=BIG, **FNS)
        a.search(g.clone())
        nodes_by_depth[d] = a.stats["nodes"]
    # đồng hồ giả: hết giờ sau khi vòng 3 xong + một ít nút của vòng 4
    cut = nodes_by_depth[3] + 40
    ticks = {"n": 0}
    a = AlphaBetaAgent(depth=6, time_limit=1.0, **FNS)

    def clock():
        ticks["n"] += 1
        return 0.0 if a._nodes < cut else 10.0

    a._clock = clock
    res = a.search(g.clone())
    assert a.stats["depth_reached"] == 3 and a.stats["timed_out"] == 1
    assert res == fixed[3]


def _position_of(key: tuple[bytes, int]) -> KInRow:
    board, player = key
    xs = [i for i, v in enumerate(board) if v == 1]
    os = [i for i, v in enumerate(board) if v == 2]
    g = KInRow(15, 5)
    for i in range(len(os)):
        g.play(xs[i])
        g.play(os[i])
    if len(xs) > len(os):
        g.play(xs[-1])
    assert g.current_player() == player and not g.is_terminal()
    return g


def _check_tt_entries_valid(agent: AlphaBetaAgent, root_player: int, sample: int = 60):
    """Mọi entry TT (value theo góc nhìn gốc) khớp tìm kiếm tươi cùng độ sâu còn lại: EXACT = đúng,
    LOWER/UPPER = cận đúng. Entry của nút dở dang (nếu bị ghi) sẽ vi phạm."""
    rng = random.Random(0)
    items = list(agent._tt.items())
    assert items, "TT rỗng — test không có ý nghĩa"
    for key, val in rng.sample(items, min(sample, len(items))):
        if agent._deep:
            flag, tv, rem, _mv = val
        else:  # tt exact: khóa = (khóa thế, độ sâu còn lại)
            (key, rem), (flag, tv) = key, val
        pos = _position_of(key)
        fresh = AlphaBetaAgent(depth=rem, **FNS).search(pos)[1]  # góc nhìn người đang đi ở `pos`
        val = _from_tt(tv, 0)
        mover_view = val if pos.current_player() == root_player else -val
        if flag == EXACT:
            assert mover_view == fresh, (key, rem)
        elif flag == LOWER:  # cận dưới của giá trị theo góc nhìn gốc
            true_root = fresh if pos.current_player() == root_player else -fresh
            assert true_root >= val, (key, rem)
        else:
            true_root = fresh if pos.current_player() == root_player else -fresh
            assert true_root <= val, (key, rem)


@pytest.mark.parametrize("deep", [False, True])
def test_timeout_does_not_write_partial_tt_entries(deep):
    """_Timeout unwind không ghi TT cho nút dở dang: mọi entry còn lại đều hợp lệ."""
    g = mid_game(15, 5, 10, 4)
    kw = {"use_tt": True, **({"tt_mode": "deep"} if deep else {})}
    probe = AlphaBetaAgent(depth=3, time_limit=BIG, **kw, **FNS)
    probe.search(g.clone())
    cut = probe.stats["nodes"] // 2 + 7  # giữa vòng 3, cắt ở nút bất kỳ
    for extra in (0, 13, 101, 377):
        a = AlphaBetaAgent(depth=4, time_limit=1.0, **kw, **FNS)
        a._clock = lambda a=a, c=cut + extra: 0.0 if a._nodes < c else 10.0
        a.search(g.clone())
        assert a.stats["timed_out"] == 1
        _check_tt_entries_valid(a, g.current_player())


@pytest.mark.parametrize("deep", [False, True])
def test_cut_search_then_unlimited_same_value_as_empty_tt(deep):
    """Search bị cắt rồi search lại không giới hạn (giữ TT lần cắt) ⇒ cùng giá trị như TT rỗng."""
    g = mid_game(15, 5, 12, 5)
    kw = {"use_tt": True, **({"tt_mode": "deep"} if deep else {})}
    cutter = AlphaBetaAgent(depth=4, time_limit=1.0, **kw, **FNS)
    cutter._clock = lambda: 0.0 if cutter._nodes < 900 else 10.0
    cutter.search(g.clone())
    assert cutter.stats["timed_out"] == 1 and cutter._tt
    cutter.time_limit = BIG
    cutter._clock = lambda: 0.0
    cutter._preserve_tt = True  # giữ TT của lần bị cắt
    with_tt = cutter.search(g.clone())
    fresh = AlphaBetaAgent(depth=4, time_limit=BIG, **kw, **FNS)
    assert with_tt[1] == fresh.search(g.clone())[1]
    assert cutter.stats["depth_reached"] == 4


def test_deep_tt_uses_hits_and_agrees_on_value_with_exact_when_fixed_depth():
    """Ở depth cố định, TT sâu không đổi giá trị gốc so với không TT (chỉ dùng entry đủ sâu)."""
    for seed in range(3):
        g = mid_game(15, 5, 10 + seed, seed)
        plain = AlphaBetaAgent(depth=3, **FNS).search(g.clone())[1]
        deep = AlphaBetaAgent(depth=3, use_tt=True, tt_mode="deep", **FNS)
        assert deep.search(g.clone())[1] == plain


def test_deep_tt_helps_iterative_deepening():
    g = mid_game(15, 5, 12, 6)
    plain = AlphaBetaAgent(depth=4, time_limit=BIG, **FNS)
    deep = AlphaBetaAgent(depth=4, time_limit=BIG, use_tt=True, tt_mode="deep", **FNS)
    plain.search(g.clone())
    deep.search(g.clone())
    assert deep.stats["tt_hits"] > 0
    assert deep.stats["nodes"] < plain.stats["nodes"]


def test_tt_cap_clears_instead_of_growing(monkeypatch):
    import gameai.agents.alphabeta as ab

    monkeypatch.setattr(ab, "TT_MAX_ENTRIES", 50)
    g = mid_game(15, 5, 10, 7)
    a = AlphaBetaAgent(depth=3, time_limit=BIG, use_tt=True, tt_mode="deep", **FNS)
    a.search(g)
    assert len(a._tt) <= 50


def test_registry_builds_id_agent_from_spec():
    spec = AgentSpec(
        "alphabeta",
        {"depth": 6, "eval": "evaluate", "delta": "delta_eval", "order": "move_score",
         "use_tt": True, "tt_mode": "deep", "time_limit": 0.2, "top_k": [8, 6, 4]},
        label="id",
    )  # fmt: skip
    spec.to_dict()
    a = make_agent(spec, 0)
    g = mid_game(15, 5, 10, 8)
    assert a.select_move(g) in g.legal_moves() and a.stats["depth_reached"] >= 1
