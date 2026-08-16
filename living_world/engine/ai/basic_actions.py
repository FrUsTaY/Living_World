from living_world.engine.ai.action import Action
from living_world.engine.life_cycle_manager import LifeStage

class SleepAction(Action):
    @property
    def name(self) -> str:
        return "Спит"

    def check_preconditions(self, npc, simulation, time_dict) -> bool:
        # Младенцы могут спать сами (это естественный процесс, не требующий явного действия родителя,
        # хотя родитель может укладывать спать в будущем. Пока оставим True)
        return True

    def calculate_utility(self, npc, simulation, time_dict) -> float:
        hour = time_dict['hour']
        utility = 0.0

        # Гистерезис
        if getattr(npc, '_last_state', None) == self.name and npc.energy < 95:
            return 1000.0

        if hour >= 22 or hour < 7:
            utility += 100

            life_stage = npc.get_life_stage(simulation.time.current_datetime)
            if life_stage in [LifeStage.BABY, LifeStage.CHILD]:
                utility += 50

            if npc.energy < 30:
                utility += 50
        elif npc.energy < 20:
             utility += 50

        return utility

    def execute(self, npc, simulation, time_dict):
        npc.energy += 0.3
        if npc.current_location != npc.home_id:
             npc.current_location = npc.home_id

class EatAction(Action):
    @property
    def name(self) -> str:
        return "Ест"

    def check_preconditions(self, npc, simulation, time_dict) -> bool:
        from living_world.engine.life_cycle_manager import LifeStage
        if npc.get_life_stage(simulation.time.current_datetime) == LifeStage.BABY:
            return False
        return True

    def calculate_utility(self, npc, simulation, time_dict) -> float:
        utility = 0.0

        if getattr(npc, '_last_state', None) == self.name and npc.hunger < 95:
            return 1000.0

        if npc.hunger < 30:
            utility += 150
        elif npc.hunger < 60:
            utility += 50

        return utility

    def execute(self, npc, simulation, time_dict):
        npc.hunger += 2.0
        if npc.current_location != npc.home_id:
             npc.current_location = npc.home_id

class WorkAction(Action):
    @property
    def name(self) -> str:
        return "Работает"

    def check_preconditions(self, npc, simulation, time_dict) -> bool:
        from living_world.engine.life_cycle_manager import LifeStage
        if npc.get_life_stage(simulation.time.current_datetime) == LifeStage.BABY:
            return False
        return npc.work_id is not None

    def calculate_utility(self, npc, simulation, time_dict) -> float:
        hour = time_dict['hour']
        utility = 0.0

        prog_id = getattr(npc, 'current_education_id', None)
        if prog_id:
            prog = simulation.education_manager.programs.get(prog_id)
            if prog and prog.type in ["school_9", "school_11", "bachelor", "college"]:
                if 8 <= hour < 15:
                    return 0.0 # Очная учеба блокирует работу днем

        if 8 <= hour < 17:
            life_stage = npc.get_life_stage(simulation.time.current_datetime)
            if life_stage in [LifeStage.YOUNG_ADULT, LifeStage.ADULT]:
                utility += 80
            elif life_stage == LifeStage.ELDER:
                utility += 30

        return utility

    def execute(self, npc, simulation, time_dict):
        if npc.current_location != npc.work_id:
             npc.current_location = npc.work_id
        npc.energy -= 0.1
        npc.money += 1.0

class RelaxAction(Action):
    @property
    def name(self) -> str:
        return "Отдыхает"

    def check_preconditions(self, npc, simulation, time_dict) -> bool:
        from living_world.engine.life_cycle_manager import LifeStage
        if npc.get_life_stage(simulation.time.current_datetime) == LifeStage.BABY:
            return False
        return True

    def calculate_utility(self, npc, simulation, time_dict) -> float:
        utility = 0.0
        hour = time_dict['hour']

        if npc.mood < 40:
            utility += 60

        if 17 <= hour < 22 or 7 <= hour < 8:
             utility += 50

        return utility

    def execute(self, npc, simulation, time_dict):
        if npc.current_location != npc.home_id:
             npc.current_location = npc.home_id
        npc.mood += 1.0

class PlayAction(Action):
    @property
    def name(self) -> str:
        return "Играет"

    def check_preconditions(self, npc, simulation, time_dict) -> bool:
        life_stage = npc.get_life_stage(simulation.time.current_datetime)
        return life_stage in [LifeStage.BABY, LifeStage.CHILD, LifeStage.SCHOOL, LifeStage.TEEN]

    def calculate_utility(self, npc, simulation, time_dict) -> float:
        utility = 0.0
        hour = time_dict['hour']
        life_stage = npc.get_life_stage(simulation.time.current_datetime)

        if 9 <= hour < 21:
             if life_stage in [LifeStage.BABY, LifeStage.CHILD, LifeStage.SCHOOL]:
                 utility += 70

        return utility

    def execute(self, npc, simulation, time_dict):
        if npc.current_location != npc.home_id:
             npc.current_location = npc.home_id
        npc.mood += 1.5

class SocializeAction(Action):
    @property
    def name(self) -> str:
        return "Общается"

    def check_preconditions(self, npc, simulation, time_dict) -> bool:
        from living_world.engine.life_cycle_manager import LifeStage
        if npc.get_life_stage(simulation.time.current_datetime) == LifeStage.BABY:
            return False
        return True

    def calculate_utility(self, npc, simulation, time_dict) -> float:
        utility = 0.0
        hour = time_dict['hour']

        if 10 <= hour < 22:
             if npc.traits.get("sociability", 0) > 0.5:
                 utility += 40

        return utility

    def execute(self, npc, simulation, time_dict):
        pass

class StudyAction(Action):
    @property
    def name(self) -> str:
        return "Учится"

    def check_preconditions(self, npc, simulation, time_dict) -> bool:
        return getattr(npc, 'education_status', None) == "Обучается" and getattr(npc, 'current_education_id', None) is not None

    def calculate_utility(self, npc, simulation, time_dict) -> float:
        hour = time_dict['hour']
        utility = 0.0

        prog_id = getattr(npc, 'current_education_id', None)
        is_full_time = False
        if prog_id:
            prog = simulation.education_manager.programs.get(prog_id)
            if prog and prog.type in ["school_9", "school_11", "bachelor", "college"]:
                is_full_time = True

        if is_full_time:
            if 8 <= hour < 15:
                utility += 90
        else:
            # Заочное/вечернее обучение (part-time)
            if 18 <= hour < 21:
                utility += 70

        # Домашнее задание
        if 16 <= hour < 19 and is_full_time:
            patience = npc.traits.get('patience', 0)
            if patience > 0:
                utility += 40

        return utility

    def execute(self, npc, simulation, time_dict):
        prog_id = getattr(npc, 'current_education_id', None)
        if not prog_id: return

        prog = simulation.education_manager.programs.get(prog_id)
        if not prog: return

        inst = simulation.education_manager.institutions.get(prog.institution_id)
        if inst and npc.current_location != inst.building_id:
             npc.current_location = inst.building_id

        npc.energy -= 0.15
