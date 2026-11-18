"""Test figfmt: số kiểu VN cho tick hình (phẩy thập phân, "−", cùng số chữ số trên một trục)."""

from __future__ import annotations

import matplotlib
import pytest

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from gameai.experiments import figfmt, plots  # noqa: E402


def test_vn_tick_basic():
    """Không biết bước tick: số chữ số tối thiểu; số nguyên không nhóm nghìn dưới 10 000."""
    assert figfmt.vn_tick(0.5) == "0,5"
    assert figfmt.vn_tick(-0.1) == "−0,1"
    assert figfmt.vn_tick(1000) == "1000"
    assert figfmt.vn_tick(0) == "0"
    assert figfmt.vn_tick(-0.0) == "0"
    assert figfmt.vn_tick(0.85) == "0,85"
    assert figfmt.vn_tick(1.0) == "1"
    assert figfmt.vn_tick(10_000) == "10 000"


def test_vn_is_shared_with_plots():
    assert plots.vn is figfmt.vn and plots._EPS == figfmt.EPS
    assert figfmt.vn(-0.001) == "0,00" and figfmt.vn(-1, 0) == "−1"


def test_tick_decimals_from_step():
    assert figfmt.tick_decimals([0.8, 0.85, 0.9, 0.95, 1.0, 1.05]) == 2
    assert figfmt.tick_decimals([0, 0.2, 0.4, 0.6, 0.8, 1.0]) == 1
    assert figfmt.tick_decimals([0.5, 0.6, 0.7]) == 1
    assert figfmt.tick_decimals([1000, 2000, 5000]) == 0
    assert figfmt.tick_decimals([1]) == 0


def _labels(axis) -> list[str]:
    return [t.get_text() for t in axis.get_ticklabels() if t.get_text()]


def test_vn_figure_same_decimals_per_axis():
    """Bước 0,05 → mọi tick 2 chữ số (0,80 … 1,00); bước 0,2 → 0 0,2 … 1; không còn . - $."""
    fig, (a, b) = plt.subplots(1, 2)
    a.plot([0, 1], [0.8, 1.0])
    a.set_ylim(0.8, 1.0)
    a.yaxis.set_major_locator(plt.MultipleLocator(0.05))
    b.plot([-0.4, 0.6], [0.0, 1.0])
    b.yaxis.set_major_locator(plt.MultipleLocator(0.2))
    b.set_xlim(-0.4, 0.6)
    b.xaxis.set_major_locator(plt.MultipleLocator(0.1))
    figfmt.vn_figure(fig)
    fig.canvas.draw()
    ya = [lb for lb in _labels(a.yaxis) if lb in ("0,80", "0,85", "0,90", "0,95", "1,00")]
    assert ya == ["0,80", "0,85", "0,90", "0,95", "1,00"]
    assert {"0", "0,2", "1"} <= set(_labels(b.yaxis))
    assert "−0,4" in _labels(b.xaxis) and "0,6" in _labels(b.xaxis)
    assert not any(c in s for s in _labels(a.yaxis) + _labels(b.yaxis) for c in ".-$")
    plt.close(fig)


def test_vn_figure_log_axis_and_hand_labels():
    """Trục log: chỉ tick chính (1, 2, 5 × 10^k) có nhãn, không mathtext; nhãn tay giữ nguyên."""
    fig, ax = plt.subplots()
    ax.plot([1300, 5700], [1, 2])
    ax.set_xscale("log")
    ax.set_yticks([1, 2], ["x1", "x2"])
    figfmt.vn_figure(fig)
    fig.canvas.draw()
    assert _labels(ax.yaxis) == ["x1", "x2"]
    assert not any("$" in s for s in _labels(ax.xaxis))
    assert [t.get_text() for t in ax.xaxis.get_ticklabels(minor=True) if t.get_text()] == []
    plt.close(fig)


@pytest.mark.parametrize("top", [1.03, 1.05])
def test_ratio_axis_no_tick_above_one(top):
    """Trục tỷ lệ: ylim chừa khoảng trống > 1 nhưng không tick (và gridline) nào > 1."""
    fig, ax = plt.subplots()
    ax.plot([0, 1], [0.9, 1.0])
    ax.set_ylim(0.0, top)
    figfmt.ratio_axis(ax)
    figfmt.vn_figure(fig)
    fig.canvas.draw()
    locs = [v for v in ax.get_yticks() if 0 <= v <= top]
    assert max(locs) == pytest.approx(1.0)
    assert "1" in _labels(ax.yaxis) and not any(s in _labels(ax.yaxis) for s in ("1,2", "1,02"))
    plt.close(fig)
