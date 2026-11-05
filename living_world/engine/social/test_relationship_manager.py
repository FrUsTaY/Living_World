from living_world.engine.simulation import Simulation
from living_world.population.generation import generate_initial_world


def test_regular_interaction_does_not_reset_meaningful_contact_time():
    simulation = Simulation()
    simulation.time.paused = False
    generate_initial_world(simulation.city, simulation, 2)
    npc_a, npc_b = simulation.npcs
    relationships = simulation.relationship_manager

    relationships.touch_relationship(npc_a.id, npc_b.id, is_meaningful=False)
    simulation.time.tick(24 * 60)
    relationships.modify_relationship(npc_a.id, npc_b.id, "affinity", 1.0)

    relationship = relationships.get_relationship(npc_a.id, npc_b.id)
    assert relationship["last_interaction_time"] == 24 * 60
    assert relationship["last_meaningful_interaction_time"] == 0
