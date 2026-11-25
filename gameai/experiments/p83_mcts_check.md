# p83_mcts_check — `gameai/experiments/p83_mcts_check.py`

> Cấu hình MCTS cờ tướng (rollout cắt + eval) và các phép đo của P8.3: tốc độ theo L, hiệu chỉnh `scale`, chi phí `check_tactics`, trận L=0 vs L=10. **Không phải số liệu thí nghiệm** (E7 ở P8.4).

**Trạng thái:** ✅ (L=10 chốt, D-24)  ·  **Task:** P8.3  ·  **Cập nhật:** 2026-11-23

## Mục đích
Dùng nguyên `MCTSAgent` (không sửa `agents/`) cho cờ tướng: rollout ngẫu nhiên cắt `L` ply rồi chấm thế bằng `sigmoid(xq_evaluate / scale)`. Module cho `xq_mcts_spec(...)` (cấu hình mẫu cho test, GUI P6.2, E7) và các lệnh đo kèm quyết định D-24.

## Public API
```python
XQ_MCTS_C = sqrt(2); XQ_MCTS_L = 10; XQ_MCTS_SCALE = 2000.0; XQ_MCTS_TIME_LIMIT = 1.0
xq_mcts_spec(time_limit=1.0, iterations=None, rollout_limit=10, scale=2000.0, tactics=False, c=sqrt(2), label=None) -> AgentSpec
wilson_score(score, n) -> (lo, hi)            # CI Wilson 95 % cho điểm
fit_scale(samples, max_ext=4) -> {scale: mean_loglik}
```
`xq_mcts_spec` = `AgentSpec("mcts", {iterations, time_limit?, c, rollout_limit, value_eval="xq_evaluate", value_scale, check_tactics})` qua registry. Mặc định `tactics=False` (E7 chọn bật/tắt theo D-24).

Lệnh: `python -m gameai.experiments.p83_mcts_check <speed|labels|fit|lmatch|tactics> [--quick] [--depth 2] [--scale 2000] ...`

| Lệnh | Làm gì | Ra |
|---|---|---|
| `speed` | iter/s, độ sâu, nút theo `L ∈ {0,10,20,40}`; µs/lần `evaluate` | `results/tables/p83_speed.csv` |
| `labels --depth d` | AB depth d tự đấu 200 ván (seed 50 000–50 199, khai cuộc ngẫu nhiên 2–8 nước, `max_plies` 300); in tỉ lệ ván phân thắng thua, lý do hòa, vật chất cuối ván | `local_out/p83/labels_d{d}.csv` (không track) |
| `fit --depth d` | hồi quy logistic `scale` trên lưới (100…5000, mở rộng nếu tốt nhất ở biên); hai bản `main` (hòa = 0,5) và `no_draw` | `results/tables/p83_scale_fit.csv` (cột `label_depth`; giữ dòng các depth khác) |
| `lmatch` | L=0 vs L=10, mỗi khai cuộc 2 ván đổi bên; tiêu chí chốt trước (xem D-24). **Ghi từng ván** (append) vào `local_out/p83/lmatch_games.csv`; chạy lại cùng lệnh = tiếp tục từ ván chưa có (khác cấu hình → báo lỗi). Chỉ khi đủ 2×25 ván mới ghi `lmatch_*` vào `p83_speed.csv` | `local_out/p83/lmatch_games.csv`, `p83_speed.csv` |
| `tactics` | ms/nước + % nước đi thẳng của `check_tactics` (12 thế, 300 iteration) | `results/tables/p83_tactics_cost.csv` |

## Phụ thuộc
- Dùng: `agents/registry.py` (`mcts`, `xq_evaluate`), `arena.py`, `experiments/p82_ab_check.py` (`ab_spec`, `midgame_fens`, `run_match`), `games/xiangqi.py`, `heuristics/xiangqi_eval.py`.
- Được dùng bởi: `tests/test_xiangqi_mcts.py`; sau này P6.2, P8.4.

## Thiết kế & quyết định
Xem D-24 (`docs/DECISIONS.md`). Tóm tắt:
- Số `scale` **fit từ dữ liệu** như D-12: nhãn = kết quả ván AB depth 2 tự đấu (depth 1 bị loại vì 54 % hòa → LL ≈ −ln 2, không có thông tin).
- Hai bản fit; chỉ dùng `main` khi hai scale lệch ≤ 2×, ngược lại `no_draw` (thiên lệch, ghi rõ).
- Không cộng dồn `delta` trong MCTS: `evaluate` ~2,9 µs không phải điểm nghẽn; `legal_moves` (~59 µs/ply) mới là.

## Giải thích cho báo cáo (mục 3.4)
**Bản chất.** Rollout ngẫu nhiên tới hết ván trong cờ tướng gần như vô dụng: ván ngẫu nhiên rất dài, kết quả gần như tung đồng xu, và đo được chỉ ~60 ván/s (`p81_speed.csv`, < 200 iter/s) nên cây gần như không mọc. Cách làm: **cắt rollout sau `L` nước ngẫu nhiên rồi lượng giá thế cuối bằng hàm vật chất + PST**, đổi điểm thành xác suất thắng bằng sigmoid. Đây là tinh thần của *value network* trong AlphaGo/AlphaZero, nhưng thay mạng nơ-ron bằng hàm viết tay, và vẫn dùng UCT để chọn nhánh.

**Công thức.**
```
v(s) = σ( eval(s, P1) / scale ) = 1 / (1 + exp(−eval(s, P1)/scale))   ∈ (0, 1), xác suất P1 thắng
z    = kết quả thật nếu ván kết thúc trong L ply (1 / 0,5 / 0);  ngược lại z = v(s_L)
```
`scale` đặt độ dốc: nhỏ → chênh vài trăm điểm đã gần 0/1; lớn → mọi thế gần 0,5. Chọn `scale` bằng cực đại hóa log-likelihood của nhãn kết quả ván thật: `LL(scale) = mean[ z·log σ(e/scale) + (1−z)·log(1−σ(e/scale)) ]`.

**Pseudocode** (khác MCTS gốc đúng ở bước 3):
```
3. Simulation: đi ngẫu nhiên tối đa L nước từ node mới
     nếu ván kết thúc: z = kết quả thật
     ngược lại:        z = sigmoid(eval(thế, P1) / scale)
```
Chọn `L`: `L = 0` (chấm eval ngay tại node mới) nhanh nhất; `L` lớn hơn thêm nhiễu ngẫu nhiên nhưng cho thấy đòn ăn quân gần. L chọn bằng trận trực tiếp (D-24): 50 ván L=0 vs L=10, L=0 được 23/5/22 (điểm 0,51, Wilson 95 % [0,38; 0,64]) → ngang → **L = 10**; L=0 chạy ~9× iteration mà không mạnh hơn.

**Ví dụ trace tay** (thế `3k5/9/9/9/r8/9/9/9/9/R3K4`, Đỏ đi, `L = 0`, `scale = 2000`): với `Xa0×a5` (ăn xe Đen): `eval(Đỏ) = 925` (xem `xiangqi_eval.md`) → `v = σ(925/2000) = σ(0,4625) = 0,614`. Với nước yên tĩnh `Tướng e0-e1`: `eval ≈ −20` → `v = σ(−0,01) = 0,497`. Node ăn xe được điểm cao hơn, UCT dồn lượt thăm vào đó. Chú ý với `scale = 2000` chênh một xe chỉ ra 0,61 — sigmoid rất phẳng vì nhãn (ván AB) nhiễu; vì thế cây cần nhiều lượt thăm để phân biệt (nêu ở D-24 mục hạn chế).

## Kết quả đo (2026-11-23, một máy dev, Windows)
Nguồn: `results/tables/p83_speed.csv`, `p83_scale_fit.csv`, `p83_tactics_cost.csv`. Số đo thời gian phụ thuộc máy.

| `L` | iter/s (9 thế, 1 s) | độ sâu cây TB |
|---|---|---|
| 0 | 9 564 | 4,0 |
| 10 | 1 013 | 2,6 |
| 20 | 511 | 2,3 |
| 40 | 274 | 2,2 |

Mọi `L` đều > 200 iter/s nên không cần phiên tối ưu. Số `scale`, `tactics` và trận L=0 vs L=10: xem D-24.

Trận L=0 vs L=10 (`lmatch`, 50 ván, 3 920 s, **tactics tắt** ở cả hai bên — mặc định `xq_mcts_spec`): L=0 W/D/L 23/5/22, điểm 0,51, Wilson 95 % [0,38; 0,64] → **L = 10** (dòng `lmatch_*` trong `p83_speed.csv`). Theo bên: L=0 cầm Đỏ 0,62, cầm Đen 0,40. E7(c) (tactics bật, cấu hình dùng thật) là phép kiểm lại lựa chọn L (D-24).

## Test
`tests/test_xiangqi_mcts.py` (xem docstring từng test). Chạy: `python -m pytest tests/test_xiangqi_mcts.py -q` (trận nhanh gắn `slow`).

## Hạn chế / TODO
- `local_out/p83/` không track; muốn tái lập: `labels --depth 2` rồi `fit --depth 2` (~1 phút).
- **Chạy dài (`lmatch`, ~1,1–1,9 h) trên Windows PowerShell 5.1:** đặt `[Console]::OutputEncoding = [System.Text.Encoding]::UTF8` trước khi chạy; nếu không, log chuyển hướng (`> lmatch_full.log`) thành UTF-16 và chữ tiếng Việt/ký hiệu bị lỗi mã hóa. **Lấy số từ CSV** (`local_out/p83/lmatch_games.csv`, dòng `lmatch_*` trong `p83_speed.csv`), không đọc từ log.
- Nhãn là kết quả của AB depth 2, không phải kết quả "thật" của thế cờ; `scale` phản ánh chất lượng nhãn đó.
