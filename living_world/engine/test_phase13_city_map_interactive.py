from datetime import datetime
import pytest
from PySide6.QtWidgets import QApplication
from living_world.engine.simulation import Simulation
from living_world.gui.tabs.city_map_tab import CityMapTab, BuildingGraphicsItem, NPCGraphicsItem
from living_world.population.npc import NPC
from living_world.city.city import Building


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_city_map_tab_creation_and_layout(qapp):
    sim = Simulation()
    sim.time.current_datetime = datetime(2025, 6, 1, 14, 0) # Daytime
    
    # Add buildings of different types
    b_home = Building("Дом №1", "home", 4, b_id="home_1", x=100.0, y=100.0)
    b_shop = Building("Супермаркет", "shop", 15, b_id="shop_1", x=300.0, y=100.0)
    b_park = Building("Парк", "park", 30, b_id="park_1", x=500.0, y=100.0)
    sim.city.buildings = [b_home, b_shop, b_park]
    
    # Add NPCs inside home and shop
    npc1 = NPC("Иван", "Жильцов", datetime(1990, 1, 1), "М", "Инженер", b_home.id, b_shop.id)
    npc1.current_location = b_home.id
    npc1.money = 25000.0
    npc1.is_alive = True
    
    npc2 = NPC("Ольга", "Кассир", datetime(1992, 1, 1), "Ж", "Продавец", b_home.id, b_shop.id)
    npc2.current_location = b_shop.id
    npc2.money = 12000.0
    npc2.is_alive = True
    
    sim.npcs = [npc1, npc2]
    
    # Create map tab
    map_tab = CityMapTab(sim, None)
    map_tab.update_data()
    
    # Check scene items
    items = map_tab.scene.items()
    assert len(items) > 0
    
    # Building items exist
    building_items = [i for i in items if isinstance(i, BuildingGraphicsItem)]
    assert len(building_items) == 3
    
    # NPC items exist
    npc_items = [i for i in items if isinstance(i, NPCGraphicsItem)]
    assert len(npc_items) == 2


def test_heatmap_modes_update_colors(qapp):
    sim = Simulation()
    sim.time.current_datetime = datetime(2025, 6, 1, 12, 0)
    
    b1 = Building("Дом Новый", "home", 4, b_id="h1", condition=95.0, x=100.0, y=100.0)
    b2 = Building("Ветхий Склад", "work", 10, b_id="w1", condition=45.0, x=300.0, y=100.0)
    sim.city.buildings = [b1, b2]
    
    map_tab = CityMapTab(sim, None)
    
    # 1. Condition / Wear Heatmap
    map_tab.current_mode = "Технический износ фонда (Теплокарта)"
    color_b1 = map_tab._get_building_color(b1)
    color_b2 = map_tab._get_building_color(b2)
    # Good condition is green, poor condition is red
    assert color_b1.name().upper() == "#2ECC71"
    assert color_b2.name().upper() == "#E74C3C"
    
    # 2. Population Density Heatmap
    map_tab.current_mode = "Плотность населения (Теплокарта)"
    color_empty = map_tab._get_building_color(b1)
    assert color_empty.name().upper() == "#7F8C8D" # Gray for 0 occupants
    
    # Add 4 occupants to b1
    for i in range(4):
        n = NPC(f"Житель{i}", "Тест", datetime(1995, 1, 1), "М", "Рабочий", b1.id, None)
        n.current_location = b1.id
        n.is_alive = True
        sim.npcs.append(n)
        
    color_populated = map_tab._get_building_color(b1)
    assert color_populated.name().upper() == "#F1C40F" # Yellow for 3-5 occupants


def test_building_selection_updates_side_panel(qapp):
    sim = Simulation()
    b_cafe = Building("Уютное кафе", "cafe", 12, b_id="cafe_1")
    sim.city.buildings = [b_cafe]
    
    waiter = NPC("Сергей", "Бариста", datetime(1998, 1, 1), "М", "Бариста", "home_1", b_cafe.id)
    waiter.current_location = b_cafe.id
    waiter.is_alive = True
    sim.npcs = [waiter]
    
    map_tab = CityMapTab(sim, None)
    map_tab.select_building(b_cafe)
    
    # Side panel updated
    assert "Уютное кафе" in map_tab.lbl_building_title.text()
    assert map_tab.occupants_list.count() == 1
    assert "Сергей Бариста" in map_tab.occupants_list.item(0).text()


def test_night_mode_environment_lighting(qapp):
    sim = Simulation()
    # Nighttime at 23:00
    sim.time.current_datetime = datetime(2025, 6, 1, 23, 0)
    
    b_home = Building("Ночной дом", "home", 4, b_id="home_night", x=120.0, y=120.0)
    sim.city.buildings = [b_home]
    
    sleeper = NPC("Михаил", "Спящий", datetime(1985, 1, 1), "М", "Слесарь", b_home.id, None)
    sleeper.current_location = b_home.id
    sleeper.state = "Спит"
    sleeper.is_alive = True
    sim.npcs = [sleeper]
    
    map_tab = CityMapTab(sim, None)
    map_tab.update_data()
    
    # Background is dark night color
    bg = map_tab.scene.backgroundBrush().color()
    assert bg.name().upper() == "#141A29"
    assert "🌙" in map_tab.lbl_env.text()
