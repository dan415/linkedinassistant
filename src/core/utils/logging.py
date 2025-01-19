import logging
import os
import sys
import time
from src.core.constants import LINKEDIN_ASSISTANT_LOGGING_LEVEL, LOGGING_DIR, LOGGING_ONLY_CONSOLE


class TruncateByTimeHandler(logging.FileHandler):
    _instances = {}

    def __new__(cls, filename, *args, **kwargs):
        if filename not in cls._instances:
            instance = super().__new__(cls)
            cls._instances[filename] = instance
        return cls._instances[filename]

    def __init__(self, filename, mode='a', encoding='utf-8', interval_seconds=3600):
        """
        Initializes the custom logging handler.

        :param: filename: Name of the file to write logs to.
        :param: mode: File mode (default is append 'a').
        :param: encoding: File encoding (default is 'utf-8').
        :param: interval_seconds: Time interval (in seconds) after which the log file will be truncated.
        """
        super().__init__(filename=filename, mode=mode, encoding=encoding)
        self.interval_seconds = interval_seconds  # Interval for truncating the log file.
        self.last_truncate_time = time.time()  # Tracks the last time the file was truncated.

    def emit(self, record):
        """
        Writes a log record to the file and checks if truncation is needed.

        :param: record: The log record to write.
        """
        super().emit(record)  # Write the log record to the file.
        current_time = time.time()  # Get the current time.

        # Check if the interval since the last truncation has passed.
        if current_time - self.last_truncate_time > self.interval_seconds:
            self._truncate_file()  # Truncate the log file.
            self.last_truncate_time = current_time  # Update the last truncation time.

    def _truncate_file(self):
        """
        Truncates the log file to clear its contents.
        """
        with open(self.baseFilename, 'r+') as file:  # Open the file in read/write mode.
            file.truncate()  # Clear the contents of the file.


class ServiceLogger(logging.Logger):
    """
    A utility class for providing a thread-specific logger.

    This class ensures that each thread gets its own unique logger instance.
    The logger is named based on the thread name and is configured with a
    StreamHandler and a standard message format.

    This class overrides the logging methods (e.g., info, debug, etc.) to
    automatically use the thread-specific logger instance.
    """

    def __init__(self,
                 name: str,
                 main=False,
                 noconsole=False,
                 formatter='%(asctime)s - %(pathname)s - %(funcName)s - %(thread)d - %(levelname)s - %(message)s'
                 ):
        super().__init__(name)
        self.filename = "Main" if main else self.name
        self.noconsole = noconsole
        self.formatter = formatter

        if not self.hasHandlers():
            self._init_handlers()

    def _init_file_handler(self, log_level):
        try:
            os.makedirs(LOGGING_DIR, exist_ok=True)
            filehandler = TruncateByTimeHandler(
                filename=os.path.join(LOGGING_DIR, f'{self.filename}.log'),
                encoding='utf-8',
                mode='a+'
            )
            filehandler.setLevel(log_level)
            filehandler.setFormatter(
                logging.Formatter(self.formatter)
            )
            self.addHandler(filehandler)

        except OSError as ex:
            self.error(f"Error adding handler to file {ex}")

    def _init_handlers(self):
        log_level = logging.getLevelNamesMapping().get(os.environ.get(LINKEDIN_ASSISTANT_LOGGING_LEVEL, "INFO"))
        self.setLevel(log_level)

        if not self.noconsole or os.environ.get(LOGGING_ONLY_CONSOLE, False):
            stdhandler = logging.StreamHandler(sys.stdout)
            stdhandler.setLevel(log_level)
            stdhandler.setFormatter(
                logging.Formatter(self.formatter)
            )
            self.addHandler(stdhandler)

        if not os.environ.get(LOGGING_ONLY_CONSOLE, False):
            self._init_file_handler(log_level)


class DefaultLogger(ServiceLogger):
    """
    A utility class for providing a thread-specific logger.

    This class ensures that each thread gets its own unique logger instance.
    The logger is named based on the thread name and is configured with a
    StreamHandler and a standard message format.

    This class overrides the logging methods (e.g., info, debug, etc.) to
    automatically use the thread-specific logger instance.
    """

    def __init__(self, name: str):
        super().__init__(name, main=True)


class StreamToLogger:
    """
    Fake file-like stream object that redirects writes to a logger instance.
    """

    def __init__(self, logger, level):
        self.logger = logger
        self.level = level
        self.linebuf = ''

    def write(self, buf):
        for line in buf.rstrip().splitlines():
            self.logger.log(self.level, line.rstrip())

    def flush(self):
        pass
