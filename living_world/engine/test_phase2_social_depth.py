from datetime import datetime
import pytest
from living_world.engine.simulation import Simulation
from living_world.population.npc import NPC
from living_world.city.city import Building
from living_world.database.repository import Database
import tempfile
import os

def test_colleagues_and_neighbors_circles():
    sim = Simulation()
    office = Building("Офисный центр", "office", 20, b_id="work_1")
    home = Building("Жилой дом 1", "home", 6, b_id="home_1")
    sim.city.add_building(office)
    sim.city.add_building(home)

    npc_a = NPC("Анна", "Смирнова", datetime(1993, 2, 10), "Ж", "Инженер", home.id, office.id)
    npc_b = NPC("Борис", "Иванов", datetime(1990, 5, 12), "М", "Инженер", home.id, office.id)
    npc_c = NPC("Олег", "Петров", datetime(1985, 8, 20), "М", "Врач", "home_2", "work_2")

    sim.add_npc(npc_a)
    sim.add_npc(npc_b)
    sim.add_npc(npc_c)

    # Colleagues check
    colleagues_a = npc_a.get_colleagues(sim)
    assert len(colleagues_a) == 1
    assert colleagues_a[0].id == npc_b.id

    # Neighbors check
    neighbors_a = npc_a.get_neighbors(sim)
    assert len(neighbors_a) == 1
    assert neighbors_a[0].id == npc_b.id

    # SocialManager appeal bonus check
    appeal = sim.social_manager._calculate_appeal(npc_a, npc_b)
    assert appeal >= 25.0  # Boosted by both colleague and neighbor status

def test_divorce_property_division_and_alimony():
    sim = Simulation()
    home_1 = Building("Дом 1", "home", 4, b_id="home_1")
    home_2 = Building("Дом 2", "home", 4, b_id="home_2")
    sim.city.add_building(home_1)
    sim.city.add_building(home_2)

    father = NPC("Сергей", "Кузнецов", datetime(1985, 3, 1), "М", "Инженер", home_1.id, "work_1")
    mother = NPC("Елена", "Кузнецова", datetime(1988, 6, 15), "Ж", "Учитель", home_1.id, "work_2")
    child = NPC("Михаил", "Кузнецов", datetime(2015, 4, 10), "М", "Ребенок", home_1.id, None,
                mother_id=mother.id, father_id=father.id)

    father.money = 12000.0
    mother.money = 4000.0

    sim.add_npc(father)
    sim.add_npc(mother)
    sim.add_npc(child)

    sim.family_manager.create_family(father, mother, {'day': 1, 'hour': 10, 'minute': 0})
    assert father.family_id is not None
    assert father.family_id == mother.family_id

    # Now divorce
    sim.family_manager.divorce_family(father, mother, {'day': 10, 'hour': 12, 'minute': 0})

    # Property divided 50/50: total was 16000 -> 8000 each
    assert father.family_id is None
    assert mother.family_id is None
    assert father.money == 8000.0
    assert mother.money == 8000.0

    # Custody of child goes to mother, father gets alimony obligation
    assert father.alimony_to_id == mother.id
    assert child.home_id == mother.home_id

    # Father moves out to home_2
    assert father.home_id == home_2.id

def test_daily_alimony_transfer():
    sim = Simulation()
    father = NPC("Сергей", "Кузнецов", datetime(1985, 3, 1), "М", "Инженер", "home_2", "work_1",
                 alimony_to_id="mother_1")
    father.money = 4000.0
    father.id = "father_1"

    mother = NPC("Елена", "Кузнецова", datetime(1988, 6, 15), "Ж", "Учитель", "home_1", "work_2",
                 npc_id="mother_1")
    mother.money = 1000.0

    child = NPC("Михаил", "Кузнецов", datetime(2015, 4, 10), "М", "Ребенок", "home_1", None,
                mother_id=mother.id, father_id=father.id)

    sim.add_npc(father)
    sim.add_npc(mother)
    sim.add_npc(child)

    # Process daily lifecycle (current date is around 2026, child is ~11 years old)
    sim._process_daily_lifecycle(datetime(2026, 5, 1))

    # Father pays 25% of 4000 = 1000 rubles to mother
    assert father.money == 3000.0
    assert mother.money == 2000.0

    # If child turns 18 (e.g. year 2035)
    sim._process_daily_lifecycle(datetime(2035, 5, 1))
    assert father.alimony_to_id is None  # Alimony obligation cleared

def test_phase2_database_persistence():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        db = Database(db_path)
        home = Building("Жилой дом", "home", 4, b_id="h1")
        npc = NPC("Виктор", "Алиментов", datetime(1980, 1, 1), "М", "Механик", "h1", "w1",
                  alimony_to_id="target_mother_id")
        sim_time = {"year": 2026, "month": 5, "day": 10, "hour": 14, "minute": 0}

        db.save_world(sim_time, [npc], [home], [])
        loaded = db.load_world()
        loaded_npcs = loaded[2]
        assert len(loaded_npcs) == 1
        ln = loaded_npcs[0]

        assert ln["alimony_to_id"] == "target_mother_id"
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)
