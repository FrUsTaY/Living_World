import re

with open('living_world/gui/main_window.py', 'r') as f:
    content = f.read()

# I messed up with the regex replace and it added it to new_world as well. Reverting that.

# Clean up the file. It's getting messy. Let's write the whole file to be safe.
