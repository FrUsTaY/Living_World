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

    # We must ensure they are in an available state, otherwise process_social_ticks ignores them
    mother.state = "Отдыхает"
    child.state = "Отдыхает"

    # Force process social ticks
    sim.social_manager.tick_counter = 10
    sim.social_manager.process_social_ticks()

    # Note: we refactored _check_emergent_family_conflicts into the main pipeline.
    # So we call `_resolve_action` directly to ensure it happens.

    sim.social_manager._resolve_action('argue', mother, child, sim.time.get_time_dict())

    assert household.stress > 100.0 - hm.STRESS_DAILY_DECAY # It went over the decay because STRESS_CONFLICT_IMPACT (+2) was added

    conflict_memory_found = False
    for mem in sim.memory_manager.get_memories_for(mother.id):
        if mem['event_type'] == "Семейный конфликт" and mem['target_npc_id'] == child.id:
            conflict_memory_found = True
            break

    assert conflict_memory_found

def test_npc_card_memory_population():
    # Regression test for GUI NPC Card Memory Population issue
    from PySide6.QtWidgets import QApplication, QMainWindow
    from living_world.gui.dialogs.npc_card import NPCCardDialog

    # Needs a QApplication instance to run GUI code
    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    sim = Simulation()
    class FakeParent(QMainWindow):
        pass
    p = FakeParent()
    p.sim = sim

    npc1 = create_npc(sim, 'М', 20)
    npc2 = create_npc(sim, 'Ж', 20)

    sim.memory_manager.add_memory(npc1.id, npc2.id, "Test Event", "Test Desc", 1.0, 1.0)

    # Initialize dialog and verify it populates memories without KeyError
    d = NPCCardDialog(npc1, sim.city, p)
    d._populate_memories() # Should not raise KeyError: 'time'

    assert d.mem_list.count() == 1
    item_text = d.mem_list.item(0).text()
    assert "Test Event" in item_text

def test_social_availability_and_conflict_limit():
    sim = Simulation()
    hm = sim.household_manager
    fm = sim.family_manager
    rel_mgr = sim.relationship_manager

    # Create home and household
    home_id = "test_home_1"
    household = hm.create_household(home_id)

    npc_a = create_npc(sim, "М", 30, home_id)
    npc_b = create_npc(sim, "Ж", 28, home_id)
    npc_a.household_id = household.id
    npc_b.household_id = household.id
    fm.create_family(npc_a, npc_b, sim.time.get_time_dict())

    # Set up high tension/stress scenario
    rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'tension', 100.0)
    rel_mgr.modify_relationship(npc_a.id, npc_b.id, 'affinity', -50.0)
    hm.modify_stress(household.id, 100.0)

    # 1. Test different locations (working)
    npc_a.current_location = "work_1"
    npc_b.current_location = "work_2"
    npc_a.state = "Работает"
    npc_b.state = "Работает"

    sim.social_manager.tick_counter = 10
    sim.social_manager.process_social_ticks()

    memories_a = sim.memory_manager.get_memories_for(npc_a.id)
    assert len(memories_a) == 1 # Just the marriage memory

    # 2. Test sleeping
    npc_a.current_location = home_id
    npc_b.current_location = home_id
    npc_a.state = "Спит"
    npc_b.state = "Отдыхает"

    sim.social_manager.tick_counter = 10
    sim.social_manager.process_social_ticks()

    memories_a = sim.memory_manager.get_memories_for(npc_a.id)
    assert len(memories_a) == 1 # Still just marriage

    # 3. Test runaway loop prevention
    npc_a.state = "Отдыхает"

    import random

    # We don't want a divorce to randomly trigger instead of argue, so we monkey patch _select_action
    original_select = sim.social_manager._select_action
    sim.social_manager._select_action = lambda a, b: 'argue'

    try:
        # First tick - should conflict and create memory
        # We bypass process_group random initiate_chance and call resolve_action directly
        sim.social_manager._resolve_action('argue', npc_a, npc_b, sim.time.get_time_dict())

        memories_a = sim.memory_manager.get_memories_for(npc_a.id)
        assert len(memories_a) == 2
        assert memories_a[-1]['event_type'] == "Семейный конфликт"

        # Second tick right after - memory cooldown should prevent relationship penalty loop
        # We need to simulate the social pipeline calling _resolve_action('argue') again
        sim.social_manager._resolve_action('argue', npc_a, npc_b, sim.time.get_time_dict())

        memories_a_after = sim.memory_manager.get_memories_for(npc_a.id)
        assert len(memories_a_after) == 2 # No new memory due to cooldown

    finally:
        sim.social_manager._select_action = original_select

def test_household_vs_family_conflict_and_cooldown():
    sim = Simulation()
    hm = sim.household_manager
    rel_mgr = sim.relationship_manager

    # Create home and household
    home_id = "test_home_2"
    household = hm.create_household(home_id)

    # Create two NON-related NPCs
    npc_c = create_npc(sim, "М", 30, home_id)
    npc_d = create_npc(sim, "М", 28, home_id)
    npc_c.household_id = household.id
    npc_d.household_id = household.id

    # 1. Test "Бытовой конфликт"
    sim.social_manager._resolve_action('argue', npc_c, npc_d, sim.time.get_time_dict())

    memories_c = sim.memory_manager.get_memories_for(npc_c.id)
    assert len(memories_c) == 1
    assert memories_c[-1]['event_type'] == "Бытовой конфликт"

    # 2. Test cooldown
    tension_before = rel_mgr.get_relationship(npc_c.id, npc_d.id)['tension']
    stress_before = household.stress

    # Try resolving argue again immediately
    sim.social_manager._resolve_action('argue', npc_c, npc_d, sim.time.get_time_dict())

    memories_c_after = sim.memory_manager.get_memories_for(npc_c.id)
    assert len(memories_c_after) == 1 # Still 1 memory

    tension_after = rel_mgr.get_relationship(npc_c.id, npc_d.id)['tension']
    stress_after = household.stress

    # Verify no penalties applied during cooldown
    assert tension_before == tension_after
    assert stress_before == stress_after
