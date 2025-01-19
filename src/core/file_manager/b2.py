import os
from typing import Optional, List, Dict, Union
from b2sdk.v2 import LifecycleRule
from b2sdk.v2.exception import NonExistentBucket
from b2sdk.v2.exception import B2Error
from b2sdk.v2 import B2Api, InMemoryAccountInfo
from retry import retry
from src.core.constants import SecretKeys, FileManagedFolders
from src.core.utils.logging import ServiceLogger
from src.core.vault.hashicorp import VaultClient

logger = ServiceLogger(__name__)
RETRY_DELAY = 1
RETRY_TRIES = 3


def ensure_authenticated(method):
    """
    Decorator to ensure the B2Handler instance is authenticated before executing the method.
    """

    def wrapper(self, *args, **kwargs):
        if not self.api or not self.bucket:
            if not self.authenticate():
                logger.error("Authentication failed. Cannot proceed with the operation.")
                return False
        return method(self, *args, **kwargs)

    return wrapper


class B2Handler:
    """
    Handler for managing Backblaze B2 Cloud Storage operations.
    """

    _BUCKET_NAME = "linkedin-assistant"  # Replace with the actual bucket name
    _BUCKET_TYPE = "allPrivate"
    _LIFECYCLE_RULES = [
        LifecycleRule(
            fileNamePrefix=FileManagedFolders.INPUT_PDF_FOLDER,
            daysFromHidingToDeleting=1,
            daysFromUploadingToHiding=60
        ),
        LifecycleRule(
            fileNamePrefix=FileManagedFolders.OUTPUT_PDF_FOLDER,
            daysFromHidingToDeleting=1,
            daysFromUploadingToHiding=30
        ),
        LifecycleRule(
            fileNamePrefix=FileManagedFolders.IMAGES_FOLDER,
            daysFromHidingToDeleting=1,
            daysFromUploadingToHiding=30
        )
    ]

    def __init__(self):
        """
        Initialize the B2 Cloud Storage handler.
        """
        self.vault_client = VaultClient()
        self.api = None
        self.bucket = None
        self.authenticate()

    def _get_credentials(self) -> tuple[Optional[str], Optional[str]]:
        """
        Retrieve B2 credentials from Vault.

        :returns: tuple: (application_key_id, application_key) if successful, (None, None) otherwise.
        """
        try:
            logger.info("Retrieving B2 credentials from Vault.")
            key_id = self.vault_client.get_secret(SecretKeys.B2_APPLICATION_KEY_ID_KEY)
            key = self.vault_client.get_secret(SecretKeys.B2_APPLICATION_KEY_KEY)

            if not key_id or not key:
                logger.error("No B2 credentials found in Vault.")
                return None, None

            logger.info("Successfully retrieved B2 credentials.")
            return key_id, key
        except Exception as e:
            logger.error(f"Error retrieving B2 credentials: {str(e)}")
            return None, None

    def authenticate(self) -> bool:
        """
        Authenticate with B2 using credentials from Vault.

        :returns: bool: True if authentication is successful, False otherwise.
        """
        try:
            logger.info("Authenticating with B2.")
            key_id, key = self._get_credentials()
            if not key_id or not key:
                logger.error("Failed to get credentials for authentication.")
                return False

            info = InMemoryAccountInfo()
            self.api = B2Api(info)
            self.api.authorize_account("production", key_id, key)

            try:
                self.bucket = self.api.get_bucket_by_name(self._BUCKET_NAME)
            except NonExistentBucket:
                self.bucket = self.api.create_bucket(
                    self._BUCKET_NAME,
                    bucket_type=self._BUCKET_TYPE,
                    lifecycle_rules=self._LIFECYCLE_RULES
                )
            logger.info("Successfully authenticated with B2.")
            return True
        except B2Error as e:
            logger.error(f"B2 authentication error: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error connecting to B2: {str(e)}")
            return False

    @retry(B2Error, delay=RETRY_DELAY, tries=RETRY_TRIES, logger=logger)
    @ensure_authenticated
    def upload_from_bytes(self, content: bytes, file_path: str) -> Optional[str]:
        """
        Upload content directly to B2.

        :param: content (bytes): content as bytes.
        :param: file_path (str): B2 destination path.

        :returns: Optional[str]: B2 file ID if successful, None otherwise.
        """

        file_path = file_path.lstrip('/')

        logger.info(f"Uploading file to B2: {file_path}")
        file_info = self.bucket.upload_bytes(data_bytes=content, file_name=file_path)

        logger.info(f"File uploaded successfully: {file_info.file_name}")
        return file_info.id_

    @retry(B2Error, delay=RETRY_DELAY, tries=RETRY_TRIES, logger=logger)
    @ensure_authenticated
    def upload_pdf(self, file_path: str, b2_path: str = None) -> Optional[str]:
        """
        Upload a PDF file to B2.

        :param: file_path (str): Local path to the PDF file.
        :param: b2_path (str, optional): B2 destination path. Defaults to the file name.

        :returns: Optional[str]: B2 file ID if successful, None otherwise.
        """

        b2_path = b2_path if b2_path else os.path.basename(file_path)

        logger.info(f"Reading file for upload: {file_path}")
        with open(file_path, 'rb') as f:
            content = f.read()
            return self.upload_from_bytes(content, b2_path)

    @retry(B2Error, delay=RETRY_DELAY, tries=RETRY_TRIES, logger=logger)
    @ensure_authenticated
    def download(self, file_path: str) -> bytes:
        """
        Download a file from B2.

        :param: file_path (str): B2 file path.

        :returns: bool: True if the download is successful, False otherwise.
        """
        logger.info(f"Downloading file from B2: {file_path}")
        return self.bucket.download_file_by_name(file_path).response.content

    @retry(B2Error, delay=RETRY_DELAY, tries=RETRY_TRIES, logger=logger)
    @ensure_authenticated
    def list_folder_contents(self, folder_path: str = "") -> List[Dict[str, Union[str, int]]]:
        """
        List contents of a B2 folder.

        :param: folder_path (str, optional): B2 folder path. Defaults to "".

        :returns: List[Dict[str, Union[str, int]]]: List of items in the folder with their details.
        """

        logger.info(f"Listing folder contents in B2: {folder_path}")
        items = []
        for file_version, _ in self.bucket.ls(folder_path):
            items.append({
                'id': file_version.id_,
                'name': os.path.basename(file_version.file_name),
                'path': file_version.file_name,
                'type': 'file',
                'size': file_version.size
            })

        logger.info(f"Folder contents listed successfully: {len(items)} items found.")
        return items

    @retry(B2Error, delay=RETRY_DELAY, tries=RETRY_TRIES, logger=logger)
    @ensure_authenticated
    def delete_file(self, file_path: str) -> bool:
        """
        Delete a file from B2.

        :param: file_path (str): B2 file path.

        :returns: bool: True if the deletion is successful, False otherwise.
        """

        file_path = file_path.lstrip('/')

        logger.info(f"Deleting file in B2: {file_path}")
        file_version = self.bucket.get_file_info_by_name(file_path)
        return self.bucket.delete_file_version(file_version.id_, file_path)

    @retry(B2Error, delay=RETRY_DELAY, tries=RETRY_TRIES, logger=logger)
    @ensure_authenticated
    def move_file(self, from_path: str, to_path: str) -> bool:
        """
        Move a file within B2.

        :param: from_path (str): Source path in B2.
        :param: to_path (str): Target path in B2.

        :returns: bool: True if the move is successful, False otherwise.
        """
        logger.info(f"Moving file in B2 from {from_path} to {to_path}")
        file_version = self.bucket.get_file_info_by_name(from_path)
        self.bucket.copy(file_version.id_, to_path)
        return self.bucket.delete_file_version(file_version.id_, from_path)
