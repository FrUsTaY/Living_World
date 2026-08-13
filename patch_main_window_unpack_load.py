import re

with open('living_world/gui/main_window.py', 'r') as f:
    content = f.read()

load_pattern = r'time_dict, b_dicts, npc_dicts, events = db.load_world\(\)'
load_replacement = 'time_dict, b_dicts, npc_dicts, events, families, relationships, memories = db.load_world()'
content = re.sub(load_pattern, load_replacement, content)

with open('living_world/gui/main_window.py', 'w') as f:
    f.write(content)
