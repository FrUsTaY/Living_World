import pytest
import math
from living_world.engine.simulation import Simulation
from living_world.population.generation import generate_initial_world
from living_world.engine.social.compatibility import CompatibilityManager

def setup_sim():
    sim = Simulation()
    sim.time.paused = False
    generate_initial_world(sim.city, sim, 2)
    return sim, sim.npcs[0], sim.npcs[1]

def test_interaction_saturation():
    sim, npc1, npc2 = setup_sim()
    sim.relationship_manager.modify_relationship(npc1.id, npc2.id, 'affinity', 0)

    # Track gains
    gains = []

    # Needs a world_date for NPC actions
    time_dict = sim.time.get_time_dict()

    for _ in range(10):
        before = sim.relationship_manager.get_relationship(npc1.id, npc2.id)['affinity']
        sim.social_manager._resolve_action("chat", npc1, npc2, time_dict)
        after = sim.relationship_manager.get_relationship(npc1.id, npc2.id)['affinity']
        gains.append(after - before)

    # Since chat success is random, we filter out 0 gains to test the saturation curve of successful chats
    actual_gains = [g for g in gains if g > 0]
    if len(actual_gains) >= 3:
        assert actual_gains[0] > actual_gains[1]
        assert actual_gains[0] > actual_gains[-1]
        assert actual_gains[-1] < 0.3

def test_superficial_vs_meaningful_decay():
    sim, npc1, npc2 = setup_sim()

    # Establish strong relationship
    sim.relationship_manager.modify_relationship(npc1.id, npc2.id, 'affinity', 80)

    # Just chat every 5 days for 30 days
    for day in range(6):
        sim.time.tick(minutes=5 * 24 * 60)
        time_dict = sim.time.get_time_dict()
        sim.social_manager._resolve_action("chat", npc1, npc2, time_dict)

    rel_chat = sim.relationship_manager.get_relationship(npc1.id, npc2.id)
    affinity_with_chat = rel_chat['affinity']

    # Should have decayed despite chat (chat doesn't update meaningful time)
    assert affinity_with_chat < 78.0

    # Reset and use deep talk
    sim, npc1, npc2 = setup_sim()
    sim.relationship_manager.modify_relationship(npc1.id, npc2.id, 'affinity', 80)

    for day in range(6):
        sim.time.tick(minutes=5 * 24 * 60)
        time_dict = sim.time.get_time_dict()
        sim.social_manager._resolve_action("deep_talk", npc1, npc2, time_dict)

    rel_deep = sim.relationship_manager.get_relationship(npc1.id, npc2.id)
    affinity_with_deep = rel_deep['affinity']

    # Deep talk should maintain it much better
    assert affinity_with_deep > affinity_with_chat

def test_social_mass_scaling():
    sim = Simulation()
    sim.time.paused = False
    generate_initial_world(sim.city, sim, 35)

    npc_main = sim.npcs[0]

    # Give NPC main 20 friends
    for i in range(1, 21):
        sim.relationship_manager.modify_relationship(npc_main.id, sim.npcs[i].id, 'affinity', 50)

    # Get one specific relationship and test its decay rate implicitly via apply_lazy_decay
    # We can calculate mass directly to verify
    rel_mgr = sim.relationship_manager
    rel_mock = {'target_npc_id': sim.npcs[1].id, 'affinity': 50, 'tension': 0, 'trust': 0, 'romantic_interest': 0, 'last_interaction_time': 0, 'last_meaningful_interaction_time': 0}

    sim.time.tick(minutes=24 * 60) # 1 day passed
    decayed_heavy = rel_mgr._apply_lazy_decay(rel_mock.copy(), npc_main.id)

    # Now try for NPC with only 1 friend
    npc_light = sim.npcs[25]
    sim.relationship_manager.modify_relationship(npc_light.id, sim.npcs[26].id, 'affinity', 50)
    decayed_light = rel_mgr._apply_lazy_decay(rel_mock.copy(), npc_light.id)

    # The heavy one should have lost more affinity due to mass penalty
    assert decayed_heavy['affinity'] < decayed_light['affinity']

def test_reciprocity_feedback():
    sim, npc1, npc2 = setup_sim()
    # A initiates everything
    time_dict = sim.time.get_time_dict()
    for _ in range(5):
        sim.social_manager._resolve_action("chat", npc1, npc2, time_dict)

    # Test appeal of B in eyes of A
    appeal = sim.social_manager._calculate_appeal(npc1, npc2)
    # Should be heavily penalized (ratio is 0/5 < 0.3)
    assert appeal < 8.0

def test_friendship_decay_to_zero():
    sim, npc1, npc2 = setup_sim()
    sim.relationship_manager.modify_relationship(npc1.id, npc2.id, 'affinity', 30)

    sim.time.tick(minutes=600 * 24 * 60) # Almost 2 years

    rel = sim.relationship_manager.get_relationship(npc1.id, npc2.id)
    # Should be cleaned up to 0 by the tail cleanup
    assert rel['affinity'] == 0.0

def test_enmity_decay_to_zero():
    sim, npc1, npc2 = setup_sim()
    sim.relationship_manager.modify_relationship(npc1.id, npc2.id, 'affinity', -30)
    sim.relationship_manager.modify_relationship(npc1.id, npc2.id, 'tension', 60)

    sim.time.tick(minutes=600 * 24 * 60)

    rel = sim.relationship_manager.get_relationship(npc1.id, npc2.id)
    assert rel['affinity'] == 0.0
    assert rel['tension'] == 0.0

def test_recovery_is_slow_but_faster_than_initial_connection():
    # We test that appeal is higher due to memory context, but affinity gain isn't instant
    sim, npc1, npc2 = setup_sim()
    sim.memory_manager.add_memory(npc1.id, npc2.id, "Past Friendship", "Were good friends", valence=0.9, significance=0.8)

    sim.relationship_manager.modify_relationship(npc1.id, npc2.id, 'affinity', 5) # Decayed to 5

    appeal = sim.social_manager._calculate_appeal(npc1, npc2)

    # Appeal should be boosted significantly by context
    assert appeal > 15.0

    # But one deep talk should NOT shoot it to 80
    time_dict = sim.time.get_time_dict()
    # It might take a few talks to get over the deep_talk threshold due to random success
    for _ in range(5):
        sim.social_manager._resolve_action("deep_talk", npc1, npc2, time_dict)
    rel = sim.relationship_manager.get_relationship(npc1.id, npc2.id)
    assert rel['affinity'] > 5.5
    assert rel['affinity'] < 60 # Still not full friends instantly

def test_divorce_lifecycle():
    sim, npc1, npc2 = setup_sim()
    # Force marriage
    sim.family_manager.create_family(npc1, npc2, sim.time.get_time_dict())
    assert npc1.family_id is not None

    # Ruin relationship
    sim.relationship_manager.modify_relationship(npc1.id, npc2.id, 'affinity', -50)
    sim.relationship_manager.modify_relationship(npc1.id, npc2.id, 'romantic_interest', 0)

    sim.social_manager._resolve_action("divorce", npc1, npc2, sim.time.get_time_dict())

    assert npc1.family_id is None
    assert npc2.family_id is None

if __name__ == "__main__":
    pytest.main(["-v", __file__])
