import re

with open('living_world/gui/main_window.py', 'r') as f:
    content = f.read()

# Fix save_world call to pass memories
save_pattern = r'getattr\(self.sim, \'families\', \[\]\),\n\s*self.sim.relationship_manager.get_all_relationships\(\)'
save_replacement = """getattr(self.sim, 'families', []),
                    self.sim.relationship_manager.get_all_relationships(),
                    self.sim.memory_manager.get_all_memories()"""
content = re.sub(save_pattern, save_replacement, content)

with open('living_world/gui/main_window.py', 'w') as f:
    f.write(content)
