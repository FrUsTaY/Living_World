import re

with open('living_world/database/repository.py', 'r') as f:
    content = f.read()

memories_save = """
            # Сохраняем память
            cursor.execute("DELETE FROM memories")
            for m in memories:
                cursor.execute(
                    "INSERT INTO memories (owner_npc_id, target_npc_id, event_type, description, timestamp, sim_time, significance) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (m['owner_npc_id'], m.get('target_npc_id'), m['event_type'], m['description'], m['timestamp'], m['sim_time'], m['significance'])
                )
"""

content = content.replace("# Сохраняем только новые (несохраненные) события", memories_save + "\n            # Сохраняем только новые (несохраненные) события")

with open('living_world/database/repository.py', 'w') as f:
    f.write(content)
