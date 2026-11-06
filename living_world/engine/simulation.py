import time
from living_world.engine.time_manager import TimeManager
from living_world.engine.event_bus import bus
from living_world.city.city import City
from living_world.engine.social.memory_manager import MemoryManager
from living_world.engine.social.relationship_manager import RelationshipManager
from living_world.engine.social.social_manager import SocialManager
from living_world.engine.social.family_manager import FamilyManager
from living_world.engine.social.household_manager import HouseholdManager
from living_world.engine.ai.ai_controller import AIController
from living_world.engine.education.manager import EducationManager
from living_world.engine.reproduction.manager import ReproductionManager
from living_world.engine.economy.economy_manager import EconomyManager
from living_world.engine.autosave_manager import AutosaveManager
from living_world.engine.urban.construction_manager import ConstructionManager
from living_world.engine.observer.event_journal import EventJournal
from living_world.engine.observer.event_aggregator import EventAggregator
from living_world.engine.observer.world_event import EventType, EventImportance

class Simulation:
    def __init__(self):
        self.time = TimeManager()
        self.city = City()
        self.npcs = []
        self._has_babies = False
        self.events_log = []
        # Чтобы при сохранении в новый файл не терялась старая история,
        # нам нужно хранить ВСЮ историю в RAM (но GUI отобразит лишь срез)
        self.full_history = []

        self.memory_manager = MemoryManager(self)
        self.relationship_manager = RelationshipManager(self)
        self.social_manager = SocialManager(self)
        self.family_manager = FamilyManager(self)
        self.household_manager = HouseholdManager(self)
        self.families = []

        self.ai_controller = AIController(self)
        self.education_manager = EducationManager(self)
        self.reproduction_manager = ReproductionManager(self)
        self.economy_manager = EconomyManager(self)
        self.autosave_manager = AutosaveManager(self)
        self.construction_manager = ConstructionManager(self)
        from living_world.engine.environment.weather_manager import WeatherManager
        self.weather_manager = WeatherManager(self)
        from living_world.engine.chronicle.city_chronicle import CityChronicle
        self.city_chronicle = CityChronicle(self)
        from living_world.engine.politics.politics_manager import PoliticsManager
        self.politics_manager = PoliticsManager(self)
        from living_world.engine.justice.crime_manager import CrimeManager
        self.crime_manager = CrimeManager(self)

        # Observer 3.5.1
        self.event_journal = EventJournal()
        self.event_aggregator = EventAggregator(self.event_journal, self)

        bus.subscribe("log_event", self._on_log_event)

    def close(self):
        """Release global event-bus subscriptions before discarding a world."""
        bus.unsubscribe("log_event", self._on_log_event)
        self.family_manager.close()
        self.household_manager.close()
        self.event_aggregator.close()

    def _on_log_event(self, msg):
        event = {"time": self.time.format_time(), "msg": msg}
        self.events_log.append(event)
        self.full_history.append(event)
        if len(self.events_log) > 200:
            self.events_log.pop(0)

    def save_to_file(self, file_path: str):
        from living_world.database.repository import Database
        edu_inst = getattr(self, 'education_manager', None)
        households = list(self.household_manager.households.values()) if hasattr(self, 'household_manager') else []
        pregnancies = getattr(self, 'reproduction_manager', None).active_pregnancies if hasattr(self, 'reproduction_manager') else []
        enterprises = list(self.economy_manager.enterprises.values()) if hasattr(self, 'economy_manager') else []

        db = Database(file_path)
        db.save_world(
            sim_time=self.time.get_time_dict(),
            npcs=self.npcs,
            buildings=self.city.buildings,
            events=self.full_history,
            families=getattr(self, 'families', []),
            relationships=self.relationship_manager.get_all_relationships(),
            memories=self.memory_manager.get_all_memories(),
            educational_institutions=list(edu_inst.institutions.values()) if edu_inst else [],
            education_programs=list(edu_inst.programs.values()) if edu_inst else [],
            education_history=[r.to_dict() for r in getattr(edu_inst, 'history', [])] if edu_inst else [],
            pregnancies=pregnancies,
            households=households,
            world_events=self.event_journal.to_dicts(),
            enterprises=enterprises,
            city_treasury=getattr(self.economy_manager, 'city_treasury', 100000.0) if hasattr(self, 'economy_manager') else 100000.0,
            politics=self.politics_manager.to_dict() if hasattr(self, 'politics_manager') else None,
            crimes=self.crime_manager.to_dict() if hasattr(self, 'crime_manager') else None
        )

    def add_npc(self, npc):
        self.npcs.append(npc)

    def update(self):
        # Реальное время, которое должно симулироваться за один цикл
        # зависит от self.time.speed

        if self.time.paused:
            return

        # Будем считать, что при вызове update() проходит 1 минута игрового времени
        if self.time.tick(1):
            time_dict = self.time.get_time_dict()
            self.weather_manager.update_weather(self.time.current_datetime)
            self.city_chronicle.check_and_publish_monthly(self.time.current_datetime)

            # Check for natural death once a day (at midnight, e.g. 00:00)
            is_new_day = (time_dict['hour'] == 0 and time_dict['minute'] == 0)
            if is_new_day:
                from living_world.engine.life_cycle_manager import LifeStage
                self._has_babies = any(n.is_alive and n.get_life_stage(self.time.current_datetime) == LifeStage.BABY for n in self.npcs)
            if is_new_day:
                from living_world.engine.life_cycle_manager import LifeCycleManager
                current_date = self.time.current_datetime
                for npc in self.npcs:
                    if npc.is_alive:
                        age = npc.get_age(current_date)
                        if LifeCycleManager.check_natural_death(age):
                            npc.is_alive = False
                            npc.date_of_death = current_date
                            npc.state = "Умер"

                            self.event_aggregator.publish_event(
                                event_type=EventType.DEATH,
                                importance=EventImportance.CRITICAL,
                                message=f"✝ {npc.get_full_name()} скончался в возрасте {age} лет.",
                                participants=[npc.id]
                            )
                            bus.publish("npc_died", {"npc": npc})

                for household in self.household_manager.households.values():
                    if household.stress > 0:
                        self.household_manager.modify_stress(household.id, -self.household_manager.STRESS_DAILY_DECAY)

            if time_dict['minute'] == 0 and time_dict['hour'] in [14, 21]:
                self.crime_manager.evaluate_and_trigger_crimes(self.time.current_datetime)

            if is_new_day:
                self.reproduction_manager.update()
                self.economy_manager.daily_cycle()
                self._process_daily_lifecycle(self.time.current_datetime)
                self.autosave_manager.check_and_autosave(time_dict['day'])
                self.construction_manager.evaluate_city_growth()
                self._process_daily_health()
                self.politics_manager.daily_update(self.time.current_datetime)
                self.crime_manager.daily_update(self.time.current_datetime)

            for npc in self.npcs:
                if not npc.is_alive:
                    continue

                if is_new_day:
                    self.education_manager.update_npc_education(npc, time_dict)
                # 1. Изменение базовых потребностей, гигиены, стресса и здоровья
                npc.hunger -= 0.1
                npc.energy -= 0.05
                npc.hunger = max(0.0, min(100.0, npc.hunger))
                npc.energy = max(0.0, min(100.0, npc.energy))

                hygiene_decay = 0.08 if npc.state in ["Работает", "Учится"] else 0.04
                npc.hygiene = max(0.0, getattr(npc, 'hygiene', 100.0) - hygiene_decay)

                stress = getattr(npc, 'stress', 0.0)
                stress_inc = 0.0
                if npc.hunger < 30.0:
                    stress_inc += 0.03
                if npc.energy < 30.0:
                    stress_inc += 0.03
                if getattr(npc, 'hygiene', 100.0) < 30.0:
                    stress_inc += 0.03

                if npc.state in ["Спит", "Отдыхает", "Гуляет", "Занимается хобби", "Принимает душ"]:
                    stress = max(0.0, stress - 0.05)
                else:
                    stress = min(100.0, stress + stress_inc)
                npc.stress = stress

                if npc.hunger <= 0.0 or npc.energy <= 0.0 or npc.stress >= 85.0:
                    npc.health = max(0.0, getattr(npc, 'health', 100.0) - 0.1)

                bio_baseline = (npc.hunger + npc.energy) / 2.0
                current_mood = getattr(npc, 'mood', 100.0)
                npc.mood = max(0.0, min(100.0, current_mood * 0.96 + bio_baseline * 0.04))

                # 2. Выбор и выполнение действия через Utility AI
                self.ai_controller.choose_and_execute_action(npc, time_dict)

                # Логируем смену состояния
                if npc.state != getattr(npc, '_last_state', None) and getattr(npc, '_last_state', None) is not None:
                    self.event_aggregator.publish_event(
                        event_type=EventType.STATE_CHANGE,
                        importance=EventImportance.LOW,
                        message=f"{npc.get_full_name()} переходит в состояние: {npc.state}",
                        participants=[npc.id],
                        data={"old_state": getattr(npc, '_last_state', None), "new_state": npc.state}
                    )
                npc._last_state = npc.state
            self.social_manager.process_social_ticks()

    def _process_daily_lifecycle(self, current_date):
        from living_world.engine.life_cycle_manager import LifeStage
        import random

        # 1. Выход пожилых на пенсию
        for npc in self.npcs:
            if not npc.is_alive:
                continue
            age = npc.get_age(current_date)
            if age >= 65 and npc.profession != "Пенсионер":
                retire_chance = 0.5 if age >= 70 or npc.profession in ["Строитель", "Механик", "Фермер", "Разнорабочий"] else 0.25
                if random.random() < retire_chance:
                    npc.profession = "Пенсионер"
                    npc.work_id = None
                    if hasattr(self, 'event_aggregator'):
                        self.event_aggregator.publish_event(
                            event_type=EventType.JOB_CHANGE,
                            importance=EventImportance.LOW,
                            message=f"{npc.get_full_name()} ({age} лет) вышел(ла) на заслуженную пенсию.",
                            participants=[npc.id]
                        )

        # 2. Отделение повзрослевших детей и переезд в свободные дома
        homes = self.city.get_homes() if hasattr(self, 'city') else []
        if homes:

            home_occupants = {h.id: 0 for h in homes}
            for n in self.npcs:
                if n.is_alive and n.home_id in home_occupants:
                    home_occupants[n.home_id] += 1

            for npc in self.npcs:
                if not npc.is_alive:
                    continue
                stage = npc.get_life_stage(current_date)
                if stage in [LifeStage.YOUNG_ADULT, LifeStage.ADULT]:
                    parents = self.family_manager.get_parents(npc.id) if hasattr(self, 'family_manager') else []
                    living_with_parent = any(p.is_alive and p.home_id == npc.home_id for p in parents)
                    if living_with_parent and (npc.money >= 10000.0 or getattr(npc, 'family_id', None) is not None):
                        available_homes = [h for h in homes if h.id != npc.home_id and home_occupants[h.id] < h.capacity]
                        if available_homes and random.random() < 0.25:
                            target_home = random.choice(available_homes)
                            old_home_id = npc.home_id
                            new_hh = self.household_manager.create_household(target_home.id) if hasattr(self, 'household_manager') else None

                            npc.home_id = target_home.id
                            if new_hh:
                                npc.household_id = new_hh.id
                            home_occupants[old_home_id] -= 1
                            home_occupants[target_home.id] += 1

                            spouse = self.family_manager.get_spouse(npc.id) if hasattr(self, 'family_manager') else None
                            if spouse and spouse.home_id != target_home.id and spouse.home_id in home_occupants:
                                home_occupants[spouse.home_id] -= 1
                                spouse.home_id = target_home.id
                                if new_hh:
                                    spouse.household_id = new_hh.id
                                home_occupants[target_home.id] += 1

                            if hasattr(self, 'memory_manager'):
                                self.memory_manager.add_memory(
                                    npc.id, None, "Переезд", f"Начал(а) самостоятельную жизнь, переехав в {target_home.name}", 0.7, 0.8
                                )
                            if hasattr(self, 'event_aggregator'):
                                self.event_aggregator.publish_event(
                                    event_type=EventType.MOVE,
                                    importance=EventImportance.MEDIUM,
                                    message=f"{npc.get_full_name()} начал(а) самостоятельную жизнь и переехал(а) в {target_home.name}.",
                                    participants=[npc.id] + ([spouse.id] if spouse else [])
                                )

        # 3. Выплата алиментов на содержание несовершеннолетних детей
        for npc in self.npcs:
            if not npc.is_alive:
                continue
            alimony_to = getattr(npc, 'alimony_to_id', None)
            if not alimony_to:
                continue

            custodial = next((n for n in self.npcs if n.id == alimony_to and n.is_alive), None)
            if not custodial:
                npc.alimony_to_id = None
                continue

            minor_children = [
                c for c in self.family_manager.get_children(npc.id)
                if c.is_alive and c.get_age(current_date) < 18
            ]
            if not minor_children:
                npc.alimony_to_id = None
                continue

            alimony_amount = min(npc.money * 0.25, 2500.0)
            if alimony_amount >= 100.0:
                npc.money -= alimony_amount
                custodial.money += alimony_amount
                if hasattr(self, 'event_aggregator'):
                    self.event_aggregator.publish_event(
                        event_type=EventType.ECONOMIC,
                        importance=EventImportance.LOW,
                        message=f"⚖ Алименты: {npc.get_full_name()} перечислил(а) {alimony_amount:,.0f} ₽ {custodial.get_full_name()} на содержание детей ({len(minor_children)} чел.).",
                        participants=[npc.id, custodial.id] + [c.id for c in minor_children]
                    )

    def _process_daily_health(self):
        import random
        for npc in self.npcs:
            if not npc.is_alive:
                continue

            if getattr(npc, 'is_sick', False):
                npc.sick_days = getattr(npc, 'sick_days', 0) + 1
                if npc.current_location == npc.home_id and random.random() < 0.20:
                    npc.is_sick = False
                    npc.sick_days = 0
                    npc.health = min(100.0, getattr(npc, 'health', 50.0) + 20.0)
                    if hasattr(self, 'event_aggregator'):
                        self.event_aggregator.publish_event(
                            event_type=EventType.SOCIAL_INTERACTION,
                            importance=EventImportance.LOW,
                            message=f"🌿 {npc.get_full_name()} отлежался(лась) дома и выздоровел(а).",
                            participants=[npc.id]
                        )
                elif npc.sick_days > 5:
                    npc.health = max(5.0, getattr(npc, 'health', 100.0) - random.uniform(3.0, 8.0))
            else:
                sick_prob = 0.004
                if getattr(npc, 'health', 100.0) < 60.0:
                    sick_prob += 0.015
                if getattr(npc, 'stress', 0.0) > 60.0:
                    sick_prob += 0.01
                if getattr(npc, 'hygiene', 100.0) < 30.0:
                    sick_prob += 0.01
                if hasattr(self, 'weather_manager') and self.weather_manager.temperature < 0.0:
                    sick_prob += 0.012

                if random.random() < sick_prob:
                    npc.is_sick = True
                    npc.sick_days = 0
                    npc.mood = max(0.0, getattr(npc, 'mood', 50.0) - 15.0)
                    if hasattr(self, 'event_aggregator'):
                        self.event_aggregator.publish_event(
                            event_type=EventType.SOCIAL_INTERACTION,
                            importance=EventImportance.LOW,
                            message=f"🤒 {npc.get_full_name()} заболел(а) простудой.",
                            participants=[npc.id]
                        )
