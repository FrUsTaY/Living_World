import pytest
from datetime import datetime, timedelta
from living_world.engine.simulation import Simulation
from living_world.population.npc import NPC

def test_relationship_status_ru():
    sim = Simulation()
    dob = sim.time.current_datetime - timedelta(days=25*365)
    npc1 = NPC("Иван", "Петров", dob, "М", "Инженер", "home_1", "work_1")
    npc2 = NPC("Мария", "Петрова", dob, "Ж", "Врач", "home_1", "work_1")
    sim.add_npc(npc1)
    sim.add_npc(npc2)

    rm = sim.relationship_manager

    # Initially Strangers
    assert rm.get_relationship_status_ru(npc1.id, npc2.id) == "Незнакомцы"

    # Acquaintances
    rm.modify_relationship(npc1.id, npc2.id, 'familiarity', 15.0)
    assert rm.get_relationship_status_ru(npc1.id, npc2.id) == "Знакомые"

    # Friends
    rm.modify_relationship(npc1.id, npc2.id, 'affinity', 30.0)
    assert rm.get_relationship_status_ru(npc1.id, npc2.id) == "Друзья"

    # Best Friends
    rm.modify_relationship(npc1.id, npc2.id, 'affinity', 40.0)
    rm.modify_relationship(npc1.id, npc2.id, 'trust', 40.0)
    assert rm.get_relationship_status_ru(npc1.id, npc2.id) == "Лучшие друзья"

    # Dating
    npc1.dating_partner_id = npc2.id
    assert rm.get_relationship_status_ru(npc1.id, npc2.id) == "Встречаются"

    # Conflict
    npc1.dating_partner_id = None
    rm.modify_relationship(npc1.id, npc2.id, 'tension', 60.0)
    assert rm.get_relationship_status_ru(npc1.id, npc2.id) == "Вражда / Конфликт"

def test_social_apology():
    sim = Simulation()
    dob = sim.time.current_datetime - timedelta(days=25*365)
    npc1 = NPC("Иван", "Петров", dob, "М", "Инженер", "home_1", "work_1")
    npc2 = NPC("Петр", "Сидоров", dob, "М", "Механик", "home_1", "work_1")
    npc1.traits['empathy'] = 0.8
    npc2.traits['empathy'] = 0.8
    sim.add_npc(npc1)
    sim.add_npc(npc2)

    rm = sim.relationship_manager
    rm.modify_relationship(npc1.id, npc2.id, 'familiarity', 30.0)
    rm.modify_relationship(npc2.id, npc1.id, 'familiarity', 30.0)
    rm.modify_relationship(npc1.id, npc2.id, 'tension', 50.0)
    rm.modify_relationship(npc2.id, npc1.id, 'tension', 50.0)

    time_dict = sim.time.get_time_dict()
    sim.social_manager._resolve_action('apology', npc1, npc2, time_dict)

    rel_after = rm.get_relationship(npc1.id, npc2.id)
    assert rel_after['tension'] < 50.0
    memories = sim.memory_manager.get_memories_for(npc1.id)
    assert any(m['event_type'] == "Примирение" for m in memories)

def test_social_help_or_gift():
    sim = Simulation()
    dob = sim.time.current_datetime - timedelta(days=25*365)
    wealthy = NPC("Алексей", "Кузнецов", dob, "М", "Инженер", "home_1", "work_1")
    wealthy.money = 5000.0
    wealthy.traits['empathy'] = 0.6
    wealthy.traits['frugality'] = -0.5

    poor = NPC("Ольга", "Иванова", dob, "Ж", "Учитель", "home_1", "work_1")
    poor.money = 300.0
    poor.mood = 30.0

    sim.add_npc(wealthy)
    sim.add_npc(poor)

    rm = sim.relationship_manager
    rm.modify_relationship(wealthy.id, poor.id, 'familiarity', 25.0)
    rm.modify_relationship(poor.id, wealthy.id, 'familiarity', 25.0)
    rm.modify_relationship(wealthy.id, poor.id, 'affinity', 30.0)
    rm.modify_relationship(poor.id, wealthy.id, 'affinity', 30.0)

    sim.social_manager._resolve_action('help_or_gift', wealthy, poor, sim.time.get_time_dict())

    assert wealthy.money == 4500.0
    assert poor.money == 800.0
    assert poor.mood > 30.0

def test_social_breakup():
    sim = Simulation()
    dob = sim.time.current_datetime - timedelta(days=25*365)
    npc1 = NPC("Иван", "Петров", dob, "М", "Инженер", "home_1", "work_1")
    npc2 = NPC("Елена", "Смирнова", dob, "Ж", "Врач", "home_1", "work_1")
    npc1.dating_partner_id = npc2.id
    npc2.dating_partner_id = npc1.id
    sim.add_npc(npc1)
    sim.add_npc(npc2)

    sim.social_manager._resolve_action('breakup', npc1, npc2, sim.time.get_time_dict())

    assert npc1.dating_partner_id is None
    assert npc2.dating_partner_id is None
    memories = sim.memory_manager.get_memories_for(npc1.id)
    assert any(m['event_type'] == "Расставание" for m in memories)
