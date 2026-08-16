import pytest
from datetime import datetime, timedelta
from living_world.engine.reproduction.manager import ReproductionManager
from living_world.engine.reproduction.pregnancy import Pregnancy
from living_world.engine.life_cycle_manager import LifeStage

class DummyNPC:
    def __init__(self, id, gender, stage, mother_id=None, father_id=None, family_id=None, desire=0.5):
        self.id = id
        self.gender = gender
        self.mother_id = mother_id
        self.father_id = father_id
        self.family_id = family_id
        self.children_desire = desire
        self.is_alive = True
        self.money = 2000.0
        self.first_name = "Test"
        self.last_name = "Testov"
        self.home_id = "h1"
        self._stage = stage
    def get_life_stage(self, date): return self._stage
    def get_full_name(self): return f"{self.first_name} {self.last_name}"

class DummyRelManager:
    def get_relationship(self, a, b): return {'affinity': 80, 'trust': 80, 'tension': 10}
    def modify_relationship(self, a, b, prop, val): pass

class DummyTime:
    def __init__(self): self.current_datetime = datetime(2000, 1, 1)

class DummySimulation:
    def __init__(self):
        self.npcs = []
        self.families = []
        self.time = DummyTime()
        self.relationship_manager = DummyRelManager()
    def add_npc(self, npc): self.npcs.append(npc)

def test_eligibility():
    sim = DummySimulation()
    mgr = ReproductionManager(sim)
    m = DummyNPC("m1", "Ж", LifeStage.ADULT, family_id="fam1")
    f = DummyNPC("f1", "М", LifeStage.ADULT, family_id="fam1")
    fam = {'id': 'fam1', 'last_reproduction_check': None}

    assert mgr.check_eligibility(m, f, fam) == True

    # Cooldown test
    fam['last_reproduction_check'] = datetime(1999, 12, 20).isoformat()
    assert mgr.check_eligibility(m, f, fam) == False

def test_birth():
    sim = DummySimulation()
    mgr = ReproductionManager(sim)
    m = DummyNPC("m1", "Ж", LifeStage.ADULT, family_id="fam1")
    m.last_name = "Mama"
    f = DummyNPC("f1", "М", LifeStage.ADULT, family_id="fam1")
    f.last_name = "Papa"

    sim.npcs.extend([m, f])
    start = datetime(2000, 1, 1)
    end = start + timedelta(days=280)
    p = Pregnancy(m.id, f.id, start, end, "active")
    mgr.active_pregnancies.append(p)
    sim.time.current_datetime = end + timedelta(days=1)
    mgr.update()
    assert p.status == "completed"
    assert len(sim.npcs) == 3
    baby = sim.npcs[-1]
    assert baby.mother_id == "m1"
    assert baby.father_id == "f1"
    assert baby.last_name == "Papa"

def test_idempotent_birth():
    sim = DummySimulation()
    mgr = ReproductionManager(sim)
    m = DummyNPC("m1", "Ж", LifeStage.ADULT, family_id="fam1")
    f = DummyNPC("f1", "М", LifeStage.ADULT, family_id="fam1")
    sim.npcs.extend([m, f])
    start = datetime(2000, 1, 1)
    end = start + timedelta(days=280)
    p = Pregnancy(m.id, f.id, start, end, "active")
    mgr.active_pregnancies.append(p)
    sim.time.current_datetime = end + timedelta(days=1)
    mgr.update()
    assert p.status == "completed"
    assert len(sim.npcs) == 3
    mgr.update()
    assert len(sim.npcs) == 3

def test_mother_death():
    sim = DummySimulation()
    mgr = ReproductionManager(sim)
    m = DummyNPC("m1", "Ж", LifeStage.ADULT, family_id="fam1")
    f = DummyNPC("f1", "М", LifeStage.ADULT, family_id="fam1")
    sim.npcs.extend([f])
    start = datetime(2000, 1, 1)
    end = start + timedelta(days=280)
    p = Pregnancy(m.id, f.id, start, end, "active")
    mgr.active_pregnancies.append(p)
    sim.time.current_datetime = end + timedelta(days=1)
    mgr.update()
    assert p.status == "completed"
    assert len(sim.npcs) == 1
