from datetime import datetime, timedelta
import pytest
from living_world.engine.simulation import Simulation
from living_world.engine.culture.holiday_manager import HolidayManager, HolidayType
from living_world.population.npc import NPC
from living_world.city.city import Building
from living_world.database.repository import Database


def test_calendar_holidays_schedule():
    sim = Simulation()
    hol_mgr = sim.holiday_manager
    
    # New Year
    ny = hol_mgr.get_current_holiday(datetime(2025, 1, 1, 10, 0))
    assert ny is not None
    assert ny["type"] == HolidayType.NEW_YEAR
    
    # Spring festival
    spring = hol_mgr.get_current_holiday(datetime(2025, 3, 15, 12, 0))
    assert spring is not None
    assert spring["type"] == HolidayType.SPRING_FESTIVAL
    
    # City Day
    city_day = hol_mgr.get_current_holiday(datetime(2025, 7, 15, 18, 0))
    assert city_day is not None
    assert city_day["type"] == HolidayType.CITY_DAY
    assert city_day["discount"] == 0.20
    
    # Harvest Day
    harvest = hol_mgr.get_current_holiday(datetime(2025, 10, 15, 14, 0))
    assert harvest is not None
    assert harvest["type"] == HolidayType.HARVEST_DAY
    
    # Normal day
    regular = hol_mgr.get_current_holiday(datetime(2025, 5, 20, 11, 0))
    assert regular is None


def test_midnight_new_year_fireworks():
    sim = Simulation()
    sim.time.current_datetime = datetime(2025, 1, 1, 0, 0)
    
    npc = NPC("Празднующий", "Горожанин", datetime(1995, 1, 1), "М", "Инженер", "home_1", "work_1")
    npc.mood = 50.0
    npc.stress = 60.0
    npc.is_alive = True
    sim.npcs = [npc]
    
    initial_fireworks = sim.holiday_manager.fireworks_count
    
    # Trigger fireworks check
    sim.holiday_manager.check_and_trigger_fireworks(sim.time.current_datetime)
    
    assert sim.holiday_manager.fireworks_count == initial_fireworks + 1
    assert npc.mood == 85.0
    assert npc.stress == 30.0
    
    # Memory recorded
    mems = sim.memory_manager.get_memories_for(npc.id)
    assert any("Новогодний Салют" in m["event_type"] for m in mems)


def test_visit_culture_action_effects():
    sim = Simulation()
    sim.time.current_datetime = datetime(2025, 6, 14, 18, 0)  # Weekend evening
    
    # Add cultural institutions to city
    b_lib = Building("Центральная библиотека", "library", 20, b_id="lib_1")
    b_cinema = Building("Городской кинотеатр", "cinema", 50, b_id="cin_1")
    b_stadium = Building("Стадион «Энергия»", "stadium", 100, b_id="stad_1")
    sim.city.add_building(b_lib)
    sim.city.add_building(b_cinema)
    sim.city.add_building(b_stadium)
    
    npc = NPC("Культурный", "Зритель", datetime(1990, 1, 1), "Ж", "Учитель", "home_1", "work_1")
    npc.mood = 40.0
    npc.stress = 70.0
    npc.health = 90.0
    npc.traits['patience'] = 0.2
    npc.is_alive = True
    sim.npcs = [npc]
    
    time_dict = sim.time.get_time_dict()
    time_dict['is_weekend'] = True
    time_dict['hour'] = 18
    
    from living_world.engine.ai.basic_actions import VisitCultureAction
    action = VisitCultureAction()
    assert action.check_preconditions(npc, sim, time_dict) is True
    assert action.calculate_utility(npc, sim, time_dict) > 0.0
    
    # Test cinema execution
    sim.city.buildings = [b_cinema]
    action.execute(npc, sim, time_dict)
    
    assert npc.current_location == b_cinema.id
    assert npc.inspiration_buffer_days == 7
    assert npc.mood > 40.0
    assert npc.stress < 70.0
    
    # Test library execution
    sim.city.buildings = [b_lib]
    action.execute(npc, sim, time_dict)
    assert npc.traits['patience'] > 0.2


def test_inspiration_buffer_preserves_mood_daily():
    sim = Simulation()
    sim.time.current_datetime = datetime(2025, 4, 1, 8, 0)
    
    npc = NPC("Вдохновленный", "Художник", datetime(1993, 1, 1), "М", "Художник", "home_1", None)
    npc.mood = 50.0
    npc.stress = 20.0
    npc.inspiration_buffer_days = 3
    npc.is_alive = True
    sim.npcs = [npc]
    
    # Run daily update
    sim.holiday_manager.daily_update(sim.time.current_datetime)
    
    # Decremented buffer and protected mood
    assert npc.inspiration_buffer_days == 2
    assert npc.mood >= 60.0
    assert npc.stress <= 20.0


def test_culture_persistence_in_db(tmp_path):
    db_file = str(tmp_path / "test_culture.db")
    repo = Database(db_file)
    
    sim = Simulation()
    sim.time.current_datetime = datetime(2025, 1, 1, 12, 0)
    citizen = NPC("Семен", "Праздничный", datetime(1985, 1, 1), "М", "Пекарь", "home_1", "work_1",
                  inspiration_buffer_days=5)
    sim.npcs = [citizen]
    
    sim.holiday_manager.fireworks_count = 3
    sim.holiday_manager.last_celebrated_date = "2025-01-01"
    sim.holiday_manager.celebration_history = [
        {"date": "2025-01-01", "holiday": "Новый Год", "type": "NEW_YEAR"}
    ]
    
    # Save world
    repo.save_world(
        sim_time=sim.time.get_time_dict(),
        npcs=sim.npcs,
        buildings=[],
        events=[],
        culture=sim.holiday_manager.to_dict()
    )
    
    # Load world
    load_res = repo.load_world()
    assert len(load_res) >= 18
    cult_data = load_res[17]
    
    assert cult_data is not None
    assert cult_data["fireworks_count"] == 3
    assert cult_data["last_celebrated_date"] == "2025-01-01"
    assert len(cult_data["celebration_history"]) == 1
    
    # Restore to another simulation
    sim2 = Simulation()
    sim2.holiday_manager.load_from_dict(cult_data)
    assert sim2.holiday_manager.fireworks_count == 3
    assert sim2.holiday_manager.last_celebrated_date == "2025-01-01"
