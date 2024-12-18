from abc import ABC, abstractmethod
from enum import Enum

from src.core.config.manager import ConfigManager


class DocumentInformationRetrieval(ABC):

    def __init__(self, document_name):
        self.document_name = document_name
        self.load_config()

    @abstractmethod
    def extract_title(self, text):
        """Extract title from the document text.
        
        :param text: The document text to extract title from
        :return: Extracted title as string
        """
        pass

    @property
    @abstractmethod
    def config_schema(self):
        """Child classes must implement this attribute."""
        pass

    @abstractmethod
    def __enter__(self):
        pass

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    @abstractmethod
    def search(self, paragraphs, queries=None):
        pass

    def load_config(self):
        config = ConfigManager().load_config(self.config_schema)
        for key in config.keys():
            self.__setattr__(key, config[key])
