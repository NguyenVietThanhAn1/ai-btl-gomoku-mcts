# figfmt — `gameai/experiments/figfmt.py`

> Mục tiêu của file này: agent/thành viên khác dùng được module **mà không cần đọc code**.

**Trạng thái:** ✅ ổn định  ·  **Task:** P7.2  ·  **Cập nhật:** 2026-11-18

## Mục đích
Một nơi duy nhất định dạng số kiểu Việt Nam (dấu phẩy thập phân, dấu trừ "−" U+2212) cho **bảng** (`vn`) và **tick/nhãn hình**
(`vn_tick`, `vn_figure`, `ratio_axis`). Không dùng locale hệ thống (không ổn định giữa máy). Báo cáo dùng "tỷ lệ" (không "tỉ lệ").

## Public API
```python
vn(x, d=2) -> str                    # 0.5 → "0,50"; −1 → "−1"; d = 0 và ≥ 10 000 → "10 000"; làm tròn về 0 không mang dấu
vn_tick(x, pos=None, d=None) -> str  # nhãn một tick (FuncFormatter-compatible)
tick_decimals(values) -> int         # số chữ số thập phân chung, theo bước tick nhỏ nhất
ratio_axis(ax)                       # trục y tỷ lệ: không tick/gridline nào > 1 dù ylim chừa chỗ (1,03…)
vn_figure(fig)                       # gọi trước savefig: định dạng mọi trục mặc định của mọi axes
EPS = 1e-9                           # dung sai coi là 0
```
- **Cùng số chữ số trên một trục:** `VNFormatter` suy `d` từ bước nhỏ nhất giữa hai tick liền kề. Bước 0,05 → `0,80 0,85 … 1,00`;
  bước 0,02 → `0,90 0,92 … 1,00`; bước 0,1 / 0,2 / 0,5 hoặc nguyên (d ≤ 1) → số nguyên viết trần: `0 0,2 … 1`, `0,5 0,6 … 1`.
  `vn_tick(x)` không có `d`: số chữ số tối thiểu (0.5 → `0,5`, 0 → `0`, 1000 → `1000`).
- **Trục log:** chỉ tick chính (1, 2, 5 × 10^k) có nhãn; tick phụ không nhãn (không có `10^3`, `2×10^3`).
- **Nhãn tay** (`set_xticks(…, labels)`, `set_xticklabels`) giữ nguyên; nhãn đó tự gọi `vn`/`vn_tick`
  (legend E3 `c = {vn(c, 1)}`, tick E5 `{vn_tick(t)} s`).
- **Trục tỷ lệ:** gọi `ratio_axis(ax)` cùng chỗ `set_ylim(0, 1.03)`; tick lớn nhất = 1.
- Số nguyên không nhóm nghìn dưới 10 000 (1000, 5000), đúng cách viết trong `report/report.md` (nhóm nghìn từ 10 000: `20 000`).

## Phụ thuộc
- Chỉ stdlib; matplotlib import khi dùng. **Không** import `plots`/`e*` (tránh vòng).
- Được dùng bởi: `plots.py` (re-export `vn`, `EPS` → `_EPS`; `report_check` vẫn import `vn`/`ci` từ `plots`), `e3_c_sweep`, `e4_final_move`,
  `e5_rollout`, `e6_tactics`, `e6_mechanism` (import ở đầu file; gọi `vn_figure(fig)` ngay trước `tight_layout`/`savefig`).

## Test
`tests/test_figfmt.py`: `vn_tick` (0.5, −0.1, 1000, 0, 0.85, 10 000); `vn` dùng chung với `plots`; `tick_decimals` theo bước;
`vn_figure` (bước 0,05 → `0,80 … 1,00`; bước 0,2; không còn `.`/`-`/`$`; log không mathtext, minor không nhãn; nhãn tay giữ nguyên);
`ratio_axis` (không tick > 1 với ylim 1,03 / 1,05). Chạy: `python -m pytest tests/test_figfmt.py -q`.

## Hạn chế / TODO
- Trục `FixedFormatter` (nhãn tay) không được đồng bộ số chữ số — người gọi tự định dạng.
- `ratio_axis` chỉ áp dụng trục y.
