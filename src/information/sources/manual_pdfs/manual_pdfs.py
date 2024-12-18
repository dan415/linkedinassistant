import os
import re
import tempfile
from typing import AnyStr

from src.core.b2.b2_handler import B2Handler
from src.core.pdf.provider import PDFExtractorProvider
from src.information.sources.information_source import ContentSearchEngine, requires_valid_period
from src.llm.retrieval.provider import DocumentRetrieverProvider
from src.core.pdf.extractor import PDFExtractor
import src.core.utils.functions as F

FILE = os.path.basename(__file__)
logger = F.get_logger(dump_to=FILE)


class ManualSourceEngine(ContentSearchEngine):
    """
    Searches for content in B2 folders.
    It will check for updates on the input folder every once in a while, process the PDFs,
    and move them to the output folder.

    For PDFs I am using Adobe API, which has a limit of requests on free tier, so need to be careful.
    However, It is the best one I have access to. Azure Document Intelligence works fine as well.
    """

    def __init__(self, information_source):
        """Initialize the searcher with the information source."""
        super().__init__(information_source)
        self.minimum_length = 50
        self.paragraph_min_length = 10
        self.provider = None
        self.pdf_extractor_provider = None
        self.input_directory = "/Information/Sources/Manual/Input"
        self.output_directory = "/Information/Sources/Manual/Output"
        self.pdf_manager = B2Handler()
        self.reload_config()

    @requires_valid_period
    def search(self, save_callback=None) -> list:
        """Search for the query in the information source."""
        logger.info("Searching for content in %s", self.information_source)
        res = []
        try:
            # Get PDFs from B2 input folder
            if not self.pdf_manager.authenticate():
                logger.error("Failed to authenticate with B2")
                return res

            files = self.pdf_manager.list_folder_contents(self.input_directory)
            pdfs = [f for f in files if isinstance(f, dict) and f.get('name', '').lower().endswith('.pdf')]

            for pdf in pdfs:
                # Download and process each PDF
                pdf_content = self.get_pdf_content(pdf['name'])
                if pdf_content:
                    extracted_content = self.extract_pdf_info(pdf_content)
                    if extracted_content:
                        res.append(extracted_content)
                        if save_callback:
                            self.save_if_valid(save_callback, extracted_content)
                    # Move processed PDF to output folder
                    source_path = f"{self.input_directory}/{pdf['name']}"
                    dest_path = f"{self.output_directory}/{pdf['name']}"
                    self.pdf_manager.move_file(source_path, dest_path)

        except Exception as e:
            logger.error(f"Error in search: {e}")
        finally:
            logger.info("Content found: %s", res)
            return res

    def get_pdf_content(self, filename: str) -> AnyStr | None:
        """
        Download PDF content directly from B2.

        Args:
            filename: Name of the PDF file in B2

        Returns:
            bytes: PDF content if successful, None otherwise
        """
        logger.info(f"Getting content for PDF: {filename}")
        try:
            # Download the file to a temporary location
            with tempfile.NamedTemporaryFile(suffix=f".{filename}") as f:
                if self.pdf_manager.download_pdf(f"{self.input_directory}/{filename}", f.name):
                    # Read the content
                    f.seek(0)
                    content = f.read()
                    return content
            return None
        except Exception as e:
            logger.error(f"Error getting PDF content: {e}")
            return None

    def extract_pdf_info(self, pdf_content: bytes):
        """
        Extract the PDF info and content using Document Retriever Provider.

        Args:
            pdf_content: Raw PDF bytes

        Returns:
            dict: Extracted information including title and content
        """
        assert self.provider is not None, "Document Retrieval Provider must be specified beforehand"
        logger.info("Extracting pdf info")
        try:
            extractor = PDFExtractorProvider.build(self.pdf_extractor_provider)
            text = extractor.extract(pdf_content)

            # Create provider with temporary title first
            with DocumentRetrieverProvider.get_document_retriever_provider(self.provider,
                                                                           "temp").update_from_config() as provider:
                extracted_title = provider.extract_title(text)
                important_paragraphs = provider.search([text])

            res = {
                "title": extracted_title,
                "information_source": self.information_source.value,
                "content": important_paragraphs
            }
        except Exception as e:
            logger.error(f"Error extracting PDF info: {e}")
            res = {}
        return res

    def filter(self, content):
        """Filter the content (not used in this class)."""
        return content

    def clean_title(self, title):
        """Clean the title by removing special characters and making it lowercase."""
        title = title.lower().strip()
        title = re.sub(r'[^a-zA-Z0-9_]', '_', title)
        title = title[0:min(len(title), 90)]
        return title

    def save_if_valid(self, save, result):
        """Save the result if it meets minimum length requirements."""
        if len(result.get("content", "")) > self.minimum_length and result.get("title", "") != "":
            save(result)
