from src.information.sources.arxiv import ArxivSearchEngine
from src.information.sources.base import InformationSource
from src.information.sources.manual_pdfs import ManualSourceEngine
from src.information.sources.rapid.medium import MediumSearchEngine
from src.information.sources.rapid.google_news import GoogleNewsInformationEngine
from src.information.sources.rapid.youtube.retriever import YoutubeTranscriptRetriever


class ContentSearchEngineProvider:
    """Provides a content search engine for different information sources.
    This class abstracts the logic of instantiating the appropriate search engine
    based on the given information source."""

    SEARCH_ENGINE_MAP: dict[InformationSource, type] = {
        InformationSource.ARXIV: ArxivSearchEngine,
        InformationSource.MEDIUM: MediumSearchEngine,
        InformationSource.GOOGLE_NEWS: GoogleNewsInformationEngine,
        InformationSource.MANUAL: ManualSourceEngine,
        InformationSource.YOUTUBE: YoutubeTranscriptRetriever,
    }

    @classmethod
    def get_content_search_engine(cls, information_source: InformationSource) -> object:
        """Retrieve the appropriate content search engine for the specified information source.
        Args:
            information_source (InformationSource): Enum value representing the information source.

        Returns:
            An instance of the appropriate search engine class.

        Raises:
            ValueError: If the information source is not supported.
        """
        search_engine_class = cls.SEARCH_ENGINE_MAP.get(information_source)

        if search_engine_class is None:
            raise ValueError(f"Information source {information_source} is not supported.")

        return search_engine_class()
