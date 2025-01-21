import datetime
import threading
import xml.etree.ElementTree as ET
import requests
from src.core.pdf.provider import PDFExtractorProvider
from src.core.utils.logging import ServiceLogger
from src.information.sources.base import (
    ContentSearchEngine,
    require_valid_run_time,
    InformationSource,
    stateful,
)
from src.core.llm.retrieval.provider import DocumentRetrieverProvider


class ArxivSearchEngine(ContentSearchEngine):
    """
    Searches for content in Arxiv. Arxiv makes paper metadata available through an API as XML, and then
    we can download the PDF and extract the content.
    """

    _REQUEST_TIMEOUT = 10  # Timeout for all HTTP requests

    def __init__(self):
        super().__init__(ServiceLogger(__name__))
        """Initialize the searcher with the information source."""
        self.max_results = (
            None  # Maximum number of results to fetch from the query
        )
        self.pdf_extractor_provider = (
            None  # Provider for extracting PDF content
        )
        self.provider = None  # Provider for document retrieval
        self.topics = []  # List of topics to search in Arxiv
        self.url = None  # Base URL for Arxiv API
        self.information_source = InformationSource.ARXIV

    def extract_from_xmls(self, xml):
        """
        Extract the document information from the XML response.
        Parses the XML structure to retrieve metadata like title, authors, and summary.
        :param xml: XML string from the Arxiv API response
        :return: List of extracted metadata dictionaries
        """
        self.logger.info("Extracting from XML")
        try:
            root = ET.fromstring(xml)  # Parse the XML response
            namespace = "{" + root.tag.split("}")[0][1:] + "}"
            entries = root.findall(
                f".//{namespace}entry"
            )  # Find all entry nodes
            arxivs = []
            for entry in entries:
                # Extract metadata for each entry
                entry_id = entry.find(f"{namespace}id").text
                entry_updated = entry.find(f"{namespace}updated").text
                entry_published = entry.find(f"{namespace}published").text
                entry_title = entry.find(f"{namespace}title").text
                entry_summary = entry.find(f"{namespace}summary").text
                # Extract authors as a list
                authors = list(
                    map(
                        lambda x: x.find(f".//{namespace}name").text,
                        entry.findall(f".//{namespace}author"),
                    )
                )
                link = entry.find(f"{namespace}id").text
                # Append metadata to the result list
                arxivs.append(
                    {
                        "id": entry_id,
                        "updated": entry_updated,
                        "published": entry_published,
                        "title": entry_title,
                        "summary": entry_summary,
                        "authors": authors,
                        "information_source": "arxiv",
                        "link": link,
                    }
                )
                self.logger.info("Extracted %s", entry_title)
            return arxivs
        except ET.ParseError as e:
            self.logger.error(
                "Error parsing XML: %s", e
            )  # Log XML parsing errors
            return []

    def _process_arxivs(self, stop_event, arxivs, save_callback=None):
        """
        Process the extracted Arxiv metadata and extract content from the PDFs.

        :param stop_event: Optional thread event to trigger graceful termination
        :param arxivs: List of extracted Arxiv metadata
        :param save_callback: Optional callback to save valid results
        :return: List of processed Arxiv metadata
        """
        results = []
        for arxiv in arxivs:
            if stop_event and stop_event.is_set():
                self.logger.info(
                    "Stop event called in the middle of procesing a pdf"
                )
                break

            arxiv = self.process_pdf(
                arxiv
            )  # Process the PDF content for each result
            if arxiv:
                results.append(arxiv)
                if save_callback:
                    self.save_if_valid(
                        save_callback, arxiv
                    )  # Save valid results using the callback
        return results

    @require_valid_run_time
    @stateful
    def search(
        self, save_callback=None, stop_event: threading.Event = None
    ) -> list:
        """
        Search for the query in the information source.
        Constructs a query URL with the specified topics and time period and fetches results sorted by relevance.
        :param stop_event: Optional thread event to trigger graceful termination
        :param save_callback: Optional callback to save valid results
        :return: List of search results with metadata and processed content
        """
        self.logger.info("Searching for content in %s", self.information_source)
        categories = (
            "(" + "+OR+".join(self.topics) + ")"
        )  # Build category query
        to_date = datetime.datetime.now()
        from_date = to_date - datetime.timedelta(
            days=self.period
        )  # Calculate the date range
        last_updated = f"lastUpdatedDate:[{from_date.strftime('%Y%m%d%H%M')}+TO+{to_date.strftime('%Y%m%d%H%M')}]"
        max_results = f"max_results={self.max_results}"  # Limit results
        sortby = "sortBy=relevance"  # Sort results by relevance
        url = f"{self.url}query?search_query={categories}+AND+{last_updated}&{sortby}&{max_results}"
        try:
            response = requests.get(
                url, timeout=self._REQUEST_TIMEOUT
            )  # Perform the HTTP GET request
            if response.status_code != 200:
                self.logger.error(
                    "Failed to fetch data from URL: %s, Status Code: %s",
                    url,
                    response.status_code,
                )
                return []
            arxivs = self.extract_from_xmls(
                response.text
            )  # Extract metadata from XML response
            return self._process_arxivs(
                stop_event, arxivs, save_callback
            )  # Process the extracted metadata
        except Exception as e:
            self.logger.error("Error during search: %s. URL: %s", e, url)
            return []

    def process_pdf(self, arxiv):
        """
        Extract content from the PDF file and process it using the document retriever.
        :param arxiv: Dictionary containing metadata for an Arxiv entry
        :return: Updated dictionary with extracted content or None on failure
        """
        assert (
            self.provider is not None
        ), "Document Retrieval Provider must be specified beforehand"
        self.logger.info("Extracting PDF info")
        url = arxiv["link"].replace("abs", "pdf") + ".pdf"  # Construct PDF URL
        try:
            response = requests.get(
                url, timeout=self._REQUEST_TIMEOUT
            )  # Fetch the PDF content
            if response.status_code != 200:
                self.logger.error(
                    "Failed to fetch PDF: %s, Status Code: %s",
                    url,
                    response.status_code,
                )
                return None
            extractor = PDFExtractorProvider.build(
                self.pdf_extractor_provider
            )  # Initialize PDF extractor
            text = extractor.extract(
                response.content
            )  # Extract text from the PDF

            title = arxiv["title"]  # Use the title for document retrieval
            with DocumentRetrieverProvider.get_document_retriever_provider(
                self.provider, document_name=title, logger=self.logger
            ) as provider:
                important_paragraphs, _ = provider.search(
                    [text]
                )  # Retrieve important paragraphs
                if important_paragraphs:
                    res = "\n".join(
                        important_paragraphs
                    )  # Join paragraphs into a single string
                    arxiv["content"] = (
                        res  # Add the extracted content to the metadata
                    )
                    arxiv["information_source"] = self.information_source.value
                    arxiv[
                        "extracted_images"
                    ]: (
                        extractor.extracted_images
                    )  # Extracted raw images if used docling engine

                else:
                    self.logger.warning(
                        "No important paragraphs found for title: %s", title
                    )
        except Exception as e:
            self.logger.error(
                "Error during PDF extraction: %s. URL: %s", e, url
            )
            arxiv = None
        finally:
            return arxiv
