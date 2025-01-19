import logging
import sys
from dotenv import load_dotenv
from src.core.utils.logging import DefaultLogger, StreamToLogger, ServiceLogger

load_dotenv()
logging.setLoggerClass(DefaultLogger)
logger = logging.getLogger(__name__)
stderr_logger = ServiceLogger(
    "stderr",
    noconsole=True,
    formatter="%(asctime)s - %(thread)d - %(message)s",
)
sys.stderr = StreamToLogger(
    stderr_logger, logging.INFO
)  # Redirect Standard error to Main Logger
