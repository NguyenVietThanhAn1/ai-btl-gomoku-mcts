# Rollout policies — `gameai/agents/rollout.py`

> Mục tiêu của file này: agent/thành viên khác dùng được module **mà không cần đọc code**.
> Cập nhật cùng lúc với code.

**Trạng thái:** ✅ ổn định (bản chuẩn; bản nhanh cho k-in-row ở `heuristics/kinrow_rollout.py`)  ·  **Task:** P3.1 (D-11), P3.2 (D-12)  ·  **Cập nhật:** 2026-11-10

## Mục đích
Chính sách chọn nước trong pha mô phỏng (simulation) của MCTS, và `value_fn` chấm điểm khi rollout bị cắt.
So sánh random vs heavy là thí nghiệm E5 (đề ý 5); `value_fn` là cầu nối tới ý "value network" (P8.3).

## Public API
```python
RolloutPolicy = Callable[[Game, random.Random], Move]
ValueFn = Callable[[Game], float]                 # xác suất P1 thắng, trong [0, 1]

class RandomRollout:   name = "random"; def __call__(self, game, rng) -> Move
class HeavyRollout:    name = "heavy"
    def __init__(self, score_fn: MoveFn, temperature: float = 100.0): ...   # T ≤ 0 → ValueError
    def __call__(self, game, rng) -> Move
def make_policy(policy: str | RolloutPolicy, score_fn: MoveFn | None = None) -> RolloutPolicy
def sigmoid_value(eval_fn: EvalFn, scale: float) -> ValueFn                    # scale ≤ 0 → ValueError
```
- `RandomRollout`: `rng.choice(game.candidate_moves())`.
- `HeavyRollout(score_fn, T)`: chấm `score_fn(game, m)` mọi candidate, lấy mẫu với xác suất
  ∝ `exp((s − max) / T)` (`rng.choices`). K-in-row: `score_fn = kinrow_eval.move_score`.
- `make_policy`: `"random"` → `RandomRollout()`; `"heavy"` → `HeavyRollout(score_fn)` (thiếu `score_fn` →
  `ValueError`); callable → trả nguyên; chuỗi khác → `ValueError`. `MCTSAgent` gọi hàm này.
- `sigmoid_value(eval_fn, scale)(g) = 1 / (1 + exp(−eval_fn(g, P1) / scale))`, không tràn số với eval rất lớn.
- `HeavyRollout` là **bản chuẩn** (tổng quát, chậm). Với k-in-row dùng `KInRowHeavyRollout(T)`
  (`heuristics/kinrow_rollout.md`): cùng chuỗi nước với `HeavyRollout(move_score, T)` khi cùng rng (có test),
  nhanh hơn 4–11× mỗi rollout. `make_policy("heavy")` vẫn trả bản chuẩn.
- Policy chỉ dùng `rng` được truyền vào (RNG của agent) → tái lập theo seed. Không mutate `game`.

## Phụ thuộc
- Dùng: `core/game.py` (`P1`), `agents/alphabeta.py` (`MoveFn`), `agents/minimax.py` (`EvalFn`).
- Hàm truyền vào: `heuristics/kinrow_eval.py` (`move_score`, `evaluate`).
- Được dùng bởi: `agents/mcts.py`, `heuristics/kinrow_rollout.py` (test so với bản chuẩn),
  `experiments/p32_heavy_speed.py`, `experiments/e5_rollout.py` (chưa có).

## Thiết kế & quyết định (D-11)
- **Softmax thay cho ngưỡng thắng/chặn:** bậc WIN (10^6) / BLOCK (10^5) của `move_score` cách delta thường
  (vài chục – vài nghìn) rất xa nên với T = 100 trọng số các nước khác ≈ e^−1000 = 0 → thắng ngay, rồi chặn
  thua ngay, được chọn với xác suất ≈ 1, không cần biết hằng số của k-in-row. Còn lại nghiêng về nước có
  delta cao nhưng vẫn ngẫu nhiên (T lớn → gần đều; T nhỏ → gần argmax).
- **Loại ε-greedy:** đo được rollout ε-greedy (ε = 0,3) theo `move_score` chỉ dài 5,8 nước trên 15×15, bên đi
  trước trong rollout gần như luôn thắng → tín hiệu lệch.
- **Chi phí** (15×15, sau 6 nước, máy dev): random 0,35 ms/rollout (trung bình 91 nước); chấm `move_score`
  ~100 candidate 0,5 ms/bước → heavy ~0,5–0,6 ms/bước, chơi tới hết ~45 ms/rollout (≈ 100× random). Vì vậy
  dùng bản nhanh `KInRowHeavyRollout` (P3.2) cho thí nghiệm.
- **Rollout heavy rất ngắn ở T nhỏ** (`results/tables/p32_heavy_speed.csv`, 15×15): T=100 trung bình
  9,4 nước sau khai cuộc 6 nước (5,1 sau 20 nước), T=300: 13,3 / 5,8, T=1000: 33,1 / 22,4; random 80–88.
  Heavy thích tạo open-four nhưng chỉ thấy đe dọa k−1 quân (không chặn open-three) nên ván thử kết thúc
  nhanh. Vì vậy ở T=100, **`rollout_limit=10` gần như không có tác dụng** (đa số rollout kết thúc trước
  10 nước); `rollout_limit` chỉ đáng kể ở T lớn. Tính theo rollout, bản chuẩn chậm ~10× random (không
  phải ~100× như theo bước).
- `value_fn` trả xác suất của **P1** (không phải người đi) để `backpropagate` chỉ có một quy ước z.

## Giải thích cho báo cáo
**Bản chất.** Giá trị một nút MCTS được ước lượng bằng trung bình kết quả các ván chơi thử từ nút đó. Rollout
ngẫu nhiên đều không thiên lệch nhưng nhiễu: hai bên bỏ qua cả nước thắng ngay lẫn nước chặn, nên kết quả
ván thử ít liên quan tới giá trị thật. Rollout "heavy" dùng tri thức (hàm điểm heuristic) để ván thử giống ván
thật hơn: tín hiệu ít nhiễu hơn trên mỗi rollout nhưng mỗi rollout đắt hơn → so sánh công bằng phải xét cả
cùng số iteration lẫn cùng thời gian (E5). Cắt rollout sau L nước rồi chấm bằng hàm lượng giá là thay phần
"chơi tiếp tới hết" bằng một ước lượng giá trị — cùng vai trò với value network trong AlphaGo.

**Công thức.**
```
P(m) = exp((s_m − s_max) / T) / Σ_j exp((s_j − s_max) / T),   s_m = move_score(s, m)
value_fn(s) = σ(eval(s, P1) / scale) = 1 / (1 + e^(−eval(s, P1)/scale))
```

**Ví dụ trace tay** (15×15, T = 100): ba candidate có điểm 1 000 000 (thắng ngay), 1 915 (tạo open-four),
20 (nước thường) → trọng số 1, e^−9981 ≈ 0, e^−9999,8 ≈ 0 → luôn thắng ngay. Không có nước chiến thuật:
điểm 300, 200, 20 → trọng số 1; e^−1 = 0,37; e^−2,8 = 0,06 → xác suất 0,70 / 0,26 / 0,04.

**Chọn tham số.** T = 100 tạm thời theo thang delta (nước thường ~20, tạo three vài trăm, tạo four ~1000);
T, `rollout_limit` và `scale` của `sigmoid_value` chọn bằng quét sơ bộ ở P3.3 (sau P4.1) trước E5:
T ∈ {100, 300, 1000} × {không cắt, cắt 10 + `sigmoid_value`}, `scale` hiệu chỉnh bằng hồi quy logistic (D-12).

## Test
- File: `tests/test_rollout.py` — random trả candidate và tái lập theo rng; heavy luôn thắng ngay (15×15) và
  luôn chặn four; T nhỏ → chỉ chọn trong argmax, T rất lớn → > 20 nước khác nhau; T ≤ 0 lỗi; `make_policy`
  (chuỗi, callable, thiếu `score_fn`, tên sai); `sigmoid_value` (0 → 0,5, ±10^12 không tràn, đối xứng,
  luôn gọi eval với P1, scale ≤ 0 lỗi). Heavy trong MCTS: `tests/test_mcts.py::test_heavy_rollout_policy`.
- Chạy riêng: `python -m pytest tests/test_rollout.py -q` (< 1 s).

## Hạn chế / TODO
- P3.3: chọn T, `rollout_limit`, `scale` (quét sơ bộ, D-12).
- Heavy dùng `move_score` nên chỉ thấy đe dọa k−1 quân (không thấy open-three của đối thủ là nguy hiểm).
