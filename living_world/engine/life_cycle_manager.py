from enum import Enum, auto
from datetime import datetime
import random

class LifeStage(Enum):
    BABY = auto()         # 0-2
    CHILD = auto()        # 3-6
    SCHOOL = auto()       # 7-12
    TEEN = auto()         # 13-17
    YOUNG_ADULT = auto()  # 18-24
    ADULT = auto()        # 25-64
    ELDER = auto()        # 65+
    DEAD = auto()

class LifeCycleManager:
    @staticmethod
    def calculate_age(world_date: datetime, date_of_birth: datetime) -> int:
        if date_of_birth is None:
            return 0
        age = world_date.year - date_of_birth.year - ((world_date.month, world_date.day) < (date_of_birth.month, date_of_birth.day))
        return max(0, age)

    @staticmethod
    def get_life_stage(age: int, is_alive: bool = True) -> LifeStage:
        if not is_alive:
            return LifeStage.DEAD

        if age <= 2:
            return LifeStage.BABY
        elif age <= 6:
            return LifeStage.CHILD
        elif age <= 12:
            return LifeStage.SCHOOL
        elif age <= 17:
            return LifeStage.TEEN
        elif age <= 24:
            return LifeStage.YOUNG_ADULT
        elif age <= 64:
            return LifeStage.ADULT
        else:
            return LifeStage.ELDER

    @staticmethod
    def format_life_stage_ru(stage: LifeStage) -> str:
        stages_ru = {
            LifeStage.BABY: "Младенец",
            LifeStage.CHILD: "Ребёнок",
            LifeStage.SCHOOL: "Школьник",
            LifeStage.TEEN: "Подросток",
            LifeStage.YOUNG_ADULT: "Молодой взрослый",
            LifeStage.ADULT: "Взрослый",
            LifeStage.ELDER: "Пожилой",
            LifeStage.DEAD: "Умер"
        }
        return stages_ru.get(stage, "Неизвестно")

    @staticmethod
    def check_natural_death(age: int) -> bool:
        """
        Calculates the probability of natural death and rolls the dice.
        Returns True if the NPC dies.
        """
        # Very simple probablity curve
        if age < 65:
            # Almost zero for young people, but keep tiny chance to avoid hard rules
            prob = 0.000001
        elif age < 75:
            prob = 0.0001  # Small chance
        elif age < 85:
            prob = 0.001   # Medium chance
        elif age < 95:
            prob = 0.01    # High chance
        elif age < 100:
            prob = 0.1     # Very high chance
        else:
            prob = 0.5     # Extremely high chance

        return random.random() < prob
