import datetime
from living_world.engine.event_bus import bus

class MemoryManager:
    def __init__(self):
        self.memories = []

    def get_memories_for(self, npc_id):
        return [m for m in self.memories if m['owner_npc_id'] == npc_id]

    def add_memory(self, owner_id, target_id, event_type, description, sim_time_dict, significance=0.5):
        # Format time to a readable string like "Day X, 12:00"
        sim_time_str = f"День {sim_time_dict.get('day', 1)}, {sim_time_dict.get('hour', 0):02d}:{sim_time_dict.get('minute', 0):02d}"

        memory = {
            'owner_npc_id': owner_id,
            'target_npc_id': target_id,
            'event_type': event_type,
            'description': description,
            'timestamp': datetime.datetime.now().isoformat(),
            'sim_time': sim_time_str,
            'significance': significance
        }
        self.memories.append(memory)
        # Log via event bus so it gets stored globally
        bus.publish("memory_created", memory)
        return memory

    def load_memories(self, loaded_memories):
        self.memories = loaded_memories

    def get_all_memories(self):
        return self.memories
