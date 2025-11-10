import pytest
from Simulator.core.generators import HistoricalGenerator, RequestGenerator
from Simulator.core.queues import Queue
from Simulator.core.routers import RandomRouter
from Simulator.core.utils import get_generated_request


def test_request_generator(env, router, collector):
    callback = lambda e, r: 1
    gen = RequestGenerator("gen", env, router, callback, collector=collector)

    env.run(3)

    # 3 request where generated
    requests = get_generated_request(collector.metrics)
    assert len(requests) == 3


@pytest.mark.parametrize("timeouts, nb_items", [([], 0), ([1], 1), ([1, 1], 2)])
def test_historical_generator(env, queue, router, timeouts, nb_items):
    gen = HistoricalGenerator("gen", env, router, timeouts=timeouts)

    env.run()

    # check if there is request in the queue
    assert len(queue.items) == nb_items
