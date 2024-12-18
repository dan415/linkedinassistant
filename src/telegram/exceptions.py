class FetchFileException(Exception):

    def __init__(self, result):
        self.result = result
        self.message = f"Failed to fetch file from Telegram: {result}"


class DownloadFileException(Exception):

    def __init__(self, result):
        self.result = result
        self.message = f"Failed to download file from Telegram: {result}"
