import datetime
import os
import re
import xml.etree.ElementTree as ET

import requests

from src.core.pdf.extractor import PDFExtractor
from src.core.pdf.provider import PDFExtractorProvider
from src.information.sources.information_source import ContentSearchEngine, requires_valid_period
from src.llm.retrieval.provider import DocumentRetrieverProvider
from .constants import (
    ARXIV_API_URL,
    MAX_RESULTS, MINIMUM_LENGTH, PARAGRAPH_MIN_LENGTH,
    DEFAULT_PERIOD, ARXIV_TOPICS
)
import src.core.utils.functions as F

FILE = os.path.basename(__file__)
logger = F.get_logger(dump_to=FILE)


def extract_from_xmls(xml):
    """
    Extract the document information from the xml.
    :param xml:
    :return:
    """
    logger.info("Extracting from xml")
    root = ET.fromstring(xml)
    namespace = "{" + root.tag.split('}')[0][1:] + "}"
    entries = root.findall(f".//{namespace}entry")
    arxivs = []
    for entry in entries:
        entry_id = entry.find(f"{namespace}id").text
        entry_updated = entry.find(f"{namespace}updated").text
        entry_published = entry.find(f"{namespace}published").text
        entry_title = entry.find(f"{namespace}title").text
        entry_summary = entry.find(f"{namespace}summary").text
        authors = list(map(lambda x: x.find(f".//{namespace}name").text, entry.findall(f".//{namespace}author")))
        link = entry.find(f"{namespace}id").text
        arxivs.append({
            "id": entry_id,
            "updated": entry_updated,
            "published": entry_published,
            "title": entry_title,
            "summary": entry_summary,
            "authors": authors,
            "information_source": "arxiv",
            "link": link
        })
        logger.info("Extracted %s", entry_title)
    return arxivs


class ArxivSearchEngine(ContentSearchEngine):
    """
    Searches for content in Arxiv. Arxiv makes papaer metadata available through an API as xml, and then
    we can download the pdf and extract the content.
    """

    def __init__(self, information_source):
        """Initialize the searcher with the information source."""
        self.max_results = MAX_RESULTS
        self.minimum_length = MINIMUM_LENGTH
        self.paragraph_min_length = PARAGRAPH_MIN_LENGTH
        self.period = DEFAULT_PERIOD
        self.pdf_extractor_provider = None
        self.provider = None
        self.url = ARXIV_API_URL
        super().__init__(information_source)

        # These are Topic IDs from arxiv. They are used to select the topics we want to search for.
        self.topics = ARXIV_TOPICS

    def filter(self, content):
        """
        Filter the content. It needs to be implemented by the child class, but it is not used in this class.
        :param content:  content to be filtered
        :return:
        """
        return content

    @requires_valid_period
    def search(self, save_callback=None) -> list:
        """
        Search for the query in the information source. We search by topic and by date, and sort by relevance, including
        only a maxium of results from last week
        :param save_callback:
        :return:
        """
        logger.info("Searching for content in %s", self.information_source)
        categories = "(" + "+OR+".join(self.topics) + ")"
        to_date = datetime.datetime.now()
        from_date = to_date - datetime.timedelta(days=self.period)
        last_updated = f"lastUpdatedDate:[{from_date.strftime('%Y%m%d%H%M')}+TO+{to_date.strftime('%Y%m%d%H%M')}]"
        max_results = f"max_results={self.max_results}"
        sortby = "sortBy=relevance"
        url = f"{self.url}query?search_query={categories}+AND+{last_updated}&{sortby}&{max_results}"
        try:
            response = requests.get(url)
            arxivs = extract_from_xmls(response.text)
            results = []
            for arxiv in arxivs:
                arxiv = self.extract_pdf_info(arxiv)
                results.append(arxiv)
                if save_callback:
                    self.save_if_valid(save_callback, arxiv)
            return results
        except Exception as e:
            logger.error(e)
            return []

    def save_if_valid(self, save, result):
        """
        Save the result if it is valid.
        :param save:  save callback
        :param result:  result to be saved
        :return:
        """
        if len(result.get("content", "")) > self.minimum_length and result.get("title", "") != "":
            save(result)

    def preprocess(self, arxiv):
        """
        Preprocess the text. It removes special characters and makes it lower case.
        :param arxiv:  arxiv content to be preprocessed
        :return:
        """
        text = re.sub(r'[^a-zA-Z\s.,!?\'"]', '', arxiv)
        text = text.lower()
        text = text.strip()

        return text

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

    def extract_pdf_info(self, arxiv):
        """Extract content from PDF and process it using the document retriever.
        :param arxiv: arxiv dictionary
        """
        assert self.provider is not None, "Document Retrieval Provider must be specified beforehand"
        res = ""
        try:
            logger.info("Extracting pdf info")
            url = arxiv["link"].replace("abs", "pdf") + ".pdf"
            response = requests.get(url)
            extractor = PDFExtractorProvider.build(self.pdf_extractor_provider)
            text = extractor.extract(response.content)

            title = arxiv["title"]
            with DocumentRetrieverProvider.get_document_retriever_provider(self.provider,
                                                                           title) as provider:
                important_paragraphs = provider.search([text])
                res = "\n".join(important_paragraphs)
                arxiv["content"] = res
                arxiv["information_source"] = self.information_source.value
        except Exception as e:
            logger.error(e)
            arxiv = {}
        finally:
            return arxiv
