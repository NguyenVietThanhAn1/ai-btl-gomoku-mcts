"""Định dạng số kiểu Việt Nam cho bảng (`vn`) và tick hình matplotlib (phẩy thập phân, "−").

Không dùng locale hệ thống (không ổn định giữa máy). Không import `plots`/`e*` (tránh vòng):
mọi hàm vẽ E3–E6 và `plots` import module này ở đầu file; matplotlib chỉ import khi vẽ.
"""

from __future__ import annotations

from typing import Any

EPS = 1e-9  # |giá trị| < EPS coi là đúng 0 (nhiễu số học của cận Wilson)


def vn(x: Any, d: int = 2) -> str:
    """Số kiểu VN: dấu phẩy thập phân, dấu trừ "−" (U+2212); số nguyên (d = 0) ≥ 10 000 nhóm nghìn
    bằng khoảng trắng. Giá trị làm tròn thành 0 không mang dấu."""
    v = float(x)
    if d == 0:
        s = f"{round(v):,}".replace(",", " ")
        s = s if abs(v) >= 10_000 else s.replace(" ", "")
    else:
        s = f"{v:.{d}f}".replace(".", ",")
    if s.startswith("-") and not any(c in "123456789" for c in s):
        s = s[1:]
    return s.replace("-", "−")


def _decimals(v: float) -> int:
    """Số chữ số thập phân tối thiểu để viết đúng `v` (tới 1e-6): 0.05 → 2, 0.2 → 1, 1000 → 0."""
    s = f"{abs(v):.6f}".rstrip("0")
    return len(s.split(".")[1]) if "." in s else 0


def vn_tick(x: float, pos: Any = None, d: int | None = None) -> str:
    """Nhãn một tick kiểu VN (cũng dùng làm hàm cho `FuncFormatter`).

    `d = None`: số chữ số tối thiểu (0.5 → "0,5", −0.1 → "−0,1", 0.0 → "0", 1000 → "1000",
    10 000 → "10 000"). `d` cho trước (từ bước tick của trục): số thực luôn viết đủ `d` chữ số
    (0.8 → "0,80" khi d = 2); số nguyên viết "0"/"1" trần khi d ≤ 1."""
    v = float(x)
    integer = abs(v - round(v)) < EPS
    if integer and (d is None or d <= 1):
        return vn(round(v), 0)
    return vn(v, _decimals(v) if d is None else d)


def tick_decimals(values: Any) -> int:
    """Số chữ số thập phân chung của các tick: theo **bước nhỏ nhất** giữa hai tick liền kề
    (bước 0,05 → 2; bước 0,2 → 1; bước 500 → 0). Tick lẻ (log: 1, 2, 5, 10…) toàn số nguyên → 0."""
    vs = sorted({round(float(v), 9) for v in values})
    steps = [b - a for a, b in zip(vs, vs[1:], strict=False) if b - a > EPS]
    return max((_decimals(s) for s in steps), default=0) if steps else 0


def _formatter() -> Any:
    from matplotlib.ticker import Formatter

    class VNFormatter(Formatter):
        """Mọi tick trên một trục cùng số chữ số thập phân (suy từ bước tick); không locale."""

        def __init__(self) -> None:
            self.d: int | None = None

        def format_ticks(self, values: Any) -> list[str]:
            self.set_locs(values)
            self.d = tick_decimals(values)
            return [self(v, i) for i, v in enumerate(values)]

        def __call__(self, x: float, pos: int | None = None) -> str:
            return vn_tick(x, pos, self.d)

    return VNFormatter()


def ratio_axis(ax: Any) -> None:
    """Trục y là tỷ lệ/xác suất: không tick (và gridline) nào > 1 dù ylim có chừa khoảng trống
    phía trên (1,03…). Gọi cùng chỗ `set_ylim`."""
    from matplotlib.ticker import AutoLocator

    class RatioLocator(AutoLocator):
        def tick_values(self, vmin: float, vmax: float) -> Any:
            vals = super().tick_values(vmin, vmax)
            return vals[vals <= 1 + EPS]

    ax.yaxis.set_major_locator(RatioLocator())


def vn_figure(fig: Any) -> None:
    """Gọi trước `savefig`: trục số mặc định (ScalarFormatter / LogFormatter) của mọi axes → tick
    kiểu VN qua `VNFormatter`. Trục log: chỉ tick chính có nhãn (1, 2, 5 × 10^k), tick phụ không
    nhãn. Trục đã đặt nhãn tay (`set_xticks(…, labels)`) giữ nguyên — nhãn đó tự dùng `vn_tick`."""
    from matplotlib.ticker import LogFormatter, LogLocator, NullFormatter, ScalarFormatter

    for ax in fig.axes:
        for axis in (ax.xaxis, ax.yaxis):
            if not isinstance(axis.get_major_formatter(), ScalarFormatter | LogFormatter):
                continue
            if axis.get_scale() == "log":
                axis.set_major_locator(LogLocator(base=10, subs=(1.0, 2.0, 5.0)))
                axis.set_minor_formatter(NullFormatter())
            axis.set_major_formatter(_formatter())
