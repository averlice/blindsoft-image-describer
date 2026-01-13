import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

owner_id_str = os.getenv("OWNER_ID")
OWNER_IDS = set()
OWNER_ID = 0

if owner_id_str:
    try:
        # Support comma-separated list of IDs
        for id_str in owner_id_str.split(','):
            if id_str.strip():
                OWNER_IDS.add(int(id_str.strip()))
        
        if OWNER_IDS:
            OWNER_ID = list(OWNER_IDS)[0] # Set the first one as primary for compatibility if needed
            
    except ValueError:
        print("Warning: OWNER_ID in .env contains invalid integers. Owner commands will not work correctly.")

if not OWNER_IDS:
    print("Warning: OWNER_ID not found or invalid in .env. Owner commands will not work.")


ERROR_LOG_CHANNEL_ID = None
ERROR_LOG_DM = False