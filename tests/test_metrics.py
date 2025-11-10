import pytest
from Simulator.core.metrics import MetricCollector, Metric


def test_metrics_collector(env):
    collector = MetricCollector(env)

    collector.add("test-metric", 1, object_type="test", object_id="test")

    assert collector.metrics == [
        Metric(
            run=0,
            timestamp=0,
            name="test-metric",
            value=1,
            object_id="test",
            object_type="test",
        )
    ]

    # Reset the run
    collector.reset(run=1)
    collector.add("test-metric", 1, object_type="test", object_id="test")

    assert collector.metrics == [
        Metric(
            run=0,
            timestamp=0,
            name="test-metric",
            value=1,
            object_id="test",
            object_type="test",
        ),
        Metric(
            run=1,
            timestamp=0,
            name="test-metric",
            value=1,
            object_id="test",
            object_type="test",
        ),
    ]
