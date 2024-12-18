import os
from enum import Enum

from src.llm.retrieval.langchain import LangChainRetriever
import src.core.utils.functions as F

FILE = os.path.basename(__file__)
logger = F.get_logger(dump_to=FILE)


class Retriever(Enum):
    LANGCHAIN_RAG = "Langchain-RAG"


class DocumentRetrieverProvider:
    """Provides a content search engine. This is just a class that returns a search
     engine for a given information source, just for abstraction purposes"""

    @classmethod
    def get_document_retriever_provider(cls, provider, document_name):
        """Get a content search engine for the information source."""
        logger.info("Getting document retriever engine for %s", provider)
        if provider == Retriever.LANGCHAIN_RAG.value:
            return LangChainRetriever(document_name)
        else:
            raise ValueError(f"Provider {provider} is not supported.")
