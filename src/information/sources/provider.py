import os

from src.information.sources.arxiv.arxiv_searcher import ArxivSearchEngine
from src.information.sources.information_source import InformationSource
from src.information.sources.manual_pdfs.manual_pdfs import ManualSourceEngine
from src.information.sources.rapid.medium.medium_searcher import MediumSearchEngine
from src.information.sources.rapid.news.google_news_searcher import GoogleNewsInformationEngine
from src.information.sources.rapid.youtube.retriever import YoutubeTranscriptRetriever
import src.core.utils.functions as F

FILE = os.path.basename(__file__)
logger = F.get_logger(dump_to=FILE)


class ContentSearchEngineProvider:
    """Provides a content search engine. This is just a class that returns a search
     engine for a given information source, just for abstraction purposes"""

    @classmethod
    def get_content_search_engine(cls, information_source):
        """Get a content search engine for the information source."""
        logger.info("Getting content search engine for %s", information_source)
        if information_source == InformationSource.ARXIV:
            return ArxivSearchEngine(information_source)
        elif information_source == InformationSource.MEDIUM:
            return MediumSearchEngine(information_source)
        elif information_source == InformationSource.GOOGLE_NEWS:
            return GoogleNewsInformationEngine(information_source)
        elif information_source == InformationSource.MANUAL:
            return ManualSourceEngine(information_source)
        elif information_source == InformationSource.YOUTUBE:
            return YoutubeTranscriptRetriever(information_source)
        else:
            raise ValueError(f"Information source {information_source} is not supported.")
