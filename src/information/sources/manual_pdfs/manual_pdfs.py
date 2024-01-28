import json
import logging
import os
import re
import shutil
from functools import wraps


from src.information.sources.information_source import ContentSearchEngine, requires_valid_period
from src.llm.ColBERT.colvbert_information_retrieval import ColbertDocumentChapterRetrieval
from src.pdf.extractor import AdobePDFExtractor
from src.utils.log_handler import TruncateByTimeHandler

PWD = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.abspath(os.path.join(PWD, '..', "..", "..", ".."))
LOGGING_DIR = os.path.join(PROJECT_DIR, "logs") if os.name != 'nt' else os.path.join(r"C:\\", "ProgramData", "linkedin_assistant", "logs")
FILE = os.path.basename(__file__)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = TruncateByTimeHandler(filename=os.path.join(LOGGING_DIR, f'{FILE}.log'), encoding='utf-8', mode='a+')
handler.setLevel(logging.INFO)
handler.setFormatter(logging.Formatter(f'%(asctime)s - %(name)s - {__name__} - %(levelname)s - %(message)s'))
logger.addHandler(handler)
config_dir = os.path.join(r"C:\\", "ProgramData", "linkedin_assistant", "information", "sources", "manual_pdfs", "config.json") if os.name == 'nt' else os.path.join(PWD, "config.json")

def stateful(func):
    @wraps(func)
    def update_config(self, *args, **kwargs):
        result = func(self, *args, **kwargs)
        logger.info("Updating config of sources handler.")
        with open(config_dir, "r") as f:
            config = json.load(f)

        for key in config.keys():
            config[key] = getattr(self, key)

        with open(config_dir, "w") as f:
            json.dump(config, f, default=str, indent=4)

        return result

    return update_config


class ManualSourceEngine(ContentSearchEngine):

    """
    Searches for content in a folder specified in config.json.
    It will check for updates on the folder every once in a while, and process the pdf.

    For pdfs I am using Adobe API, which has a limit of requests on free tier, so need to be careful. However, It is the best one I have access
    to. Azure Document Intelligence works fine as well.
    """

    def __init__(self, information_source):
        """Initialize the searcher with the information source."""
        super().__init__(information_source)
        self.pwd = os.path.dirname(os.path.abspath(__file__))
        self.project_dir = os.path.abspath(os.path.join(self.pwd, '..', "..", "..", ".."))
        self.input_directory = os.path.join("res", "manual_pdfs", "input")
        self.output_directory = os.path.join("res", "manual_pdfs", "output")
        self.minimum_length = 50
        self.paragraph_min_length = 10
        self.reload_config(config_dir)

    @requires_valid_period
    def search(self, save_callback=None) -> list:
        """Search for the query in the information source."""
        logger.info("Searching for content in %s", self.information_source)
        res = []
        try:
            pdfs, pdfs_bytes = self.get_pdf_bytes()
            for pdf_info in pdfs_bytes:
                extracted_content = self.extract_pdf_info(pdf_info)
                res.append(extracted_content)
                if save_callback:
                    self.save_if_valid(save_callback, extracted_content)

            self.move_pdfs(pdfs)
        except Exception as e:
            logger.error(e)
        finally:
            logger.info("Content found: %s", res)
            return res

    def filter(self, content):
        """"
        Filter the content. It needs to be implemented by the child class, but it is not used in this class.
        """
        return content

    def clean_title(self, title):
        """
        Clean the title. It removes special characters and makes it lower case.
        :param title:  title to be cleaned
        :return:
        """
        title = title.lower().strip()
        title = re.sub(r'[^a-zA-Z0-9_]', '_', title)
        title = title[0:min(len(title), 90)]
        return title

    def save_if_valid(self, save, result):
        """
        Save the result if it is valid.
        :param save:  save callback
        :param result:  result to be saved
        :return:
        """
        if len(result.get("content", "")) > self.minimum_length and result.get("title", "") != "":
            save(result)

    def get_pdf_bytes(self):
        """
        Get the pdf bytes from the input directory, it iterates all the pdfs in the directory.
        :return:  pdfs names and pdfs bytes
        """
        logger.info("Getting pdf bytes")
        pdfs = []
        pdfs_bytes = []
        for file in os.listdir(os.path.join(os.path.abspath("/"), *self.input_directory.split("/"))):
            if file.endswith(".pdf"):
                with open(os.path.join(os.path.abspath("/"), *self.input_directory.split("/"), file), "rb") as f:
                    pdfs_bytes.append(f.read())
                pdfs.append(file)
        logger.info(f"Pdf bytes retrieved for {pdfs}")
        return pdfs, pdfs_bytes

    def move_pdfs(self, pdfs):
        """Move the pdfs from input directory to the output directory."""
        logger.info("Moving pdfs")
        for pdf in pdfs:
            logger.info(f"Moving {pdf}")
            shutil.move(os.path.join(os.path.abspath("/"), *self.input_directory.split("/"), pdf), os.path.join(os.path.abspath("/"), self.output_directory, pdf))

    def preprocess(self, pdf):
        """
        Preprocess the pdf, removing non alphanumeric characters, and lowercasing the text.
        :param pdf:
        :return:
        """
        text = re.sub(r'[^a-zA-Z\s.,!?\'"]', '', pdf)
        text = text.lower()
        text = text.strip()

        return text
    def extract_pdf_info(self, pdf):
        """
        Extract the pdf info, title and content.
        Then it uses Colbert's Query-Document model in order to retrieve the most important paragraphs. This is the stuff that will actually get included
        in the publication.
        :param pdf:
        :return:
        """
        logger.info("Extracting pdf info")
        try:
            extractor = AdobePDFExtractor()
            title, chapters = extractor.extract(pdf, return_title=True)
            res = {"title": title}
            paragraphs = []
            for chapter in chapters:
                paragraphs.extend(chapter["paragraphs"])

            paragraphs = list(map(lambda x: self.preprocess(x), filter(lambda x: len(x) > self.paragraph_min_length, paragraphs)))

            title = self.clean_title(title)
            with ColbertDocumentChapterRetrieval(title).update_from_config() as colbert:
                colbert.index_paragraphs(paragraphs)
                important_paragraphs = colbert.search(paragraphs)
            res["information_source"] = self.information_source
            res["content"] = important_paragraphs
        except Exception as e:
            logger.error(e)
            res = {}
        return res
