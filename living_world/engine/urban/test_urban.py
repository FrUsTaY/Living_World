import pytest
from datetime import datetime
from living_world.engine.simulation import Simulation
from living_world.population.npc import NPC
from living_world.population.generation import generate_initial_world
from living_world.city.district import District
from living_world.city.city import Building
from living_world.engine.urban.construction_manager import ConstructionProject, ConstructionManager

def test_district_basics():
    d = District("Северный район", "residential")
    assert d.name == "Северный район"
    assert d.district_type == "residential"
    assert len(d.building_ids) == 0

    d.add_building("b-1")
    assert "b-1" in d.building_ids

    d_dict = d.to_dict()
    assert d_dict["name"] == "Северный район"
    restored = District.from_dict(d_dict)
    assert restored.name == d.name
    assert restored.building_ids == ["b-1"]

def test_construction_project_progress():
    proj = ConstructionProject("Дом №11", "home", target_capacity=4)
    assert proj.progress == 0.0
    assert proj.is_completed is False

    done = proj.advance(50.0)
    assert done is False
    assert proj.progress == 50.0

    done = proj.advance(60.0)
    assert done is True
    assert proj.progress == 100.0
    assert proj.is_completed is True

def test_evaluate_city_growth_triggers_home_project():
    sim = Simulation()
    generate_initial_world(sim.city, sim, 20)

    cm = sim.construction_manager
    assert len(cm.active_projects) == 0

    # Fill homes to create artificial housing deficit
    homes = sim.city.get_homes()
    for i in range(16):
        dummy = NPC(f"Test{i}", "Fake", datetime(1990, 1, 1), "М", "Разнорабочий", homes[0].id, "work")
        sim.add_npc(dummy)

    # 36 npcs out of 40 capacity = 90% occupancy!
    cm.evaluate_city_growth()

    # A home project should be initiated!
    assert len(cm.active_projects) >= 1
    home_projs = [p for p in cm.active_projects if p.building_type == "home"]
    assert len(home_projs) >= 1

def test_advance_and_finalize_construction():
    sim = Simulation()
    generate_initial_world(sim.city, sim, 20)
    cm = sim.construction_manager

    # Create project manually
    proj = ConstructionProject("Мастерская №2", "work", target_capacity=6, enterprise_type="workshop")
    cm.active_projects.append(proj)

    builder = next(n for n in sim.npcs if n.profession == "Строитель")

    # Complete the project by advancing construction
    while not proj.is_completed:
        cm.advance_construction(builder, minutes=100.0)

    assert proj.is_completed is True
    assert proj in cm.completed_projects
    assert proj not in cm.active_projects

    # Check building was added to city
    new_b = next((b for b in sim.city.buildings if b.name == "Мастерская №2"), None)
    assert new_b is not None
    assert new_b.b_type == "work"

    # Check enterprise was created
    ent = sim.economy_manager.get_enterprise_for_building(new_b.id)
    assert ent is not None
    assert ent.name == "Мастерская №2"

def test_district_expansion():
    sim = Simulation()
    generate_initial_world(sim.city, sim, 20)
    cm = sim.construction_manager

    initial_districts_cnt = len(sim.city.districts)

    # Fill all existing districts with dummy buildings
    for d in sim.city.districts:
        for i in range(10):
            d.add_building(f"dummy-{d.id}-{i}")

    # Now ask for a target district
    new_d = cm.get_or_create_target_district()
    assert len(sim.city.districts) == initial_districts_cnt + 1
    assert "район" in new_d.name.lower() or "массив" in new_d.name.lower()

def test_order_private_home():
    sim = Simulation()
    generate_initial_world(sim.city, sim, 20)
    cm = sim.construction_manager

    wealthy = NPC("Григорий", "Романов", datetime(1985, 1, 1), "М", "Инженер", "home_1", "work_1")
    wealthy.money = 70000.0
    sim.add_npc(wealthy)

    proj = cm.order_private_home(wealthy, house_name="Усадьба Романовых")
    assert proj is not None
    assert proj.commissioner_id == wealthy.id
    assert wealthy.money == 35000.0
    assert proj in cm.active_projects

    builder = next((n for n in sim.npcs if n.profession == "Строитель"), None)
    if not builder:
        builder = NPC("Иван", "Строителев", datetime(1990, 1, 1), "М", "Строитель", "home_1", "work_1")
        sim.add_npc(builder)
    while not proj.is_completed:
        cm.advance_construction(builder, minutes=100.0)

    # Commissioner moves in!
    b = next((b for b in sim.city.buildings if b.name == "Усадьба Романовых"), None)
    assert b is not None
    assert wealthy.home_id == b.id
