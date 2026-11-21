# xiangqi_eval — `gameai/heuristics/xiangqi_eval.py`

> Lượng giá cờ tướng cho Alpha-Beta (P8.2) và MCTS cắt + eval (P8.3). Thiết kế: D-23.

**Trạng thái:** ✅ ổn định  ·  **Task:** P8.2  ·  **Cập nhật:** 2026-11-21

## Mục đích
Cho `AlphaBetaAgent` (và sau này `sigmoid_value` của MCTS) một hàm điểm cho thế cờ tướng: **vật chất + điểm theo ô (PST)**, cộng dồn tăng dần được (`delta_eval`), cùng hàm sắp nước ăn quân (`mvv_lva`). Dùng qua registry: `xq_evaluate`, `xq_delta`, `xq_mvv_lva` (+ `xq_mvv_lva_check`, tùy chọn, **không bật**).

## Public API
```python
MATERIAL: tuple[int, ...]            # theo loại quân K..P: (0, 0, 200, 200, 400, 900, 450, 100) [_, K, A, B, N, R, C, P]
PST_RED: tuple[tuple[int, ...], ...] # PST_RED[loại][ô] = vật chất + điểm vị trí, góc nhìn Đỏ (rank 0 = nhà Đỏ)
CAPTURE_BASE = 10_000                # mọi nước ăn quân xếp trên mọi nước yên tĩnh

def evaluate(game: Xiangqi, player: int) -> int        # điểm theo góc nhìn player; không phụ thuộc bên sắp đi
def delta_eval(game: Xiangqi, move: int) -> int        # evaluate(sau) − evaluate(trước), góc nhìn người sắp đi; gọi TRƯỚC play
def mvv_lva(game: Xiangqi, move: int) -> int           # điểm sắp nước (cao = duyệt trước)
def mvv_lva_check(game, move, check_bonus=5_000) -> int # mvv_lva + thưởng nước chiếu (play + in_check + undo)
def piece_value(piece: int, sq: int) -> int            # đóng góp của một quân (có dấu) vào Đỏ − Đen
```
- `evaluate(g, RED) = −evaluate(g, BLACK)`; thế khởi đầu = 0. O(90). **Không** xử lý ván đã kết thúc (agent kiểm `winner()` trước).
- `delta_eval` O(1), **đúng bằng** hiệu `evaluate` (test trên > 1 500 nước ngẫu nhiên, cả hai bên, có ăn quân).
- Dùng với `AlphaBetaAgent(eval_fn=xq_evaluate, delta_fn=xq_delta, order_fn=xq_mvv_lva)`; spec mẫu: `experiments/p82_ab_check.ab_spec`.

## Phụ thuộc
- Dùng: `games/xiangqi.py` (mã quân, `board`, `in_check`, `play/undo` cho bản `_check`).
- Được dùng bởi: `agents/registry.py` (`FUNCTIONS`), `experiments/p82_ab_check.py`, `tests/test_xiangqi_eval.py`, `tests/test_xiangqi_ab.py`; sau này P8.3/P8.4.

## Thiết kế & quyết định (D-23)
- **Một bảng cho hai bên:** `PST_RED[loại][ô]` (đã gồm vật chất) góc nhìn Đỏ; quân Đen dùng **cùng bảng, lật rank** (`rank → 9 − rank`). Bảng đối xứng trái–phải nên lật rank = xoay 180°. Nhờ đó eval đối xứng Đỏ/Đen **theo cấu trúc**, không cần hai bảng khớp tay.
- `_SCORE[quân + 7][ô]` = đóng góp có dấu vào (Đỏ − Đen), dựng một lần lúc import. `evaluate` = Σ `_SCORE` rồi đổi dấu nếu `player = Đen`. Không phụ thuộc bên sắp đi nên `delta_eval` chính xác.
- **Bảng tự thiết kế theo nguyên tắc, không tinh chỉnh bằng dữ liệu** (An duyệt 2026-11-21): vật chất theo quy ước phổ biến (không gắn nguồn cụ thể); điểm vị trí là công thức đơn giản giải thích được, chọn **một lần** trước khi chạy bất kỳ thí nghiệm nào và không chỉnh theo kết quả ván. Không lấy bảng ngoài (không có nguồn kiểm chứng được). `c(f) = 4 − |f − 4|` (cột giữa = 4, biên = 0), `r` = rank theo góc nhìn quân.

| Quân | Vật chất | Điểm vị trí (cộng thêm) |
|---|---|---|
| Tốt (P) | 100 | `r < 5` (chưa qua sông): 0. Qua sông: `100 + 20·(r−5)` (r ≤ 8; r = 9: 100) `+ 5·c(f)`, `+ 20` nếu `r ≥ 7` và cột d–f (trước cung địch) |
| Sĩ (A) | 200 | 20 ở tâm cung (e1), còn lại 0 |
| Tượng (B) | 200 | 20 ở e2; 10 ở c4, g4; 5 ở a3, i3; 0 ở c0, g0 |
| Mã (N) | 400 | `8·c(f) + 5·min(r, 7)` (trung tâm tốt, biên xấu, tiến lên tốt) |
| Xe (R) | 900 | `4·c(f) + 5·r` |
| Pháo (C) | 450 | `6·c(f) + 3·min(r, 6)` |
| Tướng (K) | 0 | 0 (không bị bắt; ván kết thúc do `winner()`) |

- **`mvv_lva` (MVV-LVA):** ăn quân → `10 000 + 10·giá_trị_nạn_nhân − giá_trị_quân_đi` (nạn nhân giá trị cao trước; cùng nạn nhân thì quân rẻ ăn trước; tướng đi ăn xếp sau cùng). Nước yên tĩnh → `delta_eval` (|·| < 10 000) nên quân yên tĩnh có thứ tự ổn định theo PST thay vì thứ tự sinh nước.
- **`check_bonus` (nước chiếu) — không bật.** `mvv_lva_check` thưởng +5 000 nước chiếu nhưng cần `play`+`in_check`+`undo` mỗi nước. Đo (`p82_ab_speed.csv`, depth 3, 9 thế): nút 17 417 → 16 277 (−6,5 %) nhưng thời gian 0,299 s → 0,356 s (**+19 %**) → chậm hơn, mặc định dùng `xq_mvv_lva`. Vẫn đăng ký `xq_mvv_lva_check` để đo lại khi cần.
- **Không có:** quiescence search (cần sửa `agents/`), tempo, di động, an toàn tướng, phạt tướng bị lộ. Rủi ro đã biết: **hiệu ứng chân trời** ở lá độ sâu cố định (nước ăn quân ở ply cuối không được đáp lại). Giảm nhẹ bằng iterative deepening + ordering ăn quân trước; nếu P8.3/P8.4 cho thấy lỗi rõ thì đề xuất riêng.

## Giải thích cho báo cáo
**Bản chất.** Alpha-Beta cần một hàm cho điểm thế cờ ở độ sâu giới hạn. Cờ tướng không có cách tính "thắng hay thua" ở thế giữa ván, nên dùng heuristic kinh điển: **tổng giá trị quân còn trên bàn** (Xe 900 > Pháo 450 > Mã 400 > Sĩ = Tượng 200 > Tốt 100) cộng **điểm theo ô** thưởng vị trí tốt (Tốt qua sông có giá trị gấp đôi và tăng khi áp sát cung; Xe/Pháo/Mã thích cột giữa và tiến lên; Sĩ/Tượng thích ô giữa cung). Điểm tính theo góc nhìn một bên; bên kia là số đối.

**Công thức.**
```
eval(s, Đỏ) = Σ_{quân Đỏ} PST[loại][ô]  −  Σ_{quân Đen} PST[loại][lật rank(ô)]      eval(s, Đen) = −eval(s, Đỏ)
delta(s, m) = [PST[p][đến] − PST[p][đi]] + (nếu ăn: PST của quân bị ăn tại ô đến)    (góc nhìn người đi; Đen: dùng ô lật)
leaf(AB)    = eval(gốc) + Σ_{dọc nhánh} ± delta     (+ nếu người đi là root, − nếu đối thủ)
```

**Ví dụ trace tay** (`3k5/9/9/9/r8/9/9/9/9/R3K4`, Đỏ đi: xe Đỏ a0, xe Đen a5, hai tướng): xe Đỏ ở a0: 900 + 4·c(a)=0 + 5·0 = **900**. Xe Đen ở a5 = rank 4 theo góc nhìn Đen: 900 + 0 + 5·4 = **920**. `eval(Đỏ) = 900 − 920 = −20`. Nước Xa0×a5: xe tiến lên a5: (900 + 0 + 5·5) − 900 = +25; ăn xe Đen (ô a5 theo góc nhìn Đen = rank 4, 920) = +920 → `delta = 945`; kiểm: `eval(sau) = 925 − 0 = 925 = −20 + 945` ✓ (test `test_hand_trace_example_matches_docs`).

**Chọn tham số.** Giá trị quân theo tỉ lệ phổ biến của cờ tướng (Xe ≈ 2 Pháo/Mã, Sĩ/Tượng ≈ nửa Mã, Tốt ≈ nửa Sĩ nhưng tăng sau khi qua sông). Hệ số PST nhỏ (tối đa vài chục điểm, riêng Tốt qua sông cao hơn) để **vật chất luôn quan trọng hơn vị trí**: một quân Tốt (100) hơn mọi lợi thế vị trí của Xe/Mã/Pháo. Giá trị không tinh chỉnh bằng dữ liệu (D-23); sức mạnh đo ở E7.

## Test
- `tests/test_xiangqi_eval.py`: `delta` = hiệu `evaluate` (> 1 500 nước ngẫu nhiên, có ăn quân, cả hai bên, đủ 7 loại quân); thế khởi đầu = 0; tổng không (Đỏ = −Đen); không phụ thuộc bên đi; **lật màu + lật rank → đổi dấu**; lật trái–phải → không đổi; bảng 90 ô, đối xứng trái–phải; thứ tự giá trị quân và thưởng qua sông; ví dụ trace tay ở trên; `mvv_lva` (Tốt ăn Xe > Xe ăn Xe > Tốt ăn Tốt; mọi nước ăn > mọi nước yên tĩnh; tất định); `mvv_lva_check` chỉ cộng khi chiếu và không đổi game.
- Chạy riêng: `python -m pytest tests/test_xiangqi_eval.py -q` (~1 s). AB dùng hàm này: `tests/test_xiangqi_ab.py` (xem `alphabeta.md`, `p82_ab_check.md`).

## Hạn chế / TODO
- Không quiescence, không phạt/ thưởng cấu trúc (tướng bị lộ, Sĩ–Tượng đủ bộ, Xe liên hoàn…). Bảng chưa được kiểm so với bảng ngoài (chủ ý: không tinh chỉnh bằng dữ liệu).
- `evaluate` O(90) mỗi lần gọi; MCTS (P8.3) gọi ở mỗi lá — nếu thành điểm nghẽn thì tối ưu ở P8.3.
