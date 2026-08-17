import pytest
from datetime import datetime, timedelta
import uuid

from living_world.engine.simulation import Simulation
from living_world.engine.social.household import Household
from living_world.population.npc import NPC
from living_world.engine.event_bus import bus
from living_world.engine.life_cycle_manager import LifeCycleManager

def create_npc(sim, gender, age_years, home_id="home_1"):
    birth_date = sim.time.current_datetime - timedelta(days=age_years * 365)
    npc = NPC(
        first_name="Test",
        last_name="Testov",
        date_of_birth=birth_date,
        gender=gender,
        profession="Безработный",
        home_id=home_id,
        work_id=None
    )
    sim.add_npc(npc)
    return npc

def test_family_events_idempotency_and_stress():
    sim = Simulation()
    hm = sim.household_manager
    fm = sim.family_manager
    rel_mgr = sim.relationship_manager

    # Create home and household
    home_id = "test_home_1"
    household = hm.create_household(home_id)

    # Create family
    father = create_npc(sim, "М", 30, home_id)
    mother = create_npc(sim, "Ж", 28, home_id)
    child = create_npc(sim, "М", 5, home_id)

    father.household_id = household.id
    mother.household_id = household.id
    child.household_id = household.id

    child.father_id = father.id
    child.mother_id = mother.id

    fm.create_family(father, mother, sim.time.get_time_dict())

    assert household.stress == 0.0

    # Test 1: Natural death triggers event exactly once, generates stress, and adds memory
    memories_before = len(sim.memory_manager.get_memories_for(child.id))

    # Fast forward time or force death
    # We will manipulate LifeCycleManager.check_natural_death to always return True for father only
    original_check = LifeCycleManager.check_natural_death

    def mock_check(age):
        if age == father.get_age(sim.time.current_datetime):
            return True
        return False

    LifeCycleManager.check_natural_death = mock_check

    try:
            # We need to trigger the midnight check in Simulation.update()
            # is_new_day = (time_dict['hour'] == 0 and time_dict['minute'] == 0)

            # Unpause to allow simulation update
            sim.time.paused = False

            # Set time to 23:59 and tick 1 minute to hit midnight exactly
            current_date = sim.time.current_datetime
            sim.time.set_time(datetime(current_date.year, current_date.month, current_date.day, 23, 59, 0))

            sim.update() # Will tick 1 minute internally to 00:00 and trigger death
    finally:
        LifeCycleManager.check_natural_death = original_check

    assert father.is_alive == False
    assert household.stress == hm.STRESS_DEATH_IMPACT - hm.STRESS_DAILY_DECAY # Added 50, then decayed 5 because of new day

    memories_after = len(sim.memory_manager.get_memories_for(child.id))
    assert memories_after > memories_before

    memory = sim.memory_manager.get_memories_for(child.id)[-1]
    assert memory['event_type'] == "Смерть близкого"
    assert memory['target_npc_id'] == father.id

    # Test 2: Idempotency (second tick on same dead NPC does not increase stress again)
    stress_before = household.stress
    sim.update() # Not a new day, just a regular tick
    assert household.stress == stress_before

    # Fast forward time to next midnight
    current_date = sim.time.current_datetime
    sim.time.set_time(datetime(current_date.year, current_date.month, current_date.day, 23, 59, 0))
    sim.update() # Will tick to midnight and trigger decay

    assert household.stress == stress_before - hm.STRESS_DAILY_DECAY

    # Test 3: Emergent conflict mechanics
    # We set up mother and child with high tension, low affinity and verify conflict chance
    rel_mgr.modify_relationship(mother.id, child.id, 'tension', 100.0)
    rel_mgr.modify_relationship(mother.id, child.id, 'affinity', -50.0)

    # Set stress high
    hm.modify_stress(household.id, 100.0)

    events_log_len = len(sim.events_log)

    # Run social manager checks
    mother.current_location = "home_1"
    child.current_location = "home_1"

    # Force process social ticks
    sim.social_manager.tick_counter = 10
    sim.social_manager.process_social_ticks()

    # Note: the chance is probabilistic.
    # With tension=100, stress=100, affinity=-50, the conflict_chance is maxed out at 0.8
    # There is an 80% chance for a conflict to trigger on this exact tick.
    # We could force random.random to return 0.0 to guarantee it, but we can also just run it a few times.
    import random
    original_random = random.random
    random.random = lambda: 0.0 # Guarantee success

    try:
        sim.social_manager.tick_counter = 10
        sim.social_manager.process_social_ticks()
    finally:
        random.random = original_random

    assert household.stress > 100.0 - hm.STRESS_DAILY_DECAY # It went over the decay because STRESS_CONFLICT_IMPACT (+10) was added

    conflict_memory_found = False
    for mem in sim.memory_manager.get_memories_for(mother.id):
        if mem['event_type'] == "Семейный конфликт" and mem['target_npc_id'] == child.id:
            conflict_memory_found = True
            break

    assert conflict_memory_found
