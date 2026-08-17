from living_world.engine.event_bus import bus
from living_world.engine.observer.world_event import WorldEvent, EventImportance, EventType
from living_world.engine.observer.event_journal import EventJournal
from collections import defaultdict
import datetime

class EventAggregator:
    def __init__(self, journal: EventJournal, sim):
        self.journal = journal
        self.sim = sim
        self._recent_low_events = defaultdict(list)

        bus.subscribe("world_event", self._on_world_event)

    def _on_world_event(self, event_data: dict):
        event = WorldEvent(
            timestamp=event_data["timestamp"],
            event_type=event_data["type"],
            importance=event_data["importance"],
            message=event_data["message"],
            participants=event_data.get("participants", []),
            data=event_data.get("data", {})
        )

        # Защита: MEDIUM, HIGH, CRITICAL события всегда попадают в журнал без изменений
        if event.importance in (EventImportance.MEDIUM, EventImportance.HIGH, EventImportance.CRITICAL):
            self.journal.add_event(event)
        else:
            # Для LOW событий (например, STATE_CHANGE, SOCIAL_INTERACTION обычное)
            # В будущем здесь будет логика агрегации (например схлопывание N мелких в 1)
            # Сейчас мы их тоже добавляем в журнал, но UI будет фильтровать их сам.
            # Мы не отбрасываем их из Журнала, так как они нужны для отладки.
            self.journal.add_event(event)

    def publish_event(self, event_type: EventType, importance: EventImportance, message: str, participants: list = None, data: dict = None):
        """
        Публикует WorldEvent и также дублирует в log_event для старой совместимости.
        """
        timestamp = self.sim.time.format_time()

        bus.publish("world_event", {
            "timestamp": timestamp,
            "type": event_type,
            "importance": importance,
            "message": message,
            "participants": participants or [],
            "data": data or {}
        })

        # Дублируем для старых систем
        bus.publish("log_event", message)
