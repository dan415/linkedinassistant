import os
import threading
import datetime
import src.core.utils.functions as F
from src.core.database.mongo import MongoDBClient
from src.information.constants import YOUTUBE_POOL_COLLECTION

FILE = os.path.basename(__file__)
logger = F.get_logger(dump_to=FILE)


class YoutubeUrlPool:
    """
    Singleton class to manage the pool of YouTube URLs to be processed using MongoDB
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(YoutubeUrlPool, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.client = MongoDBClient(collection_name=YOUTUBE_POOL_COLLECTION)
        self.mutex = threading.Lock()
        self._initialized = True

    def add_url(self, url):
        """Add a URL to the pool"""
        with self.mutex:
            # Check if URL already exists
            if not self.client.find_one({"url": url}):
                self.client.insert_one({
                    "url": url,
                    "timestamp": datetime.datetime.utcnow()
                })

    def release(self, url):
        """Remove a URL from the pool"""
        with self.mutex:
            self.client.delete_one({"url": url})

    def get_next_url(self):
        """Get the next URL to process ordered by timestamp"""
        with self.mutex:
            url_doc = self.client.find_one(
                sort=[("timestamp", 1)]  # 1 for ascending order
            )
            return url_doc["url"] if url_doc else None

    def has_urls(self):
        """Check if there are URLs to process"""
        with self.mutex:
            return self.client.count_documents({}) > 0

    def is_processed(self, url):
        """Check if a URL exists in the pool"""
        with self.mutex:
            return bool(self.client.find_one({"url": url}))

    def __iter__(self):
        """Make the pool iterable"""
        return self

    def __next__(self):
        """Get the next URL from the pool"""
        url = self.get_next_url()
        if url is None:
            raise StopIteration
        self.release(url)  # Remove the URL after retrieving it
        return url
