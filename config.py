import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

owner_id_str = os.getenv("OWNER_ID")
if owner_id_str:
    try:
        OWNER_ID = int(owner_id_str)
    except ValueError:
        print("Warning: OWNER_ID in .env is not a valid integer. Owner commands will not work correctly.")
        OWNER_ID = 0
else:
    print("Warning: OWNER_ID not found in .env. Owner commands will not work.")
    OWNER_ID = 0

ERROR_LOG_CHANNEL_ID = None
ERROR_LOG_DM = False