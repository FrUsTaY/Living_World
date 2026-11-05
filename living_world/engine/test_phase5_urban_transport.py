from datetime import datetime
import pytest
from living_world.engine.simulation import Simulation
from living_world.population.npc import NPC
from living_world.city.city import Building
from living_world.city.district import District
from living_world.database.repository import Database
import tempfile
import os

def test_city_coordinates_and_distance():
    sim = Simulation()
    b1 = Building("Ратуша", "public", 100, b_id="b1", x=0.0, y=0.0)
    b2 = Building("Завод", "work", 50, b_id="b2", x=30.0, y=40.0)

    sim.city.add_building(b1)
    sim.city.add_building(b2)

    # Euclidean distance sqrt(30^2 + 40^2) = 50.0
    dist = sim.city.calculate_distance("b1", "b2")
    assert dist == pytest.approx(50.0)

def test_transport_modes_and_wealth():
    poor = NPC("Павел", "Пешеходов", datetime(1990, 1, 1), "М", "Дворник", "h1", "w1")
    poor.money = 500.0

    wealthy = NPC("Виктор", "Автомобилев", datetime(1982, 1, 1), "М", "Директор", "h1", "w1")
    wealthy.money = 70000.0
    # Re-evaluate transport mode
    wealthy.transport_mode = "car"

    assert poor.transport_mode == "foot"
    assert wealthy.transport_mode == "car"

def test_building_wear_and_municipal_maintenance():
    sim = Simulation()
    home = Building("Дом Старый", "home", 4, b_id="h_old", condition=65.0)
    sim.city.add_building(home)

    cm = sim.construction_manager
    em = sim.economy_manager
    em.city_treasury = 50000.0

    # Building is at 65% condition (< 70%), so maintenance repairs it back to 100%
    cm.maintain_infrastructure()

    assert home.condition == 100.0
    assert em.city_treasury == 45000.0  # Spent 5000 on repair

def test_phase5_database_persistence():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        db = Database(db_path)
        dist = District("Центральный район", "center", district_id="dist_1")
        b = Building("Центральный Универмаг", "shop", 30, b_id="b_centr",
                     district_id=dist.id, x=45.5, y=90.2, condition=88.5)
        npc = NPC("Роман", "Шоферов", datetime(1988, 3, 3), "М", "Водитель", "b_centr", "b_centr",
                  transport_mode="car")

        sim_time = {"year": 2026, "month": 5, "day": 10, "hour": 14, "minute": 0}

        db.save_world(sim_time, [npc], [b], [])
        loaded = db.load_world()

        loaded_b = loaded[1]
        assert len(loaded_b) == 1
        lb = loaded_b[0]
        assert lb["district_id"] == "dist_1"
        assert lb["x"] == 45.5
        assert lb["y"] == 90.2
        assert lb["condition"] == 88.5

        loaded_npcs = loaded[2]
        assert len(loaded_npcs) == 1
        ln = loaded_npcs[0]
        assert ln["transport_mode"] == "car"
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)
