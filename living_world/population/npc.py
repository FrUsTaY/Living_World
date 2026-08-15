import uuid
import random
from datetime import datetime
from living_world.engine.event_bus import bus
from living_world.engine.life_cycle_manager import LifeCycleManager, LifeStage

class NPC:
    def __init__(self, first_name, last_name, date_of_birth: datetime, gender, profession, home_id, work_id, npc_id=None, traits=None, family_id=None):
        self.id = npc_id or str(uuid.uuid4())
        self.first_name = first_name
        self.last_name = last_name

        self.date_of_birth = date_of_birth
        self.date_of_death = None
        self.is_alive = True

        self.gender = gender
        self.profession = profession

        self.home_id = home_id
        self.work_id = work_id

        self.money = 0.0

        # Потребности (0-100%)
        self.hunger = 100.0   # 100 = сыт
        self.energy = 100.0   # 100 = полон сил
        self.mood = 100.0     # 100 = счастлив

        self.current_location = home_id
        self.state = "Спит"

        self.traits = traits or self._generate_traits()
        self.family_id = family_id

        self.current_education_id = None
        self.education_status = None

        self._last_state = self.state

        # Cache for age, to avoid recalculating if time hasn't changed.
        self._cached_age = 0
        self._last_calculated_date = None

    def get_age(self, current_world_date: datetime) -> int:
        current_date_tuple = (current_world_date.year, current_world_date.month, current_world_date.day)
        if self._last_calculated_date == current_date_tuple:
             return self._cached_age
        self._cached_age = LifeCycleManager.calculate_age(current_world_date, self.date_of_birth)
        self._last_calculated_date = current_date_tuple
        return self._cached_age

    def get_life_stage(self, current_world_date: datetime) -> LifeStage:
        age = self.get_age(current_world_date)
        return LifeCycleManager.get_life_stage(age, self.is_alive)

    def _generate_traits(self):
        return {
            'sociability': random.uniform(-1.0, 1.0),
            'friendliness': random.uniform(-1.0, 1.0),
            'conflict': random.uniform(-1.0, 1.0),
            'empathy': random.uniform(-1.0, 1.0),
            'boldness': random.uniform(-1.0, 1.0),
            'patience': random.uniform(-1.0, 1.0)
        }

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

    def update(self, time_dict):
        pass # Updated via Simulation.ai_controller

    def _move_to(self, location_id):
        if self.current_location != location_id:
            self.current_location = location_id

    def to_dict(self, city=None, current_world_date: datetime = None):
        age = self.get_age(current_world_date) if current_world_date else 0
        stage = LifeCycleManager.format_life_stage_ru(self.get_life_stage(current_world_date) if current_world_date else LifeStage.DEAD)

        data = {
            "Имя": self.get_full_name(),
            "Возраст": f"{age} лет",
            "Дата рождения": self.date_of_birth.strftime("%d.%m.%Y") if self.date_of_birth else "Неизвестно",
            "Жизненный этап": stage,
            "Статус": "Жив" if self.is_alive else "Умер",
            "Профессия": self.profession,
            "Деньги": f"{self.money:.2f} ₽",
            "Настроение": f"{int(self.mood)}%",
            "Энергия": f"{int(self.energy)}%",
            "Голод": f"{int(self.hunger)}%",
            "Состояние": self.state
        }

        if city:
            home = city.get_building(self.home_id)
            work = city.get_building(self.work_id)
            loc = city.get_building(self.current_location)

            data["Дом"] = home.name if home else "Неизвестно"
            data["Место работы"] = work.name if work else "Безработный"
            data["Текущая локация"] = loc.name if loc else "На улице"

        return data
