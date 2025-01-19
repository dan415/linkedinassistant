import logging
from enum import Enum
from src.core.llm.retrieval.langchain import LangChainRetriever
from src.core.utils.logging import ServiceLogger


class Retriever(Enum):
    LANGCHAIN_RAG = "Langchain-RAG"


class DocumentRetrieverProvider:
    """Provides a content search engine. This is just a class that returns a search
    engine for a given information source, just for abstraction purposes"""

    @classmethod
    def get_document_retriever_provider(
        cls,
        provider: str,
        logger: logging.Logger = ServiceLogger(__name__),
        document_name: str = "",
    ):
        """Get a content search engine for the information source.

        :param: provider: String value identifier for the provider. Right now only langchain is supported :)
        :param: logger: Logger to use
        :param: document_name: Optional document name to pass to the provider for the title. If empty, the title
        will get extracted as part of the flow
        """
        if provider == Retriever.LANGCHAIN_RAG.value:
            return LangChainRetriever(document_name, logger=logger)
        else:
            raise ValueError(f"Provider {provider} is not supported.")
