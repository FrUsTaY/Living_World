import pytest
import os
from living_world.database.repository import Database
from living_world.population.npc import NPC
from datetime import datetime

def test_database_migrations_and_save_load():
    db_path = "test_db.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    db = Database(db_path)

    current_date = datetime(2001, 1, 1)
    sim_time = {"year": 2001, "month": 1, "day": 1, "hour": 8, "minute": 0}

    npc = NPC("Test", "Test", current_date, "Ж", "None", "home_1", "work_1")
    npc.current_education_id = "prog_1"
    npc.education_status = "Обучается"

    class MockInstitution:
        def __init__(self):
            self.id = "inst_1"
            self.type = "university"
            self.name = "Uni"
            self.capacity = 100
            self.building_id = "build_1"

    class MockProgram:
        def __init__(self):
            self.id = "prog_1"
            self.institution_id = "inst_1"
            self.name = "Engineering"
            self.type = "bachelor"
            self.duration = 4
            self.requirements = {"education": "high_school"}

    hist = {
        "npc_id": npc.id,
        "institution_id": "inst_1",
        "program_id": "prog_1",
        "start_date": "2000-01-01",
        "end_date": None,
        "status": "Обучается",
        "qualification": None
    }

    db.save_world(sim_time, [npc], [], [], [], [], [], [MockInstitution()], [MockProgram()], [hist])

    loaded = db.load_world()

    assert loaded[7][0]["id"] == "inst_1"
    assert loaded[8][0]["name"] == "Engineering"
    assert loaded[9][0]["npc_id"] == npc.id

    # test npc props
    assert loaded[2][0]["current_education_id"] == "prog_1"
    assert loaded[2][0]["education_status"] == "Обучается"

    if os.path.exists(db_path):
        os.remove(db_path)
