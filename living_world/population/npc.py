import uuid
import random
from datetime import datetime
from living_world.engine.event_bus import bus
from living_world.engine.life_cycle_manager import LifeCycleManager, LifeStage

class NPC:
    HOBBIES = ["Чтение", "Рыбалка", "Спорт", "Кулинария", "Садоводство"]

    def __init__(self, first_name, last_name, date_of_birth: datetime, gender, profession, home_id, work_id,
                 npc_id=None, traits=None, family_id=None, mother_id=None, father_id=None, children_desire=None, health=100.0,
                 hygiene=100.0, stress=0.0, hobby=None, chronotype=None, is_sick=False, sick_days=0, alimony_to_id=None,
                 career_level=1, work_experience_days=0,
                 is_renting=False, mortgage_debt=0.0, mortgage_payment=0.0,
                 transport_mode=None, has_criminal_record=False, jail_days=0,
                 inspiration_buffer_days=0, has_warm_clothes=False,
                 genetics=None):
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
        self.health = float(health) # 100 = идеально здоров

        self.current_location = home_id
        self.state = "Спит"

        self.traits = traits or self._generate_traits()
        self.family_id = family_id
        self.mother_id = mother_id
        self.father_id = father_id
        self.household_id = None
        self.dating_partner_id = None
        self.children_desire = children_desire if children_desire is not None else random.uniform(0.0, 1.0)

        self.current_education_id = None
        self.education_status = None
        self.alimony_to_id = alimony_to_id
        self.career_level = int(career_level)
        self.work_experience_days = int(work_experience_days)
        self.is_renting = bool(is_renting)
        self.mortgage_debt = float(mortgage_debt)
        self.mortgage_payment = float(mortgage_payment)
        self.transport_mode = transport_mode or ("car" if self.money >= 50000.0 else "foot")

        self.hygiene = float(hygiene)
        self.stress = float(stress)
        self.hobby = hobby or random.choice(self.HOBBIES)
        self.chronotype = chronotype or random.choice(["lark", "owl"])
        self.is_sick = bool(is_sick)
        self.sick_days = int(sick_days)
        self.has_criminal_record = bool(has_criminal_record)
        self.jail_days = int(jail_days)
        self.inspiration_buffer_days = int(inspiration_buffer_days)
        self.has_warm_clothes = bool(has_warm_clothes)
        from living_world.engine.genetics.genetics_manager import GeneticsManager
        self.genetics = genetics if genetics is not None else GeneticsManager.generate_genome(gender=self.gender)

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
        current_date_tuple = (current_world_date.year, current_world_date.month, current_world_date.day)
        if (getattr(self, '_last_stage_date', None) == current_date_tuple and
                getattr(self, '_last_stage_alive', None) == self.is_alive):
            return self._cached_stage
        age = self.get_age(current_world_date)
        self._cached_stage = LifeCycleManager.get_life_stage(age, self.is_alive)
        self._last_stage_date = current_date_tuple
        self._last_stage_alive = self.is_alive
        return self._cached_stage

    def _generate_traits(self):
        return {
            'sociability': random.uniform(-1.0, 1.0),
            'friendliness': random.uniform(-1.0, 1.0),
            'conflict': random.uniform(-1.0, 1.0),
            'empathy': random.uniform(-1.0, 1.0),
            'boldness': random.uniform(-1.0, 1.0),
            'patience': random.uniform(-1.0, 1.0),
            'ambition': random.uniform(-1.0, 1.0),
            'frugality': random.uniform(-1.0, 1.0),
            'diligence': random.uniform(-1.0, 1.0)
        }

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

    def is_available_for_social(self):
        """
        Contract defining whether the NPC can physically engage in social interactions.
        Returns False if dead, sleeping, working, studying, or otherwise incapacitated.
        """
        if not self.is_alive:
            return False

        # Blocking states
        if self.state in ["Спит", "Работает", "Учится", "Мёртв", "В тюрьме"] or getattr(self, 'jail_days', 0) > 0:
            return False

        return True

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
            "Квалификация": f"{self.career_level} разряд ({self.work_experience_days} дн. стажа)",
            "Деньги": f"{self.money:.2f} ₽",
            "Здоровье": f"{int(self.health)}%" if not self.is_sick else f"{int(self.health)}% (Болен)",
            "Гигиена": f"{int(self.hygiene)}%",
            "Стресс": f"{int(self.stress)}%",
            "Хобби": self.hobby,
            "Хронотип": "Жаворонок" if self.chronotype == "lark" else "Сова",
            "Настроение": f"{int(self.mood)}%",
            "Энергия": f"{int(self.energy)}%",
            "Голод": f"{int(self.hunger)}%",
            "Состояние": self.state,
            "Партнёр": self.dating_partner_id if self.dating_partner_id else "Нет",
            "Алименты": "Выплачивает" if self.alimony_to_id else "Нет",
            "Ипотека": f"{self.mortgage_debt:,.0f} ₽ ({self.mortgage_payment:,.0f} ₽/день)" if self.mortgage_debt > 0 else "Нет",
            "Транспорт": "Автомобиль" if self.transport_mode == "car" else ("Автобус" if self.transport_mode == "bus" else "Пешком"),
            "Судимость": "Есть" if self.has_criminal_record else "Нет",
            "Статус заключения": f"В тюрьме ({self.jail_days} дн.)" if self.jail_days > 0 else "На свободе",
            "Зимняя одежда": "Есть" if self.has_warm_clothes else "Нет",
            "Фенотип": f"Глаза: {self.genetics.get('eye_color', '—')}, Волосы: {self.genetics.get('hair_color', '—')}, Рост: {self.genetics.get('height_cm', 175)} см ({self.genetics.get('body_type', 'Нормальное')})"
        }

        if city:
            home = city.get_building(self.home_id)
            work = city.get_building(self.work_id)
            loc = city.get_building(self.current_location)

            district = city.get_district_for_building(self.home_id) if hasattr(city, 'get_district_for_building') else None
            data["Дом"] = home.name if home else "Неизвестно"
            data["Место работы"] = work.name if work else "Безработный"
            data["Текущая локация"] = loc.name if loc else "На улице"
            data["Район"] = district.name if district else "Центральный район"

        return data

    def get_colleagues(self, simulation):
        if not self.work_id:
            return []
        return [n for n in simulation.npcs if n.is_alive and n.id != self.id and n.work_id == self.work_id]

    def get_neighbors(self, simulation):
        if not self.home_id:
            return []
        return [n for n in simulation.npcs if n.is_alive and n.id != self.id and n.home_id == self.home_id]
