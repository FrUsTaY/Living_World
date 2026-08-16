from living_world.engine.social.household import Household
from living_world.engine.life_cycle_manager import LifeStage

class HouseholdManager:
    def __init__(self, simulation):
        self.simulation = simulation
        self.households = {}

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
