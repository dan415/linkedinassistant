import logging
from abc import ABC, abstractmethod
from typing import Tuple
from src.core.config.manager import ConfigManager
from src.core.utils.logging import ServiceLogger


class DocumentInformationRetrieval(ABC):
    _CONFIG_SCHEMA = None  # Forces to implement this constant

    def __init__(
        self, document_name, logger: logging.Logger = ServiceLogger(__name__)
    ):
        self.document_name = document_name
        self.logger = logger

    def __enter__(self):
        self.load_config()

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    @abstractmethod
    def search(
        self, paragraphs: list[str], queries: list[str] = None
    ) -> Tuple[str, str]:
        """
        Execute the retrieval workflow to process input text and dynamically generate questions and answers.

        :param: paragraphs (List[str]): A list of paragraphs that constitute the input text.
            queries (Optional[List[str]]): Ignored. This retriever dynamically generates its own queries.

        :returns: Tuple[str, str]: A formatted Q&A dialog string and the extracted title of the document.
        """
        pass

    def load_config(self):
        """
        Method to load the provider's config file
        """
        config = ConfigManager().load_config(self._CONFIG_SCHEMA)
        for key in config.keys():
            self.__setattr__(key, config[key])
