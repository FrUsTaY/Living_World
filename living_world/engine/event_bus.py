class EventBus:
    def __init__(self):
        self._subscribers = {}

    def subscribe(self, event_type, callback):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type, callback):
        callbacks = self._subscribers.get(event_type)
        if not callbacks:
            return

        self._subscribers[event_type] = [item for item in callbacks if item != callback]
        if not self._subscribers[event_type]:
            del self._subscribers[event_type]

    def publish(self, event_type, data=None):
        if event_type in self._subscribers:
            for callback in self._subscribers[event_type]:
                callback(data)

# Глобальная шина событий для Этапа 1
bus = EventBus()
