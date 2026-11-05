import pytest
from datetime import datetime, timedelta
from living_world.engine.time_manager import TimeManager
from living_world.population.npc import NPC
from living_world.engine.ai.basic_actions import (
    WorkAction, StudyAction, SocializeAction, StrollAction, DateAction, SleepAction, EatAction
)
from living_world.database.repository import Database

class DummyCity:
    def get_places_by_type(self, t):
        return []
    def get_building(self, b_id):
        return None

class DummySim:
    def __init__(self, time_manager):
        self.time = time_manager
        self.city = DummyCity()
        self.npcs = []

def test_time_manager_calendar():
    tm = TimeManager()
    # 2000-01-01 is a Saturday
    assert tm.current_datetime.year == 2000
    assert tm.current_datetime.month == 1
    assert tm.current_datetime.day == 1
    assert tm.weekday == 5
    assert tm.is_weekend is True
    assert tm.weekday_name == "Суббота"
    assert tm.weekday_short == "Сб"
    assert tm.season_name == "Зима"
    assert "01.01.2000" in tm.format_time()
    assert "(Сб)" in tm.format_time()

    # Move to Monday (Jan 3, 2000)
    tm.set_time(datetime(2000, 1, 3, 10, 0, 0))
    assert tm.weekday == 0
    assert tm.is_weekend is False
    assert tm.weekday_name == "Понедельник"
    assert tm.weekday_short == "Пн"

def test_npc_health_and_traits():
    dob = datetime(1985, 5, 20)
    npc = NPC("Иван", "Петров", dob, "М", "Инженер", "home_1", "work_1")
    assert npc.health == 100.0
    assert "ambition" in npc.traits
    assert "frugality" in npc.traits
    assert "diligence" in npc.traits

    d = npc.to_dict()
    assert "Здоровье" in d
    assert d["Здоровье"] == "100%"

def test_work_action_weekdays_vs_weekends():
    tm = TimeManager()
    # Monday 10:00 AM
    tm.set_time(datetime(2000, 1, 3, 10, 0, 0))
    sim = DummySim(tm)

    dob = datetime(1975, 5, 20)
    engineer = NPC("Иван", "Петров", dob, "М", "Инженер", "home_1", "work_1")
    doctor = NPC("Мария", "Петрова", dob, "Ж", "Врач", "home_1", "work_hospital")
    action = WorkAction()

    # On Monday, both work
    time_dict = tm.get_time_dict()
    assert action.calculate_utility(engineer, sim, time_dict) > 0.0
    assert action.calculate_utility(doctor, sim, time_dict) > 0.0

    # Move to Sunday 12:00 PM
    tm.set_time(datetime(2000, 1, 9, 12, 0, 0))
    time_dict = tm.get_time_dict()

    # Engineer rests on Sunday
    assert action.calculate_utility(engineer, sim, time_dict) == 0.0
    # Doctor has shift coverage
    assert action.calculate_utility(doctor, sim, time_dict) > 0.0

def test_weekend_social_boost():
    tm = TimeManager()
    sim = DummySim(tm)
    dob = datetime(1990, 1, 1)
    npc = NPC("Сергей", "Смирнов", dob, "М", "Механик", "home_1", "work_1")
    npc.traits['sociability'] = 0.5
    action = SocializeAction()

    # Weekday 14:00
    tm.set_time(datetime(2000, 1, 4, 14, 0, 0))
    weekday_util = action.calculate_utility(npc, sim, tm.get_time_dict())

    # Weekend 14:00
    tm.set_time(datetime(2000, 1, 8, 14, 0, 0))
    weekend_util = action.calculate_utility(npc, sim, tm.get_time_dict())

    assert weekend_util > weekday_util

def test_health_recovery_and_decay(tmp_path):
    dob = datetime(1990, 1, 1)
    npc = NPC("Сергей", "Смирнов", dob, "М", "Механик", "home_1", "work_1")
    npc.health = 50.0
    npc.energy = 80.0
    npc.hunger = 80.0

    sleep = SleepAction()
    sim = DummySim(TimeManager())
    sleep.execute(npc, sim, {})
    assert npc.health > 50.0

    # Persistence of health and traits
    db_file = tmp_path / "test_stage1.db"
    db = Database(str(db_file))
    db.save_world(sim.time.get_time_dict(), [npc], [], [])
    loaded = db.load_world()
    npcs_loaded = loaded[2]
    loaded_npc = npcs_loaded[0]
    assert loaded_npc['health'] == pytest.approx(npc.health, 0.01)
    assert 'trait_ambition' in loaded_npc
