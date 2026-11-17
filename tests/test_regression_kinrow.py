"""Hồi quy k-in-row (P8.0): agent/arena phải cho đúng chuỗi nước + stats như tag `kinrow-final`.

Golden sinh bởi `python tests/kinrow_golden_cases.py` từ code của tag, trước mọi sửa đổi P8.
"""

import json

import pytest
from kinrow_golden_cases import GOLDEN_PATH, normalize, run_cases


@pytest.fixture(scope="module")
def current():
    return normalize(run_cases())


def test_golden_matches_kinrow_final(current):
    golden = normalize(json.loads(GOLDEN_PATH.read_text(encoding="utf-8")))
    assert len(current) == len(golden)
    for got, want in zip(current, golden, strict=True):
        assert got == want
