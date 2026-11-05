from datetime import datetime
import pytest
from living_world.engine.simulation import Simulation
from living_world.population.npc import NPC
from living_world.city.city import Building
from living_world.engine.economy.enterprise import Enterprise
from living_world.database.repository import Database
import tempfile
import os

def test_supply_chains_production_and_trade():
    sim = Simulation()
    farm_b = Building("Ферма", "farm", 10, b_id="b_farm")
    shop_b = Building("Пекарня", "shop", 10, b_id="b_shop")
    cafe_b = Building("Кафе", "cafe", 10, b_id="b_cafe")
    sim.city.add_building(farm_b)
    sim.city.add_building(shop_b)
    sim.city.add_building(cafe_b)

    farm = Enterprise("Ферма Родниковая", "farm", farm_b.id, budget=10000.0, raw_materials=0.0)
    farm.add_employee("worker_1")
    farm.add_employee("worker_2")
    shop = Enterprise("Пекарня Хлеб", "shop", shop_b.id, budget=5000.0, raw_materials=0.0, finished_goods=0.0)
    cafe = Enterprise("Уютное кафе", "cafe", cafe_b.id, budget=5000.0, finished_goods=0.0)

    em = sim.economy_manager
    em.register_enterprise(farm)
    em.register_enterprise(shop)
    em.register_enterprise(cafe)

    # 1. Farm produces raw materials
    em.process_supply_chains()
    assert farm.raw_materials > 0.0

    # 2. Shop buys raw materials from farm and converts to finished goods
    # Run cycle again: farm produces more, shop converts
    em.process_supply_chains()
    assert shop.finished_goods > 0.0

def test_mortgage_financing_and_daily_repayment():
    sim = Simulation()
    home_b = Building("Жилой дом", "home", 4, b_id="home_1")
    sim.city.add_building(home_b)

    buyer = NPC("Илья", "Ипотечников", datetime(1985, 1, 1), "М", "Инженер", home_b.id, "work_1")
    buyer.money = 15000.0  # Has down payment (> 10000) but less than 35000 full cost
    sim.add_npc(buyer)

    cm = sim.construction_manager
    em = sim.economy_manager
    em.city_treasury = 50000.0

    # Order private home with mortgage
    proj = cm.order_private_home(buyer, house_name="Ипотечный дом")
    assert proj is not None
    assert buyer.money == 0.0
    assert buyer.mortgage_debt > 0.0  # Loan was (35000 - 15000) = 20000 * 1.05 = 21000
    assert buyer.mortgage_payment > 0.0

    # Give buyer income to pay mortgage
    buyer.money = 1000.0
    initial_debt = buyer.mortgage_debt
    initial_treasury = em.city_treasury

    em.process_banking_and_welfare()

    assert buyer.mortgage_debt < initial_debt
    assert em.city_treasury > initial_treasury

def test_motherhood_welfare_benefit():
    sim = Simulation()
    current_date = datetime(2026, 5, 1)
    sim.time.current_datetime = current_date

    mother = NPC("Светлана", "Мамина", datetime(1995, 1, 1), "Ж", "Безработная", "home_1", None)
    mother.money = 100.0
    # Infant is 6 months old (BABY stage)
    baby = NPC("Малыш", "Мамин", datetime(2025, 11, 1), "М", "Младенец", "home_1", None,
               mother_id=mother.id)

    sim.add_npc(mother)
    sim.add_npc(baby)

    em = sim.economy_manager
    em.city_treasury = 10000.0

    em.process_banking_and_welfare()

    # Mother received 200 rubles allowance
    assert mother.money == 300.0
    assert em.city_treasury == 9800.0

def test_phase4_database_persistence():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        db = Database(db_path)
        home = Building("Жилой дом", "home", 4, b_id="h1")
        farm_b = Building("Ферма", "farm", 10, b_id="b1")

        npc = NPC("Антон", "Арендаторов", datetime(1990, 1, 1), "М", "Инженер", "h1", "w1",
                  is_renting=True, mortgage_debt=18500.0, mortgage_payment=308.33)
        ent = Enterprise("Ферма Восход", "farm", "b1", raw_materials=45.0, finished_goods=30.0)

        sim_time = {"year": 2026, "month": 5, "day": 10, "hour": 14, "minute": 0}

        db.save_world(sim_time, [npc], [home, farm_b], [], enterprises=[ent])
        loaded = db.load_world()

        loaded_npcs = loaded[2]
        assert len(loaded_npcs) == 1
        ln = loaded_npcs[0]
        assert ln["is_renting"] == 1
        assert ln["mortgage_debt"] == 18500.0
        assert ln["mortgage_payment"] == pytest.approx(308.33, rel=1e-2)

        loaded_ents = loaded[13]
        assert len(loaded_ents) == 1
        le = loaded_ents[0]
        assert le["raw_materials"] == 45.0
        assert le["finished_goods"] == 30.0
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)
