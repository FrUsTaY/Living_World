from datetime import datetime, timedelta
import pytest
from living_world.engine.simulation import Simulation
from living_world.engine.genetics.genetics_manager import GeneticsManager
from living_world.engine.genetics.family_tree_builder import FamilyTreeBuilder
from living_world.population.npc import NPC
from living_world.database.repository import Database


def test_mendelian_eye_and_hair_inheritance():
    # Father: homozygous blue eyes (bb), blonde hair (bb)
    father = NPC("Отец", "Блондинов", datetime(1980, 1, 1), "М", "Фермер", "home_1", "work_1")
    father.genetics = {
        "eye_alleles": ("b", "b"),
        "eye_color": "Голубые",
        "hair_alleles": ("b", "b"),
        "hair_color": "Блондин",
        "height_cm": 182,
        "body_type": "Атлетическое",
        "immunity": 0.8,
        "longevity": 0.85
    }
    
    # Mother: homozygous brown eyes (BB), dark hair (DD)
    mother = NPC("Мать", "Брюнетова", datetime(1982, 1, 1), "Ж", "Врач", "home_1", "work_2")
    mother.genetics = {
        "eye_alleles": ("B", "B"),
        "eye_color": "Карие",
        "hair_alleles": ("D", "D"),
        "hair_color": "Брюнет",
        "height_cm": 168,
        "body_type": "Нормальное",
        "immunity": 0.9,
        "longevity": 0.9
    }
    
    # Child genome
    child_genome = GeneticsManager.generate_genome(father=father, mother=mother, gender="М")
    
    # Due to dominance of B over b and D over b:
    # Child MUST inherit one B from mother and one b from father -> phenotype Brown eyes!
    assert child_genome["eye_color"] == "Карие"
    assert "B" in child_genome["eye_alleles"]
    assert "b" in child_genome["eye_alleles"]
    
    # Child MUST inherit D from mother -> phenotype Brunette!
    assert child_genome["hair_color"] == "Брюнет"
    assert "D" in child_genome["hair_alleles"]
    assert "b" in child_genome["hair_alleles"]
    
    # Height between parents
    assert 165 <= child_genome["height_cm"] <= 195


def test_child_birth_inherits_genetics():
    sim = Simulation()
    sim.time.current_datetime = datetime(2025, 5, 1, 12, 0)
    
    mother = NPC("Анна", "Петрова", datetime(1995, 1, 1), "Ж", "Учитель", "home_1", "work_1")
    father = NPC("Сергей", "Петров", datetime(1993, 1, 1), "М", "Механик", "home_1", "work_2")
    mother.is_alive = True
    father.is_alive = True
    sim.npcs = [mother, father]
    
    # Create pregnancy and trigger birth
    from living_world.engine.reproduction.pregnancy import Pregnancy
    preg = Pregnancy(mother.id, father.id, sim.time.current_datetime, sim.time.current_datetime)
    sim.reproduction_manager.process_birth(preg)
    
    # Baby was born
    assert len(sim.npcs) == 3
    baby = sim.npcs[-1]
    assert baby.mother_id == mother.id
    assert baby.father_id == father.id
    assert baby.genetics is not None
    assert baby.genetics["eye_color"] in ["Карие", "Зеленые", "Голубые"]
    assert baby.genetics["hair_color"] in ["Брюнет", "Шатен", "Рыжий", "Блондин"]


def test_family_tree_builder_multi_generation():
    sim = Simulation()
    sim.time.current_datetime = datetime(2025, 6, 1, 12, 0)
    
    # 3 Generations:
    # Gen 1: Grandparents
    grandpa = NPC("Дед", "Родоначальник", datetime(1940, 1, 1), "М", "Пенсионер", "home_1", None)
    grandma = NPC("Бабушка", "Родоначальница", datetime(1942, 1, 1), "Ж", "Пенсионер", "home_1", None)
    
    # Gen 2: Father, Mother, Sibling
    father = NPC("Отец", "Второй", datetime(1965, 1, 1), "М", "Инженер", "home_1", "work_1",
                 father_id=grandpa.id, mother_id=grandma.id)
    mother = NPC("Мать", "Вторая", datetime(1968, 1, 1), "Ж", "Учитель", "home_1", "work_2")
    
    # Gen 3: Subject, Sister, Spouse, Child (Gen 4)
    subject = NPC("Ярослав", "Главный", datetime(1992, 1, 1), "М", "Архитектор", "home_2", "work_3",
                  father_id=father.id, mother_id=mother.id)
    sister = NPC("Ольга", "Сестра", datetime(1995, 1, 1), "Ж", "Врач", "home_2", "work_4",
                 father_id=father.id, mother_id=mother.id)
    spouse = NPC("Елена", "Супруга", datetime(1993, 1, 1), "Ж", "Бухгалтер", "home_2", "work_5")
    subject.dating_partner_id = spouse.id
    spouse.dating_partner_id = subject.id
    
    # Gen 4: Child
    child = NPC("Малыш", "Потомок", datetime(2020, 1, 1), "М", "Ребенок", "home_2", None,
                father_id=subject.id, mother_id=spouse.id)
    
    sim.npcs = [grandpa, grandma, father, mother, subject, sister, spouse, child]
    
    # Build tree for subject
    tree = FamilyTreeBuilder.build_tree(subject.id, sim)
    
    assert tree["subject"]["id"] == subject.id
    assert tree["parents"]["father"]["id"] == father.id
    assert tree["parents"]["mother"]["id"] == mother.id
    assert tree["grandparents"]["paternal_grandfather"]["id"] == grandpa.id
    assert tree["grandparents"]["paternal_grandmother"]["id"] == grandma.id
    assert len(tree["siblings"]) == 1
    assert tree["siblings"][0]["id"] == sister.id
    assert tree["spouse"]["id"] == spouse.id
    assert len(tree["children"]) == 1
    assert tree["children"][0]["id"] == child.id


def test_genetics_persistence_in_db(tmp_path):
    db_file = str(tmp_path / "test_genetics.db")
    repo = Database(db_file)
    
    sim = Simulation()
    sim.time.current_datetime = datetime(2025, 7, 1, 12, 0)
    
    npc = NPC("Генетик", "Наследников", datetime(1990, 1, 1), "М", "Биолог", "home_1", "work_1")
    npc.genetics = {
        "eye_alleles": ("B", "g"),
        "eye_color": "Карие",
        "hair_alleles": ("C", "b"),
        "hair_color": "Шатен",
        "height_cm": 184,
        "body_type": "Атлетическое",
        "immunity": 0.88,
        "longevity": 0.92
    }
    sim.npcs = [npc]
    
    # Save world
    repo.save_world(
        sim_time=sim.time.get_time_dict(),
        npcs=sim.npcs,
        buildings=[],
        events=[]
    )
    
    # Load world
    load_res = repo.load_world()
    npc_dicts = load_res[2]
    
    loaded_npc = next(n for n in npc_dicts if n['id'] == npc.id)
    assert loaded_npc['genetics'] is not None
    
    import json
    gen_data = json.loads(loaded_npc['genetics']) if isinstance(loaded_npc['genetics'], str) else loaded_npc['genetics']
    assert gen_data['eye_color'] == "Карие"
    assert gen_data['hair_color'] == "Шатен"
    assert gen_data['height_cm'] == 184
    assert gen_data['immunity'] == 0.88
