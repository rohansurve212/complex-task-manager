import pytest
from simpy import Environment
from Simulator.core.metrics import MetricCollector
from Simulator.core.queues import Queue
from Simulator.core.routers import RandomRouter


@pytest.fixture
def env():
    return Environment()


@pytest.fixture
def collector(env):
    return MetricCollector(env)


@pytest.fixture
def queue(env):
    return Queue("test-queue", env)


@pytest.fixture
def router(env, queue):
    return RandomRouter("test-router", env, queues=[queue])
