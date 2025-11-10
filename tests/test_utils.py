import pytest

from Simulator.core.request import Request
from Simulator.core.utils import compute_foc_ratio


def test_compute_foc_ratio():
    requests = [Request(created_at=0, closed_at=5, foc_target=i) for i in range(1, 11)]

    assert compute_foc_ratio(requests) == 0.6  # (10-6)/10
