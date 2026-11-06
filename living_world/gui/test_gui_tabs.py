import os
import pytest

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication
from living_world.engine.simulation import Simulation
from living_world.population.generation import generate_initial_world
from living_world.gui.main_window import MainWindow
from living_world.gui.tabs.city_tab import CityTab
from living_world.gui.tabs.stats_tab import StatsTab
from living_world.gui.tabs.history_tab import HistoryTab
from living_world.gui.tabs.events_tab import EventsTab
from living_world.gui.tabs.settings_tab import SettingsTab, load_settings, save_settings

@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app

def test_main_window_all_eight_tabs(qapp):
    win = MainWindow()
    assert win.tabs.count() == 9

    expected_titles = [
        "Мир",
        "Жители",
        "Семьи",
        "Город",
        "Карта города",
        "Статистика",
        "История",
        "События",
        "Настройки"
    ]

    for i, title in enumerate(expected_titles):
        assert win.tabs.tabText(i) == title

def test_city_tab_updates(qapp):
    sim = Simulation()
    generate_initial_world(sim.city, sim, 20)
    tab = CityTab(sim, None)
    tab.update_data()

    assert tab.table.rowCount() == len(sim.city.buildings)
    assert "Всего зданий" in tab.lbl_summary.text()

def test_stats_tab_updates(qapp):
    sim = Simulation()
    generate_initial_world(sim.city, sim, 20)
    tab = StatsTab(sim, None)
    tab.update_data()

    assert "Живых жителей:" in tab.lbl_demo.text() and "20" in tab.lbl_demo.text()
    assert "Официальных семей" in tab.lbl_family.text()
    assert "Общий капитал жителей" in tab.lbl_econ.text()
    assert "Жилых домов:" in tab.lbl_infra.text() and "10" in tab.lbl_infra.text()

def test_history_and_events_tabs(qapp):
    sim = Simulation()
    generate_initial_world(sim.city, sim, 20)

    from living_world.engine.observer.world_event import EventType, EventImportance
    sim.event_aggregator.publish_event(
        event_type=EventType.ECONOMIC,
        importance=EventImportance.CRITICAL,
        message="Открыто новое городское предприятие!",
        participants=[]
    )

    h_tab = HistoryTab(sim, None)
    h_tab.update_data()
    assert h_tab.table.rowCount() >= 1

    ev_tab = EventsTab(sim, None)
    ev_tab.update_data()
    assert ev_tab.list_widget.count() >= 1

def test_settings_tab_save_load(qapp, tmp_path):
    settings_file = str(tmp_path / "settings.json")
    from living_world.gui.tabs import settings_tab
    old_file = settings_tab.CONFIG_FILE
    settings_tab.CONFIG_FILE = settings_file
    try:
        data = {
            "autosave_enabled": True,
            "autosave_interval_days": 10,
            "autosave_filename": "my_world_save.db",
            "llm_enabled": True,
            "llm_url": "http://127.0.0.1:11434",
            "llm_model": "llama3.2:3b"
        }
        save_settings(data)
        loaded = load_settings()
        assert loaded["autosave_interval_days"] == 10
        assert loaded["llm_model"] == "llama3.2:3b"
        assert loaded["llm_enabled"] is True
    finally:
        settings_tab.CONFIG_FILE = old_file
