import datetime
from living_world.engine.event_bus import bus

class MemoryManager:
    def __init__(self, simulation):
        self.simulation = simulation
        self.memories = []

    def get_memories_for(self, npc_id):
        return [m for m in self.memories if m['owner_npc_id'] == npc_id]

    def add_memory(self, owner_id, target_id, event_type, description, significance, valence):
        sim_time_dict = self.simulation.time.get_time_dict()
        sim_time_str = f"День {sim_time_dict.get('day', 1)}, {sim_time_dict.get('hour', 0):02d}:{sim_time_dict.get('minute', 0):02d}"

        memory = {
            'owner_npc_id': owner_id,
            'target_npc_id': target_id,
            'event_type': event_type,
            'description': description,
            'timestamp': datetime.datetime.now().isoformat(),
            'sim_time': sim_time_str,
            'sim_minutes': self.simulation.time.get_total_minutes(),
            'significance': significance,
            'valence': valence
        }
        self.memories.append(memory)
        bus.publish("memory_created", memory)
        return memory

    def get_context_score(self, owner_id, target_id):
        """
        Calculates the Memory Context Score for owner -> target.
        Range is theoretically unbounded, but practically [-1.0, 1.0] scaled up later.
        """
        # Get memories owner has about target
        relevant_mems = [m for m in self.memories if m['owner_npc_id'] == owner_id and m.get('target_npc_id') == target_id]

        # Take the most recent 10 memories
        recent_mems = sorted(relevant_mems, key=lambda x: x.get('sim_minutes', 0), reverse=True)[:10]

        score = 0.0
        current_minutes = self.simulation.time.get_total_minutes()

        for m in recent_mems:
            mem_minutes = m.get('sim_minutes', current_minutes)
            days_passed = (current_minutes - mem_minutes) / (24 * 60.0)
            if days_passed < 0: days_passed = 0

            # Time weight decreases by 2% per day, minimum 10%
            time_weight = max(0.1, 1.0 - (days_passed * 0.02))

            valence = m.get('valence', 0.0)
            significance = m.get('significance', 0.5)

            score += valence * significance * time_weight

        return score

    def load_memories(self, loaded_memories):
        self.memories = loaded_memories
        # Need to backfill sim_minutes if missing from old saves
        for m in self.memories:
            if 'sim_minutes' not in m:
                # Approximation: try to parse 'День X'
                try:
                    day_part = m['sim_time'].split(',')[0]
                    day = int(day_part.split(' ')[1])
                    m['sim_minutes'] = (day - 1) * 24 * 60
                except:
                    m['sim_minutes'] = 0

    def get_all_memories(self):
        return self.memories
