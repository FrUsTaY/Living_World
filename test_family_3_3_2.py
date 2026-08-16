import pytest
from datetime import datetime, timedelta
from living_world.engine.simulation import Simulation
from living_world.engine.life_cycle_manager import LifeCycleManager, LifeStage
from living_world.population.npc import NPC

def create_npc(sim, gender, age_years):
    birth_date = sim.time.current_datetime - timedelta(days=age_years * 365)
    npc = NPC(
        first_name="Test",
        last_name="Testov",
        date_of_birth=birth_date,
        gender=gender,
        profession="Безработный",
        home_id="home_1",
        work_id=None
    )
    sim.add_npc(npc)
    return npc

def test_family_manager_relationships():
    sim = Simulation()
    sim.time.paused = False

    father = create_npc(sim, "М", 30)
    mother = create_npc(sim, "Ж", 28)

    # Ребенок 1 (полные сиблинги)
    child1 = create_npc(sim, "М", 5)
    child1.mother_id = mother.id
    child1.father_id = father.id

    # Ребенок 2
    child2 = create_npc(sim, "Ж", 2)
    child2.mother_id = mother.id
    child2.father_id = father.id

    # Ребенок 3 (неполнородный - другой отец)
    other_father = create_npc(sim, "М", 35)
    child3 = create_npc(sim, "М", 10)
    child3.mother_id = mother.id
    child3.father_id = other_father.id

    fm = sim.family_manager

    # 1. get_parents
    parents = fm.get_parents(child1.id)
    assert len(parents) == 2
    parent_ids = [p.id for p in parents]
    assert mother.id in parent_ids
    assert father.id in parent_ids

    # 2. get_children
    mother_children = fm.get_children(mother.id)
    assert len(mother_children) == 3
    mother_child_ids = [c.id for c in mother_children]
    assert child1.id in mother_child_ids
    assert child2.id in mother_child_ids
    assert child3.id in mother_child_ids

    father_children = fm.get_children(father.id)
    assert len(father_children) == 2
    father_child_ids = [c.id for c in father_children]
    assert child1.id in father_child_ids
    assert child2.id in father_child_ids
    assert child3.id not in father_child_ids

    # 3. get_siblings
    child1_siblings = fm.get_siblings(child1.id)
    assert len(child1_siblings) == 2
    child1_sibling_ids = [s.id for s in child1_siblings]
    assert child2.id in child1_sibling_ids
    assert child3.id in child1_sibling_ids

    # Смерть родителя не ломает связи
    father.is_alive = False
    father.date_of_death = sim.time.current_datetime

    parents_after_death = fm.get_parents(child1.id)
    assert len(parents_after_death) == 2

def test_care_for_child_action_and_dead_npc():
    sim = Simulation()
    sim.time.paused = False

    father = create_npc(sim, "М", 30)
    mother = create_npc(sim, "Ж", 28)

    baby = create_npc(sim, "М", 1)  # 1 год = BABY
    baby.mother_id = mother.id
    baby.father_id = father.id

    # Доводим младенца до голода
    baby.hunger = 10.0
    baby.mood = 10.0

    # Мать должна хотеть позаботиться о нем
    time_dict = sim.time.get_time_dict()

    from living_world.engine.ai.family_actions import CareForChildAction
    care_action = CareForChildAction()

    assert care_action.check_preconditions(mother, sim, time_dict) == True
    utility = care_action.calculate_utility(mother, sim, time_dict)
    assert utility > 100

    # Выполняем уход
    mother_energy_before = mother.energy
    care_action.execute(mother, sim, time_dict)

    assert baby.hunger > 10.0
    assert baby.mood > 10.0
    assert mother.energy < mother_energy_before

    # Смерть родителя - мертвый не заботится и не вызывает AI
    mother.is_alive = False
    mother.hunger = 50.0

    # Прогоняем цикл
    sim.update()

    # Голод матери не должен измениться
    assert mother.hunger == 50.0

    # У отца должен быть доступ к уходу
    assert care_action.check_preconditions(father, sim, time_dict) == True

def test_two_parents_care_guarantee():
    sim = Simulation()
    sim.time.paused = False

    father = create_npc(sim, "М", 30)
    mother = create_npc(sim, "Ж", 28)

    # Ребенок голоден и требует ухода
    baby = create_npc(sim, "М", 1)
    baby.mother_id = mother.id
    baby.father_id = father.id
    baby.hunger = 0.0
    baby.mood = 0.0

    # Родители сыты и полны сил
    father.hunger = 100.0
    father.energy = 100.0
    mother.hunger = 100.0
    mother.energy = 100.0

    # Оба в той же локации что и ребенок
    father.current_location = baby.home_id
    mother.current_location = baby.home_id
    baby.current_location = baby.home_id

    time_dict = sim.time.get_time_dict()

    from living_world.engine.ai.family_actions import CareForChildAction
    care_action = CareForChildAction()

    assert care_action.check_preconditions(mother, sim, time_dict) == True
    assert care_action.check_preconditions(father, sim, time_dict) == True

    # Вычисляем utility для обоих
    mother_utility = care_action.calculate_utility(mother, sim, time_dict)
    father_utility = care_action.calculate_utility(father, sim, time_dict)

    # Даже со штрафом за второго родителя (utility *= 0.6), базовая мотивация
    # для критического голода (hunger_deficit=100 -> +250) и настроения (+80) = 330.
    # 330 * 0.6 = 198. Это должно быть значительно больше 0,
    # чтобы родитель мог выбрать уход (например RelaxAction при сытости дает около 0).
    assert mother_utility > 150.0
    assert father_utility > 150.0

if __name__ == "__main__":
    pytest.main(["-v", __file__])
