import json
import logging
import os

import requests

from src.information.sources.information_source import requires_valid_period
from src.information.sources.rapid.manager import RapidSource
from src.utils.log_handler import TruncateByTimeHandler

PWD = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.abspath(os.path.join(PWD, '..', "..", "..", "..", ".."))
LOGGING_DIR = os.path.join(PROJECT_DIR, "logs") if os.name != 'nt' else os.path.join(r"C:\\", "ProgramData",
                                                                                      "linkedin_assistant", "logs")
FILE = os.path.basename(__file__)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = TruncateByTimeHandler(filename=os.path.join(LOGGING_DIR, f'{FILE}.log'), encoding='utf-8', mode='a+')
handler.setLevel(logging.INFO)
handler.setFormatter(logging.Formatter(f'%(asctime)s - %(name)s - {__name__} - %(levelname)s - %(message)s'))
logger.addHandler(handler)
config_dir = os.path.join(r"C:\\", "ProgramData", "linkedin_assistant", "information", "sources", "rapid", "medium",
                          "config.json") if os.name == 'nt' else os.path.join(PWD, "config.json")
DEBUG_FLAG = False


class MediumSearchEngine(RapidSource):

    """
    Searches for content in Medium.
    """

    def __init__(self, information_source):
        """Initialize the searcher with the information source."""
        super().__init__(information_source)
        self.max_results = 25
        self.url = ""
        self.information_source = information_source
        self.topics = []
        self.minimum_length = 50
        self.limit = 1000
        self.max_results = 25
        self.period = 30
        self.api_key = None
        self.pwd = os.path.dirname(os.path.abspath(__file__))
        self.host = ""
        self.reload_config(config_dir)

    @requires_valid_period
    def get_author(self, author):
        """
        Get the author name given the author id.
        :param author:  author id
        :return:  author full name
        """
        url = f'{self.url}/user/{author}'
        headers = {
            'x-rapidapi-key': self.api_key,
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
            'x-rapidapi-key': self.api_key,
            'x-rapidapi-host': self.host
        }
        result = {}
        try:
            if DEBUG_FLAG:
                return {"title": "test", "published_at": "test", "subtitle": "test", "author": "test"}
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
            'x-rapidapi-key': self.api_key,
            'x-rapidapi-host': self.host
        }
        result = ""
        try:
            if DEBUG_FLAG:
                return "test"
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
            'x-rapidapi-key': self.api_key,
            'x-rapidapi-host': self.host
        }
        try:
            url = f'{self.url}/search/articles'
            if not DEBUG_FLAG:
                response = requests.get(url, params=querystring, headers=headers, timeout=30)
                results = response.json().get("articles", [])
                logger.info("Found %s results for topic %s", len(results), topic)
            else:
                results = [{"test": "test"} for _ in range(10)]  # should end up producing an increment in the counter of 21
            for result in results:
                article = {}
                article.update(self.get_article_info(result))
                article["content"] = self.get_article_content(result)
                article["information_source"] = self.information_source
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
