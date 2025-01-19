import threading
import requests
from bs4 import BeautifulSoup

from src.core.utils.logging import ServiceLogger
from src.information.sources.base import (
    requires_valid_period,
    InformationSource,
)
from src.information.sources.rapid.base import RapidSource
import src.core.utils.functions as F


class GoogleNewsInformationEngine(RapidSource):
    """Searches for content in the information source."""

    def __init__(self):
        super().__init__(ServiceLogger(__name__))
        self.information_source = InformationSource.GOOGLE_NEWS

    def get_text(self, url):
        """Get the text given a Google News URL. It uses Beautiful Soup to extract the text from the HTML."""
        article_content = ""
        try:
            response = requests.get(url, timeout=self.request_timeout)
            response.raise_for_status()
            self.logger.info("Extracting content from %s", url)

            soup = BeautifulSoup(response.text, "html.parser")

            article_content = soup.get_text(strip=True)
            self.logger.info("Extracted content from %s", url)
        except Exception as e:
            self.logger.error(e)
        finally:
            return article_content

    def process_topic(
        self, results, save_callback=None, stop_event: threading.Event = None
    ):
        for result in results:

            if stop_event and stop_event.is_set():
                self.logger.info(
                    "Stop event called in the middle of procesing the results of a topic"
                )
                break

            result["summary"] = result.pop("body", "")
            result["link"] = result.pop("url", "")
            result["content"] = self.get_text(result["link"])
            result["information_source"] = self.information_source.value

            if result.get("image", None):
                try:
                    result["image"] = F.get_base64_from_url(result.pop("image"))
                except Exception as ex:
                    self.logger.error(f"Error setting image: {ex}")

            if save_callback:
                self.save_if_valid(save_callback, result)

    @requires_valid_period
    def search(
        self, save_callback=None, stop_event: threading.Event = None
    ) -> list:
        """
        Search for content in the information source.
        This method generates a dictionary with Google News results for each topic.

        :param stop_event: Optional thread event to trigger graceful termination
        :param save_callback: Callback function that receives the material to save
        """

        self.logger.info("Searching for content in %s", self.information_source)

        all_results = []
        for topic in self.topics:

            if stop_event and stop_event.is_set():
                self.logger.info(
                    "Stop event called in the middle of procesing the topics"
                )
                break

            payload = {
                "text": topic,
                "region": "wt-wt",
                "max_results": self.max_results,
            }
            try:
                response = self.execute_rapid_request(self.url, payload=payload)
                results = response.json().get("news", [])
                self.logger.info(
                    "Found %s results for topic %s", len(results), topic
                )
                self.process_topic(results)
                all_results.extend(results)
            except Exception as e:
                self.logger.error(e)

        return all_results
