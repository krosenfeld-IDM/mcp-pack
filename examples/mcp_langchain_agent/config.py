from pathlib import Path
import dotenv

# Load environment variables from .env file
dotenv.load_dotenv()

# URLs for MCP services
SCIRIS_URL = "http://localhost:8001/sse"
STARSIM_URL = "http://localhost:8002/sse"

# Dictionary to store MCP servers with their names and URLs
MCP_SERVERS = {
     "sciris": 
     {
        "url": SCIRIS_URL,
        "transport": "sse" ,}
        ,
    "starsim": {
        "url": STARSIM_URL,
        "transport": "sse" ,}
}
