import pytest
from living_world.engine.observer.world_event import WorldEvent, EventImportance, EventType
from living_world.engine.observer.event_journal import EventJournal
from living_world.engine.observer.event_aggregator import EventAggregator
from living_world.engine.simulation import Simulation

def test_world_event_creation_and_serialization():
    event = WorldEvent(
        timestamp="День 1",
        event_type=EventType.BIRTH,
        importance=EventImportance.CRITICAL,
        message="Родился ребенок",
        participants=["npc_1", "npc_2"],
        data={"child_id": "npc_3"}
    )

    assert event.type == EventType.BIRTH
    assert event.importance == EventImportance.CRITICAL

    d = event.to_dict()
    assert d["type"] == "BIRTH"
    assert d["importance"] == "CRITICAL"

    e2 = WorldEvent.from_dict(d)
    assert e2.id == event.id
    assert e2.type == EventType.BIRTH
    assert e2.importance == EventImportance.CRITICAL
    assert e2.participants == ["npc_1", "npc_2"]
    assert e2.data["child_id"] == "npc_3"

def test_event_journal_filtering():
    journal = EventJournal()

    e1 = WorldEvent("D1", EventType.SOCIAL_INTERACTION, EventImportance.LOW, "Hi", ["n1", "n2"])
    e2 = WorldEvent("D1", EventType.MARRIAGE, EventImportance.HIGH, "Married", ["n1", "n3"])
    e3 = WorldEvent("D2", EventType.BIRTH, EventImportance.CRITICAL, "Birth", ["n1", "n3"])

    journal.add_event(e1)
    journal.add_event(e2)
    journal.add_event(e3)

    high_events = journal.get_events_by_importance([EventImportance.HIGH, EventImportance.CRITICAL])
    assert len(high_events) == 2

    n2_events = journal.get_events_for_participant("n2")
    assert len(n2_events) == 1
    assert n2_events[0].id == e1.id

def test_simulation_integration():
    sim = Simulation()
    assert hasattr(sim, "event_journal")
    assert hasattr(sim, "event_aggregator")

    # Прямая публикация через агрегатор
    sim.event_aggregator.publish_event(
        EventType.SOCIAL_INTERACTION,
        EventImportance.MEDIUM,
        "Test message",
        ["npc_test"]
    )

    events = sim.event_journal.get_all_events()
    assert len(events) == 1
    assert events[0].type == EventType.SOCIAL_INTERACTION
    assert events[0].importance == EventImportance.MEDIUM


def test_world_dashboard_data_loading():
    from PySide6.QtWidgets import QApplication, QLabel
    from living_world.gui.tabs.world_tab import WorldTab
    from living_world.population.generation import generate_initial_world

    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    sim = Simulation()
    generate_initial_world(sim.city, sim, 5)

    sim.event_aggregator.publish_event(
        EventType.SOCIAL_INTERACTION,
        EventImportance.HIGH,
        "Test Important Event"
    )

    tab = WorldTab(sim, None)
    tab.update_data()

    # Check stats label contains households word
    assert "Всего жителей:" in tab.lbl_stats.text()
    assert "Свободны:" in tab.lbl_stats.text()

    # Check feed
    assert tab.feed_list.count() == 1
    assert "Test Important Event" in tab.feed_list.item(0).text()

def test_npc_card_history_tab():
    from PySide6.QtWidgets import QApplication, QLabel
    from living_world.gui.dialogs.npc_card import NPCCardDialog
    from living_world.population.generation import generate_initial_world

    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    sim = Simulation()
    generate_initial_world(sim.city, sim, 5)

    npc = sim.npcs[0]

    sim.event_aggregator.publish_event(
        EventType.SOCIAL_INTERACTION,
        EventImportance.CRITICAL,
        "Test Life Event",
        [npc.id]
    )

    from PySide6.QtWidgets import QWidget
    class DummyParent(QWidget):
        pass
    parent = DummyParent()
    parent.sim = sim

    dialog = NPCCardDialog(npc, sim.city, parent)

    # 5 is history tab index
    assert "Test Life Event" in dialog.history_list.item(0).text()

def test_families_tab_redesign():
    from PySide6.QtWidgets import QApplication, QLabel
    from living_world.gui.tabs.families_tab import FamiliesTab
    from living_world.population.generation import generate_initial_world

    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    sim = Simulation()
    generate_initial_world(sim.city, sim, 10)

    # Искусственно создадим семью и домохозяйство
    f = {"id": "fam_1", "is_active": 1}
    sim.families.append(f)

    npc1 = sim.npcs[0]
    npc2 = sim.npcs[1]

    npc1.family_id = "fam_1"
    npc2.family_id = "fam_1"

    hm = sim.household_manager
    hh = hm.create_household("home_1")
    npc1.household_id = hh.id
    npc2.household_id = hh.id

    # Добавим "сожителя"
    npc3 = sim.npcs[2]
    npc3.household_id = hh.id

    tab = FamiliesTab(sim, None)
    tab.update_data()

    # Проверяем, что создалась одна карточка
    assert tab.grid_layout.count() == 1

    widget = tab.grid_layout.itemAt(0).widget()
    # Проверяем наличие секций внутри FamilyWidget (ищем по тексту QLabel'ов)
    labels = widget.findChildren(QLabel)
    texts = [l.text() for l in labels]

    assert any("Биологические / брачные связи" in t for t in texts)
    assert any("Домохозяйство" in t for t in texts)
    assert any("(сожитель)" in t for t in texts) # npc3
