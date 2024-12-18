import os
import requests

from src.core.constants import SecretKeys
from src.information.sources.information_source import requires_valid_period
from src.information.sources.rapid.manager import RapidSource
import src.core.utils.functions as F

FILE = os.path.basename(__file__)
logger = F.get_logger(dump_to=FILE)


class MediumSearchEngine(RapidSource):

    """
    Searches for content in Medium.
    """

    def __init__(self, information_source):
        """Initialize the searcher with the information source."""
        self.max_results = 25
        self.url = ""
        self.information_source = information_source
        self.topics = []
        self.minimum_length = 50
        self.limit = 1000
        self.max_results = 25
        self.period = 30
        self.host = ""
        super().__init__(information_source)

    @requires_valid_period
    def get_author(self, author):
        """
        Get the author name given the author id.
        :param author:  author id
        :return:  author full name
        """
        url = f'{self.url}/user/{author}'
        headers = {
            'x-rapidapi-key': self.get_api_key(),
            'x-rapidapi-host': self.host
        }
        result = ""
        try:
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code != 200:
                logger.error(response.text)
                return result
            result = response.json().get("fullname", "")
        except Exception as e:
            logger.error(e)
            return result
        finally:
            return result

    @requires_valid_period
    def get_article_info(self, article):
        """
        Get the article metadata information given the article id.
        :param article:  article id
        :return: article information
        """
        url = f'{self.url}/article/{article}'
        headers = {
            'x-rapidapi-key': self.get_api_key(),
            'x-rapidapi-host': self.host
        }
        result = {}
        try:
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code != 200:
                logger.error(response.text)
                return result
            tmp_res = response.json()
            result["title"] = tmp_res.get("title", "")
            result["published_at"] = tmp_res.get("published_at", "")
            result["subtitle"] = tmp_res.get("subtitle", "")
            result["author"] = self.get_author(tmp_res.get("author", ""))
        except Exception as e:
            logger.error(e)
            return result
        finally:
            return result

    @requires_valid_period
    def get_article_content(self, article):
        """
        Get the article content given the article id.
        :param article:  article id
        :return:  article content
        """
        url = f'{self.url}/article/{article}/content'
        headers = {
            'x-rapidapi-key': self.get_api_key(),
            'x-rapidapi-host': self.host
        }
        result = ""
        try:
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code != 200:
                logger.error(response.text)
                return result
            result = response.json().get("content", "")
        except Exception as e:
            logger.error(e)
            return result
        finally:
            return result

    @requires_valid_period
    def research_topic(self, topic, save_callback=None):
        """
        Research a topic in medium and saves the results if a save callback is provided. It returns the results. Note that
        each call to this method will account for 1 + 3 * the number of results found updates on the counter
        :param topic:
        :param save_callback:
        :return:
        """
        all_results = []
        querystring = {"query": topic}
        headers = {
            'x-rapidapi-key': self.get_api_key(),
            'x-rapidapi-host': self.host
        }
        try:
            url = f'{self.url}/search/articles'
            response = requests.get(url, params=querystring, headers=headers, timeout=30)
            results = response.json().get("articles", [])
            logger.info("Found %s results for topic %s", len(results), topic)
            for result in results:
                article = {}
                article.update(self.get_article_info(result))
                article["content"] = self.get_article_content(result)
                article["information_source"] = self.information_source.value
                all_results.append(article)
                if save_callback:
                    self.save_if_valid(save_callback, article)
        except Exception as e:
            logger.error(e)
        finally:
            return all_results

    def search(self, save_callback=None) -> list:
        """
        Runs the search for each topic. Then returns the results
        :param save_callback:
        :return:
        """
        logger.info("Searching for content in %s", self.information_source)
        all_results = []
        for topic in self.topics:
           all_results.extend(self.research_topic(topic, save_callback))
        return all_results

    def save_if_valid(self, save, result):
        """
        Saves the result if it is valid, some results might not have content, so they are not valid
        :param save:  callback to save the result
        :param result:  result to be saved
        :return:
        """
        if len(result.get("content", "")) > self.minimum_length and result.get("title", "") != "":
            save(result)

    def filter(self, results):
        """
        Filters the results, removing those that do not have content or title

        :param results:  results to be filtered
        :return:  filtered results
        """
        return list(
            filter(lambda x: x.get("title", "") != "",
                   filter(lambda x: len(x.get("content", "")) > self.minimum_length, results))
        )
