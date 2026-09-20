with open("ps3_agent/execution/wokwi_adapter.py", "r") as f:
    code = f.read()

import re
code = re.sub(r'  - write-serial:.*?\'\n\'', '  - write-serial: "\\\\n"', code, flags=re.DOTALL)
# Actually, I should just completely rewrite it without risking regex issues on newlines.
