"""MCTSAgent: Monte Carlo Tree Search với UCT (đề ý 2, 4, 5).

Mỗi iteration: Selection (UCT) → Expansion (1 node) → Simulation (rollout policy) → Backpropagation.
Bất biến: `W`, `N` của node tính theo góc nhìn `player_just_moved` (người vừa đi nước dẫn vào node);
thắng = 1, hòa = 0,5, thua = 0. Lật góc nhìn **chỉ** xảy ra trong `backpropagate`.
"""

from __future__ import annotations

import math
import random
import time

from gameai.agents.alphabeta import MoveFn
from gameai.agents.base import Agent
from gameai.agents.rollout import RolloutPolicy, ValueFn, make_policy
from gameai.core.game import DRAW, P1, Game, Move, result_for

FINAL_MOVES = ("max_n", "max_wn")

# stats["tactic"]
TACTIC_NONE, TACTIC_WIN, TACTIC_BLOCK, TACTIC_RESTRICT = 0, 1, 2, 3


class Node:
    """Node của cây tìm kiếm. `W/N` = tỷ lệ điểm của `player_just_moved`."""

    __slots__ = ("move", "parent", "children", "untried", "W", "N", "player_just_moved")

    def __init__(
        self, move: Move | None, parent: Node | None, player_just_moved: int, untried: list[Move]
    ) -> None:
        self.move = move
        self.parent = parent
        self.player_just_moved = player_just_moved
        self.untried = untried  # nước chưa mở rộng; [] nếu node là trạng thái kết thúc
        self.children: list[Node] = []
        self.W = 0.0
        self.N = 0


def uct(child: Node, log_np: float, c: float) -> float:
    """UCT(i) = W_i/N_i + c·sqrt(ln N_p / N_i), với `log_np` = ln N_p. Yêu cầu N_i ≥ 1."""
    return child.W / child.N + c * math.sqrt(log_np / child.N)


def select_child(node: Node, c: float) -> Node:
    """Con có UCT lớn nhất; bằng nhau → con mở rộng trước. Không lật dấu: W của con đã theo góc nhìn
    người sắp đi ở `node`."""
    log_np = math.log(node.N)
    best, best_v = node.children[0], -math.inf
    for child in node.children:
        v = uct(child, log_np, c)
        if v > best_v:
            best, best_v = child, v
    return best


def backpropagate(node: Node, z: float) -> None:
    """Cộng kết quả mô phỏng từ `node` lên gốc. `z` = điểm của P1 ∈ [0, 1].

    Chỗ lật góc nhìn duy nhất: node của P1 nhận z, node của đối thủ nhận 1 − z.
    """
    while node is not None:
        node.N += 1
        node.W += z if node.player_just_moved == P1 else 1.0 - z
        node = node.parent


class MCTSAgent(Agent):
    """MCTS-UCT. Ngân sách: `iterations` và/hoặc `time_limit` (giây), dừng khi chạm cái nào
    trước."""

    def __init__(
        self,
        iterations: int | None = 1000,
        time_limit: float | None = None,
        c: float = math.sqrt(2),
        rollout_policy: str | RolloutPolicy = "random",
        score_fn: MoveFn | None = None,
        rollout_limit: int | None = None,
        value_fn: ValueFn | None = None,
        final_move: str = "max_n",
        check_tactics: bool = False,
        seed: int | None = None,
    ) -> None:
        super().__init__()
        if iterations is None and time_limit is None:
            raise ValueError("cần ít nhất một trong iterations / time_limit")
        if iterations is not None and iterations < 1:
            raise ValueError("iterations phải ≥ 1")
        if time_limit is not None and time_limit <= 0:
            raise ValueError("time_limit phải > 0")
        if c < 0:
            raise ValueError("c phải ≥ 0")
        if rollout_limit is not None and rollout_limit < 0:
            raise ValueError("rollout_limit phải ≥ 0 hoặc None")
        if final_move not in FINAL_MOVES:
            raise ValueError(f"final_move phải thuộc {FINAL_MOVES}")
        self.iterations = iterations
        self.time_limit = time_limit
        self.c = c
        self.policy = make_policy(rollout_policy, score_fn)
        self.rollout_limit = rollout_limit
        self.value_fn = value_fn
        self.final_move = final_move
        self.check_tactics = check_tactics
        self.rng = random.Random(seed)
        self.root: Node | None = None  # cây của lần tìm gần nhất (None nếu đi tắt bằng tactic)
        self._rollout_plies = 0

    # ------------------------------------------------------------------ public

    def last_root_stats(self) -> list[tuple[Move, float, int, float]]:
        """(move, W, N, W/N) của các con của gốc, sắp N giảm dần. [] nếu lần trước không search."""
        if self.root is None:
            return []
        rows = [(ch.move, ch.W, ch.N, ch.W / ch.N) for ch in self.root.children]
        rows.sort(key=lambda r: r[2], reverse=True)  # ổn định: bằng N giữ thứ tự mở rộng
        return rows

    def _select_move(self, game: Game) -> Move:
        assert not game.is_terminal(), "select_move gọi trên ván đã kết thúc"
        t0 = time.perf_counter()
        self.root = None
        self._rollout_plies = 0
        root_moves: list[Move] | None = None
        tactic = TACTIC_NONE
        if self.check_tactics:
            move, tactic, root_moves = self._tactics(game)
            if move is not None:  # đi tắt, không search: value = 1 nếu thắng ngay, NaN nếu chặn
                value = 1.0 if tactic == TACTIC_WIN else math.nan
                self._write_stats(t0, 0, 0, value, max_depth=0, tactic=tactic)
                return move
        if root_moves is None:
            root_moves = list(game.candidate_moves())

        root = Node(None, None, -game.current_player(), root_moves)
        self.root = root
        iterations, nodes, max_depth = self._search(game, root, t0)
        best = self._final_child(root)
        self._write_stats(
            t0,
            iterations=iterations,
            nodes=nodes,
            value=best.W / best.N,
            max_depth=max_depth,
            tactic=tactic,
        )
        return best.move

    # ----------------------------------------------------------------- search

    def _search(self, game: Game, root: Node, t0: float) -> tuple[int, int, int]:
        """Chạy các iteration trên `root`. Trả (iterations, nodes, max_depth)."""
        max_iter = self.iterations
        deadline = None if self.time_limit is None else t0 + self.time_limit
        rng, c = self.rng, self.c
        iterations, nodes, max_depth = 0, 1, 0
        while True:
            if max_iter is not None and iterations >= max_iter:
                break
            # luôn chạy ít nhất 1 iteration để gốc có con
            if deadline is not None and iterations > 0 and time.perf_counter() >= deadline:
                break
            g = game.clone()  # 1,5 µs trên 15×15 — rẻ hơn undo cả rollout
            node, depth = root, 0

            # 1. Selection: đi xuống khi node đã mở rộng hết và còn con
            while not node.untried and node.children:
                node = select_child(node, c)
                g.play(node.move)
                depth += 1

            # 2. Expansion: thêm đúng 1 con, chọn ngẫu nhiên trong untried (swap-pop O(1))
            if node.untried:
                untried = node.untried
                i = rng.randrange(len(untried))
                move = untried[i]
                untried[i] = untried[-1]
                untried.pop()
                mover = g.current_player()
                g.play(move)
                untried_child = [] if g.is_terminal() else list(g.candidate_moves())
                child = Node(move, node, mover, untried_child)
                node.children.append(child)
                node = child
                nodes += 1
                depth += 1

            # 3. Simulation  4. Backpropagation
            backpropagate(node, self._simulate(g))
            iterations += 1
            if depth > max_depth:
                max_depth = depth
        return iterations, nodes, max_depth

    def _simulate(self, g: Game) -> float:
        """Rollout từ `g` (bị mutate). Trả z = điểm của P1 ∈ [0, 1]."""
        policy, rng, limit = self.policy, self.rng, self.rollout_limit
        plies = 0
        while not g.is_terminal():
            if limit is not None and plies >= limit:
                self._rollout_plies += plies
                return self.value_fn(g) if self.value_fn is not None else 0.5
            g.play(policy(g, rng))
            plies += 1
        self._rollout_plies += plies
        return result_for(g.winner(), P1)

    def _final_child(self, root: Node) -> Node:
        """`max_n`: N lớn nhất (bằng → W lớn hơn); `max_wn`: W/N lớn nhất (bằng → N lớn hơn).
        Còn bằng nữa → con mở rộng trước."""
        if self.final_move == "max_n":
            return max(root.children, key=lambda ch: (ch.N, ch.W))
        return max(root.children, key=lambda ch: (ch.W / ch.N, ch.N))

    # ---------------------------------------------------------------- tactics

    def _tactics(self, game: Game) -> tuple[Move | None, int, list[Move] | None]:
        """Kiểm tra trước khi search, chỉ qua play/undo (dùng được cho mọi `Game`).

        Trả (nước đi ngay | None, mã tactic, tập nước cho gốc | None).
        """
        me = game.current_player()
        moves = list(game.candidate_moves())
        for m in moves:  # thắng ngay
            game.play(m)
            w = game.winner()
            game.undo()
            if w == me:
                return m, TACTIC_WIN, None
        safe = []  # nước mà sau đó đối thủ không thắng ngay
        for m in moves:
            game.play(m)
            lost = False
            if game.winner() is None:
                for reply in game.candidate_moves():
                    game.play(reply)
                    w = game.winner()
                    game.undo()
                    if w is not None and w != DRAW and w != me:
                        lost = True
                        break
            game.undo()
            if not lost:
                safe.append(m)
        if len(safe) == 1:
            return safe[0], TACTIC_BLOCK, None
        if 0 < len(safe) < len(moves):
            return None, TACTIC_RESTRICT, safe
        return None, TACTIC_NONE, None  # S = ∅ (đã thua) hoặc mọi nước đều an toàn

    def _write_stats(
        self,
        t0: float,
        iterations: int,
        nodes: int,
        value: float,
        max_depth: int,
        tactic: int,
    ) -> None:
        self.stats["iterations"] = iterations
        self.stats["nodes"] = nodes
        self.stats["time"] = time.perf_counter() - t0
        self.stats["value"] = value
        self.stats["max_depth"] = max_depth
        self.stats["rollout_plies"] = self._rollout_plies
        self.stats["tactic"] = tactic
