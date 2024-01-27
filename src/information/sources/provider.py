import logging
import os

from src.information.sources.arxiv.arxiv_searcher import ArxivSearchEngine
from src.information.sources.information_source import InformationSource
from src.information.sources.manual_pdfs.manual_pdfs import ManualSourceEngine
from src.information.sources.rapid.medium.medium_searcher import MediumSearchEngine
from src.information.sources.rapid.news.google_news_searcher import GoogleNewsInformationEngine
from src.utils.log_handler import TruncateByTimeHandler

PWD = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.abspath(os.path.join(PWD, '..', "..", ".."))
LOGGING_DIR = os.path.join(PROJECT_DIR, "logs") if os.name != 'nt' else os.path.join(r"C:\\", "ProgramData", "linkedin_assistant", "logs")
FILE = os.path.basename(__file__)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = TruncateByTimeHandler(filename=os.path.join(LOGGING_DIR, f'{FILE}.log'), encoding='utf-8', mode='a+')
handler.setLevel(logging.DEBUG)
handler.setFormatter(logging.Formatter(f'%(asctime)s - %(name)s - {__name__} - %(levelname)s - %(message)s'))
logger.addHandler(handler)
config_dir = os.path.join(r"C:\\", "ProgramData", "linkedin_assistant", "information", "sources", "config.json") if os.name == 'nt' else os.path.join(PWD, "config.json")

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
        else:
            raise ValueError(f"Information source {information_source} is not supported.")
