import pytest
from living_world.engine.simulation import Simulation
from living_world.population.generation import generate_initial_world
from living_world.engine.observer.world_event import EventType, EventImportance

@pytest.fixture
def sim():
    s = Simulation()
    generate_initial_world(s.city, s, 5)
    return s

def test_observer_birth(sim):
    mother = sim.npcs[0]
    father = sim.npcs[1]
    # Насильно создадим ребенка
    preg = sim.reproduction_manager.conception(mother, father)

    events = sim.event_journal.get_all_events()
    preg_events = [e for e in events if e.type == EventType.PREGNANCY]
    assert len(preg_events) == 1
    assert preg_events[0].importance == EventImportance.MEDIUM
    assert mother.id in preg_events[0].participants

    # Process birth
    sim.reproduction_manager.process_birth(preg)
    events = sim.event_journal.get_all_events()
    birth_events = [e for e in events if e.type == EventType.BIRTH]
    assert len(birth_events) == 1
    assert birth_events[0].importance == EventImportance.CRITICAL
    assert mother.id in birth_events[0].participants

def test_observer_death(sim):
    npc = sim.npcs[0]
    npc.is_alive = False

    from living_world.engine.life_cycle_manager import LifeCycleManager
    sim.event_aggregator.publish_event(
        event_type=EventType.DEATH,
        importance=EventImportance.CRITICAL,
        message="Death test",
        participants=[npc.id]
    )

    events = sim.event_journal.get_all_events()
    death_events = [e for e in events if e.type == EventType.DEATH]
    assert len(death_events) == 1
    assert death_events[0].importance == EventImportance.CRITICAL

def test_observer_family(sim):
    npc1, npc2 = sim.npcs[0], sim.npcs[1]

    sim.family_manager.create_family(npc1, npc2, sim.time.get_time_dict())
    events = sim.event_journal.get_all_events()
    fam_events = [e for e in events if e.type == EventType.FAMILY_CREATED]
    assert len(fam_events) == 1
    assert fam_events[0].importance == EventImportance.HIGH

    sim.family_manager.divorce_family(npc1, npc2, sim.time.get_time_dict())
    events = sim.event_journal.get_all_events()
    div_events = [e for e in events if e.type == EventType.DIVORCE]
    assert len(div_events) == 1
    assert div_events[0].importance == EventImportance.HIGH

def test_observer_education(sim):
    npc = sim.npcs[0]

    from living_world.engine.education.models import EducationalInstitution, EducationProgram
    inst = EducationalInstitution("inst_1", "school", "School", 100, "bld_1")
    prog = EducationProgram("prog_1", "inst_1", "Prog", "school_9", 9, {})
    sim.education_manager.add_institution(inst)
    sim.education_manager.add_program(prog)

    sim.education_manager._try_enroll(npc, "school_9", sim.time.current_datetime)
    events = sim.event_journal.get_all_events()
    enroll_events = [e for e in events if e.type == EventType.EDUCATION_ENROLL]
    assert len(enroll_events) == 1
    assert enroll_events[0].importance == EventImportance.MEDIUM

def test_observer_social(sim):
    npc1, npc2 = sim.npcs[0], sim.npcs[1]
    # Знакомство
    sim.social_manager._handle_greeting(npc1, npc2, sim.time.get_time_dict())
    events = sim.event_journal.get_all_events()
    soc_events = [e for e in events if e.type == EventType.SOCIAL_INTERACTION]
    assert len(soc_events) == 1
    assert soc_events[0].importance == EventImportance.MEDIUM

    # Искра (т.к. chance_b/chance_a < 1.0 из-за random, придется зафорсить)
    import random
    random.seed(42) # Чтобы random.random() < 0.25 (или 0.05) сработало. Либо просто повторим
    for _ in range(100):
        sim.social_manager._check_spark(npc1, npc2, 10.0, 100, 100, True)

    events = sim.event_journal.get_all_events()
    rom_events = [e for e in events if e.type == EventType.ROMANCE_START]
    assert len(rom_events) >= 1
    assert rom_events[0].importance == EventImportance.HIGH

def test_observer_no_spam_low_events(sim):
    npc = sim.npcs[0]

    # Сгенерируем несколько LOW событий изменения стейта
    for _ in range(5):
        npc.state = "Спит"
        sim.event_aggregator.publish_event(
            event_type=EventType.STATE_CHANGE,
            importance=EventImportance.LOW,
            message=f"{npc.get_full_name()} спит",
            participants=[npc.id]
        )

    events = sim.event_journal.get_all_events()
    assert len(events) == 5

    # Проверим фильтр "Feed"
    feed_events = sim.event_journal.get_events_by_importance([EventImportance.MEDIUM, EventImportance.HIGH, EventImportance.CRITICAL])
    assert len(feed_events) == 0
