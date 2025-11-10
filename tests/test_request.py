import pytest

from Simulator.core.request import Request


def test_request_foc():
    request = Request(created_at=0)

    request.closed_at = 10
    assert request.foc == 10

    request.closed_at = 5
    assert request.foc == 5


def test_request_foc_raise_when_open():
    request = Request(created_at=0)

    with pytest.raises(ValueError):
        request.foc


@pytest.mark.parametrize("target,met", [(5, False), (10, True), (15, True)])
def test_request_foc_target(target, met):
    request = Request(created_at=0, foc_target=target)

    request.closed_at = 10
    assert request.foc_met == met
