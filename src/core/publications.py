import base64
import datetime
import logging
import uuid
from typing import Optional, Iterator, Dict, Any
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from src.core.constants import (
    PublicationState,
    SecretKeys,
    PUBLICATIONS_COLLECTION,
)
from src.core.utils.logging import ServiceLogger
from src.core.vault.hashicorp import VaultClient

"""Publication iterator module for filtering and iterating through publications."""


class PublicationIterator:
    """Iterator class for filtering and iterating through publications based on their state."""

    def __init__(
        self,
        state_filter: Optional[PublicationState] = None,
        do_format=True,
        logger: logging.Logger = ServiceLogger(__name__),
    ):
        """Initialize the publication iterator.

        Args:
            state_filter (Optional[PublicationState]): Optional state filter for publications.
        """
        self.logger = logger
        vault_client = VaultClient()
        client: MongoClient = MongoClient(
            vault_client.get_secret(SecretKeys.MONGO_URI)
        )
        self.db: Database = client.get_database(
            vault_client.get_secret(SecretKeys.MONGO_DATABASE)
        )
        self.client: Collection = self.db[PUBLICATIONS_COLLECTION]
        self.state_filter = state_filter
        self._cursor = None
        self.current_index = 0
        self.format = do_format
        self._total_count = None  # Cache for total count

    def _format(self, publication: dict) -> dict:
        """Format a publication dictionary by removing internal MongoDB ID and converting datetime fields to ISO format.

        Args:
            publication (dict): The publication document from MongoDB.

        Returns:
            dict: The formatted publication dictionary.
        """
        if not self.format:
            return publication

        if publication:
            publication.pop("_id", None)
            for key, value in publication.items():
                if isinstance(value, datetime.datetime):
                    publication[key] = value.isoformat()
                if key == "image" and publication[key]:
                    publication[key] = base64.b64decode(publication[key])
        return publication

    def remove(self, publication_id: str) -> bool:
        """Remove a publication by its ID.

        Args:
            publication_id (str): The ID of the publication to remove.

        Returns:
            bool: True if the publication was removed, False otherwise.
        """
        result = self.client.delete_one({"publication_id": publication_id})
        self._total_count = None  # Reset cache
        return result.deleted_count > 0

    def get(self, publication_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a publication by its ID.

        Args:
            publication_id (str): The ID of the publication to retrieve.

        Returns:
            Optional[Dict[str, Any]]: The publication document if found, None otherwise.
        """
        return self._format(
            self.client.find_one({"publication_id": publication_id})
        )

    def get_content(self, publication_id: str) -> Optional[str]:
        """Retrieve the content field of a specific publication.

        Args:
            publication_id (str): The ID of the publication.

        Returns:
            Optional[str]: The content of the publication.
        """
        return self.get(publication_id).get("content")

    def get_image(self, publication_id: str) -> bytes:
        """Retrieve the image field of a specific publication.

        Args:
            publication_id (str): The ID of the publication.

        Returns:
            Optional[str]: The image of the publication.
        """
        image = self.get(publication_id).get("image")
        return base64.b64decode(image) if image else None

    def reset_iterator(self) -> None:
        """Reset the iterator to the beginning of the results."""
        self.__iter__()

    def select(self, n: int) -> Optional[Dict[str, Any]]:
        """Retrieve the nth publication in order.

        Args:
            n (int): The index of the publication to retrieve.

        Returns:
            Optional[Dict[str, Any]]: The nth publication if it exists, None otherwise.
        """

        last_index = self.current_index
        self.reset_iterator()
        try:
            self.current_index = n
            self.logger.debug(
                f"Current index: {self.current_index} out of {len(self)}"
            )
            return self._format(next(self._cursor.skip(n)))
        except StopIteration:
            self.logger.debug("Iterator reset")
            self.reset_iterator()
            self.current_index = last_index
            return None

    def _update_publication(
        self, publication_id: str, update: Dict[str, Any]
    ) -> bool:
        """Update a publication with new values.

        Args:
            publication_id (str): The ID of the publication to update.
            update (Dict[str, Any]): The update fields and values.

        Returns:
            bool: True if the update was successful, False otherwise.
        """
        update["last_updated"] = datetime.datetime.now()
        result = self.client.update_one(
            {"publication_id": publication_id}, {"$set": update}
        )
        return result.modified_count > 0

    def update_content(self, publication_id: str, content: str) -> bool:
        """Update the content of a publication.

        Args:
            publication_id (str): The ID of the publication to update.
            content (str): The new content value.

        Returns:
            bool: True if the content was updated, False otherwise.
        """
        return self._update_publication(publication_id, {"content": content})

    def update_image(self, publication_id: str, image: Optional[bytes]) -> bool:
        """Update the image of a publication.

        Args:
            publication_id (str): The ID of the publication to update.
            image (bytes| None): The new image value. If None, remove the image

        Returns:
            bool: True if the image was updated, False otherwise.
        """
        return self._update_publication(
            publication_id, {"image": base64.b64encode(image).decode("utf-8")}
        )

    def update_state(
        self, publication_id: str, state: PublicationState
    ) -> bool:
        """Update the state of a publication.

        Args:
            publication_id (str): The ID of the publication to update.
            state (PublicationState): The new state value.

        Returns:
            bool: True if the state was updated, False otherwise.
        """
        return self._update_publication(publication_id, {"state": state.value})

    def insert(self, publication: Dict[str, Any]) -> Optional[str]:
        """Insert a new publication into the database.

        :param: publication (Dict[str, Any]): The publication data to insert.

        :returns: bool: True if the insertion was successful, False otherwise.
        """
        publication["creation_date"] = datetime.datetime.now()
        publication["last_updated"] = publication["creation_date"]
        publication["publication_id"] = str(uuid.uuid4())
        publication["state"] = PublicationState.DRAFT.value
        result = self.client.insert_one(publication)
        self._total_count = None  # Reset cache
        return (
            publication["publication_id"]
            if result.inserted_id is not None
            else None
        )

    def last(self) -> Optional[Dict[str, Any]]:
        """Retrieve the previous publication in the iterator with circular behavior.

        :returns: Optional[Dict[str, Any]]: The previous publication if available, None otherwise.
        """

        current_index = self.current_index
        self.reset_iterator()

        total_count = len(self)
        if total_count == 0:
            return None

        self.current_index = (current_index - 1 + total_count) % total_count
        self.logger.warning(
            f"Current index: {self.current_index} out of {len(self)}"
        )
        publication = self._cursor.skip(self.current_index)

        return self._format(next(publication, None))

    def center_iterator(self, publication_id: str) -> bool:
        """Update the current index to center on the publication with the given ID.

        :param: publication_id (str): The ID of the publication to center on.

        :returns: bool: True if the index was successfully updated, False otherwise.
        """
        self.reset_iterator()
        for index, publication in enumerate(self._cursor):
            if publication.get("publication_id") == publication_id:
                self.current_index = index
                self.logger.warning(
                    f"Current index: {self.current_index} out of {len(self)}"
                )
                return True

        return False

    def list(self):
        result = []
        tmp_cursor = self._build_cursor()
        for index, publication in enumerate(tmp_cursor):
            result.append((index, publication))
        return result

    def _build_cursor(self):
        """
        It creates the cursor object with the state filter
        """
        state_filter = (
            {"state": self.state_filter.value} if self.state_filter else {}
        )
        return self.client.find(state_filter).sort("creation_date", 1)

    def __iter__(self) -> Iterator[Dict[str, Any]]:
        """Initialize the iterator for the publication results.

        :returns: Iterator[Dict[str, Any]]: The iterator over publication documents.
        """
        self._cursor = self._build_cursor()
        self.current_index = 0
        self._total_count = None
        return self

    def __len__(self) -> int:
        """Get the number of publications matching the query.

        :returns: int: The number of matching publications.
        """
        if self._total_count is None:
            state_filter = (
                {"state": self.state_filter.value} if self.state_filter else {}
            )
            self._total_count = self.client.count_documents(state_filter)
        return self._total_count

    def __next__(self) -> Dict[str, Any]:
        """Retrieve the next publication in the iterator with circular behavior.

        :returns: Dict[str, Any]: The next publication document.

        :raises: StopIteration: If no more publications are available.
        """
        if self._cursor is None:
            self.__iter__()

        total_count = len(self)
        if total_count == 0 or (total_count == 1 and self.current_index > 0):
            self.logger.debug("Iterator reset")
            raise StopIteration("No publications available.")

        self.current_index = self.current_index + 1
        self.logger.warning(
            f"Current index: {self.current_index} out of {len(self)}"
        )
        if self.current_index >= total_count:
            self.reset_iterator()
        return self._format(next(self._cursor))
