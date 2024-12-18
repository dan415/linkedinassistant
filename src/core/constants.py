import os

PWD = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.abspath(os.path.join(PWD, '..', '..'))
LOGGING_DIR = os.path.join(PROJECT_DIR, "logs") if os.name != 'nt' else os.path.join(r"C:\\", "ProgramData",
                                                                                     "linkedin_assistant", "logs")


DEBUG = True
CONFIGS_COLLECTION = "config"


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
