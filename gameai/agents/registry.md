# Registry — `gameai/agents/registry.py`

> Mục tiêu của file này: agent/thành viên khác dùng được module **mà không cần đọc code**.
> Cập nhật cùng lúc với code.

**Trạng thái:** ✅ ổn định  ·  **Task:** P4.1 (D-13)  ·  **Cập nhật:** 2026-11-10

## Mục đích
Mô tả agent / game bằng dữ liệu kiểu JSON (`AgentSpec`, `GameSpec`) và dựng object **mới** từ đó. Spec
pickle được (chạy qua `ProcessPoolExecutor` trên Windows) và băm được (`config_hash` để resume).

## Public API
```python
@dataclass(frozen=True)
class AgentSpec:
    kind: str                       # "random" | "greedy" | "minimax" | "alphabeta" | "mcts" | "module:Class"
    params: dict = {}               # chỉ giá trị JSON
    label: str | None = None        # tên hiển thị / cột label_a, label_b; None → kind
    name: str                       # property: label or kind
    def to_dict(self) -> dict       # TypeError nếu params không phải JSON
@dataclass(frozen=True)
class GameSpec:
    kind: str = "kinrow"; params: dict = {}      # vd. GameSpec("kinrow", {"n": 15, "k": 5})
    def to_dict(self) -> dict
FUNCTIONS: dict[str, Callable]      # "move_score", "evaluate", "delta_eval"
def make_agent(spec: AgentSpec, seed: int | None) -> Agent
def make_game(spec: GameSpec) -> Game
```
**Params theo `kind`** (còn lại truyền thẳng vào constructor; khóa lạ → `TypeError`):

| kind | params riêng (tên hàm là chuỗi trong `FUNCTIONS`) | truyền thẳng |
|---|---|---|
| `random` | — | `use_candidates` |
| `greedy` | `score` (mặc định `"move_score"`) | `use_candidates` |
| `minimax` | `eval` (None) | `depth`, `use_candidates` |
| `alphabeta` | `eval`, `delta`, `order` (đều None) | `depth`, `use_candidates`, `use_tt` |
| `mcts` | `rollout` (`"random"` / `"heavy"` = `HeavyRollout(score, temperature)` bản chuẩn / `"heavy_kinrow"` = `KInRowHeavyRollout(temperature)`), `temperature` (100), `score` (`"move_score"`), `value_scale` (None; có → `sigmoid_value(value_eval, value_scale)`), `value_eval` (`"evaluate"`) | `iterations`, `time_limit`, `c`, `rollout_limit`, `final_move`, `check_tactics` |
| `"module:Class"` | — | mọi params, gọi `Class(seed=seed, **params)` |

- Param chung `seeded` (mặc định `true`): `false` → truyền `seed=None` (Minimax/AB tất định).
- Sai config (kind lạ, tên hàm lạ, rollout lạ, khóa lạ) → `ValueError` / `TypeError`.

Ví dụ (đối thủ chuẩn D-10 và MCTS heavy cho P3.3):
```python
GREEDY = AgentSpec("greedy", label="greedy")
AB2 = AgentSpec("alphabeta", {"depth": 2, "eval": "evaluate", "delta": "delta_eval",
                              "order": "move_score"}, label="ab2")
MCTS_H = AgentSpec("mcts", {"iterations": None, "time_limit": 0.5, "rollout": "heavy_kinrow",
                            "temperature": 300, "rollout_limit": 10, "value_scale": 500}, label="h300c10")
```

## Phụ thuộc
- Dùng: mọi agent trong `agents/`, `agents/rollout.py` (`sigmoid_value`, `HeavyRollout`),
  `heuristics/kinrow_eval.py`, `heuristics/kinrow_rollout.py`, `games/kinrow.py`.
- Được dùng bởi: `arena.py`, `experiments/common.py`.

## Thiết kế & quyết định (D-13)
- Spec thay vì object/lambda: lambda không pickle được với spawn; spec cho nhãn + hash ổn định, và mỗi ván
  dựng agent mới.
- Đây là module **duy nhất** trong `agents/` import heuristic của k-in-row (tầng ghép nối). Cờ tướng (P8)
  thêm hàm vào `FUNCTIONS` và `GameSpec` kind mới.
- `"module:Class"` cho agent thử nghiệm / agent lỗi giả trong test (worker import được qua `sys.path`).

## Test
- `tests/test_arena.py` (phần registry): dựng mọi kind, heavy_kinrow đúng object và T, agent mới mỗi lần,
  seed điều khiển lựa chọn, `seeded: false`, đường dẫn `module:Class`, sai config → lỗi, params không JSON →
  `TypeError`, `name` / `to_dict`.
- Chạy: `python -m pytest tests/test_arena.py -q -k "make_ or spec"`.

## Hạn chế / TODO
- `value_fn` chỉ hỗ trợ dạng sigmoid của một hàm eval có tên.
