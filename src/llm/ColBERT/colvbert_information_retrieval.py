import json
import logging
import os

from src.llm.ColBERT.colbert import Indexer, Searcher
from src.llm.ColBERT.colbert.infra import Run, RunConfig, ColBERTConfig
from src.utils.log_handler import TruncateByTimeHandler


PWD = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.abspath(os.path.join(PWD, '..', "..", ".."))
LOGGING_DIR = os.path.join(PROJECT_DIR, "logs") if os.name != 'nt' else os.path.join(r"C:\\", "ProgramData", "linkedin_assistant", "logs")
FILE = os.path.basename(__file__)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = TruncateByTimeHandler(filename=os.path.join(LOGGING_DIR, f'{FILE}.log'), encoding='utf-8', mode='a+')
handler.setLevel(logging.INFO)
handler.setFormatter(logging.Formatter(f'%(asctime)s - %(name)s - {__name__} - %(levelname)s - %(message)s'))
logger.addHandler(handler)
config_dir = os.path.join(r"C:\\", "ProgramData", "linkedin_assistant", "llm",  "ColBERT", "config.json") if os.name == 'nt' else os.path.join(PWD, "config.json")

class ColbertDocumentChapterRetrieval:
    """
    This class is used to retrieve the most important paragraphs from a document. It uses the ColBERT model to index
    the paragraphs and then it uses the ColBERT model to search for the most important paragraphs.
    """

    def __init__(self,
                 document_name,
                 max_total=10,
                 kmeans_iters=10,
                 k=10,
                 max_per_query=2,
                 document_max_len=300,
                 queries=None
                 ):
        if queries is None:
            queries = [
                'What is the document about?',
                'How does it work?',
                'What is the main idea?',
                'What is innovative about it?',
                'What are the conclusions?',
            ]
        self.n_bits = 2
        self.kmeans_iters = kmeans_iters
        self.k = k
        self.max_per_query = max_per_query
        self.max_total = max_total
        self.context = None
        self.checkpoint = 'colbert-ir/colbertv2.0'
        self.index_name = f'{document_name}.{self.n_bits}bits'
        self.queries = queries
        self.docs_max_len = document_max_len
        self.indexer = None

    def update_from_config(self, config=None):

        if config is None:
            config = config_dir

        with open(config) as f:
            config = json.load(f)

        for key in config.keys():
            setattr(self, key, config[key])

        return self

    def __enter__(self):
        """
        Initialize the ColBERT model context
        :return:
        """
        logger.info("Initializing ColBERT")
        self.context = Run().context(RunConfig(nranks=1)).__enter__()
        return self

    def index_paragraphs(self, paragraphs):
        """
        Index the paragraphs. The searches will be done by paragraph
        :param paragraphs:
        :return:
        """
        logger.info("Indexing paragraphs")
        config = ColBERTConfig(doc_maxlen=self.docs_max_len, nbits=self.n_bits, kmeans_niters=self.kmeans_iters)
        self.indexer = Indexer(checkpoint=self.checkpoint, config=config)
        logger.info("Indexing paragraphs")
        self.indexer.index(name=self.index_name, collection=paragraphs, overwrite=True)

    def search(self, paragraphs, queries=None):
        """
        Search for the most important paragraphs after they had been indexed Various queries are used, and the paragraphs
        are ranked by the number of queries they appear in, and then by the score of the query. The paragraphs are also
        sorted by the order they appear in the document.
        :param paragraphs:
        :param queries:
        :return:
        """
        logger.info("Searching paragraphs")
        if queries:
            self.queries = queries
        searcher = Searcher(index=self.index_name, collection=paragraphs)
        important_paragraphs = {}
        for query in self.queries:
            logger.info("Searching for query: %s", query)
            results = searcher.search(query, k=self.k)
            for passage_id, passage_rank, passage_score in zip(*results):
                if passage_id in important_paragraphs.keys():
                    important_paragraphs[passage_id]["count"] += 1
                    if passage_score > important_paragraphs[passage_id]["score"]:
                        important_paragraphs[passage_id]["score"] = passage_score
                    if passage_rank < important_paragraphs[passage_id]["rank"]:
                        important_paragraphs[passage_id]["rank"] = passage_rank
                else:
                    important_paragraphs[passage_id] = {"count": 1, "score": passage_score,
                                                        "order": passage_id,
                                                        "text": searcher.collection[passage_id], "rank": passage_rank}
        important_paragraphs = list(
            map(lambda x: x["text"],
                sorted(
                    sorted(important_paragraphs.values(),
                           key=lambda x: (x["rank"], -x["count"], -x["score"])
                           ), key=lambda x: x["order"]
                )
                )
        )

        logger.info("Found %d paragraphs", len(important_paragraphs))
        important_paragraphs = important_paragraphs[:self.max_total]
        return important_paragraphs

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Erase the index
        :param exc_type:
        :param exc_val:
        :param exc_tb:
        :return:
        """
        if self.indexer is not None:
            logger.info("Erasing index")
            self.indexer.erase()
        if self.context:
            self.context.__exit__(exc_type, exc_val, exc_tb)
