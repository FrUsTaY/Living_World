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
            enterprises=enterprises
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

            if is_new_day:
                self.reproduction_manager.update()
                self.economy_manager.daily_cycle()
                self.autosave_manager.check_and_autosave(time_dict['day'])
                self.construction_manager.evaluate_city_growth()

            for npc in self.npcs:
                if not npc.is_alive:
                    continue

                if is_new_day:
                    self.education_manager.update_npc_education(npc, time_dict)
                # 1. Изменение базовых потребностей
                npc.hunger -= 0.1
                npc.energy -= 0.05
                npc.hunger = max(0, min(100, npc.hunger))
                npc.energy = max(0, min(100, npc.energy))
                npc.mood = (npc.hunger + npc.energy) / 2

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
