"""Publication iterator module for filtering and iterating through publications."""
import datetime
import uuid
from typing import Optional, Iterator

from src.core.database.mongo import MongoDBClient
from src.information.constants import PublicationState


def _format(publication: dict):
    if publication:
        publication.pop("_id", None)
        for key, value in publication.items():
            if isinstance(value, datetime.datetime):
                publication[key] = value.isoformat()

    return publication


class PublicationIterator:
    """Iterator class for filtering and iterating through publications based on their state."""

    def __init__(self, collection: str, state_filter: Optional[PublicationState] = None):
        """Initialize the publication iterator.
        
        Args:
            publications_manager: MongoDB client instance for accessing publications
            state_filter: Optional PublicationState to filter publications by state
        """
        self.client = MongoDBClient(collection_name=collection)
        self.state_filter = state_filter
        self._cursor = None
        self.current_index = 0

    def remove(self, publication_id):
        """Remove a publication from the database by its ID."""
        result = self.client.delete_one({"publication_id": publication_id})
        return result > 0

    def get(self, publication_id):
        return _format(self.client.find_one({"publication_id": publication_id}))

    def get_content(self, publication_id):
        return self.get(publication_id).get("content")

    def get_image(self, publication_id):
        return self.get(publication_id).get("image")

    def refresh(self):
        self.__iter__()

    def select(self, n):
        """Retrieve the nth publication in order."""
        if self._cursor is None:
            self.__iter__()

        if 0 <= n < len(self._cursor):
            return _format(self._cursor[n])

        return None

    def _update_publication(self, publication_id, update):
        update["last_updated"] = datetime.datetime.now()
        return self.client.update_one({"publication_id": publication_id}, update)

    def update_content(self, publication_id, content):
        return self._update_publication(publication_id, {"content": content})

    def update_image(self, publication_id, image):
        return self._update_publication(publication_id, {"image": image})

    def update_state(self, publication_id, state: PublicationState):
        return self._update_publication(publication_id, {"state": state.value})

    def insert(self, publication):
        publication["creation_date"] = datetime.datetime.now()
        publication["last_updated"] = publication["creation_date"]
        publication["publication_id"] = str(uuid.uuid4())
        publication["state"] = PublicationState.DRAFT.value
        return self.client.insert_one(publication)

    def last(self):
        """Go back to the previous publication in the iterator."""
        if self._cursor is None:
            self.__iter__()
        if self.current_index > 0:
            self.current_index = (self.current_index - 1) % len(self)
            return _format(self._cursor[self.current_index])
        return None

    def __iter__(self) -> Iterator[dict]:
        """Return iterator for publications matching the state filter.
        
        Returns:
            Iterator yielding publication documents
        """
        query = {}
        if self.state_filter:
            query["state"] = self.state_filter.value

        self._cursor = self.client.find(query)
        return self

    def __len__(self):
        return len(self._cursor) if self._cursor else 0

    def __next__(self) -> dict | None:
        """Get next publication from the iterator.
        
        Returns:
            Next publication document
            
        Raises:
            StopIteration: When no more publications are available
        """
        if self._cursor is None:
            self.__iter__()

        if self.current_index < len(self):
            try:
                return _format(self._cursor[self.current_index])
            finally:
                self.current_index = (self.current_index + 1) % len(self)
        return None
