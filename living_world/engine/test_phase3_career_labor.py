from datetime import datetime
import pytest
from living_world.engine.simulation import Simulation
from living_world.population.npc import NPC
from living_world.city.city import Building
from living_world.engine.economy.enterprise import Enterprise
from living_world.database.repository import Database
import tempfile
import os

def test_career_qualification_and_wage_scaling():
    sim = Simulation()
    home = Building("Жилой дом", "home", 4, b_id="home_1")
    workshop = Building("Мастерская", "workshop", 10, b_id="work_1")
    sim.city.add_building(home)
    sim.city.add_building(workshop)

    novice = NPC("Иван", "Новичков", datetime(1995, 1, 1), "М", "Механик", home.id, workshop.id,
                 career_level=1)
    expert = NPC("Петр", "Мастеров", datetime(1980, 1, 1), "М", "Механик", home.id, workshop.id,
                 career_level=3)

    sim.add_npc(novice)
    sim.add_npc(expert)

    em = sim.economy_manager
    ent = Enterprise("Городская мастерская", "workshop", workshop.id, budget=100000.0)
    em.register_enterprise(ent)

    # 60 minutes of work
    earned_novice = em.pay_work_wage(novice, minutes=60.0)
    earned_expert = em.pay_work_wage(expert, minutes=60.0)

    # Expert level 3 has 1.50x wage multiplier vs level 1 (1.0x)
    assert earned_expert == pytest.approx(earned_novice * 1.50, rel=1e-2)

def test_experience_accumulation_and_promotion():
    sim = Simulation()
    home = Building("Жилой дом", "home", 4, b_id="home_1")
    plant = Building("Завод", "workshop", 10, b_id="work_1")
    sim.city.add_building(home)
    sim.city.add_building(plant)

    worker = NPC("Артем", "Трудолюбов", datetime(1992, 3, 10), "М", "Механик", home.id, plant.id,
                 career_level=1, work_experience_days=24)
    worker.traits['diligence'] = 0.5  # Diligent worker gets 20% faster promotion (25 * 0.8 = 20 days)
    sim.add_npc(worker)

    em = sim.economy_manager
    ent = Enterprise("Завод Металл", "workshop", plant.id, budget=50000.0)
    em.register_enterprise(ent)

    em.process_labor_market()

    assert worker.work_experience_days == 25
    assert worker.career_level == 2

def test_labor_market_hiring_and_layoff():
    sim = Simulation()
    home = Building("Жилой дом", "home", 4, b_id="home_1")
    farm_b = Building("Сельхозферма", "farm", 10, b_id="farm_1")
    sim.city.add_building(home)
    sim.city.add_building(farm_b)

    unemployed = NPC("Василий", "Поисков", datetime(1975, 5, 20), "М", "Безработный", home.id, None)
    sim.add_npc(unemployed)

    em = sim.economy_manager
    farm_ent = Enterprise("Совхоз Заря", "farm", farm_b.id, budget=30000.0)
    em.register_enterprise(farm_ent)

    # Job market hires unemployed to farm
    em.process_labor_market()

    assert unemployed.work_id == farm_b.id
    assert unemployed.profession == "Фермер"
    assert unemployed.id in farm_ent.employees

    # Now make farm insolvent and add another worker to trigger layoff
    worker2 = NPC("Григорий", "Второй", datetime(1970, 1, 1), "М", "Фермер", home.id, farm_b.id,
                  work_experience_days=50)
    sim.add_npc(worker2)
    farm_ent.add_employee(worker2.id)

    farm_ent.budget = -20000.0  # Deep deficit
    em.process_labor_market()

    # The one with less experience (unemployed has 1 day) gets laid off
    assert unemployed.work_id is None
    assert unemployed.profession == "Безработный"
    assert unemployed.id not in farm_ent.employees

def test_phase3_database_persistence():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        db = Database(db_path)
        home = Building("Дом", "home", 4, b_id="h1")
        npc = NPC("Константин", "Карьеров", datetime(1985, 1, 1), "М", "Инженер", "h1", "w1",
                  career_level=4, work_experience_days=310)
        sim_time = {"year": 2026, "month": 5, "day": 10, "hour": 14, "minute": 0}

        db.save_world(sim_time, [npc], [home], [])
        loaded = db.load_world()
        loaded_npcs = loaded[2]
        assert len(loaded_npcs) == 1
        ln = loaded_npcs[0]

        assert ln["career_level"] == 4
        assert ln["work_experience_days"] == 310
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)
