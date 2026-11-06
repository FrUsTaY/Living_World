from datetime import datetime
import pytest
from living_world.engine.simulation import Simulation
from living_world.engine.politics.politics_manager import PoliticsManager
from living_world.population.npc import NPC
from living_world.database.repository import Database


def test_candidates_and_election_winner():
    sim = Simulation()
    sim.time.current_datetime = datetime(2025, 1, 1, 8, 0)
    
    # Create several adult NPCs with different characteristics
    # NPC 1: Wealthy business owner (prefers MARKET)
    npc1 = NPC("Богач", "Олигархов", datetime(1980, 1, 1), "М", "Глава корпорации", "home_1", "work_1")
    npc1.money = 50000.0
    npc1.is_alive = True
    
    # NPC 2: Working class / Pensioner (prefers SOCIAL)
    npc2 = NPC("Пенсионер", "Трудовой", datetime(1955, 1, 1), "М", "Пенсионер", "home_1", "work_1")
    npc2.money = 1200.0
    npc2.is_alive = True
    
    # NPC 3: Middle class specialist (prefers URBANIST)
    npc3 = NPC("Инженер", "Городской", datetime(1990, 1, 1), "Ж", "Инженер", "home_1", "work_1")
    npc3.money = 15000.0
    npc3.is_alive = True
    
    sim.npcs = [npc1, npc2, npc3]
    
    # Run election
    sim.politics_manager.trigger_election(datetime(2025, 1, 1), reason="плановых выборов")
    
    assert sim.politics_manager.current_mayor_id in [npc1.id, npc2.id, npc3.id]
    assert sim.politics_manager.mayor_platform in ["SOCIAL", "MARKET", "URBANIST"]
    assert sim.politics_manager.approval_rating == 75.0
    assert sim.politics_manager.days_until_election == 1095


def test_platform_policies_affect_economy():
    sim = Simulation()
    pol = sim.politics_manager
    
    # Social platform
    pol.mayor_platform = "SOCIAL"
    assert pol.get_tax_rate() == 0.18
    assert pol.get_pension_amount() == 850.0
    assert pol.get_child_allowance() == 300.0
    
    # Market platform
    pol.mayor_platform = "MARKET"
    assert pol.get_tax_rate() == 0.08
    assert pol.get_pension_amount() == 500.0
    assert pol.get_child_allowance() == 150.0
    
    # Urbanist platform
    pol.mayor_platform = "URBANIST"
    assert pol.get_tax_rate() == 0.13
    assert pol.get_pension_amount() == 650.0
    assert pol.get_child_allowance() == 200.0


def test_mayor_daily_salary_and_approval():
    sim = Simulation()
    sim.time.current_datetime = datetime(2025, 1, 1, 8, 0)
    mayor = NPC("Иван", "Мэров", datetime(1980, 1, 1), "М", "Мэр", "home_1", "work_1")
    mayor.money = 1000.0
    mayor.is_alive = True
    sim.npcs = [mayor]
    
    sim.politics_manager.current_mayor_id = mayor.id
    sim.politics_manager.mayor_platform = "URBANIST"
    sim.politics_manager.approval_rating = 60.0
    sim.economy_manager.city_treasury = 50000.0
    
    # Run daily update
    sim.politics_manager.daily_update(datetime(2025, 1, 2))
    
    # Mayor received 600 salary from treasury
    assert mayor.money == 1600.0
    assert sim.economy_manager.city_treasury == 49400.0
    # Approval was calculated and within bounds
    assert 5.0 <= sim.politics_manager.approval_rating <= 98.0


def test_vote_of_no_confidence_triggers_early_election():
    sim = Simulation()
    sim.time.current_datetime = datetime(2025, 1, 1, 8, 0)
    mayor = NPC("Иван", "Непопулярный", datetime(1980, 1, 1), "М", "Бывший мэр", "home_1", "work_1")
    successor = NPC("Петр", "Народный", datetime(1985, 1, 1), "М", "Активист", "home_1", "work_1")
    mayor.is_alive = True
    successor.is_alive = True
    sim.npcs = [mayor, successor]
    
    sim.politics_manager.current_mayor_id = mayor.id
    sim.politics_manager.mayor_platform = "MARKET"
    sim.politics_manager.approval_rating = 15.0  # Very low approval
    sim.politics_manager.low_approval_streak = 59  # Day 59
    
    # Simulate low treasury and poverty so approval stays low (< 25.0)
    sim.economy_manager.city_treasury = 5000.0
    mayor.hunger = 10.0
    mayor.money = 50.0
    
    # Calling daily update will increment streak to 60 and trigger vote of no confidence
    sim.politics_manager.daily_update(datetime(2025, 1, 2))
    
    # New election took place, resetting approval to 75.0 and days_until_election to 1095
    assert sim.politics_manager.approval_rating == 75.0
    assert sim.politics_manager.days_until_election == 1095
    assert sim.politics_manager.low_approval_streak == 0


def test_politics_persistence_in_db(tmp_path):
    db_file = str(tmp_path / "test_politics.db")
    repo = Database(db_file)
    
    sim = Simulation()
    sim.time.current_datetime = datetime(2025, 3, 1, 12, 0)
    mayor = NPC("Сергей", "Собянин", datetime(1975, 1, 1), "М", "Градоначальник", "home_1", "work_1")
    sim.npcs = [mayor]
    sim.politics_manager.current_mayor_id = mayor.id
    sim.politics_manager.mayor_platform = "SOCIAL"
    sim.politics_manager.approval_rating = 77.5
    sim.politics_manager.days_in_office = 150
    sim.politics_manager.days_until_election = 945
    
    # Save world
    repo.save_world(
        sim_time=sim.time.get_time_dict(),
        npcs=sim.npcs,
        buildings=[],
        events=[],
        politics=sim.politics_manager.to_dict()
    )
    
    # Load world
    load_res = repo.load_world()
    assert len(load_res) >= 16
    pol_data = load_res[15]
    
    assert pol_data is not None
    assert pol_data["current_mayor_id"] == mayor.id
    assert pol_data["mayor_platform"] == "SOCIAL"
    assert pol_data["approval_rating"] == 77.5
    assert pol_data["days_in_office"] == 150
    assert pol_data["days_until_election"] == 945
    
    # Test restoring to another manager
    sim2 = Simulation()
    sim2.politics_manager.load_from_dict(pol_data)
    assert sim2.politics_manager.current_mayor_id == mayor.id
    assert sim2.politics_manager.approval_rating == 77.5
    assert sim2.politics_manager.get_tax_rate() == 0.18
