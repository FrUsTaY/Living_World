import time
from living_world.engine.time_manager import TimeManager
from living_world.engine.event_bus import bus
from living_world.city.city import City

class Simulation:
    def __init__(self):
        self.time = TimeManager()
        self.city = City()
        self.npcs = []
        self.events_log = []

        bus.subscribe("log_event", self._on_log_event)

    def _on_log_event(self, msg):
        event = {"time": self.time.format_time(), "msg": msg}
        self.events_log.append(event)
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
            for npc in self.npcs:
                npc.update(time_dict)
