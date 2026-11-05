from living_world.engine.event_bus import bus
from living_world.engine.simulation import Simulation


def test_closing_simulation_releases_event_bus_subscriptions():
    before = {event_type: list(callbacks) for event_type, callbacks in bus._subscribers.items()}
    simulation = Simulation()

    simulation.close()

    after = bus._subscribers
    assert after == before
