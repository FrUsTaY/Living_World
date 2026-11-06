from datetime import datetime
import pytest
from living_world.engine.simulation import Simulation
from living_world.population.npc import NPC
from living_world.city.city import Building
from living_world.engine.ai.basic_actions import StrollAction

def test_weather_and_seasonal_temperatures():
    sim = Simulation()
    wm = sim.weather_manager

    # Winter date (January)
    sim.time.current_datetime = datetime(2026, 1, 15, 12, 0)
    wm.update_weather(sim.time.current_datetime)
    assert wm.temperature <= 0.0
    assert sim.time.season_name == "Зима"

    # Force next day check for Summer date (July)
    wm._last_day = None
    sim.time.current_datetime = datetime(2026, 7, 15, 12, 0)
    wm.update_weather(sim.time.current_datetime)
    assert wm.temperature >= 18.0
    assert sim.time.season_name == "Лето"

def test_weather_impact_on_strolling():
    sim = Simulation()
    park = Building("Городской парк", "park", 50, b_id="p1")
    home = Building("Дом", "home", 4, b_id="h1")
    sim.city.add_building(park)
    sim.city.add_building(home)

    walker = NPC("Игорь", "Прогулкин", datetime(1995, 5, 5), "М", "Инженер", home.id, "w1")
    sim.add_npc(walker)

    stroll = StrollAction()
    time_dict = {'hour': 18, 'is_weekend': True}

    # Sunny weather boost
    sim.weather_manager.weather_condition = "Солнечно"
    util_sunny = stroll.calculate_utility(walker, sim, time_dict)

    # Rainy/stormy penalty
    sim.weather_manager.weather_condition = "Гроза, ливневый дождь"
    util_stormy = stroll.calculate_utility(walker, sim, time_dict)

    assert util_sunny > util_stormy
    assert util_stormy < util_sunny - 40.0
