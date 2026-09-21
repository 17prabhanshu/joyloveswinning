from dotenv import load_dotenv
import os
load_dotenv()
print("Token:", os.environ.get("WOKWI_CLI_TOKEN"))
