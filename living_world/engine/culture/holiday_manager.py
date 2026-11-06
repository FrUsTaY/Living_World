from datetime import datetime
from typing import Optional, Dict, List
from living_world.engine.observer.world_event import EventType, EventImportance

class HolidayType:
    NEW_YEAR = "NEW_YEAR"               # Новый Год (31 декабря - 1 января)
    SPRING_FESTIVAL = "SPRING_FESTIVAL" # Масленица / Весенний фестиваль (15 марта)
    CITY_DAY = "CITY_DAY"               # День Города (15 июля)
    HARVEST_DAY = "HARVEST_DAY"         # Праздник Урожая (15 октября)


class HolidayManager:
    """
    Календарные городские праздники, салюты, фестивали и культурная жизнь.
    """
    HOLIDAYS = {
        HolidayType.NEW_YEAR: {
            "name": "Новый Год",
            "desc": "Семейные застолья, подарки детям и полночный праздничный салют на главной площади",
            "mood_boost": 35.0,
            "stress_relief": 30.0,
            "discount": 0.10,
            "dating_mult": 1.6
        },
        HolidayType.SPRING_FESTIVAL: {
            "name": "Масленица и Весенний фестиваль",
            "desc": "Проводы зимы, горячая выпечка, уличные гуляния в парках и народные забавы",
            "mood_boost": 20.0,
            "stress_relief": 20.0,
            "discount": 0.15,
            "dating_mult": 1.4
        },
        HolidayType.CITY_DAY: {
            "name": "День Города",
            "desc": "Грандиозная городская ярмарка, уличные концерты, скидки 20% на товары и романтические встречи",
            "mood_boost": 30.0,
            "stress_relief": 25.0,
            "discount": 0.20,
            "dating_mult": 2.5
        },
        HolidayType.HARVEST_DAY: {
            "name": "Праздник Урожая",
            "desc": "Оптовая фермерская ярмарка свежих продуктов, заготовка зимних запасов и народные гуляния",
            "mood_boost": 22.0,
            "stress_relief": 20.0,
            "discount": 0.25,
            "dating_mult": 1.3
        }
    }

    def __init__(self, simulation):
        self.simulation = simulation
        self.last_celebrated_date: Optional[str] = None
        self.fireworks_count: int = 0
        self.celebration_history: List[Dict] = []

    def get_current_holiday(self, dt: datetime) -> Optional[Dict]:
        """Определяет, какой праздник отмечается сегодня."""
        m, d = dt.month, dt.day
        if (m == 12 and d == 31) or (m == 1 and d == 1):
            h_info = dict(self.HOLIDAYS[HolidayType.NEW_YEAR])
            h_info["type"] = HolidayType.NEW_YEAR
            return h_info
        elif m == 3 and d == 15:
            h_info = dict(self.HOLIDAYS[HolidayType.SPRING_FESTIVAL])
            h_info["type"] = HolidayType.SPRING_FESTIVAL
            return h_info
        elif m == 7 and d == 15:
            h_info = dict(self.HOLIDAYS[HolidayType.CITY_DAY])
            h_info["type"] = HolidayType.CITY_DAY
            return h_info
        elif m == 10 and d == 15:
            h_info = dict(self.HOLIDAYS[HolidayType.HARVEST_DAY])
            h_info["type"] = HolidayType.HARVEST_DAY
            return h_info
        return None

    def check_and_trigger_fireworks(self, dt: datetime):
        """Запуск полночного новогоднего салюта в полночь 1 января."""
        if dt.month == 1 and dt.day == 1 and dt.hour == 0 and dt.minute == 0:
            self.fireworks_count += 1
            alive_npcs = [n for n in self.simulation.npcs if n.is_alive and getattr(n, 'jail_days', 0) == 0]
            for n in alive_npcs:
                n.mood = min(100.0, n.mood + 35.0)
                n.stress = max(0.0, getattr(n, 'stress', 0.0) - 30.0)
                if hasattr(self.simulation, 'memory_manager'):
                    self.simulation.memory_manager.add_memory(
                        n.id, None, "Новогодний Салют", "Встретил(а) Новый Год под грандиозный фейерверк на площади", 0.8, 1.0
                    )

            if hasattr(self.simulation, 'event_aggregator'):
                self.simulation.event_aggregator.publish_event(
                    event_type=EventType.SOCIAL_INTERACTION,
                    importance=EventImportance.CRITICAL,
                    message="🎆🎇 С НОВЫМ ГОДОМ! Тысячи праздничных залпов салюта озарили ночное небо над главной площадью города!",
                    participants=[n.id for n in alive_npcs[:5]]
                )

    def daily_update(self, dt: datetime):
        """Ежедневная обработка праздников и культурных буферов горожан."""
        # Уменьшение вдохновляющего буфера от культурных походов
        for npc in self.simulation.npcs:
            if not npc.is_alive:
                continue
            if getattr(npc, 'inspiration_buffer_days', 0) > 0:
                npc.inspiration_buffer_days -= 1
                # Защита от уныния: настроение поддерживается на высоком уровне
                npc.mood = min(100.0, max(60.0, npc.mood))
                npc.stress = max(0.0, getattr(npc, 'stress', 0.0) - 2.0)

        # Проверка календарного праздника
        holiday = self.get_current_holiday(dt)
        today_str = dt.strftime("%Y-%m-%d")
        if holiday and self.last_celebrated_date != today_str:
            self.last_celebrated_date = today_str
            self.celebration_history.append({
                "date": today_str,
                "holiday": holiday["name"],
                "type": holiday["type"]
            })

            # Подъем настроения и снятие стресса у жителей
            for npc in self.simulation.npcs:
                if npc.is_alive and getattr(npc, 'jail_days', 0) == 0:
                    npc.mood = min(100.0, npc.mood + holiday["mood_boost"])
                    npc.stress = max(0.0, getattr(npc, 'stress', 0.0) - holiday["stress_relief"])

            if hasattr(self.simulation, 'event_aggregator'):
                self.simulation.event_aggregator.publish_event(
                    event_type=EventType.SOCIAL_INTERACTION,
                    importance=EventImportance.HIGH,
                    message=f"🎉 Сегодня в городе отмечается «{holiday['name']}»! {holiday['desc']}.",
                    participants=[]
                )

    def to_dict(self) -> dict:
        return {
            "last_celebrated_date": self.last_celebrated_date,
            "fireworks_count": self.fireworks_count,
            "celebration_history": self.celebration_history[-50:]
        }

    def load_from_dict(self, data: dict):
        if not data:
            return
        self.last_celebrated_date = data.get("last_celebrated_date")
        self.fireworks_count = int(data.get("fireworks_count", 0))
        self.celebration_history = data.get("celebration_history", [])
