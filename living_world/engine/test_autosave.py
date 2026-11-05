import os
import pytest
from living_world.engine.simulation import Simulation
from living_world.population.generation import generate_initial_world
from living_world.engine.autosave_manager import AutosaveManager
from living_world.database.repository import Database
from living_world.gui.tabs import settings_tab

def test_autosave_cycle(tmp_path):
    saves_dir = str(tmp_path / "saves")
    settings_file = str(tmp_path / "settings.json")
    old_file = settings_tab.CONFIG_FILE
    settings_tab.CONFIG_FILE = settings_file

    try:
        settings_tab.save_settings({
            "autosave_enabled": True,
            "autosave_interval_days": 2,
            "autosave_filename": "auto.db"
        })

        sim = Simulation()
        generate_initial_world(sim.city, sim, 10)
        mgr = AutosaveManager(sim, saves_dir=saves_dir)

        # Day 1 - should not save (interval = 2)
        assert mgr.check_and_autosave(1) is False
        assert not os.path.exists(os.path.join(saves_dir, "auto.db"))

        # Day 2 - should trigger autosave
        assert mgr.check_and_autosave(2) is True
        saved_file = os.path.join(saves_dir, "auto.db")
        assert os.path.exists(saved_file)

        # Calling again on day 2 should not duplicate save
        assert mgr.check_and_autosave(2) is False

        # Verify saved world is completely valid and loadable
        db = Database(saved_file)
        load_res = db.load_world()
        assert len(load_res[2]) == 10  # 10 npcs
        assert len(load_res[1]) == len(sim.city.buildings)

    finally:
        settings_tab.CONFIG_FILE = old_file

def test_autosave_disabled(tmp_path):
    saves_dir = str(tmp_path / "saves")
    settings_file = str(tmp_path / "settings.json")
    old_file = settings_tab.CONFIG_FILE
    settings_tab.CONFIG_FILE = settings_file

    try:
        settings_tab.save_settings({
            "autosave_enabled": False,
            "autosave_interval_days": 1,
            "autosave_filename": "auto_disabled.db"
        })

        sim = Simulation()
        generate_initial_world(sim.city, sim, 5)
        mgr = AutosaveManager(sim, saves_dir=saves_dir)

        # Day 1 - should not save because disabled
        assert mgr.check_and_autosave(1) is False
        assert not os.path.exists(os.path.join(saves_dir, "auto_disabled.db"))

    finally:
        settings_tab.CONFIG_FILE = old_file
