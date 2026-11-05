import pytest
from datetime import datetime, timedelta
from living_world.engine.simulation import Simulation
from living_world.population.npc import NPC
from living_world.city.city import Building
from living_world.engine.economy.enterprise import Enterprise
from living_world.engine.economy.economy_manager import EconomyManager, PROFESSION_HOURLY_WAGES
from living_world.database.repository import Database

def test_enterprise_basic_operations():
    ent = Enterprise("Ферма 'Рассвет'", "farm", "b-1", budget=10000.0, wage_rate=250.0)
    assert ent.budget == 10000.0
    assert ent.is_active is True

    ent.receive_revenue(2500.0)
    assert ent.budget == 12500.0
    assert ent.daily_revenue == 2500.0

    success = ent.pay_expense(1000.0)
    assert success is True
    assert ent.budget == 11500.0
    assert ent.daily_expenses == 1000.0

    ent.reset_daily_stats()
    assert ent.daily_revenue == 0.0
    assert ent.daily_expenses == 0.0

def test_wages_by_profession():
    sim = Simulation()
    econ = sim.economy_manager

    assert econ.get_hourly_wage("Врач") == 550.0
    assert econ.get_hourly_wage("Инженер") == 500.0
    assert econ.get_hourly_wage("Строитель") == 400.0
    assert econ.get_hourly_wage("Разнорабочий") == 190.0

    # Test work wage payout
    b = Building("Мастерская", "work", 10)
    sim.city.add_building(b)
    ent = econ.create_enterprise("Городская мастерская", "workshop", b.id, budget=50000.0)

    npc = NPC("Иван", "Кузнецов", datetime(1990, 1, 1), "М", "Механик", "h-1", b.id)
    npc.money = 0.0
    sim.add_npc(npc)

    # 60 minutes of work
    earned = econ.pay_work_wage(npc, minutes=60.0)
    assert earned == pytest.approx(375.0, 0.01)
    assert npc.money == pytest.approx(375.0, 0.01)
    assert ent.budget == pytest.approx(50000.0 - 375.0, 0.01)
    assert npc.id in ent.employees

def test_food_purchase():
    sim = Simulation()
    econ = sim.economy_manager

    b_shop = Building("Продуктовый", "shop", 10)
    sim.city.add_building(b_shop)
    shop_ent = econ.create_enterprise("Продуктовый", "shop", b_shop.id, budget=10000.0)

    npc = NPC("Мария", "Иванова", datetime(1995, 1, 1), "Ж", "Учитель", "h-1", "w-1")
    npc.money = 500.0
    sim.add_npc(npc)

    paid = econ.purchase_food(npc, cost=150.0)
    assert paid == 150.0
    assert npc.money == 350.0
    assert shop_ent.budget == 10150.0

    # If NPC has 0 money, they get subsistence food with 0 paid
    poor_npc = NPC("Петр", "Бедный", datetime(1995, 1, 1), "М", "Разнорабочий", "h-1", "w-1")
    poor_npc.money = 0.0
    sim.add_npc(poor_npc)

    paid_poor = econ.purchase_food(poor_npc, cost=150.0)
    assert paid_poor == 0.0
    assert poor_npc.money == 0.0

def test_daily_cycle_dividends():
    sim = Simulation()
    econ = sim.economy_manager

    owner = NPC("Олигарх", "Богатов", datetime(1980, 1, 1), "М", "Инженер", "h-1", "w-1")
    owner.money = 1000.0
    sim.add_npc(owner)

    b = Building("Частная клиника", "work", 10)
    sim.city.add_building(b)
    clinic = econ.create_enterprise("Частная клиника", "hospital", b.id, owner_id=owner.id, budget=100000.0)

    # Simulate strong daily revenue
    clinic.receive_revenue(10000.0)
    clinic.pay_expense(2000.0)
    # Net daily profit = 8000, 25% dividend = 2000

    econ.daily_cycle()

    assert owner.money == pytest.approx(1000.0 + 2000.0, 0.01)
    assert clinic.budget == pytest.approx(100000.0 + 8000.0 - 2000.0, 0.01)

def test_db_save_load_enterprises(tmp_path):
    db_file = str(tmp_path / "test_economy.db")
    db = Database(db_file)

    ent = Enterprise("Ферма Южная", "farm", "b-farm-1", owner_id="npc-owner", budget=75000.0, wage_rate=300.0)

    db.save_world(
        sim_time={"year": 2026, "month": 5, "day": 10, "hour": 12, "minute": 0},
        npcs=[],
        buildings=[],
        events=[],
        enterprises=[ent]
    )

    loaded = db.load_world()
    loaded_enterprises = loaded[13]

    assert len(loaded_enterprises) == 1
    loaded_ent = loaded_enterprises[0]
    assert loaded_ent["id"] == ent.id
    assert loaded_ent["name"] == "Ферма Южная"
    assert loaded_ent["type"] == "farm"
    assert loaded_ent["building_id"] == "b-farm-1"
    assert loaded_ent["owner_id"] == "npc-owner"
    assert loaded_ent["budget"] == 75000.0
    assert loaded_ent["wage_rate"] == 300.0
    assert loaded_ent["is_active"] == 1
