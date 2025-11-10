from Simulator.core.agents import Agent, ScheduleAgent
from Simulator.core.metrics import Metric
from Simulator.core.queues import Queue, FilterQueue
from Simulator.core.request import Request


def test_agent(env, queue, collector):
    request = Request(0)
    queue.put(request)

    agent = Agent(
        "test-agent",
        env,
        queues=[queue],
        handle_time_callback=lambda e, q, r, d: 1,
        collector=collector,
    )

    env.run()

    # Agent worked the queue
    assert queue.items == []

    # Agent closed the request
    assert request.closed_at is not None

    # Check the metrics
    assert collector.metrics == [
        Metric(
            run=0,
            timestamp=0,
            name="opening-request",
            value=request.id,
            object_id=agent.id,
            object_type=Agent.object_type,
        ),
        Metric(
            run=0,
            timestamp=1,
            name="completed-request",
            value=request.id,
            object_id=agent.id,
            object_type=Agent.object_type,
        ),
        Metric(
            run=0,
            timestamp=1,
            name="handle-time",
            value=1,
            object_id=agent.id,
            object_type=Agent.object_type,
        ),
    ]
