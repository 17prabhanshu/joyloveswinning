import re

with open("ps3_agent/api/server.py", "r") as f:
    code = f.read()

# Replace f.get('diagnosis', {}).get('cause_hypothesis', 'State mismatch') 
# with something that handles object or dict.
# Actually, the simplest fix is to just read the attribute if it's an object, or dict otherwise.
# To do it inline in the f-string:
# getattr(f.get('diagnosis'), 'cause_hypothesis', f.get('diagnosis', {}).get('cause_hypothesis', 'State mismatch')) if f.get('diagnosis') else 'State mismatch'

old_str = "f.get('diagnosis', {}).get('cause_hypothesis', 'State mismatch')"
new_str = "(getattr(f.get('diagnosis'), 'cause_hypothesis', 'State mismatch') if hasattr(f.get('diagnosis'), 'cause_hypothesis') else f.get('diagnosis', {}).get('cause_hypothesis', 'State mismatch') if isinstance(f.get('diagnosis'), dict) else 'State mismatch')"

code = code.replace(old_str, new_str)

with open("ps3_agent/api/server.py", "w") as f:
    f.write(code)

print("Fixed line 467")
