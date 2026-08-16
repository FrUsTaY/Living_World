import random
from datetime import timedelta, datetime
from living_world.engine.reproduction.pregnancy import Pregnancy
from living_world.engine.life_cycle_manager import LifeCycleManager, LifeStage
from living_world.engine.event_bus import bus

class ReproductionManager:
    PREGNANCY_DURATION_DAYS = 280
    REPRODUCTION_DECISION_COOLDOWN_DAYS = 30

    def __init__(self, simulation):
        self.simulation = simulation
        self.active_pregnancies = []

    def get_children_count(self, mother_id, father_id):
        children_count = 0
        for npc in self.simulation.npcs:
            if npc.mother_id == mother_id or npc.father_id == father_id:
                children_count += 1
        return children_count

    def check_eligibility(self, npc_a, npc_b, family):
        current_date = self.simulation.time.current_datetime

        # Check cooldown
        if family.get('last_reproduction_check'):
            last_check = None
            try:
                 if type(family['last_reproduction_check']) is str:
                      last_check = datetime.fromisoformat(family['last_reproduction_check'])
                 if last_check and (current_date - last_check).days < self.REPRODUCTION_DECISION_COOLDOWN_DAYS:
                      return False
            except Exception:
                 pass

        if npc_a.gender == npc_b.gender:
            return False

        mother = npc_a if npc_a.gender == 'Ж' else npc_b
        father = npc_b if npc_b.gender == 'М' else npc_a

        for p in self.active_pregnancies:
            if p.mother_id == mother.id and p.status == 'active':
                return False

        stage_m = mother.get_life_stage(current_date)
        stage_f = father.get_life_stage(current_date)

        valid_stages = [LifeStage.YOUNG_ADULT, LifeStage.ADULT]
        if stage_m not in valid_stages or stage_f not in valid_stages:
            return False

        return True

    def make_decision(self, npc_a, npc_b):
        mother = npc_a if npc_a.gender == 'Ж' else npc_b
        father = npc_b if npc_b.gender == 'М' else npc_a

        desire = (getattr(mother, 'children_desire', 0.5) + getattr(father, 'children_desire', 0.5)) / 2.0

        children_count = self.get_children_count(mother.id, father.id)
        children_modifier = max(0.01, 1.0 - (children_count * 0.3))

        rel_m_f = self.simulation.relationship_manager.get_relationship(mother.id, father.id)
        rel_f_m = self.simulation.relationship_manager.get_relationship(father.id, mother.id)

        affinity = (rel_m_f['affinity'] + rel_f_m['affinity']) / 2.0
        trust = (rel_m_f['trust'] + rel_f_m['trust']) / 2.0
        tension = (rel_m_f['tension'] + rel_f_m['tension']) / 2.0

        if affinity < 40 or trust < 40 or tension > 30:
            return False

        money_modifier = 1.0
        if mother.money + father.money < 1000:
             money_modifier = 0.5

        probability = desire * children_modifier * money_modifier * (affinity / 100.0)

        return random.random() < probability

    def conception(self, npc_a, npc_b):
        mother = npc_a if npc_a.gender == 'Ж' else npc_b
        father = npc_b if npc_b.gender == 'М' else npc_a

        start_date = self.simulation.time.current_datetime
        expected_birth_date = start_date + timedelta(days=self.PREGNANCY_DURATION_DAYS)

        p = Pregnancy(mother.id, father.id, start_date, expected_birth_date, "active")
        self.active_pregnancies.append(p)
        bus.publish("log_event", f"{mother.get_full_name()} узнала, что ждёт ребёнка!")
        return p

    def update(self):
        current_date = self.simulation.time.current_datetime

        for p in list(self.active_pregnancies):
            if p.status == 'active' and current_date >= p.expected_birth_date:
                self.process_birth(p)

        processed_families = set()
        for npc in self.simulation.npcs:
             if not npc.is_alive or not npc.family_id: continue
             if npc.family_id in processed_families: continue

             family_members = [n for n in self.simulation.npcs if n.family_id == npc.family_id and n.is_alive]
             if len(family_members) == 2:
                  npc_a, npc_b = family_members[0], family_members[1]

                  fam_record = next((f for f in self.simulation.families if f['id'] == npc.family_id), None)
                  if not fam_record: continue

                  if self.check_eligibility(npc_a, npc_b, fam_record):
                      fam_record['last_reproduction_check'] = current_date.isoformat()
                      if self.make_decision(npc_a, npc_b):
                           self.conception(npc_a, npc_b)

             processed_families.add(npc.family_id)

    def process_birth(self, pregnancy):
        pregnancy.status = 'completed'

        mother = next((n for n in self.simulation.npcs if n.id == pregnancy.mother_id), None)
        father = next((n for n in self.simulation.npcs if n.id == pregnancy.father_id), None)

        if not mother:
            return

        current_date = self.simulation.time.current_datetime

        from living_world.population.generation import MALE_FIRST_NAMES, FEMALE_FIRST_NAMES
        from living_world.population.npc import NPC

        gender = random.choice(["М", "Ж"])
        first_name = random.choice(MALE_FIRST_NAMES) if gender == "М" else random.choice(FEMALE_FIRST_NAMES)

        last_name = mother.last_name
        if father:
             last_name = father.last_name

        home_id = mother.home_id

        baby = NPC(
             first_name=first_name,
             last_name=last_name,
             date_of_birth=current_date,
             gender=gender,
             profession="Безработный",
             home_id=home_id,
             work_id=None,
             mother_id=mother.id,
             father_id=father.id if father else None,
             family_id=mother.family_id
        )
        baby.household_id = getattr(mother, 'household_id', None)
        baby.money = 0.0

        self.simulation.add_npc(baby)

        rel_mgr = self.simulation.relationship_manager
        parents = [mother]
        if father: parents.append(father)

        for parent in parents:
             rel_mgr.modify_relationship(parent.id, baby.id, 'affinity', 90)
             rel_mgr.modify_relationship(parent.id, baby.id, 'trust', 90)
             rel_mgr.modify_relationship(parent.id, baby.id, 'familiarity', 100)
             rel_mgr.modify_relationship(parent.id, baby.id, 'respect', 50)

             rel_mgr.modify_relationship(baby.id, parent.id, 'affinity', 90)
             rel_mgr.modify_relationship(baby.id, parent.id, 'trust', 90)
             rel_mgr.modify_relationship(baby.id, parent.id, 'familiarity', 100)
             rel_mgr.modify_relationship(baby.id, parent.id, 'respect', 50)

        bus.publish("log_event", f"У {mother.get_full_name()} родился ребёнок — {baby.get_full_name()}!")

    def load_pregnancies(self, pregnancies_data):
        self.active_pregnancies = []
        for p_data in pregnancies_data:
             if type(p_data) is dict:
                  self.active_pregnancies.append(Pregnancy.from_dict(p_data))
             else:
                  self.active_pregnancies.append(p_data)
