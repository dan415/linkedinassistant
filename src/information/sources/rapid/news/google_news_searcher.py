import requests
import os
from bs4 import BeautifulSoup
from src.information.sources.information_source import requires_valid_period
from src.information.sources.rapid.manager import RapidSource
import src.core.utils.functions as F

FILE = os.path.basename(__file__)
logger = F.get_logger(dump_to=FILE)


class GoogleNewsInformationEngine(RapidSource):
    """Searches for content in the information source."""

    def __init__(self, information_source):
        """Initialize the searcher with the information source."""

        self.topics = []
        self.limit = 1000
        self.max_results = 25
        self.period = 30
        self.url = "https://google-api31.p.rapidapi.com/"
        self.host = "google-api31.p.rapidapi.com"
        self.minimum_length = 50
        super().__init__(information_source)

    def get_text(self, url):
        """Get the text given a Google News URL. It uses beautiful soup to extract the text from the HTML"""
        article_content = ""
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            logger.info("Extracting content from %s", url)
            soup = BeautifulSoup(response.text, 'html.parser')

            article_content = soup.get_text(strip=True)
            logger.info("Extracted content from %s", url)
        except requests.exceptions.RequestException as e:
            logger.error(e)
        finally:
            return article_content

    @requires_valid_period
    def search(self, save_callback=None) -> list:
        """Search for content in the information source. Never mind the debug flag, it is just for testing purposes.
        It tries to generate a dictionary with google news for each topic.

        """

        logger.info("Searching for content in %s", self.information_source)
        headers = {
            'x-rapidapi-key': self.get_api_key(),
            'x-rapidapi-host': self.host
        }
        all_results = []
        for topic in self.topics:
            payload = {
                "text": topic,
                "region": "wt-wt",
                "max_results": self.max_results
            }
            try:
                response = requests.post(self.url, json=payload, headers=headers)
                results = response.json().get("news", [])
                logger.info("Found %s results for topic %s", len(results), topic)
                for result in results:
                    result['summary'] = result.pop('body')
                    result["link"] = result.pop("url")
                    result["content"] = self.get_text(result["link"])
                    result["information_source"] = self.information_source.value
                    if save_callback:
                        self.save_if_valid(save_callback, result)
                all_results.extend(results)
            except Exception as e:
                logger.error(e)
        return all_results

    def save_if_valid(self, save, result):
        """
        Saves the result if it is valid, some results might not have content, so they are not valid
        :param save:  callback to save the result
        :param result:  result to be saved

        """
        if len(result.get("content", "")) > self.minimum_length:
            save(result)

    def filter(self, news: list) -> list:
        """Filter the content. It filters the content by length, it only keeps the content that is longer than the minimum length"""
        return list(filter(lambda x: len(x.get("content", "")) > self.minimum_length, news))
