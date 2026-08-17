from typing import List, Dict
from living_world.engine.observer.world_event import WorldEvent, EventImportance

class EventJournal:
    def __init__(self):
        self.events: List[WorldEvent] = []

    def add_event(self, event: WorldEvent):
        self.events.append(event)

    def get_all_events(self) -> List[WorldEvent]:
        return self.events

    def get_events_by_importance(self, importance_levels: List[EventImportance]) -> List[WorldEvent]:
        return [e for e in self.events if e.importance in importance_levels]

    def get_events_for_participant(self, participant_id: str) -> List[WorldEvent]:
        return [e for e in self.events if participant_id in e.participants]

    def load_from_dicts(self, event_dicts: List[Dict]):
        self.events = [WorldEvent.from_dict(d) for d in event_dicts]

    def to_dicts(self) -> List[Dict]:
        return [e.to_dict() for e in self.events]
