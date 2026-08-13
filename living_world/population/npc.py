import uuid
import random
from living_world.engine.event_bus import bus

class NPC:
    def __init__(self, first_name, last_name, age, gender, profession, home_id, work_id, npc_id=None, traits=None, family_id=None):
        self.id = npc_id or str(uuid.uuid4())
        self.first_name = first_name
        self.last_name = last_name
        self.age = age
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
        hour = time_dict['hour']
        minute = time_dict['minute']

        # 1. Изменение потребностей
        self.hunger -= 0.1 # Голодает постепенно
        self.energy -= 0.05

        # Ограничения
        self.hunger = max(0, min(100, self.hunger))
        self.energy = max(0, min(100, self.energy))

        # Настроение зависит от голода и энергии
        self.mood = (self.hunger + self.energy) / 2

        # 2. Логика поведения на основе времени суток и потребностей

        # Проверка, нужно ли продолжать есть (гистерезис)
        if self.state == "Ест" and self.hunger < 95:
            self.hunger += 2.0
        else:
            # Сон
            if hour >= 22 or hour < 7:
                self._move_to(self.home_id)
                self.state = "Спит"
                self.energy += 0.3  # Восстановление энергии во сне

            # Работа (с 8 до 17)
            elif 8 <= hour < 17:
                if self.hunger < 30:
                    self.state = "Ест"
                else:
                    self._move_to(self.work_id)
                    self.state = "Работает"
                    self.energy -= 0.1 # На работе устает быстрее

            # Свободное время (7-8 и 17-22)
            else:
                if self.hunger < 60:
                    self.state = "Ест"
                else:
                    self._move_to(self.home_id)
                    self.state = "Отдыхает"

        # Проверка на изменение состояния для логирования
        if self.state != self._last_state:
            state_text = self.state.lower()
            bus.publish("log_event", f"{self.get_full_name()} теперь {state_text}.")
            self._last_state = self.state

    def _move_to(self, location_id):
        if self.current_location != location_id:
            self.current_location = location_id

    def to_dict(self, city=None):
        data = {
            "Имя": self.get_full_name(),
            "Возраст": self.age,
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
