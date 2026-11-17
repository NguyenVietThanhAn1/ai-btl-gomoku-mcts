"""P6.1: controller GUI (headless), view k-in-row, presets, app với Surface không màn hình."""

from __future__ import annotations

import os
import random
import sys
import threading
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402
import pytest  # noqa: E402

from gameai.agents.base import Agent  # noqa: E402
from gameai.agents.registry import AgentSpec, make_agent  # noqa: E402
from gameai.core.game import P1, P2  # noqa: E402
from gameai.experiments import e2_never_lose, e3_c_sweep  # noqa: E402
from gameai.gui.controller import GameController  # noqa: E402
from gameai.gui.kinrow_view import KInRowView, winning_line  # noqa: E402
from gameai.gui.presets import (  # noqa: E402
    GAME3,
    GAME15,
    PRESETS,
    Preset,
    mcts_iterations,
    swap_sides,
    with_iterations,
)
from gameai.gui.pygame_app import App, AppState  # noqa: E402
from gameai.gui.view import FONT_NAMES, OverlayOpts, get_font  # noqa: E402

GATE = threading.Event()


class SlowAgent(Agent):
    """Chờ GATE rồi đi nước nhỏ nhất (để kiểm trạng thái 'đang nghĩ')."""

    def __init__(self, seed: int | None = None) -> None:
        super().__init__()

    def _select_move(self, game):
        assert GATE.wait(10)
        return min(game.legal_moves())


class FailingAgent(Agent):
    def __init__(self, seed: int | None = None) -> None:
        super().__init__()

    def _select_move(self, game):
        raise RuntimeError("boom")


SLOW = AgentSpec("tests.test_gui_controller:SlowAgent")
FAIL = AgentSpec("tests.test_gui_controller:FailingAgent")
MCTS200 = AgentSpec("mcts", {"iterations": 200, "check_tactics": False})


def play_human_random(ctrl: GameController, rng: random.Random, timeout: float = 60) -> None:
    """Chơi hết ván: người đi ngẫu nhiên (có seed), AI qua thread."""
    while True:
        ctrl.run_until_idle(timeout)
        if ctrl.over:
            return
        assert ctrl.submit_human_move(rng.choice(ctrl.game.legal_moves()))


# ---------------------------------------------------------------- presets
def test_presets_use_experiment_specs():
    assert PRESETS["3x3_human_mcts"].o == e2_never_lose.mcts_spec(1000)
    assert PRESETS["15_human_h300"].o == e3_c_sweep.mcts_spec(15, 1.4, 5000)
    p3 = PRESETS["15_h300_vs_ab2"]
    assert p3.x == e3_c_sweep.mcts_spec(15, 1.4, 5000) and p3.o == e3_c_sweep.AB2
    assert p3.x is not None and p3.o is not None and p3.delay > 0
    for p in PRESETS.values():
        for spec in (p.x, p.o):
            if spec is not None:
                make_agent(spec, 0)


def test_with_iterations_and_swap():
    p = with_iterations(PRESETS["15_h300_vs_ab2"], 250)
    assert p.x.params["iterations"] == 250 and p.o == e3_c_sweep.AB2
    assert mcts_iterations(p) == 250
    assert PRESETS["15_h300_vs_ab2"].x.params["iterations"] == 5000  # không đổi preset gốc
    s = swap_sides(PRESETS["3x3_human_mcts"])
    assert s.x == PRESETS["3x3_human_mcts"].o and s.o is None
    with pytest.raises(ValueError):
        with_iterations(p, 0)


# ---------------------------------------------------------------- controller
@pytest.mark.parametrize("seed", range(4))
@pytest.mark.parametrize("swapped", [False, True])
def test_human_vs_mcts_3x3_full_game_never_loses(seed, swapped):
    preset = PRESETS["3x3_human_mcts"]
    preset = swap_sides(preset) if swapped else preset
    ctrl = GameController(preset, seed=seed)
    play_human_random(ctrl, random.Random(seed))
    ai = P1 if swapped else P2
    assert ctrl.error is None and ctrl.winner in (ai, 0)
    assert [m.by_ai for m in ctrl.history] == [(m.player == ai) for m in ctrl.history]


def test_swap_ai_moves_first():
    ctrl = GameController(swap_sides(PRESETS["3x3_human_mcts"]), seed=0)
    assert ctrl.agents[P1] is not None and ctrl.agents[P2] is None
    ctrl.run_until_idle()
    assert ctrl.ply == 1 and ctrl.history[0].by_ai and ctrl.history[0].player == P1
    assert ctrl.is_human_turn() and ctrl.game.current_player() == P2


def test_ai_vs_ai_3x3_full_game():
    ctrl = GameController(Preset("t", "t", GAME3, MCTS200, MCTS200), seed=5)
    ctrl.run_until_idle()
    assert ctrl.over and ctrl.error is None and ctrl.ai_vs_ai
    assert all(m.by_ai for m in ctrl.history)


def test_same_seed_same_game():
    def moves(seed):
        ctrl = GameController(PRESETS["3x3_human_mcts"], seed=seed)
        play_human_random(ctrl, random.Random(99))
        return [m.move for m in ctrl.history]

    assert moves(3) == moves(3)


def test_root_stats_recorded():
    ctrl = GameController(swap_sides(PRESETS["3x3_human_mcts"]), seed=1)
    ctrl.run_until_idle()
    info = ctrl.last
    ns = [n for _, _, n, _ in info.root_stats]
    assert ns == sorted(ns, reverse=True) and sum(ns) == 1000 == info.iterations
    assert not info.is_tactic and info.time > 0


def test_tactic_move_has_no_overlay():
    both_human = Preset("t", "t", GAME15, None, None)
    ctrl = GameController(both_human, seed=0)
    for m in (112, 0, 113, 1, 114, 2, 115, 30):  # X có 4 quân liền, tới lượt X
        assert ctrl.submit_human_move(m)
    ctrl.agents[P1] = make_agent(with_iterations(PRESETS["15_human_h300"], 50).o, 0)
    ctrl.run_until_idle()
    info = ctrl.last
    assert info.by_ai and info.tactic == 1 and info.is_tactic and info.root_stats == []
    assert ctrl.winner == P1


def test_gui_cannot_mutate_while_thinking_and_stale_result_dropped():
    ctrl = GameController(Preset("t", "t", GAME3, SLOW, None), seed=0)
    # registry có thể import module test dưới tên khác → lấy GATE từ chính module của agent
    gate = sys.modules[type(ctrl.agents[P1]).__module__].GATE
    gate.clear()
    ctrl.update()
    assert ctrl.thinking and ctrl.is_ai_turn()
    key = ctrl.game.key()
    assert not ctrl.submit_human_move(4)  # không phải lượt người, AI đang nghĩ
    assert ctrl.game.key() == key and ctrl.ply == 0
    old_id = ctrl.game_id
    ctrl.new_game()  # ván mới khi AI cũ còn nghĩ
    assert ctrl.game_id == old_id + 1 and not ctrl.thinking
    gate.set()
    time.sleep(0.05)
    ctrl.run_until_idle(5)
    # Chỉ đúng 1 nước (của ván mới) — kết quả ván cũ cùng ply 0 đã bị bỏ theo game_id.
    assert ctrl.ply == 1 and ctrl.history[0].move == 0
    assert not ctrl.submit_human_move(0)  # ô đã có quân
    assert not ctrl.submit_human_move(99)  # ngoài bàn
    assert ctrl.submit_human_move(4)


def test_pause_blocks_ai_start():
    ctrl = GameController(Preset("t", "t", GAME3, MCTS200, MCTS200), seed=0)
    ctrl.paused = True
    ctrl.run_until_idle(5)
    assert ctrl.ply == 0 and not ctrl.thinking
    ctrl.paused = False
    ctrl.run_until_idle()
    assert ctrl.over


def test_delay_respected():
    ctrl = GameController(Preset("t", "t", GAME3, MCTS200, MCTS200), seed=0, delay=10)
    ctrl.update(now=time.monotonic())
    assert not ctrl.thinking
    ctrl.update(now=time.monotonic() + 11)
    assert ctrl.thinking


def test_agent_error_stops_game():
    ctrl = GameController(Preset("t", "t", GAME3, FAIL, None), seed=0)
    ctrl.run_until_idle(5)
    assert ctrl.over and ctrl.error and "boom" in ctrl.error
    assert ctrl.ply == 0 and ctrl.result_text() == ctrl.error


# ---------------------------------------------------------------- view
def test_hit_test_3x3_and_15x15():
    ctrl = GameController(Preset("t", "t", GAME3, None, None))
    v = KInRowView(3, 3, pygame.Rect(20, 20, 680, 680))
    cell = v.cell
    ox, oy = v.origin
    assert v.hit_test((ox + 1, oy + 1), ctrl.game) == 0
    assert v.hit_test((ox + cell + cell // 2, oy + cell + cell // 2), ctrl.game) == 4
    assert v.hit_test((ox + 3 * cell - 1, oy + 3 * cell - 1), ctrl.game) == 8
    assert v.hit_test((ox - 1, oy), ctrl.game) is None
    assert v.hit_test((ox + 3 * cell, oy), ctrl.game) is None
    ctrl.submit_human_move(4)
    assert v.hit_test((ox + cell + 5, oy + cell + 5), ctrl.game) is None  # ô đã có quân
    assert v.move_label(4) == "b2"

    g15 = GameController(Preset("t", "t", GAME15, None, None)).game
    v15 = KInRowView(15, 5, pygame.Rect(20, 20, 680, 680))
    ox, oy = v15.origin
    assert v15.hit_test((ox + 7 * v15.cell + 3, oy + 7 * v15.cell + 3), g15) == 112
    assert v15.move_label(112) == "H8"


def test_winning_line():
    board = bytearray(9)
    for m in (2, 4, 6):
        board[m] = 1
    assert sorted(winning_line(board, 3, 3, 4)) == [2, 4, 6]
    assert winning_line(board, 3, 3, 0) == []


def test_vietnamese_font_renders():
    for text in ("Đang nghĩ…", "Hòa", "Lượt X: mời bạn đi"):
        img = get_font(20).render(text, True, (0, 0, 0))
        assert img.get_width() > 0


def test_font_prefers_system_vietnamese_font():
    """Có Segoe UI / Arial trên máy → phải dùng đúng font đó (không rơi về font mặc định)."""
    path = next((p for p in map(pygame.font.match_font, FONT_NAMES) if p), None)
    if path is None:
        pytest.skip("máy không có Segoe UI / Arial")
    expected = pygame.font.Font(path, 20).render("Hòa", True, (0, 0, 0))
    got = get_font(20).render("Hòa", True, (0, 0, 0))
    assert got.get_size() == expected.get_size()
    assert pygame.image.tobytes(got, "RGBA") == pygame.image.tobytes(expected, "RGBA")


def test_ai_vs_ai_15x15_full_game():
    """Preset 3 (h300 vs AB2) với iteration nhỏ: chạy hết ván không lỗi."""
    preset = with_iterations(PRESETS["15_h300_vs_ab2"], 50)
    ctrl = GameController(preset, seed=0, delay=0)
    ctrl.run_until_idle(timeout=120)
    assert ctrl.over and ctrl.error is None and ctrl.result_text() is not None


def test_app_draws_headless_with_overlay():
    surf = pygame.Surface((1280, 720))
    state = AppState("3x3_human_mcts", seed=0, swapped=True, overlay=OverlayOpts(True, True))
    app = App(state, surface=surf)
    app.ctrl.run_until_idle()
    app.tick()  # vẽ bàn + overlay + panel sau nước AI
    assert app.ctrl.last.by_ai and app.ctrl.last.root_stats
    # click vào một ô trống → nước của người
    empty = next(m for m in range(9) if app.ctrl.game.board[m] == 0)
    assert app.handle_click(app.view.cell_rect(empty).center)
    app.tick()
    # 15×15 + phím
    app.handle_key(pygame.K_2)
    assert app.state.preset_key == "15_human_h300" and app.view.n == 15
    app.handle_key(pygame.K_k)
    assert mcts_iterations(app.ctrl.preset) == 2500
    app.handle_key(pygame.K_s)
    assert app.ctrl.preset.x is not None and app.ctrl.preset.o is None
    app.handle_key(pygame.K_RIGHTBRACKET)
    assert app.ctrl.seed == 1
    app.handle_key(pygame.K_EQUALS)
    assert app.ctrl.delay == pytest.approx(0.25)
    app.tick()
    app.handle_key(pygame.K_ESCAPE)
    assert not app.running


# ---------------------------------------------------------------- P6.3: undo / đầu hàng / xem lại
HUMAN_MCTS3 = PRESETS["3x3_human_mcts"]  # người X vs MCTS 1000


def test_undo_human_vs_ai_two_plies():
    ctrl = GameController(HUMAN_MCTS3, seed=0)
    assert not ctrl.can_undo  # chưa có nước người
    empty_key = ctrl.game.key()
    assert ctrl.submit_human_move(4)
    ctrl.run_until_idle()
    assert ctrl.ply == 2 and ctrl.can_undo
    gid, old_agent = ctrl.game_id, ctrl.agents[P2]
    assert ctrl.undo()
    assert ctrl.ply == 0 and ctrl.game.key() == empty_key and ctrl.is_human_turn()
    assert ctrl.game_id == gid + 1 and ctrl.agents[P2] is not old_agent


def test_undo_when_human_is_o_keeps_ai_opening():
    ctrl = GameController(swap_sides(HUMAN_MCTS3), seed=0)
    ctrl.run_until_idle()
    assert ctrl.ply == 1 and not ctrl.can_undo and not ctrl.undo()
    free = next(m for m in range(9) if ctrl.game.board[m] == 0)
    assert ctrl.submit_human_move(free)
    ctrl.run_until_idle()
    assert ctrl.ply == 3 and ctrl.undo()
    assert ctrl.ply == 1 and ctrl.history[0].by_ai and ctrl.is_human_turn()


def test_undo_disabled_while_ai_thinking_and_stale_result_dropped():
    ctrl = GameController(Preset("t", "t", GAME3, None, SLOW), seed=0)
    gate = sys.modules[type(ctrl.agents[P2]).__module__].GATE
    gate.clear()
    assert ctrl.submit_human_move(4)
    ctrl.update()
    assert ctrl.thinking and not ctrl.can_undo and not ctrl.undo() and ctrl.ply == 1
    gate.set()
    ctrl.run_until_idle(5)
    assert [m.move for m in ctrl.history] == [4, 0]
    # undo rồi người đi lại: chỉ nhận kết quả của thread mới (ply 1 trùng ply cũ)
    assert ctrl.undo() and ctrl.ply == 0
    assert ctrl.submit_human_move(8)
    ctrl.run_until_idle(5)
    assert [m.move for m in ctrl.history] == [8, 0]


def test_stale_result_same_ply_dropped_by_game_id():
    """Kết quả cũ trùng `ply` nhưng khác `game_id` (đã undo) không được áp."""
    from gameai.gui.controller import AIResult

    ctrl = GameController(Preset("t", "t", GAME3, None, None), seed=0)
    assert ctrl.submit_human_move(4) and ctrl.submit_human_move(0)
    old_id = ctrl.game_id
    assert ctrl.undo() and ctrl.ply == 1
    ctrl._results.put(AIResult(old_id, 1, P2, 8, {}, [], 0.1))
    ctrl.update()
    assert ctrl.ply == 1


def test_undo_two_players_one_ply_and_after_win():
    ctrl = GameController(Preset("t", "t", GAME3, None, None), seed=0)
    for m in (0, 3, 1, 4, 2):  # X thắng hàng trên
        assert ctrl.submit_human_move(m)
    assert ctrl.over and ctrl.outcome == P1
    assert ctrl.undo()
    assert ctrl.ply == 4 and not ctrl.over and ctrl.game.current_player() == P1


def test_undo_ai_vs_ai_disabled():
    ctrl = GameController(Preset("t", "t", GAME3, MCTS200, MCTS200), seed=0)
    ctrl.run_until_idle()
    assert not ctrl.can_undo and not ctrl.undo() and ctrl.over


def test_resign_human_vs_ai_drops_late_result():
    ctrl = GameController(Preset("t", "t", GAME3, None, SLOW), seed=0)
    gate = sys.modules[type(ctrl.agents[P2]).__module__].GATE
    gate.clear()
    assert ctrl.submit_human_move(4)
    ctrl.update()
    assert ctrl.thinking and ctrl.resign_side() == P1
    assert ctrl.resign()
    assert ctrl.over and ctrl.outcome == P2 and ctrl.winner is None
    assert ctrl.result_text() == "X đầu hàng — O thắng"
    gate.set()
    time.sleep(0.05)
    ctrl.update()
    assert ctrl.ply == 1 and not ctrl.undo() and not ctrl.resign()


def test_resign_two_players_current_side_and_ai_vs_ai_none():
    ctrl = GameController(Preset("t", "t", GAME3, None, None), seed=0)
    assert ctrl.submit_human_move(4)
    assert ctrl.resign_side() == P2 and ctrl.resign() and ctrl.outcome == P1
    aiai = GameController(Preset("t", "t", GAME3, MCTS200, MCTS200), seed=0, delay=100)
    assert aiai.resign_side() is None and not aiai.resign(P1)


def test_position_at_does_not_touch_game_and_human_time():
    ctrl = GameController(HUMAN_MCTS3, seed=2)
    play_human_random(ctrl, random.Random(2))
    key, n = ctrl.game.key(), ctrl.ply
    assert ctrl.position_at(n).key() == key
    assert ctrl.position_at(0).key() == GameController(HUMAN_MCTS3).game.key()
    g1 = ctrl.position_at(1)
    assert g1.board[ctrl.history[0].move] == 1 and sum(1 for v in g1.board if v) == 1
    assert ctrl.game.key() == key and ctrl.ply == n
    with pytest.raises(ValueError):
        ctrl.position_at(n + 1)
    assert all(m.time >= 0 for m in ctrl.history)
    total = sum(m.time for m in ctrl.history)
    assert ctrl.side_time(P1) + ctrl.side_time(P2) == pytest.approx(total)
