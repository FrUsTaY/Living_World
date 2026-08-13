import re

with open('living_world/gui/main_window.py', 'r') as f:
    content = f.read()

# Make sure memories, relationships and families are injected back into simulation
inject_pattern = r'self.pop_tab.simulation = self.sim\n\s*self.fam_tab.simulation = self.sim'
inject_replacement = """self.pop_tab.simulation = self.sim
                self.fam_tab.simulation = self.sim

                self.sim.relationship_manager.load_relationships(relationships)
                self.sim.memory_manager.load_memories(memories)
                self.sim.families = families"""
content = re.sub(inject_pattern, inject_replacement, content)

with open('living_world/gui/main_window.py', 'w') as f:
    f.write(content)
