from living_world.engine.ai.action import Action
from living_world.engine.life_cycle_manager import LifeStage

class SocializeAction(Action):
    @property
    def name(self) -> str:
        return "Общается"

    def check_preconditions(self, npc, simulation, time_dict) -> bool:
        if npc.get_life_stage(simulation.time.current_datetime) == LifeStage.BABY:
            return False
        return True

    def calculate_utility(self, npc, simulation, time_dict) -> float:
        utility = 0.0
        hour = time_dict['hour']

        if 10 <= hour < 22:
             if npc.traits.get("sociability", 0) > 0.5:
                 utility += 40
             else:
                 utility += 20 # Give at least some base utility to allow socializing

        return utility

    def execute(self, npc, simulation, time_dict):
        # We don't need to physically do much here, SocialManager handles the interactions
        # The AI just sets the state so SocialManager knows they are available
        pass
