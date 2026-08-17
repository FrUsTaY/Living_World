import pytest
from datetime import datetime, timedelta
import uuid

from living_world.engine.simulation import Simulation
from living_world.engine.social.household import Household
from living_world.population.npc import NPC
from living_world.database.repository import Database
from living_world.city.city import Building
import os

def create_npc(sim, gender, age_years, home_id="home_1"):
    birth_date = sim.time.current_datetime - timedelta(days=age_years * 365)
    npc = NPC(
        first_name="Test",
        last_name="Testov",
        date_of_birth=birth_date,
        gender=gender,
        profession="Безработный",
        home_id=home_id,
        work_id=None
    )
    sim.add_npc(npc)
    return npc

def test_household_creation_and_roles():
    sim = Simulation()
    hm = sim.household_manager

    # 1. Создаем домохозяйство
    hh = hm.create_household("home_1")
    assert hh.id in hm.households

    # 2. Добавляем NPC
    father = create_npc(sim, "М", 30)
    mother = create_npc(sim, "Ж", 28)
    teen = create_npc(sim, "М", 15)
    baby = create_npc(sim, "Ж", 1)

    father.household_id = hh.id
    mother.household_id = hh.id
    teen.household_id = hh.id
    baby.household_id = hh.id

    # 3. Проверка ролей (взрослые и дети)
    adults = hm.get_adults(hh.id)
    assert len(adults) == 2
    assert father in adults
    assert mother in adults

    children = hm.get_children(hh.id)
    assert len(children) == 1
    assert baby in children
    assert teen not in children # Подростки (TEEN) пока не считаются "зависимыми детьми" в get_children

    # 4. Общие ресурсы
    father.money = 1000.0
    mother.money = 500.0
    baby.money = 10.0
    assert hm.get_total_wealth(hh.id) == 1510.0

def test_childbirth_inherits_household():
    sim = Simulation()
    hm = sim.household_manager

    hh = hm.create_household("home_1")
    mother = create_npc(sim, "Ж", 28)
    mother.household_id = hh.id

    father = create_npc(sim, "М", 30)
    father.household_id = hh.id

    # Искусственно вызываем беременность и рождение
    rm = sim.reproduction_manager
    p = rm.conception(mother, father)
    rm.process_birth(p)

    # Ищем новорожденного
    baby = next((n for n in sim.npcs if getattr(n, 'mother_id', None) == mother.id), None)

    assert baby is not None
    assert baby.household_id == hh.id

    # Младенец должен числиться в детях домохозяйства
    children = hm.get_children(hh.id)
    assert baby in children

def test_care_by_other_adult_in_household():
    sim = Simulation()
    hm = sim.household_manager

    hh = hm.create_household("home_1")
    mother = create_npc(sim, "Ж", 28)
    mother.household_id = hh.id

    # Не биологический родственник, но живет с ними
    other_adult = create_npc(sim, "Ж", 35)
    other_adult.household_id = hh.id

    baby = create_npc(sim, "М", 1)
    baby.mother_id = mother.id
    baby.household_id = hh.id
    baby.hunger = 0.0

    time_dict = sim.time.get_time_dict()

    from living_world.engine.ai.family_actions import CareForChildAction
    care_action = CareForChildAction()

    # Мать может заботиться (она био родитель)
    assert care_action.check_preconditions(mother, sim, time_dict) == True
    utility_mother = care_action.calculate_utility(mother, sim, time_dict)

    # Другой взрослый тоже может заботиться, так как они в одном Household
    assert care_action.check_preconditions(other_adult, sim, time_dict) == True
    utility_other = care_action.calculate_utility(other_adult, sim, time_dict)

    # Биологический родитель должен иметь более высокий приоритет
    assert utility_mother > utility_other

    # Если мать умирает
    mother.is_alive = False

    # Другой взрослый все равно должен иметь мотивацию
    utility_other_after_death = care_action.calculate_utility(other_adult, sim, time_dict)
    assert utility_other_after_death > 0
    # Причем мотивация должна вырасти, так как био родителя больше нет рядом
    assert utility_other_after_death > utility_other

def test_biological_parent_in_different_household():
    sim = Simulation()
    hm = sim.household_manager

    hh1 = hm.create_household("home_1") # Дом матери и ребенка
    hh2 = hm.create_household("home_2") # Дом отца

    mother = create_npc(sim, "Ж", 28)
    mother.household_id = hh1.id
    mother.current_location = "home_1"

    father = create_npc(sim, "М", 30)
    father.household_id = hh2.id
    father.current_location = "home_2"

    baby = create_npc(sim, "М", 1)
    baby.mother_id = mother.id
    baby.father_id = father.id
    baby.household_id = hh1.id
    baby.current_location = "home_1"
    baby.hunger = 0.0

    time_dict = sim.time.get_time_dict()
    from living_world.engine.ai.family_actions import CareForChildAction
    care_action = CareForChildAction()

    # Отец может позаботиться (он био родитель, хоть и живет отдельно)
    assert care_action.check_preconditions(father, sim, time_dict) == True

    utility_father = care_action.calculate_utility(father, sim, time_dict)
    utility_mother = care_action.calculate_utility(mother, sim, time_dict)

    # У матери приоритет (она и био родитель, и в том же домохозяйстве, и рядом физически)
    assert utility_mother > utility_father

def test_db_save_load_household():
    db_path = "test_hh_save.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    db = Database(db_path)
    sim = Simulation()
    hm = sim.household_manager

    hh = hm.create_household("home_x")
    npc = create_npc(sim, "М", 30, home_id="home_x")
    npc.household_id = hh.id

    building = Building("home_x", "home", 4)
    sim.city.add_building(building)

    db.save_world(
        sim_time=sim.time.get_time_dict(),
        npcs=sim.npcs,
        buildings=sim.city.buildings,
        events=[],
        households=list(hm.households.values())
    )

    # Загрузка
    load_res = db.load_world()
    npcs_data = load_res[2]
    hhs_data = load_res[11]

    assert len(hhs_data) == 1
    assert hhs_data[0]['id'] == hh.id
    assert hhs_data[0]['home_id'] == "home_x"

    assert len(npcs_data) == 1
    assert npcs_data[0]['household_id'] == hh.id

    if os.path.exists(db_path):
        os.remove(db_path)

if __name__ == "__main__":
    pytest.main(["-v", __file__])
