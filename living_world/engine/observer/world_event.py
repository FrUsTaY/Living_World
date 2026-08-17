from enum import Enum, auto
import uuid
import time
from typing import Dict, Any, List

class EventImportance(Enum):
    LOW = auto()        # Повседневный шум (разговор, ссора)
    MEDIUM = auto()     # Интересные события (начало отношений, смена работы)
    HIGH = auto()       # Значимые события (переезд, важный конфликт)
    CRITICAL = auto()   # Судьбоносные события (рождение, свадьба, смерть)

class EventType(Enum):
    SOCIAL_INTERACTION = auto()
    STATE_CHANGE = auto()
    CONFLICT_MINOR = auto()
    CONFLICT_MAJOR = auto()
    RELATIONSHIP_START = auto()
    MARRIAGE = auto()
    DIVORCE = auto()
    BIRTH = auto()
    DEATH = auto()
    MOVE = auto()
    JOB_CHANGE = auto()
    # Агрегированные типы
    AGGREGATED_SOCIAL = auto()

class WorldEvent:
    def __init__(self,
                 timestamp: str,
                 event_type: EventType,
                 importance: EventImportance,
                 message: str,
                 participants: List[str] = None,
                 data: Dict[str, Any] = None,
                 event_id: str = None):
        self.id = event_id if event_id else str(uuid.uuid4())
        self.timestamp = timestamp
        self.type = event_type
        self.importance = importance
        self.message = message
        self.participants = participants if participants else []
        self.data = data if data else {}

    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "type": self.type.name,
            "importance": self.importance.name,
            "message": self.message,
            "participants": self.participants,
            "data": self.data
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            timestamp=data["timestamp"],
            event_type=EventType[data["type"]],
            importance=EventImportance[data["importance"]],
            message=data["message"],
            participants=data.get("participants", []),
            data=data.get("data", {}),
            event_id=data.get("id")
        )
