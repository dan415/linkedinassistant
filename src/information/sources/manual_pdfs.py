import threading
from src.core.constants import FileManagedFolders
from src.core.file_manager.b2 import B2Handler
from src.core.pdf.provider import PDFExtractorProvider
from src.core.utils.logging import ServiceLogger
from src.information.sources.base import (
    ContentSearchEngine,
    requires_valid_period,
    InformationSource, stateful,
)
from src.core.llm.retrieval.provider import DocumentRetrieverProvider


class ManualSourceEngine(ContentSearchEngine):
    """
    Searches for content in B2 folders.
    It will check for updates on the input folder every once in a while, process the PDFs,
    and move them to the output folder.

    For PDFs I am using Adobe API, which has a limit of requests on free tier, so need to be careful.
    However, It is the best one I have access to. Azure Document Intelligence works fine as well.
    """

    def __init__(self):
        """Initialize the searcher with the information source."""
        super().__init__(ServiceLogger(__name__))
        self.provider = None  # Document retrieval provider instance
        self.pdf_extractor_provider = None  # PDF extraction provider instance
        self.information_source = InformationSource.MANUAL
        self.pdf_manager = (
            B2Handler()
        )  # Manager for interacting with the B2 storage

    @requires_valid_period
    @stateful
    def search(
        self, save_callback=None, stop_event: threading.Event = None
    ) -> list:
        """Search for the query in the information source."""
        self.logger.info("Searching for content in %s", self.information_source)
        res = []
        try:
            # List all files in the input directory
            files = self.pdf_manager.list_folder_contents(
                FileManagedFolders.INPUT_PDF_FOLDER
            )
            pdfs = [
                f
                for f in files
                if isinstance(f, dict)
                and f.get("name", "").lower().endswith(".pdf")
            ]

            for pdf in pdfs:

                if stop_event and stop_event.is_set():
                    self.logger.info(
                        "Stop event called in the middle of procesing a pdf"
                    )
                    break

                pdf_content = self.pdf_manager.download(
                    f"{FileManagedFolders.INPUT_PDF_FOLDER}/{pdf['name']}"
                )
                if pdf_content:
                    extracted_content = self.extract_pdf_info(pdf_content)
                    if extracted_content:
                        res.append(extracted_content)
                        if save_callback:
                            self.save_if_valid(
                                save_callback, extracted_content
                            )  # Save valid content using the callback
                    # Move processed PDF to the output folder
                    source_path = (
                        f"{FileManagedFolders.INPUT_PDF_FOLDER}/{pdf['name']}"
                    )
                    dest_path = (
                        f"{FileManagedFolders.OUTPUT_PDF_FOLDER}/{pdf['name']}"
                    )
                    try:
                        self.pdf_manager.move_file(source_path, dest_path)
                    except Exception as e:
                        self.logger.error(
                            f"Failed to move file {source_path} to {dest_path}: {e}"
                        )
                else:
                    self.logger.warning(f"Could not download pdf {pdf['name']}")
        except Exception as e:
            self.logger.error(f"Error in search: {e}")
        finally:
            self.logger.info("Content found: %s", res)
            return res

    def extract_pdf_info(self, pdf_content: bytes):
        """
        Extract the PDF info and content using Document Retriever Provider.

        Args:
            pdf_content: Raw PDF bytes

        Returns:
            dict: Extracted information including title and content
        """
        if self.provider is None:
            raise ValueError(
                "Document Retrieval Provider must be specified beforehand"
            )
        self.logger.info("Extracting pdf info")
        try:
            # Build the PDF extractor instance
            extractor = PDFExtractorProvider.build(self.pdf_extractor_provider)
            text = extractor.extract(
                pdf_content
            )  # Extract text from the PDF content

            # Use the provider to retrieve structured information from the text
            with DocumentRetrieverProvider.get_document_retriever_provider(
                self.provider, logger=self.logger
            ) as provider:
                important_paragraphs, extracted_title = provider.search(
                    [text]
                )  # Search for relevant paragraphs

            res = {
                "title": extracted_title,  # Extracted title of the document
                "information_source": self.information_source.value,  # Source information
                "content": important_paragraphs,  # Relevant content paragraphs,
                "extracted_images": extractor.extracted_images,  # Extracted raw images if used docling engine
            }
        except Exception as e:
            self.logger.error(f"Error extracting PDF info: {e}")
            res = {}
        return res
