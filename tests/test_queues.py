import pytest

from Simulator.core.queues import Queue
from Simulator.core.request import Request
from Simulator.core.metrics import Metric


def test_queue_put(env, collector):
    queue = Queue("test-queue", env, collector=collector)
    request = Request(0)

    assert queue.items == []
    queue.put(request)

    assert queue.items == [request]
    assert collector.metrics == [
        Metric(
            run=0,
            timestamp=0,
            name="request-received",
            value=request.id,
            object_id=queue.id,
            object_type=queue.object_type,
        ),
        Metric(
            run=0,
            timestamp=0,
            name="in-count",
            value=1,
            object_id=queue.id,
            object_type=queue.object_type,
        ),
        Metric(
            run=0,
            timestamp=0,
            name="capacity",
            value=1,
            object_id=queue.id,
            object_type=queue.object_type,
        ),
    ]


def test_queue_get(env, collector):
    queue = Queue("test-queue", env, collector=collector)
    request = Request(0)

    assert queue.items == []
    queue.put(request)

    assert queue.items == [request]

    def gen():
        output = yield queue.get()

        # Make a second get, the output should be none and no metric should be generated
        output2 = yield queue.get()

        assert output == request
        assert output2 is None

    env.process(gen())
    env.run()

    assert queue.items == []
    out_metric = Metric(
        run=0,
        timestamp=0,
        name="out-count",
        value=1,
        object_id=queue.id,
        object_type=queue.object_type,
    )

    out_metric2 = Metric(
        run=0,
        timestamp=0,
        name="out-count",
        value=2,
        object_id=queue.id,
        object_type=queue.object_type,
    )

    cap_metric = Metric(
        run=0,
        timestamp=0,
        name="capacity",
        value=0,
        object_id=queue.id,
        object_type=queue.object_type,
    )

    assert out_metric in collector.metrics
    assert cap_metric in collector.metrics

    # Only one request, this metrics should not exists
    assert out_metric2 not in collector.metrics


def test_queue_set_foc_target(env):
    queue = Queue("test-queue", env, foc_target=10)
    request = Request(0)

    assert request.foc_target is None

    queue.put(request)
    assert request.foc_target == 10
