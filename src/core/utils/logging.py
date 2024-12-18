import logging
import time


class TruncateByTimeHandler(logging.FileHandler):
    def __init__(self, filename, mode='a', encoding='utf-8', interval_seconds=3600):
        super().__init__(filename=filename, mode=mode, encoding=encoding)
        self.interval_seconds = interval_seconds
        self.last_truncate_time = time.time()

    def emit(self, record):
        super().emit(record)
        current_time = time.time()
        if current_time - self.last_truncate_time > self.interval_seconds:
            self._truncate_file()
            self.last_truncate_time = current_time

    def _truncate_file(self):
        with open(self.baseFilename, 'r+') as file:
            file.truncate()
