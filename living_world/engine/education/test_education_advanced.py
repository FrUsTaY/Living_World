import pytest
from datetime import datetime, timedelta
from living_world.engine.simulation import Simulation
from living_world.population.npc import NPC
from living_world.engine.education.models import EducationalInstitution, EducationProgram

def test_no_magic_enrollment():
    sim = Simulation()
    current_date = datetime(2000, 1, 1, 23, 59)
    sim.time.current_datetime = current_date
    sim.time.paused = False

    inst = EducationalInstitution("inst_1", "university", "Uni", 0, "build_1")
    prog = EducationProgram("prog_1", "inst_1", "Bachelor", "bachelor", 4, {"education": "Среднее общее образование"})
    sim.education_manager.add_institution(inst)
    sim.education_manager.add_program(prog)

    adult_dob = current_date - timedelta(days=20*365)
    adult = NPC("Adult", "Test", adult_dob, "Ж", "Продавец", "home_1", "work_1")
    # Simulate high school graduation
    sim.education_manager.history.append(
        type('obj', (object,), {'npc_id': adult.id, 'status': 'Окончил', 'qualification': 'Среднее общее образование'})()
    )
    sim.add_npc(adult)

    # Force decision logic to trigger
    sim.update()

    assert adult.current_education_id is None
    assert adult.education_status is None
    # Action system will fallback to relax/work/sleep since study is not available

def test_trajectory_and_forms():
    sim = Simulation()
    current_date = datetime(2000, 1, 1, 10, 0)
    sim.time.current_datetime = current_date

    inst = EducationalInstitution("inst_1", "university", "Uni", 100, "build_uni")
    # Part time (заочно) doesn't exist natively yet in basic_actions, but we can test the structure
    prog_full = EducationProgram("prog_full", "inst_1", "Bachelor Full", "bachelor", 4)
    prog_part = EducationProgram("prog_part", "inst_1", "Bachelor Part", "bachelor_part", 4)
    sim.education_manager.add_institution(inst)
    sim.education_manager.add_program(prog_full)
    sim.education_manager.add_program(prog_part)

    adult_dob = current_date - timedelta(days=20*365)
    adult1 = NPC("Adult1", "Test", adult_dob, "Ж", "Продавец", "home_1", "work_1")
    adult2 = NPC("Adult2", "Test", adult_dob, "М", "Продавец", "home_1", "work_1")
    sim.add_npc(adult1)
    sim.add_npc(adult2)

    sim.education_manager._try_enroll(adult1, "bachelor", current_date)
    # adult1 is full time
    sim.ai_controller.choose_and_execute_action(adult1, sim.time.get_time_dict())

    assert adult1.state == "Учится"
    assert adult1.current_location == "build_uni"

    adult2.current_education_id = "prog_part"
    adult2.education_status = "Обучается"
    sim.ai_controller.choose_and_execute_action(adult2, sim.time.get_time_dict())

    # Adult 2 should not be blocked from working at 10 AM if basic_actions doesn't see "bachelor" exactly
    assert adult2.state == "Работает"
    assert adult2.current_location == "work_1"

def test_utility_ai_backward_compatibility():
    sim = Simulation()
    current_date = datetime(2000, 1, 1, 3, 0) # 3 AM
    sim.time.current_datetime = current_date

    adult_dob = current_date - timedelta(days=30*365)
    adult = NPC("Adult", "Test", adult_dob, "Ж", "Врач", "home_1", "work_1")
    sim.add_npc(adult)

    adult.energy = 5
    sim.ai_controller.choose_and_execute_action(adult, sim.time.get_time_dict())

    assert adult.state == "Спит"
    assert adult.energy > 5
