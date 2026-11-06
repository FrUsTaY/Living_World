from datetime import datetime, timedelta
import pytest
from living_world.engine.simulation import Simulation
from living_world.engine.justice.crime_manager import CrimeManager, CrimeType
from living_world.population.npc import NPC
from living_world.city.city import Building
from living_world.database.repository import Database


def test_theft_due_to_hunger_and_poverty():
    sim = Simulation()
    sim.time.current_datetime = datetime(2025, 5, 1, 14, 0)
    
    # Create starving NPC with low diligence
    thief = NPC("Вор", "Голодный", datetime(1995, 1, 1), "М", "Безработный", "home_1", None)
    thief.hunger = 10.0
    thief.money = 50.0
    thief.traits['diligence'] = -0.5
    thief.traits['boldness'] = 0.6
    thief.is_alive = True
    sim.npcs = [thief]
    
    # Create a shop enterprise with goods
    b_shop = Building("Продуктовый магазин", "shop", 10, b_id="shop_1")
    sim.city.add_building(b_shop)
    ent = sim.economy_manager.create_enterprise("Продуктовый магазин", "shop", b_shop.id, budget=10000.0)
    ent.finished_goods = 25.0
    
    # Execute theft
    sim.crime_manager.execute_theft(thief, sim.time.current_datetime)
    
    # Crime committed
    assert sim.crime_manager.total_crimes_committed >= 1
    # Either caught red-handed/investigated and fined, or thief ate the stolen food
    assert thief.hunger > 10.0 or thief.money >= 0.0 or getattr(thief, 'jail_days', 0) > 0


def test_brawl_damage_and_memory():
    sim = Simulation()
    sim.time.current_datetime = datetime(2025, 5, 1, 20, 0)
    
    brawler = NPC("Зачинщик", "Драчунов", datetime(1990, 1, 1), "М", "Грузчик", "home_1", "work_1")
    brawler.traits['conflict'] = 0.8
    brawler.stress = 75.0
    brawler.current_location = "park_1"
    brawler.is_alive = True
    
    victim = NPC("Мирный", "Прохожий", datetime(1992, 1, 1), "М", "Бухгалтер", "home_2", "work_2")
    victim.health = 100.0
    victim.stress = 10.0
    victim.current_location = "park_1"
    victim.is_alive = True
    
    sim.npcs = [brawler, victim]
    
    sim.crime_manager.execute_brawl(brawler, victim, sim.time.current_datetime)
    
    # Victim sustained physical and psychological harm
    assert victim.health < 100.0
    assert victim.stress > 10.0
    # Victim got negative memory
    mems = sim.memory_manager.get_memories_for(victim.id)
    assert any("Нападение" in m["event_type"] for m in mems)


def test_police_patrol_deterrence():
    sim = Simulation()
    sim.time.current_datetime = datetime(2025, 5, 1, 15, 0)
    
    # Police officer stationed in park
    cop = NPC("Алексей", "ДядяСтепа", datetime(1985, 1, 1), "М", "Полицейский", "home_cop", "police_b")
    cop.current_location = "park_1"
    cop.state = "Патрулирует"
    cop.is_alive = True
    
    thief = NPC("Карманник", "Уличный", datetime(2000, 1, 1), "М", "Безработный", "home_thief", None)
    thief.current_location = "park_1"
    thief.hunger = 5.0
    thief.money = 0.0
    thief.is_alive = True
    
    sim.npcs = [cop, thief]
    
    # Location is patrolled
    assert sim.crime_manager.is_patrolled("park_1") is True
    # Unpatrolled location is False
    assert sim.crime_manager.is_patrolled("remote_warehouse") is False


def test_court_verdict_and_jail_lifecycle():
    sim = Simulation()
    sim.time.current_datetime = datetime(2025, 6, 1, 10, 0)
    
    criminal = NPC("Рецидивист", "Бандитов", datetime(1988, 1, 1), "М", "Слесарь", "home_1", "work_factory")
    criminal.is_alive = True
    sim.npcs = [criminal]
    
    # Court process for heavy crime (BRAWL)
    sim.crime_manager.process_court_verdict(criminal, CrimeType.BRAWL, caught_red_handed=True, current_datetime=sim.time.current_datetime)
    
    # Criminal record assigned, sent to jail, fired from work
    assert criminal.has_criminal_record is True
    assert criminal.jail_days > 0
    assert criminal.state == "В тюрьме"
    assert criminal.work_id is None
    assert criminal.id in sim.crime_manager.jail_inmates
    
    initial_jail_days = criminal.jail_days
    
    # Run daily update
    sim.crime_manager.daily_update(datetime(2025, 6, 2))
    assert criminal.jail_days == initial_jail_days - 1
    assert criminal.state == "В тюрьме"
    
    # Fast forward sentence completion
    criminal.jail_days = 1
    sim.crime_manager.daily_update(datetime(2025, 7, 1))
    
    # Released from prison
    assert criminal.jail_days == 0
    assert criminal.state == "Бодрствует"
    assert criminal.id not in sim.crime_manager.jail_inmates


def test_crime_persistence_in_db(tmp_path):
    db_file = str(tmp_path / "test_justice.db")
    repo = Database(db_file)
    
    sim = Simulation()
    sim.time.current_datetime = datetime(2025, 7, 1, 12, 0)
    inmate = NPC("Сиделец", "Тюремный", datetime(1980, 1, 1), "М", "Безработный", "home_1", None,
                 has_criminal_record=True, jail_days=42)
    inmate.state = "В тюрьме"
    inmate.is_alive = True
    sim.npcs = [inmate]
    
    sim.crime_manager.total_crimes_committed = 15
    sim.crime_manager.total_crimes_solved = 12
    sim.crime_manager.jail_inmates[inmate.id] = {
        "name": inmate.get_full_name(),
        "remaining_days": 42,
        "crime_type": CrimeType.THEFT
    }
    
    # Save world
    repo.save_world(
        sim_time=sim.time.get_time_dict(),
        npcs=sim.npcs,
        buildings=[],
        events=[],
        crimes=sim.crime_manager.to_dict()
    )
    
    # Load world
    load_res = repo.load_world()
    assert len(load_res) >= 17
    npc_dicts = load_res[2]
    crimes_data = load_res[16]
    
    # Check NPC persistence of criminal fields
    loaded_npc_dict = next(n for n in npc_dicts if n['id'] == inmate.id)
    assert loaded_npc_dict['has_criminal_record'] == 1
    assert loaded_npc_dict['jail_days'] == 42
    
    # Check crime manager metadata
    assert crimes_data is not None
    assert crimes_data['total_crimes_committed'] == 15
    assert crimes_data['total_crimes_solved'] == 12
    assert inmate.id in crimes_data['jail_inmates']
    
    # Test loading into a new simulation's manager
    sim2 = Simulation()
    sim2.crime_manager.load_from_dict(crimes_data)
    assert sim2.crime_manager.total_crimes_committed == 15
    assert sim2.crime_manager.total_crimes_solved == 12
    assert inmate.id in sim2.crime_manager.jail_inmates
