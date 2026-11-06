from datetime import datetime
import pytest
from living_world.engine.simulation import Simulation
from living_world.engine.property.property_manager import PropertyManager
from living_world.population.npc import NPC
from living_world.city.city import Building
from living_world.database.repository import Database


def test_household_appliances_and_home_comfort():
    sim = Simulation()
    sim.time.current_datetime = datetime(2025, 4, 1, 10, 0)
    
    b_home = Building("Дом семьи Ивановых", "home", 4, b_id="home_1")
    sim.city.add_building(b_home)
    hh = sim.household_manager.create_household(b_home.id)
    
    father = NPC("Иван", "Иванов", datetime(1985, 1, 1), "М", "Инженер", b_home.id, "work_1")
    father.money = 60000.0
    father.household_id = hh.id
    father.is_alive = True
    
    sim.npcs = [father]
    assert hh.home_comfort == 40.0
    assert len(hh.appliances) == 0
    
    # Run daily property evaluation
    sim.property_manager.daily_update(sim.time.current_datetime)
    
    # Household purchased first appliance (e.g. Refrigerator)
    assert len(hh.appliances) >= 1
    assert hh.home_comfort > 40.0
    assert father.money < 60000.0


def test_car_purchase_and_maintenance():
    sim = Simulation()
    sim.time.current_datetime = datetime(2025, 5, 1, 12, 0)
    
    rich_npc = NPC("Анатолий", "Богачев", datetime(1982, 1, 1), "М", "Директор", "home_1", "work_1")
    rich_npc.money = 150000.0
    rich_npc.transport_mode = "foot"
    rich_npc.is_alive = True
    sim.npcs = [rich_npc]
    
    # Run daily update
    sim.property_manager.daily_update(sim.time.current_datetime)
    
    # Purchased car
    assert rich_npc.transport_mode == "car"
    assert rich_npc.money <= 150000.0 - 95000.0
    assert sim.property_manager.total_cars_bought >= 1


def test_warm_clothes_winter_protection():
    sim = Simulation()
    sim.time.current_datetime = datetime(2025, 1, 10, 8, 0) # Winter
    sim.weather_manager.temperature = -12.0
    
    npc = NPC("Семен", "Мерзляков", datetime(1990, 1, 1), "М", "Продавец", "home_1", "work_1")
    npc.money = 8000.0
    npc.has_warm_clothes = False
    npc.is_alive = True
    sim.npcs = [npc]
    
    # Run update
    sim.property_manager.daily_update(sim.time.current_datetime)
    
    # Bought warm winter jacket
    assert npc.has_warm_clothes is True
    assert npc.money == 5500.0


def test_pet_adoption_and_walk_action():
    sim = Simulation()
    sim.time.current_datetime = datetime(2025, 6, 1, 19, 0)
    
    b_home = Building("Дом пенсионера", "home", 2, b_id="home_elder")
    b_park = Building("Городской парк", "park", 50, b_id="park_1")
    sim.city.add_building(b_home)
    sim.city.add_building(b_park)
    
    hh = sim.household_manager.create_household(b_home.id)
    elder = NPC("Василий", "Одинокий", datetime(1955, 1, 1), "М", "Пенсионер", b_home.id, None)
    elder.money = 12000.0
    elder.household_id = hh.id
    elder.stress = 50.0
    elder.mood = 40.0
    elder.is_alive = True
    sim.npcs = [elder]
    
    # Adopt pet
    sim.property_manager.daily_update(sim.time.current_datetime)
    assert hh.pet is not None
    assert hh.pet["name"] in (PropertyManager.DOG_NAMES + PropertyManager.CAT_NAMES)
    
    # Force pet to be dog to test park walk
    hh.pet = {"type": "dog", "name": "Дружок"}
    
    from living_world.engine.ai.basic_actions import WalkPetAction
    action = WalkPetAction()
    time_dict = sim.time.get_time_dict()
    time_dict['hour'] = 19
    time_dict['is_weekend'] = False
    
    assert action.check_preconditions(elder, sim, time_dict) is True
    assert action.calculate_utility(elder, sim, time_dict) > 0.0
    
    action.execute(elder, sim, time_dict)
    assert elder.current_location == b_park.id
    assert elder.stress < 50.0
    assert elder.mood > 40.0


def test_gift_giving_social_impact():
    sim = Simulation()
    
    sender = NPC("Роман", "Влюбленный", datetime(1995, 1, 1), "М", "Дизайнер", "home_1", "work_1")
    sender.money = 5000.0
    sender.is_alive = True
    
    receiver = NPC("Алиса", "Прекрасная", datetime(1997, 1, 1), "Ж", "Актриса", "home_2", "work_2")
    receiver.mood = 40.0
    receiver.stress = 30.0
    receiver.is_alive = True
    
    sim.npcs = [sender, receiver]
    
    sim.property_manager.give_gift(sender, receiver, "Букет роз и коробка конфет", cost=600.0)
    
    assert sender.money == 4400.0
    assert receiver.mood == 60.0
    assert receiver.stress == 15.0
    
    rm = sim.relationship_manager
    rel = rm.get_relationship(receiver.id, sender.id)
    assert rel["affinity"] == 20.0
    assert rel["trust"] == 15.0


def test_property_persistence_in_db(tmp_path):
    db_file = str(tmp_path / "test_property.db")
    repo = Database(db_file)
    
    sim = Simulation()
    sim.time.current_datetime = datetime(2025, 7, 1, 12, 0)
    
    b_home = Building("Коттедж", "home", 4, b_id="home_cottage")
    hh = sim.household_manager.create_household(b_home.id)
    hh.appliances = ["Холодильник", "Стиральная машина"]
    hh.pet = {"type": "dog", "name": "Рекс"}
    hh.home_comfort = 70.0
    
    npc = NPC("Владелец", "Имущества", datetime(1988, 1, 1), "М", "Архитектор", b_home.id, "work_1",
              has_warm_clothes=True)
    npc.household_id = hh.id
    npc.transport_mode = "car"
    npc.is_alive = True
    sim.npcs = [npc]
    
    sim.property_manager.total_cars_bought = 2
    sim.property_manager.total_pets_adopted = 5
    sim.property_manager.total_appliances_bought = 8
    
    # Save world
    repo.save_world(
        sim_time=sim.time.get_time_dict(),
        npcs=sim.npcs,
        buildings=[b_home],
        events=[],
        households=list(sim.household_manager.households.values()),
        property_data=sim.property_manager.to_dict()
    )
    
    # Load world
    load_res = repo.load_world()
    assert len(load_res) >= 19
    npc_dicts = load_res[2]
    hh_dicts = load_res[11]
    prop_data = load_res[18]
    
    # Check NPC warm clothes
    loaded_npc = next(n for n in npc_dicts if n['id'] == npc.id)
    assert loaded_npc['has_warm_clothes'] == 1
    assert loaded_npc['transport_mode'] == 'car'
    
    # Check household appliances and pet
    loaded_hh = next(h for h in hh_dicts if h['id'] == hh.id)
    assert loaded_hh is not None
    
    # Check property manager meta
    assert prop_data is not None
    assert prop_data["total_cars_bought"] == 2
    assert prop_data["total_pets_adopted"] == 5
    assert prop_data["total_appliances_bought"] == 8
