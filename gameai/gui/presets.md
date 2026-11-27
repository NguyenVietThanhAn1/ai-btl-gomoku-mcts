# Presets GUI — `gameai/gui/presets.py`

> Mục tiêu của file này: agent/thành viên khác dùng được module **mà không cần đọc code**.
> Cập nhật cùng lúc với code.

**Trạng thái:** ✅ ổn định  ·  **Task:** P6.1 (D-28), P6.3 (D-29), P6.2 (D-37)  ·  **Cập nhật:** 2026-11-25

## Mục đích
Các chế độ chơi của GUI, mô tả bằng `GameSpec` + `AgentSpec` của registry — **cùng spec với thí nghiệm**
(không tự dựng tham số riêng), để AI trong video đúng là AI trong báo cáo.

## Public API
```python
HUMAN = None
@dataclass(frozen=True)
class Preset:
    key: str; title: str; game: GameSpec
    x: AgentSpec | None             # đi trước (P1); None = người
    o: AgentSpec | None             # đi sau (P2)
    delay: float = 0.0              # giây chờ tối thiểu trước mỗi nước AI
    has_human: bool                 # property
MCTS_3X3 = e2_never_lose.mcts_spec(1000)          # 1000 iter, c = √2, tactics tắt (D-16)
MCTS_H300 = e3_c_sweep.mcts_spec(15, 1.4, 5000)   # h300 + tactics (D-14), 5000 iter
PRESETS: dict[str, Preset]; PRESET_ORDER: list[str]   # phím 1/2/3 theo thứ tự này
def swap_sides(p) -> Preset                 # đổi X ↔ O
def with_iterations(p, n) -> Preset         # đổi iterations mọi bên MCTS (ValueError nếu n < 1)
def mcts_iterations(p) -> int | None        # iteration của bên MCTS đầu tiên
def side_label(spec) -> str                 # "Người", "MCTS h300 5000 iter, c=1.4, tactics", "Alpha-Beta đầy đủ, ordering, TT"

# Độ khó (P6.3, D-29)
LEVELS = ("easy", "medium", "hard"); LEVEL_NAMES = {...: "Dễ"/"Vừa"/"Khó"}; AI_KINDS = ("mcts", "alphabeta")
@dataclass(frozen=True) class Level: spec: AgentSpec; source: str | None   # "E1"/"E2"/"E3"/"E3/E5"/"E7"; None = cấu hình riêng
    source_text: str   # "cấu hình E3" / OWN_CONFIG ("cấu hình riêng của chế độ chơi, không có trong thí nghiệm")
XIANGQI = GameSpec("xiangqi", {})            # P6.2; max_plies mặc định 300 (D-22)
BoardKey = int | str                         # khóa trò: 3, 15 (cạnh bàn k-in-row) hoặc "xiangqi"
def board_key(game: GameSpec) -> BoardKey    # kinrow → params["n"]; trò khác → game.kind
DIFFICULTY: dict[(BoardKey, kind, level), Level]   # 18 ô: 3×3, 15×15, cờ tướng × 2 AI × 3 mức
XQ_MCTS_TIMES = {"easy": 0.3, "medium": 1.0, "hard": 2.5}; XQ_AB: dict[level, AgentSpec]
def level_for(board, kind, level) -> Level   # board = BoardKey; KeyError nếu không có
def find_level(spec, board) -> (level, Level) | None   # tra ngược (thẻ người chơi, nhãn Demo)
MCTS_DEFAULTS: dict    # mặc định thật của MCTSAgent qua inspect (c = √2, iterations = 1000, …) — không gõ tay
def mcts_param(spec, name); def rollout_tag(spec) -> "random"|"h300"|"heavy"|"cắt 10 + eval" (có rollout_limit); def budget_text(spec)
def short_label(spec) -> str                       # "người", "MCTS h300 5000", "Alpha-Beta d2"
def preset_title(game, x, o) -> str               # tiêu đề preset suy từ spec (PRESETS dùng hàm này)
def source_of(spec, board) -> str | None             # source_text của spec, None nếu không có trong bảng
AB3_D1, AB3_D2, AB15_D1, AB15_HARD          # spec riêng; AB15_HARD (D-36): ID/top-k/TT sâu/VCF (P6.4)
EXPERIMENT_SPECS = [(15, AB2, "E3/E5")]      # spec thí nghiệm chỉ còn ở Demo (không phải mức độ khó)
def experiment_source(spec, board) -> str | None   # 'E3/E5' cho AB2 trên 15×15, còn lại None
```

| Trò | AI | Dễ | Vừa | Khó |
|---|---|---|---|---|
| 3×3 | MCTS | `e2.mcts_spec(100)` — E2 | `e2.mcts_spec(1000)` — E2 | `e2.mcts_spec(5000)` — E2 |
| 3×3 | AB | depth 1 + `evaluate` — riêng | depth 2 + `evaluate` — riêng | `e1.VARIANTS_3["ab_order_tt"]` — E1 |
| 15×15 | MCTS | `e3.mcts_spec(15, 1.4, 250)` — E3 | `e3.mcts_spec(15, 1.4, 1000)` — E3 | `e3.mcts_spec(15, 1.4, 5000)` — E3 |
| 15×15 | AB | depth 1 + eval + delta + ordering — riêng | `e1.variants_15(3)["ab_order"]` — E1 (**Khó cũ**) | `AB15_HARD` — riêng (D-36) |
| Cờ tướng | MCTS | `xq_mcts_spec(time_limit=0.3, tactics=True)` — riêng | `xq_mcts_spec(time_limit=1.0, tactics=True)` — E7 | `xq_mcts_spec(time_limit=2.5, tactics=True)` — E7 |
| Cờ tướng | AB | `ab_spec(1)` — E7 | `ab_spec(2, use_tt=True)` — riêng (= nguồn nhãn D-24) | `ab_spec(12, use_tt=True, time_limit=2.0)` — riêng |

**Cờ tướng (P6.2, D-37):** `xq_mcts_spec` (`experiments/p83_mcts_check.py`): rollout cắt `XQ_MCTS_L` = 10 ply rồi
σ(`xq_evaluate`/2000), c = √2, tactics **bật**, ngân sách theo thời gian (`iterations` = None). `ab_spec`
(`experiments/p82_ab_check.py`): `xq_evaluate` + `xq_delta` + order `xq_mvv_lva`, `seeded: false`, TT "exact", **không**
`top_k`/`tt_mode="deep"` (D-23: chưa đo trên cờ tướng). Spec gọi hàm thí nghiệm, không gõ tay. Nguồn
(`XQ_SOURCES`, D-39): "E7" cho mức trùng tham số E7 (MCTS Vừa = d1 1 s, MCTS Khó = d2 2,5 s, AB Dễ = a1), còn lại
= cấu hình riêng. Nhãn: "MCTS cắt 10 + eval, 1 s/nước, c=1.41, tactics",
"Alpha-Beta ID ≤12, 2 s/nước, ordering, TT".

**D-36 (2026-11-18):** bảng trên thay phần bảng độ khó của D-29 ở dòng AB 15×15 (D-29 giữ nguyên làm lịch sử): Vừa = Khó cũ (E1), Khó = `AB15_HARD` =
`depth` tối đa 12 + `time_limit` 2,4 s (iterative deepening) + `delta_eval` + `move_score` + `top_k` (16, 12, 8) *(chốt sau B5)* + TT sâu +
VCF ở gốc (`vcf_depth` 8, `vcf_time` 0,3 s). Lý do: Khó cũ quá dễ với người chơi. `e3.AB2` không còn là mức
độ khó nhưng vẫn là bên O của preset Demo (`15_h300_vs_ab2`, nhãn "cấu hình thí nghiệm · E3/E5").

- **Mọi số hiển thị (c, iter, depth, T) suy từ `AgentSpec`** (thiếu tham số → mặc định của `MCTSAgent`): E2 hiện
  c=1.41 (= √2 mặc định), E3 c=1.4 (trong spec); tiêu đề 3 preset sinh bằng `preset_title` (P6.3 3c, test kiểm).

| key | Bàn | X | O | delay |
|---|---|---|---|---|
| `3x3_human_mcts` | 3×3 k3 | người | MCTS random 1000 (spec E2) | 0 |
| `15_human_h300` | 15×15 k5 | người | MCTS h300 5000 + tactics (spec E3) | 0 |
| `15_h300_vs_ab2` | 15×15 k5 | MCTS h300 5000 + tactics | `e3_c_sweep.AB2` (depth 2) | 0,5 s |

## Phụ thuộc
- Dùng: `agents/registry.py`, `experiments/e1_nodes.py` (`VARIANTS_3`, `variants_15`), `experiments/e2_never_lose.py` (`mcts_spec`), `experiments/e3_c_sweep.py`
  (`mcts_spec`, `AB2`, `GAME3`, `GAME15`), `experiments/p82_ab_check.py` (`ab_spec`), `experiments/p83_mcts_check.py` (`xq_mcts_spec`).
- Được dùng bởi: `gui/controller.py`, `gui/pygame_app.py`, `gui/game_config.py`.

## Thiết kế & quyết định (D-28)
- 15×15 dùng 5000 iter: E3 (c = 1,4) h300 vs Greedy thắng 0,92 ở 5000 iter, chỉ 0,48 ở 1000 iter
  (`results/tables/e3_greedy.csv`). Chi phí ~2,1 s/nước (đo một lần trên máy dev, thế 5 quân, ngoài GUI).
- Lưu ý cho video: h300 5000 vs AB2 chỉ thắng 0,22 (`results/tables/e3_ab2.csv`) → ở preset 3 AB thường
  thắng; đúng với số liệu, không phải lỗi.
- Độ khó (D-29): chỉ ánh xạ sang `AgentSpec`; mức "E" trùng hệt spec thí nghiệm (test `==`), mức riêng chỉ ở AB
  (An cho phép). Spec E1 `seeded=False` → AB tất định. Thời gian/nước từng mức: D-29 (MCTS, 3×3, AB Dễ), D-36 (AB 15×15 mới).
- Đổi tham số chỉ tạo spec mới (`dataclasses.replace`), preset gốc không đổi.

## Test
- `tests/test_gui_controller.py`: spec preset == spec thí nghiệm, dựng được agent; `with_iterations`, `swap_sides`.
- `tests/test_gui_config.py`: bảng `DIFFICULTY` đủ 18 ô (6 cờ tướng == hàm thí nghiệm P8.2/P8.3, tactics bật, không top_k), mức "E" == hàm thí nghiệm, mức riêng đúng tham số, dựng được agent; `side_label` AB.

## Hạn chế / TODO
- Chưa có preset Demo cờ tướng (đợi spec E7 ở P8.4); phím 1/2/3 vẫn là 3 preset k-in-row.
- Thời gian/nước các mức cờ tướng trong GUI: D-37 (Khó MCTS 2,50 s, AB 2,00 s; minh họa).
