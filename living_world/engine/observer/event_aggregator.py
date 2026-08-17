from living_world.engine.event_bus import bus
from living_world.engine.observer.world_event import WorldEvent, EventImportance, EventType
from living_world.engine.observer.event_journal import EventJournal

class EventAggregator:
    def __init__(self, journal: EventJournal, sim):
        self.journal = journal
        self.sim = sim
        # Настройка подписки на EventBus.
        # Поскольку мы не удаляем старые "log_event", мы подпишемся на новый канал "world_event" для структурированных событий.
        bus.subscribe("world_event", self._on_world_event)

    def _on_world_event(self, event_data: dict):
        """
        Ожидает dict с ключами:
        - timestamp (str)
        - type (EventType)
        - importance (EventImportance)
        - message (str)
        - participants (list[str])
        - data (dict)
        """
        # Пока нет агрегации LOW событий, поэтому просто прокидываем все
        # Агрегация будет реализована позднее в рамках правил (например, схлопывание обычных разговоров за день)
        event = WorldEvent(
            timestamp=event_data["timestamp"],
            event_type=event_data["type"],
            importance=event_data["importance"],
            message=event_data["message"],
            participants=event_data.get("participants", []),
            data=event_data.get("data", {})
        )
        self.journal.add_event(event)

    def publish_event(self, event_type: EventType, importance: EventImportance, message: str, participants: list = None, data: dict = None):
        """
        Удобный метод для публикации событий (вызывается из симуляции, чтобы не дергать bus вручную).
        Также публикуем в старый log_event для обратной совместимости.
        """
        timestamp = self.sim.time.format_time()

        # 1. Отправляем в новый поток
        bus.publish("world_event", {
            "timestamp": timestamp,
            "type": event_type,
            "importance": importance,
            "message": message,
            "participants": participants or [],
            "data": data or {}
        })

        # 2. Отправляем в старый поток для сохранения работоспособности старых логов
        bus.publish("log_event", message)
