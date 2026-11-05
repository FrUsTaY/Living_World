from datetime import datetime
import pytest
from living_world.engine.simulation import Simulation
from living_world.population.npc import NPC
from living_world.city.city import Building
from living_world.engine.ai.basic_actions import HygieneAction, HobbyAction, VisitDoctorAction, SleepAction, WorkAction
from living_world.database.repository import Database
import tempfile
import os

def test_hygiene_decay_and_shower_action():
    sim = Simulation()
    home = Building("Жилой дом", "home", 4, b_id="home_1")
    sim.city.add_building(home)

    npc = NPC("Алексей", "Чистов", datetime(1995, 1, 1), "М", "Инженер", home.id, "work_1", hygiene=20.0)
    npc.current_location = home.id
    sim.add_npc(npc)

    action = HygieneAction()
    assert action.check_preconditions(npc, sim)
    util = action.calculate_utility(npc, sim, {'hour': 8})
    assert util >= 100.0

    action.execute(npc, sim, {'hour': 8})
    assert npc.hygiene > 20.0
    assert npc.current_location == home.id

def test_hobby_action_and_stress_relief():
    sim = Simulation()
    home = Building("Жилой дом", "home", 4, b_id="home_1")
    park = Building("Городской парк", "park", 50, b_id="park_1")
    sim.city.add_building(home)
    sim.city.add_building(park)

    npc = NPC("Марина", "Книжная", datetime(1992, 5, 10), "Ж", "Учитель", home.id, "work_1",
              hobby="Рыбалка", stress=60.0)
    sim.add_npc(npc)

    hobby_action = HobbyAction()
    assert hobby_action.check_preconditions(npc, sim)
    util = hobby_action.calculate_utility(npc, sim, {'hour': 18, 'is_weekend': False})
    assert util > 0

    hobby_action.execute(npc, sim, {'hour': 18})
    assert npc.stress < 60.0
    assert npc.current_location == park.id

def test_chronotypes_sleep_utility():
    sim = Simulation()
    lark = NPC("Иван", "Ранний", datetime(1990, 1, 1), "М", "Врач", "home_1", "work_1", chronotype="lark")
    owl = NPC("Сергей", "Ночной", datetime(1990, 1, 1), "М", "Врач", "home_1", "work_1", chronotype="owl")

    sleep = SleepAction()
    # At 21:00 lark is ready to sleep, owl is not yet
    util_lark_21 = sleep.calculate_utility(lark, sim, {'hour': 21})
    util_owl_21 = sleep.calculate_utility(owl, sim, {'hour': 21})
    assert util_lark_21 > util_owl_21

    # At 7:00 lark wakes up, owl still sleeps
    util_lark_7 = sleep.calculate_utility(lark, sim, {'hour': 7})
    util_owl_7 = sleep.calculate_utility(owl, sim, {'hour': 7})
    assert util_owl_7 > util_lark_7

def test_sickness_and_doctor_visit():
    sim = Simulation()
    clinic = Building("Городская больница", "hospital", 30, b_id="clinic_1")
    home = Building("Жилой дом", "home", 4, b_id="home_1")
    sim.city.add_building(clinic)
    sim.city.add_building(home)

    patient = NPC("Дмитрий", "Больной", datetime(1988, 3, 12), "М", "Инженер", home.id, "work_1",
                  is_sick=True, sick_days=2, health=60.0)
    patient.money = 1000.0
    sim.add_npc(patient)

    work_action = WorkAction()
    # Sick person takes sick leave, work utility is 0
    assert work_action.calculate_utility(patient, sim, {'hour': 10, 'is_weekend': False}) == 0.0

    doc_action = VisitDoctorAction()
    assert doc_action.check_preconditions(patient, sim)
    doc_util = doc_action.calculate_utility(patient, sim, {'hour': 11})
    assert doc_util >= 200.0

    doc_action.execute(patient, sim, {'hour': 11})
    assert not patient.is_sick
    assert patient.sick_days == 0
    assert patient.health > 60.0
    assert patient.money == 750.0  # Paid 250 fee
    assert patient.current_location == clinic.id

def test_phase1_database_persistence():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        db = Database(db_path)
        home = Building("h1", "Дом", "home", 4)
        npc = NPC("Ольга", "Тестова", datetime(1996, 7, 7), "Ж", "Программист", "h1", "w1",
                  hygiene=45.0, stress=35.0, hobby="Садоводство", chronotype="owl",
                  is_sick=True, sick_days=3)
        sim_time = {"year": 2026, "month": 5, "day": 10, "hour": 14, "minute": 0}

        db.save_world(sim_time, [npc], [home], [])
        loaded = db.load_world()
        loaded_npcs = loaded[2]
        assert len(loaded_npcs) == 1
        ln = loaded_npcs[0]

        assert ln["hygiene"] == 45.0
        assert ln["stress"] == 35.0
        assert ln["hobby"] == "Садоводство"
        assert ln["chronotype"] == "owl"
        assert ln["is_sick"] == 1
        assert ln["sick_days"] == 3
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)
