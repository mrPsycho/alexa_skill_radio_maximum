"""Environment-driven configuration for the skill.

No station name/URL/skill ID is ever hardcoded elsewhere in the app -
everything reads from here, which in turn reads from the environment
(populated from a local .env file via python-dotenv during development).
"""

import os

from dotenv import load_dotenv

load_dotenv()

ALEXA_SKILL_ID = os.environ.get("ALEXA_SKILL_ID", "")
STATION_NAME = os.environ.get("STATION_NAME", "Maximum Radio")
STATION_URL = os.environ.get(
    "STATION_URL", "https://hls-01-maximum.hostingradio.ru/maximum/playlist.m3u8"
)
PORT = int(os.environ.get("PORT", "5000"))
