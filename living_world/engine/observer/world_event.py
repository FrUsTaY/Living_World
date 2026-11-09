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
    RELATIONSHIP_END = auto()
    MARRIAGE = auto()
    DIVORCE = auto()
    PREGNANCY = auto()
    BIRTH = auto()
    DEATH = auto()
    MOVE = auto()
    JOB_CHANGE = auto()
    EDUCATION_ENROLL = auto()
    EDUCATION_GRADUATE = auto()
    EDUCATION_EXPEL = auto()
    FAMILY_CREATED = auto()
    FRIENDSHIP_START = auto()
    ROMANCE_START = auto()
    ECONOMIC = auto()
    # Агрегированные типы
    AGGREGATED_SOCIAL = auto()

class WorldEvent:
    _event_counter = 0

    def __init__(self,
                 timestamp: str,
                 event_type: EventType,
                 importance: EventImportance,
                 message: str,
                 participants: List[str] = None,
                 data: Dict[str, Any] = None,
                 event_id: str = None):
        if event_id:
            self.id = event_id
        else:
            WorldEvent._event_counter += 1
            self.id = f"ev_{WorldEvent._event_counter}_{int(time.time()*1000)}" 
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


import unicodedata

def has_emoji(text: str) -> bool:
    if not text:
        return False
    for ch in text:
        cat = unicodedata.category(ch)
        code = ord(ch)
        if (
            cat in ('So', 'Sk')
            or (0x2600 <= code <= 0x27BF)
            or (0x1F300 <= code <= 0x1FAFF)
            or ch in '✝💍👶🛋🚗💼🎓💾⚠🎉🏛⚖🔫👮🕯🔥🌙☀️'
        ):
            return True
    return False
