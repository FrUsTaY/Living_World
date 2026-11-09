from typing import List, Dict
from living_world.engine.observer.world_event import WorldEvent, EventImportance

class EventJournal:
    def __init__(self):
        self.events: List[WorldEvent] = []
        self._max_low = 500
        self._max_medium = 2000

    def add_event(self, event: WorldEvent):
        self.events.append(event)
        # Periodically prune non-critical events to prevent memory bloat and massive save files
        if len(self.events) > 3000:
            self._prune_events()

    def _prune_events(self):
        # High and Critical events are historical milestones — keep 100% of them forever!
        high_critical = [e for e in self.events if e.importance in (EventImportance.CRITICAL, EventImportance.HIGH)]
        medium = [e for e in self.events if e.importance == EventImportance.MEDIUM][-self._max_medium:]
        low = [e for e in self.events if e.importance == EventImportance.LOW][-self._max_low:]
        
        kept_ids = set(id(e) for e in (high_critical + medium + low))
        self.events = [e for e in self.events if id(e) in kept_ids]

    def get_all_events(self) -> List[WorldEvent]:
        return self.events

    def get_events_by_importance(self, importance_levels: List[EventImportance]) -> List[WorldEvent]:
        return [e for e in self.events if e.importance in importance_levels]

    def get_events_for_participant(self, participant_id: str) -> List[WorldEvent]:
        return [e for e in self.events if participant_id in e.participants]

    def load_from_dicts(self, event_dicts: List[Dict]):
        self.events = [WorldEvent.from_dict(d) for d in event_dicts]
        if len(self.events) > 3000:
            self._prune_events()

    def to_dicts(self) -> List[Dict]:
        return [e.to_dict() for e in self.events]
