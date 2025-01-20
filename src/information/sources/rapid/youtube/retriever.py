import base64
import threading
import time
from datetime import datetime
from urllib.parse import quote, urlparse, parse_qs

import requests
from googleapiclient.discovery import build

from src.core.utils.logging import ServiceLogger
from src.core.vault.hashicorp import VaultClient
from src.core.constants import SecretKeys
from src.information.sources.base import (
    require_valid_run_time,
    InformationSource,
    stateful,
)
from src.information.sources.rapid.base import RapidSource
from src.information.sources.rapid.youtube.pool import YoutubeUrlPool


class YoutubeTranscriptRetriever(RapidSource):
    """
    Retrieves transcripts and metadata from YouTube videos using RapidAPI and pytube
    """

    _PARTS = [
        "snippet"
    ]  # Could retrieve more information like views and stuff but don really need it tbh
    _METADATA_KEYS = ["publishedAt", "title", "description", "channelTitle"]
    _SCHEME = "https://"
    _REQUEST_TIMEOUT = 10
    _THUMBNAIL_OPTIONS = [
        "maxresdefault.jpg",
        "hqdefault.jpg",
        "mqdefault.jpg",
        "default.jpg",
    ]

    def __init__(self):
        super().__init__(ServiceLogger(__name__))
        self.information_source = InformationSource.YOUTUBE
        self.url_pool = YoutubeUrlPool()
        self.yt_client = build(
            "youtube",
            "v3",
            developerKey=VaultClient().get_secret(SecretKeys.YOUTUBE_API_KEY),
        )

    @staticmethod
    def _extract_video_id(url):
        parsed_url = urlparse(url)
        if parsed_url.hostname in ["www.youtube.com", "youtube.com"]:
            return parse_qs(parsed_url.query).get("v", [None])[0]
        elif parsed_url.hostname in ["youtu.be"]:
            return parsed_url.path.lstrip("/")
        return None

    def _execute_metadata_request(self, video_id):
        try:
            metadata = (
                self.yt_client.videos()
                .list(part=",".join(self._PARTS), id=video_id)
                .execute()
                .get("items", [])
            )

            if metadata:
                return metadata[0]
            self.logger.warning(f"Metadata for video {video_id} empty")
            return None
        except Exception as e:
            self.logger.error(
                f"Error getting metadata for {video_id}: {str(e)}"
            )
            return None

    def _extract_from_metadata(self, metadata_dict):
        result = {}
        for part in self._PARTS:
            for key in self._METADATA_KEYS:
                result[key] = metadata_dict[part][key]

        return result

    def get_metadata(self, video_id):
        """Get video metadata using pytube"""
        self.logger.info("Fetching metadata for video: %s", video_id)
        metadata = self._execute_metadata_request(video_id)
        if metadata:
            metadata = self._extract_from_metadata(metadata)
            return metadata
        return None

    def download_youtube_thumbnail(self, video_id):
        base_thumbnail_url = f"https://img.youtube.com/vi/{video_id}/"

        for option in self._THUMBNAIL_OPTIONS:
            thumbnail_url = base_thumbnail_url + option
            response = requests.get(
                thumbnail_url, timeout=self._REQUEST_TIMEOUT, stream=True
            )
            if response.status_code == 200:
                self.logger.info(
                    f"Thumbnail downloaded for video {video_id} and quality {option}"
                )
                return response.content
            self.logger.warning(
                f"Could not download thumbnail for video {video_id} and quality {option}. Response: {str(response)}"
            )
        return None

    def get_transcript(self, url):
        """Retrieve transcript for a YouTube video"""
        self.logger.info("Fetching transcript for URL: %s", url)

        try:
            encoded_url = quote(url, safe="")
            self.logger.info("Making API request to %s", self.host)

            response = self.execute_rapid_request(
                f"{self.url}?url={encoded_url}&flat_text=true",
                extra_headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()
            data = response.json()
            transcript = data.get("transcript", "")
            self.logger.info(
                "Successfully retrieved transcript of length %d characters",
                len(transcript),
            )
            return transcript

        except Exception as e:
            self.logger.error(
                f"Error retrieving transcript for {url}: {str(e)}"
            )
            return None

    def process_url(self, url):
        """Process a single URL from the pool"""
        self.logger.info("Processing URL: %s", url)

        video_id = self._extract_video_id(url)
        metadata = self.get_metadata(video_id)

        if not metadata:
            self.logger.error(f"Failed to get metadata for {url}")
            return None

        transcript = self.get_transcript(url)
        if not transcript:
            self.logger.error(f"Failed to get transcript for {url}")
            return None

        self.logger.info("Creating material for video: %s", metadata["title"])

        material = {
            "content": transcript,
            "timestamp": datetime.now().isoformat(),
            "type": "youtube_transcript",
            "information_source": self.information_source.value,
        }
        material.update(metadata)
        material["url"] = url
        image = self.download_youtube_thumbnail(video_id=video_id)
        if image:
            material["image"] = base64.b64encode(image)

        self.logger.info("Marking URL as processed: %s", url)
        return material

    @require_valid_run_time
    @stateful
    def search(
        self, save_callback=None, stop_event: threading.Event = None
    ) -> list:
        """Search for content in the URL pool and process each URL"""
        self.logger.info(
            "Starting search for content in %s", self.information_source
        )
        all_results = []

        for url in self.url_pool:

            if stop_event and stop_event.is_set():
                self.url_pool.add_url(
                    url
                )  # Urls get popped out of the queue when iterating
                self.logger.info(
                    "Stop event called in the middle of procesing the topics"
                )
                break

            self.logger.info("Processing URL: %s", url)
            material = self.process_url(url)
            if material:
                self.logger.info(
                    "Successfully processed material for: %s", material["title"]
                )
                all_results.append(material)
                if save_callback:
                    self.save_if_valid(save_callback, material)
            time.sleep(1)  # Rate limiting

        self.logger.info("Search completed. Found %d results", len(all_results))
        return all_results
