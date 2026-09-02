import pytest
from datetime import datetime, timedelta
from living_world.engine.simulation import Simulation
from living_world.population.npc import NPC
from living_world.engine.education.models import EducationalInstitution, EducationProgram

def test_education_dead_npc():
    sim = Simulation()
    current_date = datetime(2000, 1, 1, 0, 0)
    sim.time.current_datetime = current_date
    sim.time.paused = False

    inst = EducationalInstitution("inst_1", "school", "School", 100, "build_1")
    prog_9 = EducationProgram("prog_9", "inst_1", "9 Classes", "school_9", 9)
    sim.education_manager.add_institution(inst)
    sim.education_manager.add_program(prog_9)

    child_dob = current_date - timedelta(days=7*365)
    child = NPC("Child", "Test", child_dob, "М", "None", "home_1", None)
    child.is_alive = False
    sim.add_npc(child)

    sim.update()

    assert getattr(child, 'education_status', None) is None
    assert getattr(child, 'current_education_id', None) is None
