import os
import sys
from enum import Enum
from pathlib import Path

PWD = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.abspath(os.path.join(PWD, "..", ".."))
DATA_DIR = (
    PROJECT_DIR
    if sys.platform != "win32"
    else os.path.join(
        str(Path.home()), "AppData", "Local", "linkedin_assistant"
    )
)

LOGGING_DIR = os.path.join(DATA_DIR, "logs")
HTML_DIR = os.path.join(DATA_DIR, "html")
JSON_DIR = os.path.join(DATA_DIR, "json")

LOGGING_ONLY_CONSOLE = "LOGGING_ONLY_CONSOLE"
LINKEDIN_ASSISTANT_LOGGING_LEVEL = "LINKEDIN_ASSISTANT_LOGGING_LEVEL"
CONFIGS_COLLECTION = "config"
PUBLICATIONS_COLLECTION = "publications"
YOUTUBE_COLLECTION = "youtube-pool"
SERVICE_NAME = "linkedin_assistant"
COLLECTIONS_AND_INDICES = {
    CONFIGS_COLLECTION: [{"config_name": 1, "unique": True}],
    YOUTUBE_COLLECTION: [{"timestamp": 1}],
    PUBLICATIONS_COLLECTION: [
        {"publication_id": 1, "unique": True},
        {"state": 1, "creationDate": -1},
    ],
}


class FileManagedFolders:
    INPUT_PDF_FOLDER = "Sources/Pdf/Input"
    OUTPUT_PDF_FOLDER = "Sources/Pdf/Output"
    IMAGES_FOLDER = "Publications/Images"


class SecretKeys:
    MONGO_URI = "MONGO_URI"
    MONGO_DATABASE = "MONGO_DATABASE"
    RAPID_API_KEY = "RAPID_API_KEY"
    OPENAI_KEY = "OPENAI_API_KEY"
    NGROK_DOMAIN = "NGROK_DOMAIN"
    NGROK_TOKEN = "NGROK_TOKEN"
    TELEGRAM_BOT_TOKEN = "TELEGRAM_BOT_TOKEN"
    B2_APPLICATION_KEY_ID_KEY = "BLACBLAZE_KEY_ID"
    B2_APPLICATION_KEY_KEY = "BLACBLAZE_API_KEY"
    LINKEDIN_CLIENT_ID = "LINKEDIN_CLIENT_ID"
    LINKEDIN_CLIENT_SECRET = "LINKEDIN_CLIENT_SECRET"
    LINKEDIN_ACCESS_TOKEN = "LINKEDIN_ACCESS_TOKEN"
    LINKEDIN_ID = "LINKEDIN_LINKEDIN_ID"
    TELEGRAM_CHAT_ID = "TELEGRAM_CHAT_ID"
    YOUTUBE_API_KEY = "YOUTUBE_API_KEY"


class PublicationState(Enum):
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING"
    PUBLISHED = "PUBLISHED"
    DISCARDED = "DISCARDED"
