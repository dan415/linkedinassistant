from typing import Any, Dict, Optional, List, Tuple
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
import os
import threading
from threading import Lock

from src.core.constants import SecretKeys
from src.core.vault.hvault import VaultClient
import src.core.utils.functions as F

FILE = os.path.basename(__file__)
logger = F.get_logger(dump_to=FILE)


class MongoDBClient:
    _instances: Dict[str, 'MongoDBClient'] = {}
    _instance_lock = threading.Lock()

    def __new__(cls, collection_name: str):
        with cls._instance_lock:
            if collection_name not in cls._instances:
                logger.info(f"Creating new MongoDBClient instance for collection: {collection_name}")
                instance = super(MongoDBClient, cls).__new__(cls)
                instance._initialized = False
                cls._instances[collection_name] = instance
            return cls._instances[collection_name]

    def __init__(self, collection_name: str):
        with self._instance_lock:
            if self._initialized:
                return

            logger.info(f"Initializing MongoDBClient for collection: {collection_name}")
            vault_client = VaultClient()
            self.client: MongoClient = MongoClient(vault_client.get_secret(SecretKeys.MONGO_URI))
            self.db: Database = self.client.get_database(vault_client.get_secret(SecretKeys.MONGO_DATABASE))
            self.collection_name = collection_name
            self.collection: Collection = self.db[collection_name]
            self._initialized = True
            self._operation_lock = Lock()
            logger.info(f"MongoDBClient initialized successfully for collection: {collection_name}")

    def insert_one(self, document: Dict[str, Any]) -> str:
        """Insert a single document into the collection.
        
        Args:
            document: Document to insert
            
        Returns:
            str: ID of the inserted document
        """
        with self._operation_lock:
            logger.debug(f"Inserting document into collection: {self.collection_name}")
            result = self.collection.insert_one(document)
            logger.info(f"Document inserted successfully with ID: {result.inserted_id}")
            return str(result.inserted_id)

    def insert_many(self, documents: List[Dict[str, Any]]) -> List[str]:
        """Insert multiple documents into the collection.
        
        Args:
            documents: List of documents to insert
            
        Returns:
            List[str]: List of inserted document IDs
        """
        with self._operation_lock:
            logger.debug(f"Inserting {len(documents)} documents into collection: {self.collection_name}")
            result = self.collection.insert_many(documents)
            logger.info(f"Successfully inserted {len(result.inserted_ids)} documents")
            return [str(id) for id in result.inserted_ids]

    def find_one(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find a single document in the collection.
        
        Args:
            query: Query filter
            
        Returns:
            Optional[Dict[str, Any]]: Found document or None
        """
        with self._operation_lock:
            logger.debug(f"Finding document in collection {self.collection_name} with query: {query}")
            result = self.collection.find_one(query)
            if result:
                logger.info("Document found")
            else:
                logger.info("No document found matching query")
            return result

    def find(self,
            query: Dict[str, Any],
            projection: Optional[Dict[str, Any]] = None,
            sort: Optional[List[Tuple[str, int]]] = None,
            limit: Optional[int] = None,
            skip: Optional[int] = None,
            batch_size: Optional[int] = None,
            allow_disk_use: bool = False,
            no_cursor_timeout: bool = False) -> List[Dict[str, Any]]:
        """Find documents in the collection with advanced query options.
        
        Args:
            query: MongoDB query filter
            projection: Fields to include/exclude in the result
                       e.g., {"field": 1} to include, {"field": 0} to exclude
            sort: List of (field, direction) pairs for sorting
                  direction: 1 for ascending, -1 for descending
                  e.g., [("timestamp", -1), ("name", 1)]
            limit: Maximum number of documents to return
            skip: Number of documents to skip
            batch_size: Number of documents to return per batch
            allow_disk_use: Allow MongoDB to use disk for large sort operations
            no_cursor_timeout: Prevent cursor from timing out
            
        Returns:
            List[Dict[str, Any]]: List of documents matching the query
        """
        with self._operation_lock:
            logger.debug(f"Finding documents in collection {self.collection_name} with query: {query}")
            logger.debug(f"Projection: {projection}, Sort: {sort}, Limit: {limit}, Skip: {skip}")
            
            cursor = self.collection.find(
                filter=query,
                projection=projection,
                allow_disk_use=allow_disk_use,
                no_cursor_timeout=no_cursor_timeout
            )
            
            if batch_size:
                cursor = cursor.batch_size(batch_size)
            if skip:
                cursor = cursor.skip(skip)
            if limit:
                cursor = cursor.limit(limit)
            if sort:
                cursor = cursor.sort(sort)
                
            try:
                results = list(cursor)
                logger.info(f"Found {len(results)} documents")
                return results
            finally:
                if no_cursor_timeout:
                    cursor.close()

    def find_with_pagination(self,
                           query: Dict[str, Any],
                           page: int = 1,
                           page_size: int = 10,
                           projection: Optional[Dict[str, Any]] = None,
                           sort: Optional[List[Tuple[str, int]]] = None) -> Dict[str, Any]:
        """Find documents with pagination support.
        
        Args:
            query: Query filter
            page: Page number (1-based)
            page_size: Number of documents per page
            projection: Fields to include/exclude in the result
            sort: List of (field, direction) pairs for sorting
            
        Returns:
            Dict containing:
                - total: Total number of matching documents
                - pages: Total number of pages
                - current_page: Current page number
                - page_size: Number of documents per page
                - documents: List of documents for current page
        """
        with self._operation_lock:
            logger.debug(f"Finding documents with pagination in collection {self.collection_name}")
            logger.debug(f"Query: {query}, Page: {page}, Page Size: {page_size}")
            
            total = self.count_documents(query)
            total_pages = (total + page_size - 1) // page_size
            
            # Ensure page is within valid range
            page = max(1, min(page, total_pages)) if total_pages > 0 else 1
            
            skip = (page - 1) * page_size
            documents = self.find(
                query,
                projection=projection,
                sort=sort,
                limit=page_size,
                skip=skip
            )
            
            result = {
                "total": total,
                "pages": total_pages,
                "current_page": page,
                "page_size": page_size,
                "documents": documents
            }
            logger.info(f"Pagination results: Total: {total}, Pages: {total_pages}, Current Page: {page}")
            return result

    def update_one(self, 
                  query: Dict[str, Any], 
                  update: Dict[str, Any],
                  upsert: bool = False) -> int:
        """Update a single document in the collection.
        
        Args:
            query: Query filter
            update: Update operations
            upsert: If True, create document if it doesn't exist
            
        Returns:
            int: Number of modified documents
        """
        with self._operation_lock:
            logger.debug(f"Updating document in collection {self.collection_name}")
            logger.debug(f"Query: {query}, Update: {update}, Upsert: {upsert}")
            
            result = self.collection.update_one(query,{"$set": update}, upsert=upsert)
            logger.info(f"Modified {result.modified_count} documents")
            if upsert and result.upserted_id:
                logger.info(f"Upserted document with ID: {result.upserted_id}")
            return result.modified_count

    def update_many(self, 
                   query: Dict[str, Any], 
                   update: Dict[str, Any],
                   upsert: bool = False) -> int:
        """Update multiple documents in the collection.
        
        Args:
            query: Query filter
            update: Update operations
            upsert: If True, create documents if they don't exist
            
        Returns:
            int: Number of modified documents
        """
        with self._operation_lock:
            logger.debug(f"Updating multiple documents in collection {self.collection_name}")
            logger.debug(f"Query: {query}, Update: {update}, Upsert: {upsert}")
            
            result = self.collection.update_many(query, {"$set": update }, upsert=upsert)
            logger.info(f"Modified {result.modified_count} documents")
            if upsert and result.upserted_id:
                logger.info(f"Upserted document with ID: {result.upserted_id}")
            return result.modified_count

    def delete_one(self, query: Dict[str, Any]) -> int:
        """Delete a single document from the collection.
        
        Args:
            query: Query filter
            
        Returns:
            int: Number of deleted documents
        """
        with self._operation_lock:
            logger.debug(f"Deleting document from collection {self.collection_name}")
            logger.debug(f"Query: {query}")
            
            result = self.collection.delete_one(query)
            logger.info(f"Deleted {result.deleted_count} documents")
            return result.deleted_count

    def delete_many(self, query: Dict[str, Any]) -> int:
        """Delete multiple documents from the collection.
        
        Args:
            query: Query filter
            
        Returns:
            int: Number of deleted documents
        """
        with self._operation_lock:
            logger.debug(f"Deleting multiple documents from collection {self.collection_name}")
            logger.debug(f"Query: {query}")
            
            result = self.collection.delete_many(query)
            logger.info(f"Deleted {result.deleted_count} documents")
            return result.deleted_count

    def count_documents(self, query: Dict[str, Any]) -> int:
        """Count documents in the collection that match a query.
        
        Args:
            query: Query filter
            
        Returns:
            int: Number of matching documents
        """
        with self._operation_lock:
            logger.debug(f"Counting documents in collection {self.collection_name}")
            logger.debug(f"Query: {query}")
            
            count = self.collection.count_documents(query)
            logger.info(f"Found {count} matching documents")
            return count

    def aggregate(self, pipeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Perform an aggregation pipeline on the collection.
        
        Args:
            pipeline: List of aggregation stages
            
        Returns:
            List[Dict[str, Any]]: Result of the aggregation
        """
        with self._operation_lock:
            logger.debug(f"Running aggregation pipeline on collection {self.collection_name}")
            logger.debug(f"Pipeline: {pipeline}")
            
            results = list(self.collection.aggregate(pipeline))
            logger.info(f"Aggregation returned {len(results)} results")
            return results

    def close(self):
        """Close the MongoDB connection."""
        with self._operation_lock:
            logger.info(f"Closing MongoDB connection for collection: {self.collection_name}")
            self.client.close()
