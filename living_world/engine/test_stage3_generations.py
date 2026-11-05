import pytest
from datetime import datetime, timedelta
from living_world.engine.simulation import Simulation
from living_world.population.npc import NPC
from living_world.city.city import Building
from living_world.engine.event_bus import bus

def test_inheritance_to_spouse():
    sim = Simulation()
    dob = sim.time.current_datetime - timedelta(days=50*365)
    husband = NPC("Иван", "Петров", dob, "М", "Инженер", "home_1", "work_1")
    husband.money = 60000.0
    wife = NPC("Мария", "Петрова", dob, "Ж", "Врач", "home_1", "work_1")
    wife.money = 10000.0

    sim.add_npc(husband)
    sim.add_npc(wife)

    # Form family
    sim.family_manager.create_family(husband, wife, sim.time.get_time_dict())

    # Husband dies
    husband.is_alive = False
    bus.publish("npc_died", {"npc": husband})

    assert wife.money == 70000.0
    assert husband.money == 0.0

def test_inheritance_to_children():
    sim = Simulation()
    parent_dob = sim.time.current_datetime - timedelta(days=60*365)
    parent = NPC("Петр", "Сидоров", parent_dob, "М", "Механик", "home_1", "work_1")
    parent.money = 30000.0

    child_dob = sim.time.current_datetime - timedelta(days=25*365)
    child1 = NPC("Анна", "Сидорова", child_dob, "Ж", "Учитель", "home_1", "work_1", father_id=parent.id)
    child2 = NPC("Дмитрий", "Сидоров", child_dob, "М", "Строитель", "home_2", "work_1", father_id=parent.id)
    child1.money = 2000.0
    child2.money = 5000.0

    sim.add_npc(parent)
    sim.add_npc(child1)
    sim.add_npc(child2)

    parent.is_alive = False
    bus.publish("npc_died", {"npc": parent})

    assert child1.money == 17000.0
    assert child2.money == 20000.0
    assert parent.money == 0.0

def test_elderly_retirement():
    sim = Simulation()
    elder_dob = sim.time.current_datetime - timedelta(days=72*365)
    elder = NPC("Михаил", "Иванов", elder_dob, "М", "Строитель", "home_1", "work_1")
    sim.add_npc(elder)

    # Force retirement via daily lifecycle
    import random
    random.seed(123)
    # Check over a few iterations to let retire_chance trigger
    for _ in range(10):
        sim._process_daily_lifecycle(sim.time.current_datetime)
        if elder.profession == "Пенсионер":
            break

    assert elder.profession == "Пенсионер"
    assert elder.work_id is None

def test_young_adult_moving_out():
    sim = Simulation()
    parent_dob = sim.time.current_datetime - timedelta(days=50*365)
    parent = NPC("Ольга", "Семенова", parent_dob, "Ж", "Врач", "home_1", "work_1")

    child_dob = sim.time.current_datetime - timedelta(days=22*365)
    young_adult = NPC("Алексей", "Семенов", child_dob, "М", "Инженер", "home_1", "work_1", mother_id=parent.id)
    young_adult.money = 25000.0

    h1 = Building("Дом №1", "home", 4)
    h2 = Building("Дом №2", "home", 4)
    sim.city.add_building(h1)
    sim.city.add_building(h2)

    parent.home_id = h1.id
    young_adult.home_id = h1.id

    hh1 = sim.household_manager.create_household(h1.id)
    parent.household_id = hh1.id
    young_adult.household_id = hh1.id

    sim.add_npc(parent)
    sim.add_npc(young_adult)

    # Run daily lifecycle
    for _ in range(15):
        sim._process_daily_lifecycle(sim.time.current_datetime)
        if young_adult.home_id == h2.id:
            break

    assert young_adult.home_id == h2.id
    assert young_adult.household_id != hh1.id
