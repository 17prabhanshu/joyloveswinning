import re
with open("ps3_agent/cli.py", "r") as f:
    code = f.read()

code = "from dotenv import load_dotenv\nload_dotenv()\n" + code

with open("ps3_agent/cli.py", "w") as f:
    f.write(code)
