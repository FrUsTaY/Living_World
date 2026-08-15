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
        if not self.is_alive:
            return

        hour = time_dict['hour']
        minute = time_dict['minute']
        current_world_date = datetime(
            time_dict.get('year', 2000),
            time_dict.get('month', 1),
            time_dict.get('day', 1),
            hour,
            minute
        )

        life_stage = self.get_life_stage(current_world_date)

        # 1. Изменение потребностей
        self.hunger -= 0.1 # Голодает постепенно
        self.energy -= 0.05

        # Ограничения
        self.hunger = max(0, min(100, self.hunger))
        self.energy = max(0, min(100, self.energy))

        # Настроение зависит от голода и энергии
        self.mood = (self.hunger + self.energy) / 2

        # 2. Логика поведения на основе весов и потребностей
        # Определяем базовые веса для каждого действия
        weights = {
            "Спит": 0,
            "Ест": 0,
            "Работает": 0,
            "Отдыхает": 0,
            "Играет": 0,
            "Общается": 0
        }

        # Гистерезис
        if self.state == "Ест" and self.hunger < 95:
            self.hunger += 2.0
            # Continuing eating is guaranteed
            weights["Ест"] = 1000
        else:
            # Сон
            if hour >= 22 or hour < 7:
                weights["Спит"] += 100
                if life_stage in [LifeStage.BABY, LifeStage.CHILD]:
                    weights["Спит"] += 50 # Children sleep more deeply/reliably
                if self.energy < 30:
                    weights["Спит"] += 50
            else:
                if self.energy < 20:
                     weights["Спит"] += 50 # Nap

            # Еда
            if self.hunger < 30:
                weights["Ест"] += 150
            elif self.hunger < 60:
                weights["Ест"] += 50

            # Работа / Учеба (будущая система)
            if 8 <= hour < 17:
                if life_stage in [LifeStage.YOUNG_ADULT, LifeStage.ADULT]:
                    weights["Работает"] += 80
                    # Влияние характера
                    if self.traits['patience'] > 0:
                        weights["Работает"] += 20
                elif life_stage in [LifeStage.ELDER]:
                    # Пожилые могут работать, но с меньшей вероятностью
                    weights["Работает"] += 30
                    weights["Отдыхает"] += 50
                elif life_stage in [LifeStage.CHILD, LifeStage.SCHOOL, LifeStage.TEEN]:
                    # Пока нет школы, они играют/учатся дома
                    weights["Играет"] += 60
                    weights["Отдыхает"] += 20
                elif life_stage == LifeStage.BABY:
                    weights["Отдыхает"] += 50

            # Свободное время
            if 17 <= hour < 22 or 7 <= hour < 8:
                if life_stage in [LifeStage.BABY, LifeStage.CHILD]:
                    weights["Играет"] += 80
                else:
                    weights["Отдыхает"] += 50
                    if self.traits['sociability'] > 0.5:
                        weights["Общается"] += 30
                    if life_stage == LifeStage.TEEN:
                        weights["Общается"] += 40

        # Если ни один вес не сработал (например, все 0), добавляем дефолтное
        if max(weights.values()) == 0:
             weights["Отдыхает"] = 10

        # Выбираем действие с максимальным весом
        best_action = max(weights, key=weights.get)

        # Применяем действие
        self.state = best_action

        if self.state == "Спит":
            self._move_to(self.home_id)
            self.energy += 0.3
        elif self.state == "Работает":
            self._move_to(self.work_id)
            self.energy -= 0.1
        else: # Ест, Отдыхает, Играет, Общается
            self._move_to(self.home_id)

        # Проверка на изменение состояния для логирования
        if self.state != self._last_state:
            state_text = self.state.lower()
            bus.publish("log_event", f"{self.get_full_name()} теперь {state_text}.")
            self._last_state = self.state

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
