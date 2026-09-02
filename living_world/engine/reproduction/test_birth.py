import pytest
from datetime import datetime, timedelta
from living_world.engine.reproduction.manager import ReproductionManager
from living_world.engine.reproduction.pregnancy import Pregnancy
from living_world.engine.life_cycle_manager import LifeStage

class DummyRelManager:
    def __init__(self):
        self.rels = {}
    def modify_relationship(self, a, b, prop, val):
        key = (a, b)
        if key not in self.rels:
            self.rels[key] = {}
        self.rels[key][prop] = val

class DummyTime:
    def __init__(self):
        self.current_datetime = datetime(2000, 1, 1)

class DummySimulation:
    def __init__(self):
        self.npcs = []
        self.families = []
        self.time = DummyTime()
        self.relationship_manager = DummyRelManager()
    def add_npc(self, npc):
        self.npcs.append(npc)

class DummyNPC:
    def __init__(self, id, gender, stage, last_name, family_id=None):
        self.id = id
        self.gender = gender
        self.mother_id = None
        self.father_id = None
        self.family_id = family_id
        self.first_name = "Test"
        self.last_name = last_name
        self.home_id = "h1"
        self._stage = stage
    def get_full_name(self): return f"{self.first_name} {self.last_name}"
    def get_age(self, d): return 0
    def get_life_stage(self, d): return LifeStage.BABY

def test_surname_inheritance_father_known():
    sim = DummySimulation()
    mgr = ReproductionManager(sim)

    m = DummyNPC("m1", "Ж", LifeStage.ADULT, "MotherName", "fam1")
    f = DummyNPC("f1", "М", LifeStage.ADULT, "FatherName", "fam1")
    sim.npcs.extend([m, f])

    p = Pregnancy(m.id, f.id, datetime(2000, 1, 1), datetime(2000, 10, 7), "active")
    mgr.process_birth(p)

    assert len(sim.npcs) == 3
    baby = sim.npcs[-1]
    assert baby.last_name == "FatherName"

def test_surname_inheritance_father_unknown():
    sim = DummySimulation()
    mgr = ReproductionManager(sim)

    m = DummyNPC("m1", "Ж", LifeStage.ADULT, "MotherName", "fam1")
    sim.npcs.append(m)

    p = Pregnancy(m.id, "unknown_f", datetime(2000, 1, 1), datetime(2000, 10, 7), "active")
    mgr.process_birth(p)

    assert len(sim.npcs) == 2
    baby = sim.npcs[-1]
    assert baby.last_name == "MotherName"

def test_baby_init_properties():
    sim = DummySimulation()
    mgr = ReproductionManager(sim)

    m = DummyNPC("m1", "Ж", LifeStage.ADULT, "MotherName", "fam1")
    f = DummyNPC("f1", "М", LifeStage.ADULT, "FatherName", "fam1")
    sim.npcs.extend([m, f])

    p = Pregnancy(m.id, f.id, datetime(2000, 1, 1), datetime(2000, 10, 7), "active")
    mgr.process_birth(p)

    baby = sim.npcs[-1]
    assert baby.mother_id == "m1"
    assert baby.father_id == "f1"
    assert baby.money == 0.0
    assert getattr(baby, 'profession', None) == "Безработный"
    assert baby.home_id == "h1"

def test_baby_init_lifestage():
    sim = DummySimulation()
    mgr = ReproductionManager(sim)
    m = DummyNPC("m1", "Ж", LifeStage.ADULT, "MotherName", "fam1")
    f = DummyNPC("f1", "М", LifeStage.ADULT, "FatherName", "fam1")
    sim.npcs.extend([m, f])
    p = Pregnancy(m.id, f.id, datetime(2000, 1, 1), datetime(2000, 10, 7), "active")
    mgr.process_birth(p)

    baby = sim.npcs[-1]
    assert baby.get_age(sim.time.current_datetime) == 0
    assert baby.get_life_stage(sim.time.current_datetime) == LifeStage.BABY
