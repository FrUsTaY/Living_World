import os
from living_world.engine.simulation import Simulation
from living_world.population.generation import generate_initial_world
from living_world.database.repository import Database
from living_world.engine.event_bus import bus

def test_incremental_history():
    print("Testing incremental history save/load...")
    sim = Simulation()
    generate_initial_world(sim.city, sim, 25)

    os.makedirs("saves", exist_ok=True)
    db = Database("saves/history_test2.db")

    # Save 1 event
    db.save_world(sim.time.get_time_dict(), sim.npcs, sim.city.buildings, sim.events_log)

    # Generate 1000 events
    for i in range(1000):
        bus.publish("log_event", f"Fake Event {i}")

    assert len(sim.events_log) == 500 # Capped at 500 in RAM

    # Save again (should append new, not delete old)
    db.save_world(sim.time.get_time_dict(), sim.npcs, sim.city.buildings, sim.events_log)

    # Load back
    _, _, _, evs = db.load_world()

    assert len(evs) == 1001, f"Expected 1001 events in DB, got {len(evs)}"
    assert evs[0]['msg'] == "Мир создан. Население: 25 человек."

    print("History incremental test OK!")
    os.remove("saves/history_test2.db")

if __name__ == "__main__":
    test_incremental_history()
