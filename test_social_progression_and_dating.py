import pytest
from datetime import datetime, timedelta
from living_world.engine.simulation import Simulation
from living_world.population.npc import NPC

def create_npc(sim, gender, age_years, home_id="home_1"):
    birth_date = sim.time.current_datetime - timedelta(days=age_years * 365)
    npc = NPC(
        first_name="Алексей" if gender == "М" else "Елена",
        last_name="Смирнов" if gender == "М" else "Смирнова",
        date_of_birth=birth_date,
        gender=gender,
        profession="Инженер",
        home_id=home_id,
        work_id=None
    )
    npc.traits['friendliness'] = 0.5
    npc.traits['sociability'] = 0.5
    npc.traits['boldness'] = 0.5
    npc.traits['conflict'] = -0.5
    sim.add_npc(npc)
    return npc

def test_familiarity_and_deep_talk_progression():
    sim = Simulation()
    sim.time.paused = False
    npc_a = create_npc(sim, "М", 25, "home_1")
    npc_b = create_npc(sim, "Ж", 24, "home_2")

    # 1. Greeting
    time_dict = sim.time.get_time_dict()
    sim.social_manager._handle_greeting(npc_a, npc_b, time_dict)

    rel_ab = sim.relationship_manager.get_relationship(npc_a.id, npc_b.id)
    assert rel_ab['familiarity'] >= 10.0

    # 2. Sequential chats to raise familiarity
    for _ in range(8):
        sim.time.tick(minutes=24 * 60)
        td = sim.time.get_time_dict()
        sim.social_manager._resolve_action("chat", npc_a, npc_b, td)

    rel_ab = sim.relationship_manager.get_relationship(npc_a.id, npc_b.id)
    assert rel_ab['familiarity'] >= 18.0
    assert rel_ab['affinity'] > 0.0

    # 3. Deep talk eligibility and execution
    action = sim.social_manager._select_action(npc_a, npc_b)
    assert action in ['chat', 'deep_talk', 'flirt']

    trust_before = rel_ab['trust']
    sim.social_manager._resolve_action("deep_talk", npc_a, npc_b, time_dict)
    rel_ab_after = sim.relationship_manager.get_relationship(npc_a.id, npc_b.id)

    assert rel_ab_after['trust'] > trust_before
    assert rel_ab_after['familiarity'] > rel_ab['familiarity']

def test_dating_transition_and_monogamy():
    sim = Simulation()
    sim.time.paused = False
    npc_a = create_npc(sim, "М", 26, "home_1")
    npc_b = create_npc(sim, "Ж", 25, "home_2")
    npc_c = create_npc(sim, "Ж", 25, "home_3")

    time_dict = sim.time.get_time_dict()
    sim.social_manager._handle_greeting(npc_a, npc_b, time_dict)

    # Set mutual romantic interest high
    sim.relationship_manager.modify_relationship(npc_a.id, npc_b.id, 'romantic_interest', 35.0)
    sim.relationship_manager.modify_relationship(npc_b.id, npc_a.id, 'romantic_interest', 35.0)
    sim.relationship_manager.modify_relationship(npc_a.id, npc_b.id, 'affinity', 30.0)
    sim.relationship_manager.modify_relationship(npc_b.id, npc_a.id, 'affinity', 30.0)

    # Resolve successful flirt to trigger dating transition
    sim.social_manager._resolve_action("flirt", npc_a, npc_b, time_dict)

    assert npc_a.dating_partner_id == npc_b.id
    assert npc_b.dating_partner_id == npc_a.id

    # Verify monogamy: third party C flirts with A
    sim.social_manager._handle_greeting(npc_c, npc_a, time_dict)
    sim.relationship_manager.modify_relationship(npc_c.id, npc_a.id, 'romantic_interest', 20.0)

    sim.social_manager._resolve_action("flirt", npc_c, npc_a, time_dict)

    # A rejects C, remains dating B
    assert npc_a.dating_partner_id == npc_b.id
    rel_ca = sim.relationship_manager.get_relationship(npc_c.id, npc_a.id)
    assert rel_ca['romantic_interest'] < 20.0

def test_marriage_and_household_unification():
    sim = Simulation()
    hm = sim.household_manager
    sim.time.paused = False

    hh1 = hm.create_household("home_1")
    hh2 = hm.create_household("home_2")

    npc_a = create_npc(sim, "М", 28, "home_1")
    npc_b = create_npc(sim, "Ж", 27, "home_2")
    npc_a.household_id = hh1.id
    npc_b.household_id = hh2.id

    # Child of npc_b
    child = create_npc(sim, "Ж", 3, "home_2")
    child.mother_id = npc_b.id
    child.household_id = hh2.id

    time_dict = sim.time.get_time_dict()

    # Marriage
    sim.family_manager.create_family(npc_a, npc_b, time_dict)

    # Check spouses are united in one household and one home
    assert npc_a.family_id is not None
    assert npc_a.family_id == npc_b.family_id
    assert npc_a.home_id == npc_b.home_id
    assert npc_a.household_id == npc_b.household_id

    # Check child moved with mother
    assert child.home_id == npc_b.home_id
    assert child.household_id == npc_b.household_id

    # Verify total wealth combines
    npc_a.money = 5000.0
    npc_b.money = 3000.0
    assert hm.get_total_wealth(npc_a.household_id) >= 8000.0

def test_conflict_damping_and_no_cascades():
    sim = Simulation()
    hm = sim.household_manager
    hh = hm.create_household("home_1")

    npc_a = create_npc(sim, "М", 30, "home_1")
    npc_b = create_npc(sim, "М", 31, "home_1")
    npc_a.household_id = hh.id
    npc_b.household_id = hh.id

    time_dict = sim.time.get_time_dict()
    sim.relationship_manager.modify_relationship(npc_a.id, npc_b.id, 'tension', 85.0)

    # Argue with tension >= 80 discharges tension
    sim.social_manager._resolve_action("argue", npc_a, npc_b, time_dict)
    rel_ab = sim.relationship_manager.get_relationship(npc_a.id, npc_b.id)

    # Tension should have discharged (-15)
    assert rel_ab['tension'] <= 75.0

if __name__ == '__main__':
    test_familiarity_and_deep_talk_progression()
    test_dating_transition_and_monogamy()
    test_marriage_and_household_unification()
    test_conflict_damping_and_no_cascades()
    print("All new tests passed successfully!")
