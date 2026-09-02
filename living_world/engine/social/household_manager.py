from living_world.engine.social.household import Household
from living_world.engine.life_cycle_manager import LifeStage
from living_world.engine.event_bus import bus

class HouseholdManager:
    STRESS_DEATH_IMPACT = 50.0
    STRESS_CONFLICT_IMPACT = 2.0
    STRESS_DAILY_DECAY = 5.0

    def __init__(self, simulation):
        self.simulation = simulation
        self.households = {}

        bus.subscribe("npc_died", self._on_npc_died)
        bus.subscribe("family_conflict", self._on_family_conflict)

    def _on_npc_died(self, data):
        npc = data.get("npc")
        if npc and getattr(npc, 'household_id', None):
            self.modify_stress(npc.household_id, self.STRESS_DEATH_IMPACT)

    def _on_family_conflict(self, data):
        household_id = data.get("household_id")
        if household_id:
            self.modify_stress(household_id, self.STRESS_CONFLICT_IMPACT)

    def modify_stress(self, household_id: str, delta: float):
        household = self.get_household(household_id)
        if household:
            household.stress = max(0.0, min(100.0, household.stress + delta))

    def add_household(self, household: Household):
        self.households[household.id] = household

    def create_household(self, home_id: str) -> Household:
        time_str = self.simulation.time.current_datetime.isoformat()
        household = Household(home_id=home_id, creation_time=time_str)
        self.add_household(household)
        return household

    def get_household(self, household_id: str) -> Household:
        return self.households.get(household_id)

    def get_household_members(self, household_id: str):
        return [npc for npc in self.simulation.npcs if getattr(npc, 'household_id', None) == household_id]

    def get_adults(self, household_id: str):
        members = self.get_household_members(household_id)
        current_date = self.simulation.time.current_datetime
        adults = []
        for npc in members:
            if not npc.is_alive:
                continue
            stage = npc.get_life_stage(current_date)
            if stage in [LifeStage.YOUNG_ADULT, LifeStage.ADULT, LifeStage.ELDER]:
                adults.append(npc)
        return adults

    def get_children(self, household_id: str):
        members = self.get_household_members(household_id)
        current_date = self.simulation.time.current_datetime
        children = []
        for npc in members:
            if not npc.is_alive:
                continue
            stage = npc.get_life_stage(current_date)
            if stage in [LifeStage.BABY, LifeStage.CHILD, LifeStage.SCHOOL]:
                children.append(npc)
        return children

    def get_total_wealth(self, household_id: str) -> float:
        members = self.get_household_members(household_id)
        total_wealth = 0.0
        for npc in members:
            if npc.is_alive:
                total_wealth += npc.money
        return total_wealth
