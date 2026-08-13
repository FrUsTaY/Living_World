import re

with open('living_world/database/repository.py', 'r') as f:
    content = f.read()

# Fix the migration error on memory_type vs event_type in schema vs create table
# Actually schema says event_type. Load says nothing special (just dict). Let's check load_world.
# load_world doesn't have an issue.

# Ensure save_world handles missing 'target_npc_id' properly in memories
save_pattern = r'm\.get\(\'target_npc_id\'\)'
save_replacement = 'm.get(\'target_npc_id\')' # Already correct

# Let's run a test script to make sure it loads
