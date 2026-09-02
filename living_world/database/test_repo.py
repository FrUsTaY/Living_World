import pytest
from datetime import datetime
from living_world.database.repository import Database
from living_world.engine.reproduction.pregnancy import Pregnancy

def test_save_load_pregnancy(tmp_path):
    repo = Database(str(tmp_path / "test.db"))

    p = Pregnancy(mother_id="m1", father_id="f1", start_date=datetime(2000, 1, 1), expected_birth_date=datetime(2000, 10, 7), status="active")

    repo.save_world(
        sim_time={"year": 2000, "month": 1, "day": 1, "hour": 8, "minute": 0},
        npcs=[],
        buildings=[],
        events=[],
        pregnancies=[p]
    )

    loaded = repo.load_world()
    pregnancies_loaded = loaded[10]

    assert len(pregnancies_loaded) == 1
    loaded_p = pregnancies_loaded[0]
    assert loaded_p['mother_id'] == "m1"
    assert loaded_p['father_id'] == "f1"
    assert loaded_p['status'] == "active"
    assert loaded_p['start_date'] == p.start_date.isoformat()
    assert loaded_p['expected_birth_date'] == p.expected_birth_date.isoformat()

