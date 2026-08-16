from typing import List, Dict, Type
import random
from living_world.engine.ai.action import Action
from living_world.engine.ai.basic_actions import SleepAction, EatAction, WorkAction, RelaxAction, PlayAction, SocializeAction, StudyAction
from living_world.engine.ai.family_actions import CareForChildAction

class AIController:
    def __init__(self, simulation):
        self.simulation = simulation
        self.available_actions: List[Action] = [
            SleepAction(),
            EatAction(),
            WorkAction(),
            RelaxAction(),
            PlayAction(),
            SocializeAction(),
            StudyAction(),
            CareForChildAction()
        ]

    def choose_and_execute_action(self, npc, time_dict):
        valid_actions = []
        for action in self.available_actions:
            if action.check_preconditions(npc, self.simulation, time_dict):
                valid_actions.append(action)

        if not valid_actions:
            # Fallback
            npc.state = "Отдыхает"
            return

        action_utilities = []
        for action in valid_actions:
            utility = action.calculate_utility(npc, self.simulation, time_dict)
            action_utilities.append((action, utility))

        # Add a small random factor to break ties and add variety
        for i in range(len(action_utilities)):
            action, utility = action_utilities[i]
            if utility < 1000: # Don't add noise to hysteresis lock
                utility += random.uniform(0, 10)
            action_utilities[i] = (action, utility)

        # Select action with highest utility
        best_action, best_utility = max(action_utilities, key=lambda item: item[1])

        # Execute the chosen action
        best_action.execute(npc, self.simulation, time_dict)
        npc.state = best_action.name
