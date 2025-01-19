import threading
from src.core.utils.logging import ServiceLogger
from src.information.sources.base import (
    requires_valid_period,
    InformationSource,
)
from src.information.sources.rapid.base import RapidSource


class MediumSearchEngine(RapidSource):
    """
    Searches for content in Medium.
    """

    def __init__(self):
        super().__init__(ServiceLogger(__name__))
        self.information_source = InformationSource.MEDIUM

    def get_author(self, author):
        """
        Get the author name given the author id.
        :param author:  author id
        :return:  author full name
        """
        url = f"{self.url}/user/{author}"

        result = ""
        try:
            response = self.execute_rapid_request(url)
            if response.status_code != 200:
                self.logger.error(response.text)
                return result
            result = response.json().get("fullname", "")
        except Exception as e:
            self.logger.error(e)
            return result
        finally:
            return result

    def get_article_info(self, article):
        """
        Get the article metadata information given the article id.
        :param article:  article id
        :return: article information
        """
        url = f"{self.url}/article/{article}"
        result = {}
        try:
            response = self.execute_rapid_request(url)
            if response.status_code != 200:
                self.logger.error(response.text)
                return result
            tmp_res = response.json()
            result["title"] = tmp_res.get("title", "")
            result["published_at"] = tmp_res.get("published_at", "")
            result["subtitle"] = tmp_res.get("subtitle", "")
            result["author"] = self.get_author(tmp_res.get("author", ""))
            result["url"] = tmp_res.get("url", "")
        except Exception as e:
            self.logger.error(e)
            return result
        finally:
            return result

    def get_article_content(self, article):
        """
        Get the article content given the article id.
        :param article:  article id
        :return:  article content
        """
        url = f"{self.url}/article/{article}/content"
        result = ""
        try:
            response = self.execute_rapid_request(url)
            if response.status_code != 200:
                self.logger.error(response.text)
                return result
            result = response.json().get("content", "")
        except Exception as e:
            self.logger.error(e)
            return result
        finally:
            return result

    def research_topic(self, topic, save_callback=None):
        """
        Research a topic in medium and saves the results if a save callback is provided. It returns the results.
         Note that each call to this method will account for 1 + 3 * the number of results found updates on the counter
        :param topic:
        :param save_callback:
        :return:
        """
        all_results = []
        try:
            url = f"{self.url}/search/articles"
            response = self.execute_rapid_request(url, params={"query": topic})
            results = response.json().get("articles", [])
            self.logger.info(
                "Found %s results for topic %s", len(results), topic
            )
            for result in results:
                article = {}
                article.update(self.get_article_info(result))
                article["content"] = self.get_article_content(result)
                article["information_source"] = self.information_source.value
                all_results.append(article)
                if save_callback:
                    self.save_if_valid(save_callback, article)
        except Exception as e:
            self.logger.error(e)
        finally:
            return all_results

    @requires_valid_period
    def search(
        self, save_callback=None, stop_event: threading.Event = None
    ) -> list:
        """
        Runs the search for each topic. Then returns the results
        :param stop_event: Optional thread event to trigger graceful termination
        :param save_callback: Callback function that receives the material to save
        :return: All processed results in a list
        """
        self.logger.info("Searching for content in %s", self.information_source)
        all_results = []
        for topic in self.topics:

            if stop_event and stop_event.is_set():
                self.logger.info(
                    "Stop event called in the middle of processing a pdf"
                )
                break

            all_results.extend(self.research_topic(topic, save_callback))
        return all_results
