from datetime import datetime
import pytest
from living_world.engine.simulation import Simulation
from living_world.population.npc import NPC
from living_world.city.city import Building
from living_world.engine.economy.enterprise import Enterprise
from living_world.engine.event_bus import bus

def test_enterprise_dynasty_inheritance_to_adult_child():
    sim = Simulation()
    sim.time.current_datetime = datetime(2026, 5, 1, 10, 0)
    home = Building("Усадьба", "home", 6, b_id="h1")
    workshop_b = Building("Мастерская династии", "workshop", 10, b_id="w1")
    sim.city.add_building(home)
    sim.city.add_building(workshop_b)

    father = NPC("Иван", "Демидов", datetime(1955, 1, 1), "М", "Предприниматель", home.id, workshop_b.id, npc_id="father_demidov")
    son = NPC("Никита", "Демидов", datetime(1985, 5, 10), "М", "Безработный", home.id, None,
              npc_id="son_demidov", father_id="father_demidov")

    sim.add_npc(father)
    sim.add_npc(son)

    ent = Enterprise("Заводы Демидовых", "workshop", workshop_b.id, owner_id=father.id, budget=50000.0)
    sim.economy_manager.register_enterprise(ent)

    # Father passes away
    father.is_alive = False
    father.date_of_death = datetime(2026, 5, 1, 10, 0)
    bus.publish("npc_died", {"npc": father})

    # Son inherits family enterprise
    assert ent.owner_id == son.id
    assert son.id in ent.employees
    assert son.work_id == workshop_b.id
    assert son.profession == "Руководитель"

def test_city_chronicle_monthly_gazette():
    sim = Simulation()
    sim.time.current_datetime = datetime(2026, 5, 1, 10, 0)
    current_date = datetime(2026, 6, 1, 9, 30)
    sim.time.current_datetime = current_date

    # Add a citizen
    citizen = NPC("Анна", "Горожанкина", datetime(1990, 1, 1), "Ж", "Врач", "h1", "w1")
    sim.add_npc(citizen)

    chronicle = sim.city_chronicle
    chronicle.check_and_publish_monthly(current_date)

    latest = chronicle.get_latest_edition()
    assert latest is not None
    assert "Май 2026" in latest["title"]
    assert any("Население" in a for a in latest["articles"])
    assert any("Баланс городской казны" in a for a in latest["articles"])
