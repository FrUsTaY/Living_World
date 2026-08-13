import re

with open('living_world/database/repository.py', 'r') as f:
    content = f.read()

# Fix save_world arguments
save_pattern = r'def save_world\(self, sim_time, npcs, buildings, events, families=None, relationships=None\):'
save_replacement = """def save_world(self, sim_time, npcs, buildings, events, families=None, relationships=None, memories=None):
        if memories is None: memories = []"""
content = re.sub(save_pattern, save_replacement, content)


# Add memories save block
memories_pattern = r'# Сохраняем только новые \(несохраненные\) события'
memories_replacement = """# Сохраняем память (полная перезапись на сохранении для Этапа 2, можно оптимизировать позже)
            cursor.execute("DELETE FROM memories")
            for m in memories:
                cursor.execute(
                    \"\"\"INSERT INTO memories
                    (owner_npc_id, target_npc_id, event_type, description, timestamp, sim_time, significance)
                    VALUES (?, ?, ?, ?, ?, ?, ?)\"\"\",
                    (m['owner_npc_id'], m.get('target_npc_id'), m['event_type'], m['description'],
                     m['timestamp'], m['sim_time'], m['significance'])
                )

            # Сохраняем только новые (несохраненные) события"""
content = content.replace(memories_pattern, memories_replacement)

with open('living_world/database/repository.py', 'w') as f:
    f.write(content)
