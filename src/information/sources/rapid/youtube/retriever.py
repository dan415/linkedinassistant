import json
import logging
import os
import threading
import time
from datetime import datetime
from urllib.parse import quote
import requests
from pytube import YouTube
from src.information.sources.rapid.manager import RapidSource
from src.information.sources.rapid.youtube.pool import YoutubeUrlPool
from src.information.sources.information_source import requires_valid_period
import src.core.utils.functions as F

FILE = os.path.basename(__file__)
logger = F.get_logger(dump_to=FILE)


def get_metadata(url):
    """Get video metadata using pytube"""
    logger.info("Fetching metadata for URL: %s", url)
    try:
        yt = YouTube(url)
        metadata = {
            "title": yt.title,
            "channel": yt.author,
            "upload_date": yt.publish_date if yt.publish_date else "",
            "description": yt.description,
            "views": yt.views,
            "length": yt.length,
            "url": url
        }
        logger.info("Successfully retrieved metadata for video: %s by %s", yt.title, yt.author)
        return metadata
    except Exception as e:
        logger.error(f"Error getting metadata for {url}: {str(e)}")
        return None


class YoutubeTranscriptRetriever(RapidSource):
    """
    Retrieves transcripts and metadata from YouTube videos using RapidAPI and pytube
    """

    def __init__(self, information_source):
        self.url_pool = YoutubeUrlPool()
        self.period = 30
        self.host = None
        self.minimum_length = 50  # Minimum length for valid content
        super().__init__(information_source)

    @requires_valid_period
    def get_transcript(self, url):
        """Retrieve transcript for a YouTube video"""
        logger.info("Fetching transcript for URL: %s", url)
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "x-rapidapi-key": self.get_api_key(),
            "x-rapidapi-host": self.host
        }

        try:
            encoded_url = quote(url, safe='')
            logger.info("Making API request to %s", self.host)
            response = requests.get(
                f"{self.host}?url={encoded_url}&flat_text=true",
                headers=headers
            )
            response.raise_for_status()
            data = response.json()
            transcript = data.get("text", "")
            logger.info("Successfully retrieved transcript of length %d characters", len(transcript))
            return transcript

        except Exception as e:
            logger.error(f"Error retrieving transcript for {url}: {str(e)}")
            return None

    def process_url(self, url):
        """Process a single URL from the pool"""
        logger.info("Processing URL: %s", url)
        metadata = get_metadata(url)
        if not metadata:
            logger.error(f"Failed to get metadata for {url}")
            return None

        transcript = self.get_transcript(url)
        if not transcript:
            logger.error(f"Failed to get transcript for {url}")
            return None

        logger.info("Creating material for video: %s", metadata["title"])
        material = {
            "title": metadata["title"],
            "content": transcript,
            "url": url,
            "channel": metadata["channel"],
            "upload_date": metadata["upload_date"],
            "description": metadata["description"],
            "views": metadata["views"],
            "length": metadata["length"],
            "type": "youtube_transcript",
            "information_source": self.information_source.value,
            "timestamp": datetime.now().isoformat()
        }

        logger.info("Marking URL as processed: %s", url)
        self.url_pool.release(url)
        return material

    @requires_valid_period
    def search(self, save_callback=None) -> list:
        """Search for content in the URL pool and process each URL"""
        logger.info("Starting search for content in %s", self.information_source)
        all_results = []

        for url in self.url_pool:
            logger.info("Processing URL: %s", url)
            material = self.process_url(url)
            if material:
                logger.info("Successfully processed material for: %s", material["title"])
                all_results.append(material)
                if save_callback:
                    self.save_if_valid(save_callback, material)
            time.sleep(1)  # Rate limiting

        logger.info("Search completed. Found %d results", len(all_results))
        return all_results

    def filter(self, content: list) -> list:
        """Filter the content based on minimum length requirements"""
        logger.info("Filtering %d content items", len(content))
        filtered = list(filter(lambda x: len(x.get("content", "")) > self.minimum_length, content))
        logger.info("%d items passed length filter", len(filtered))
        return filtered

    def save_if_valid(self, save, result):
        """Save the result if it has valid content and title"""
        content_length = len(result.get("content", ""))
        has_title = bool(result.get("title", ""))
        logger.info("Validating result: content_length=%d, has_title=%s", content_length, has_title)

        if content_length > self.minimum_length and has_title:
            logger.info("Saving valid result: %s", result["title"])
            save(result)
        else:
            logger.info("Result did not meet validation criteria")

