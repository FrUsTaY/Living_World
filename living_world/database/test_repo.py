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


def test_save_load_relationship_activity_metadata(tmp_path):
    repo = Database(str(tmp_path / "test.db"))
    relationship = {
        "source_npc_id": "npc-a",
        "target_npc_id": "npc-b",
        "familiarity": 10.0,
        "affinity": 20.0,
        "trust": 30.0,
        "respect": 40.0,
        "romantic_interest": 50.0,
        "tension": 5.0,
        "last_interaction_time": 120,
        "last_meaningful_interaction_time": 90,
        "daily_interactions_count": 3,
        "initiations_sent": 2,
        "initiations_received": 1,
    }

    repo.save_world(
        sim_time={"year": 2000, "month": 1, "day": 1, "hour": 8, "minute": 0},
        npcs=[],
        buildings=[],
        events=[],
        relationships=[relationship],
    )

    loaded = repo.load_world()[5]
    assert len(loaded) == 1
    for key in ("last_interaction_time", "last_meaningful_interaction_time", "daily_interactions_count"):
        assert loaded[0][key] == relationship[key]

