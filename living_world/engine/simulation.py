import time
from living_world.engine.time_manager import TimeManager
from living_world.engine.event_bus import bus
from living_world.city.city import City
from living_world.engine.social.memory_manager import MemoryManager
from living_world.engine.social.relationship_manager import RelationshipManager
from living_world.engine.social.social_manager import SocialManager
from living_world.engine.social.family_manager import FamilyManager
from living_world.engine.ai.ai_controller import AIController
from living_world.engine.education.manager import EducationManager

class Simulation:
    def __init__(self):
        self.time = TimeManager()
        self.city = City()
        self.npcs = []
        self.events_log = []
        # Чтобы при сохранении в новый файл не терялась старая история,
        # нам нужно хранить ВСЮ историю в RAM (но GUI отобразит лишь срез)
        self.full_history = []

        self.memory_manager = MemoryManager(self)
        self.relationship_manager = RelationshipManager(self)
        self.social_manager = SocialManager(self)
        self.family_manager = FamilyManager(self)
        self.families = []

        self.ai_controller = AIController(self)
        self.education_manager = EducationManager(self)

        bus.subscribe("log_event", self._on_log_event)

    def _on_log_event(self, msg):
        event = {"time": self.time.format_time(), "msg": msg}
        self.events_log.append(event)
        self.full_history.append(event)
        if len(self.events_log) > 200:
            self.events_log.pop(0)

    def add_npc(self, npc):
        self.npcs.append(npc)

    def update(self):
        # Реальное время, которое должно симулироваться за один цикл
        # зависит от self.time.speed

        if self.time.paused:
            return

        # Определяем, сколько минут игрового времени проходит за 1 тик приложения
        # Допустим 1 тик (вызов update) происходит 10 раз в секунду.
        # При 1x: 1 игровая минута в секунду -> 0.1 мин за тик.
        # Чтобы не усложнять дробными минутами, будем накапливать остаток
        # Либо, для простоты, пусть tick_step зависит от speed.

        # Для 1x: 1 мин раз в N тиков
        # Для 1000x: 100 мин за тик

        pass # Логика tick_step будет реализована в QThread или таймере GUI,
             # чтобы UI контролировал частоту вызовов update.

        # Будем считать, что при вызове update() проходит 1 минута игрового времени
        if self.time.tick(1):
            time_dict = self.time.get_time_dict()

            # Check for natural death once a day (at midnight, e.g. 00:00)
            is_new_day = (time_dict['hour'] == 0 and time_dict['minute'] == 0)
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
                            bus.publish("log_event", f"✝ {npc.get_full_name()} скончался в возрасте {age} лет.")

            for npc in self.npcs:
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
                if npc.state != getattr(npc, '_last_state', None):
                    bus.publish("log_event", f"{npc.get_full_name()} переходит в состояние: {npc.state}")
                npc._last_state = npc.state
            self.social_manager.process_social_ticks()
