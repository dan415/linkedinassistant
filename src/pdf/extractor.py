import gzip
import io
import json
import logging
import re
import tempfile
import zipfile
import os
from adobe.pdfservices.operation.auth.credentials import Credentials
from adobe.pdfservices.operation.execution_context import ExecutionContext
from adobe.pdfservices.operation.io.file_ref import FileRef
from adobe.pdfservices.operation.pdfops.extract_pdf_operation import ExtractPDFOperation
from adobe.pdfservices.operation.pdfops.options.extractpdf.extract_element_type import ExtractElementType
from adobe.pdfservices.operation.pdfops.options.extractpdf.extract_pdf_options import ExtractPDFOptions

from src.utils.log_handler import TruncateByTimeHandler

PWD = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.abspath(os.path.join(PWD, '..', ".."))
LOGGING_DIR = os.path.join(PROJECT_DIR, "logs") if os.name != 'nt' else os.path.join(r"C:\\", "ProgramData", "linkedin_assistant", "logs")
FILE = os.path.basename(__file__)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = TruncateByTimeHandler(filename=os.path.join(LOGGING_DIR, f'{FILE}.log'), encoding='utf-8', mode='a+')
handler.setLevel(logging.INFO)
handler.setFormatter(logging.Formatter(f'%(asctime)s - %(name)s - {__name__} - %(levelname)s - %(message)s'))
logger.addHandler(handler)
config_dir = os.path.join(r"C:\\", "ProgramData", "linkedin_assistant", "pdf", "config.json") if os.name == 'nt' else os.path.join(PWD, "config.json")

# TODO: Extract tables and maybe images, for this one I need a good model like llava but dont wanna pay replicate xd
def get_chapters_from_json(structured_json, return_title=False):
    """Get the chapters from the structured json. I am basically taking the title paragraphs and bullet points as
    chapters. I am also taking the title of the document as the title of the book.

    :param structured_json:  structured json from the pdf
    :param return_title:  if true, it will return the title of the document
    """
    chapters = []
    title = ""
    document_title_pattern = re.compile(r"//Document/Title$")
    title_pattern = re.compile(r"//Document/H1[\[*\]]*")
    p_pattern = re.compile(r"//Document/P(\[[\d]*\])?(?:/ParagraphSpan(\[\d]*\])?)?$")
    bullet_pattern = re.compile(r"//Document/L*LBody$")
    for element in structured_json["elements"]:
        if document_title_pattern.match(element["Path"]):
            logger.debug(f"Title: {title}")
            title = element["Text"]
        if title_pattern.match(element["Path"]):
            logger.debug(f"Chapter title with path: {element['Path']}")
            chapters.append({"title": element["Text"], "paragraphs": []})
        elif (p_pattern.match(element["Path"]) or bullet_pattern.match(element["Path"])) and len(chapters) > 0:
            logger.debug(f"Paragraph or bullet point with path: {element['Path']}")
            chapters[-1]["paragraphs"].append(element["Text"])

    if return_title:
        return title, chapters
    logger.debug(f"Chapters: {chapters}")
    return chapters


class AdobePDFExtractor:
    """Extracts text from PDF files using Adobe's PDF Library SDK."""

    def __init__(self):
        self.execution_context = None
        self.reload_config()

    def reload_config(self):
        """Reload the configuration."""
        logger.debug("Reloading config")
        with open(config_dir, "r") as f:
            config = json.load(f)
        credentials = Credentials.service_principal_credentials_builder() \
            .with_client_id(config["client_credentials"]["client_id"]) \
            .with_client_secret(config["client_credentials"]["client_secret"]).build()
        self.execution_context = ExecutionContext.create(credentials)

    def extract(self, pdf_bytes, return_title=False):
        """Extracts text from PDF file. It first calls the API with the pdf bytes. The API is going to download
        the results on a file, that I do not want to keep, so I create a TemporaryDirectory and extract the results there.
        Then I read the json that's in the Zip and return the chapters. The Temp dir is discarded so I do not need to
        worry about deleting the files.

        """
        logger.info("Extracting text from PDF file")
        self.reload_config()
        extract_pdf_operation = ExtractPDFOperation.create_new()
        with tempfile.TemporaryDirectory() as tmp_dir:
            with open(os.path.join(tmp_dir, "file.pdf"), "wb") as f:
                f.write(pdf_bytes)
            source = FileRef.create_from_local_file(os.path.join(tmp_dir, "file.pdf"))
            extract_pdf_operation.set_input(source)
            extract_pdf_options: ExtractPDFOptions = ExtractPDFOptions.builder() \
                .with_element_to_extract(ExtractElementType.TEXT) \
                .build()
            extract_pdf_operation.set_options(extract_pdf_options)
            result = extract_pdf_operation.execute(self.execution_context)
            result.save_as(os.path.join(tmp_dir, "result.zip"))
            with zipfile.ZipFile(os.path.join(tmp_dir, "result.zip"), 'r') as zip_ref:
                zip_ref.extractall(tmp_dir)
            with open(os.path.join(tmp_dir, "structuredData.json"), "r") as f:
                structured_json = json.load(f)
            return get_chapters_from_json(structured_json, return_title=return_title)
