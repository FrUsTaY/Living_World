from typing import List, Dict, Type
import random
from living_world.engine.ai.action import Action
from living_world.engine.ai.basic_actions import (
    SleepAction, EatAction, WorkAction, RelaxAction, PlayAction, 
    SocializeAction, StudyAction, StrollAction, DateAction,
    HygieneAction, HobbyAction, VisitDoctorAction, VisitCultureAction
)
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
            CareForChildAction(),
            StrollAction(),
            DateAction(),
            HygieneAction(),
            HobbyAction(),
            VisitDoctorAction(),
            VisitCultureAction()
        ]

    def choose_and_execute_action(self, npc, time_dict):
        if getattr(npc, 'jail_days', 0) > 0 or npc.state == "В тюрьме":
            npc.state = "В тюрьме"
            return
        # Fast path for continuous actions
        cur_state = npc.state
        if cur_state == "Спит" and npc.energy < 95:
            # Continue sleeping
            npc.energy = min(100.0, npc.energy + 0.3)
            return
        elif cur_state == "Ест" and npc.hunger < 95:
            # Continue eating
            npc.hunger = min(100.0, npc.hunger + 2.0)
            return
        elif cur_state == "Принимает душ" and getattr(npc, 'hygiene', 100.0) < 95:
            npc.hygiene = min(100.0, getattr(npc, 'hygiene', 0.0) + 5.0)
            return

        valid_actions = []
        for action in self.available_actions:
            if action.check_preconditions(npc, self.simulation, time_dict):
                valid_actions.append(action)

        if not valid_actions:
            npc.state = "Отдыхает"
            return

        action_utilities = []
        for action in valid_actions:
            utility = action.calculate_utility(npc, self.simulation, time_dict)
            action_utilities.append((action, utility))

        for i in range(len(action_utilities)):
            action, utility = action_utilities[i]
            if utility < 500:
                utility += random.uniform(0, 8)
            action_utilities[i] = (action, utility)

        best_action, best_utility = max(action_utilities, key=lambda item: item[1])
        best_action.execute(npc, self.simulation, time_dict)
        npc.state = best_action.name