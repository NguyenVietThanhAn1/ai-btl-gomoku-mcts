# Alpha-Beta — `gameai/agents/alphabeta.py`

> Mục tiêu của file này: agent/thành viên khác dùng được module **mà không cần đọc code**.
> Cập nhật cùng lúc với code.

**Trạng thái:** ✅ ổn định  ·  **Task:** P2.4, P6.4 (`top_k`, `root_hook`, `time_limit` = iterative deepening, `tt_mode`)  ·  **Cập nhật:** 2026-11-18

## Mục đích
Minimax có cắt tỉa alpha-beta (đề ý 1): **cùng giá trị gốc** với `MinimaxAgent` nhưng thăm ít nút hơn.
Tùy chọn move ordering, cộng dồn lượng giá tăng dần (`delta_eval`) và transposition table (TT).
Là agent tìm kiếm chính cho 15×15 (depth 2–3) và đối tượng của thí nghiệm E1.

## Public API
```python
MoveFn = Callable[[Game, Move], float]
class AlphaBetaAgent(Agent):
    def __init__(self, depth: int | None = None, eval_fn: EvalFn | None = None,
                 use_candidates: bool = True, seed: int | None = None,
                 order_fn: MoveFn | None = None, delta_fn: MoveFn | None = None,
                 use_tt: bool = False, top_k: int | Sequence[int] | None = None,
                 root_hook: RootHook | None = None,
                 time_limit: float | None = None, tt_mode: str = "exact"): ...
    def select_move(self, game: Game) -> Move            # từ Agent (template method)
    def search(self, game: Game) -> tuple[Move, float]   # (nước tốt nhất, giá trị gốc)
    def value(self, game: Game) -> float                 # = MinimaxAgent(...).value với cùng depth/eval
```
- `depth`, `eval_fn`, `use_candidates`: như `MinimaxAgent` (`depth=None` → tìm tới kết thúc; `depth<1` → `ValueError`).
- `order_fn(game, move)`: điểm sắp xếp, duyệt nước **giảm dần** ở mọi nút mở rộng. K-in-row: `kinrow_eval.move_score`.
- `delta_fn(game, move)`: thay đổi lượng giá theo góc nhìn **người sắp đi**, gọi *trước* `play`.
  K-in-row: `kinrow_eval.delta_eval`. Khi có `delta_fn`, lá = `eval_fn(gốc, root)` (hoặc 0 nếu không có
  `eval_fn`) + Σ(±delta) dọc nhánh → bằng `eval_fn(lá)` nếu delta chính xác, nhưng O(k²)/nút thay vì
  quét toàn bàn. Chỉ có tác dụng khi `depth` khác `None`.
- `use_tt`: bật TT theo `game.key()`, xóa ở đầu mỗi lần `search`.
- `seed`: `None` → nước tốt nhất đầu tiên theo thứ tự duyệt (tất định). Có seed → xáo thứ tự nước **ở gốc**
  trước khi sort ổn định theo `order_fn` → tie-break ngẫu nhiên giữa các nước bằng điểm (không đảm bảo đều).
- `top_k` (P6.4, mặc định `None` = tắt, hành vi cũ không đổi): sau khi sắp theo `order_fn` chỉ duyệt **k nước đầu**.
  `int` = cùng k ở mọi ply; dãy = k theo ply (phần tử 0 = gốc, 1 = ply 1, …; ply vượt dãy dùng phần tử cuối). Cần
  `order_fn` (không có → `ValueError`). **Đây là cắt tỉa xấp xỉ, không phải alpha-beta chính xác:** giá trị gốc có
  thể khác Minimax (nước mạnh nằm ngoài top-k bị bỏ qua). Hệ quả với TT: khóa TT chỉ gồm `(key, độ sâu còn lại)`,
  còn k phụ thuộc **ply** → hai entry cùng thế, cùng độ sâu còn lại nhưng ở ply khác (k khác) có thể mang giá trị
  khác nhau, và TT dùng lại chúng. Chấp nhận có chủ đích (tìm kiếm đã xấp xỉ); chế độ `tt_mode="deep"` (đã có)
  cũng dùng lại entry giữa các ply có k khác nhau. Chỉ dùng `top_k` ở chế độ chơi (GUI), không dùng cho thí nghiệm.
- `root_hook(game) -> (nước | None, tập nước | None)` (P6.4, mặc định `None`): gọi **một lần ở gốc** trước khi tìm.
  Nước ≠ None → đi ngay, không tìm (`search` trả `(nước, NaN)`, `stats["root_hook"] = 1`, `nodes = 1`). Tập nước →
  chỉ duyệt các nước thuộc tập (giao với ứng viên; giao rỗng → dùng nguyên tập). Tham số spec `vcf_depth` +
  `vcf_time` dựng hook VCF k-in-row `heuristics/kinrow_vcf.make_root_hook` (xem `kinrow_vcf.md`).
- `time_limit` (P6.4, giây, mặc định `None` = tắt): **iterative deepening** theo thời gian. Lặp độ sâu 1, 2, …
  tới `depth` (= **độ sâu tối đa**, bắt buộc có; thiếu → `ValueError`) hoặc hết giờ; trả nước + giá trị của
  **độ sâu hoàn tất gần nhất**. Độ sâu 1 luôn chạy xong (không kiểm giờ). Kiểm giờ mỗi 32 nút bằng ngoại lệ nội bộ
  `_Timeout`; vòng dở dang bị **bỏ hẳn** (không dùng giá trị một phần) và **không ghi TT cho nút dở dang** (mọi
  ghi TT nằm sau khi duyệt xong con của nút; ngoại lệ thoát trước điểm ghi). Đồng hồ tính từ đầu `search` (gồm
  `root_hook`). Gốc giữ nguyên thứ tự nước ở mọi vòng (không xếp lại theo điểm vòng trước) ⇒ **khi không `top_k`
  và không hết giờ, ID trùng AB depth cố định `depth`** (cùng nước, cùng giá trị) ở TT "exact"
  (`tests/test_alphabeta_id.py`). Có `top_k` hoặc TT "deep" thì không đảm bảo trùng. `search` làm việc trên
  `game.clone()` ở chế độ này (bản bị hủy khi hết giờ).
- `tt_mode` (P6.4): `"exact"` (mặc định, = hành vi cũ: khóa `(key, độ sâu còn lại)`, chỉ dùng lại khi **bằng**
  độ sâu còn lại) hoặc `"deep"` (cần `use_tt=True` và `depth`): khóa chỉ theo `game.key()`, entry
  `(flag, value, độ sâu còn lại, nước tốt nhất)`, dùng lại khi độ sâu còn lại của entry **≥** cần, thay entry khi
  độ sâu mới ≥ cũ, nước tốt nhất của entry đưa lên đầu danh sách nước (PV ordering). TT dùng chung giữa các vòng
  ID trong một `search` và **dùng lại entry giữa các ply có k khác nhau** (xem `top_k`): giá trị lấy từ độ sâu sâu
  hơn / ply khác nên **không còn trùng Minimax cùng depth**. Đầy `TT_MAX_ENTRIES` (2 triệu) → xóa hết.
- `stats`: `nodes` (kể cả gốc, đếm như Minimax), `iterations` = 0, `time` (giây), `value`, `cutoffs`
  (số lần cắt β/α), `tt_hits` (số lần tra TT trúng). Với `time_limit`: thêm `depth_reached` (độ sâu hoàn tất
  cuối), `timed_out` (1 nếu chưa tới `depth`), `tt_size`; `nodes` cộng dồn mọi vòng.
- Không làm thay đổi `game`. Precondition: ván chưa kết thúc.

## Phụ thuộc
- Dùng: `agents/base.py`, `agents/minimax.py` (`terminal_score`, `WIN_SCORE`, `EvalFn`), `core/game.py`.
- Hàm truyền vào (không import cứng): `heuristics/kinrow_eval.py` (`evaluate`, `delta_eval`, `move_score`).
- Được dùng bởi: `experiments/e1_nodes.py`, arena/CLI/GUI (chưa có).

## Thiết kế & quyết định (D-9)
- Max/min tường minh theo góc nhìn `root`, **fail-soft** (trả `best` thật, có thể nằm ngoài [α, β]).
- Terminal dùng chung `terminal_score` = ±(`WIN_SCORE` − ply) với Minimax → so giá trị trực tiếp được.
- Gốc tách riêng: duyệt mọi nước với cửa sổ (α, +∞); chỉ giá trị của nước tốt nhất là chính xác.
- **TT:** lưu `(flag, value)` với flag EXACT / LOWER (fail-high) / UPPER (fail-low) so với (α₀, β₀) ban đầu
  của nút. Khóa = `(game.key(), độ sâu còn lại)` (độ sâu còn lại = `None` khi `depth=None`) — chỉ dùng lại
  khi độ sâu còn lại **bằng nhau**, để giá trị luôn trùng Minimax cùng depth (mất bớt lợi ích so với `≥`).
  Điểm thắng/thua phụ thuộc ply nên được lưu dạng "khoảng cách từ nút" (`_to_tt`/`_from_tt`).
- Đo thử (không phải số liệu E1): bàn trống 3×3 tìm hết — không tùy chọn 20 866 nút, + ordering 1 856,
  + TT 5 505, cả hai 990 (Minimax: 549 946). 15×15 sau 5 nước, depth 3: 9 599 nút; `delta_fn` giảm thời
  gian ~12 lần (1,23 s → 0,10 s), thêm ordering còn 1 959 nút.

- **Đo thử P6.4 (2026-11-18, không phải số liệu thí nghiệm):** 15×15, 8 thế giữa ván (6–34 nước), `time_limit` 2,4 s,
  `depth` tối đa 12, `delta_eval` + `move_score`: `top_k=(16,12,8)` + TT deep → `depth_reached` trung bình 7,6
  (6–10), 10,8 nghìn nút; `top_k=(12,8,6)` + deep → 9,0 (7–12); không `top_k` + deep → 3,4 (3–5, 35,6 nghìn
  nút); `top_k=(16,12,8)` không TT → 7,1 (6–9). Thời gian thực ≤ 2,41 s (quá hạn ≤ 0,01 s).

## Giải thích cho báo cáo
**Bản chất.** Alpha-Beta tính đúng giá trị minimax nhưng bỏ qua các nhánh không thể ảnh hưởng tới quyết định.
Mỗi nút mang cửa sổ [α, β]: α = giá trị tốt nhất MAX đã chắc chắn có được trên đường từ gốc, β = giá trị tốt nhất
MIN đã chắc chắn có được. Khi α ≥ β, người chơi ở tầng trên sẽ không bao giờ để ván đi vào nút này nên các con
còn lại bị cắt. Thứ tự duyệt càng tốt (nước mạnh trước) thì cắt càng sớm: lý tưởng O(b^(d/2)) nút so với O(b^d).

**Pseudocode** (khớp `_alphabeta`, chưa kể TT):
```
ALPHABETA(s, ply, α, β, score):
    nodes += 1
    if s kết thúc:      return ±(WIN − ply) theo góc nhìn root, hòa 0
    if ply = depth:     return score            (hoặc eval(s, root) nếu không dùng delta)
    if lượt của root:   best = −∞
        for m in moves(s) (sắp theo order_fn):
            v = ALPHABETA(play(s,m), ply+1, α, β, score + delta(s,m))
            best = max(best, v);  α = max(α, best);  if α ≥ β: break   # cắt β
    else:               best = +∞
        for m in moves(s):
            v = ALPHABETA(play(s,m), ply+1, α, β, score − delta(s,m))
            best = min(best, v);  β = min(β, best);  if α ≥ β: break   # cắt α
    return best
```

**Ví dụ trace tay** (cùng thế cờ với `minimax.md`: 3×3, X đi; X ở 0, 7, 8; O ở 1, 4, 6; trống 2, 3, 5):
```
X O .     X đi 2: O3 → X5 thắng: W−3 ; O5 → X3 hòa: 0  → min = 0.  Gốc: α = 0
. O .     X đi 3: O2 thắng ngay: −(W−2) ≤ α = 0  → CẮT, không xét O5
O X X     X đi 5: O2 thắng ngay: −(W−2) ≤ α = 0  → CẮT, không xét O3
```
Giá trị gốc = 0, chọn ô 2 (giống Minimax). Số nút = 1 + 5 + 2 + 2 = **10** (Minimax: 14), `cutoffs` = 2.

**Cộng dồn lượng giá.** Vì `delta_eval(s, m) = eval(sau m) − eval(trước m)` theo góc nhìn người đi, giá trị lá
theo góc nhìn root bằng `eval(gốc) + Σ ±delta` (cộng nếu root đi, trừ nếu đối thủ đi) — đúng bằng `eval(lá)`
nhưng không phải quét lại toàn bàn.

**Chọn tham số.** 3×3: `depth=None` (chơi hoàn hảo). 15×15: `depth=2–3`, `eval_fn=evaluate`,
`delta_fn=delta_eval`, `order_fn=move_score` (thắng ngay/chặn được xét đầu tiên → cắt sớm).

## Test
- File: `tests/test_alphabeta.py` — giá trị gốc bằng Minimax trên bàn trống + 25 thế cờ 3×3 ngẫu nhiên với
  4 tổ hợp (ordering, TT), nước chọn là tối ưu theo Minimax, nút ≤ Minimax; depth 2/3 trên 7×7 k=4: chế độ
  `eval_fn` và `delta_fn` đều bằng Minimax; bàn trống 3×3 ít nút hơn nhiều, có cắt, TT có hit; 15×15 depth 2
  thắng ngay và chặn four (có/không delta+ordering); không mutate; AB-vs-AB 3×3 hòa; seed cho nhiều nước khác
  nhau nhưng đều tối ưu; thắng ngay; TT với điểm thắng phụ thuộc ply (fork, thắng ở ply 3) bằng Minimax;
  `depth=0` lỗi.
- Chạy riêng: `python -m pytest tests/test_alphabeta.py -q` (~30 s, chủ yếu là Minimax tham chiếu).

## Hạn chế / TODO
- Không iterative deepening / giới hạn thời gian; TT không dùng lại kết quả sâu hơn và không lưu best move để ordering.
- Tie-break có seed chỉ xáo thứ tự gốc, không chọn đều trong các nước bằng điểm.
- `delta_fn` sai (không đúng bằng hiệu `eval_fn`) → mất tương đương với Minimax; chỉ dùng `delta_eval`.
