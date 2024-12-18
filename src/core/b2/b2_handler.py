import os
from typing import Optional, List, Dict, Union

from b2sdk.v2.exception import B2Error
from b2sdk.v2 import B2Api, InMemoryAccountInfo
from retry import retry

from src.core.constants import SecretKeys
from src.core.vault.hvault import VaultClient
import src.core.utils.functions as F

FILE = os.path.basename(__file__)
logger = F.get_logger(dump_to=FILE)


class B2Handler:
    _BUCKET_NAME = "linkedin-assistant"  # You might want to store this in vault or config

    def __init__(self):
        """
        Initialize B2 Cloud Storage handler
        """
        self.vault_client = VaultClient()
        self.api = None
        self.bucket = None

        self.authenticate()

    def _get_credentials(self) -> tuple[Optional[str], Optional[str]]:
        """
        Get B2 credentials from Vault
        
        Returns:
            tuple: (application_key_id, application_key) if successful, (None, None) otherwise
        """
        try:
            logger.info("Retrieving B2 credentials from vault")
            key_id = self.vault_client.get_secret(SecretKeys.B2_APPLICATION_KEY_ID_KEY)
            key = self.vault_client.get_secret(SecretKeys.B2_APPLICATION_KEY_KEY)
            if not key_id or not key:
                logger.error("No B2 credentials found in vault")
                return None, None
            logger.info("Successfully retrieved B2 credentials")
            return key_id, key
        except Exception as e:
            logger.error(f"Error retrieving B2 credentials: {str(e)}")
            return None, None

    def authenticate(self) -> bool:
        """
        Authenticate with B2 using credentials from Vault
        
        Returns:
            bool: True if authentication successful, False otherwise
        """
        try:
            logger.info("Authenticating with B2")
            key_id, key = self._get_credentials()
            if not key_id or not key:
                logger.error("Failed to get credentials for authentication")
                return False

            info = InMemoryAccountInfo()
            self.api = B2Api(info)
            self.api.authorize_account("production", key_id, key)
            self.bucket = self.api.get_bucket_by_name(self._BUCKET_NAME)
            logger.info("Successfully authenticated with B2")
            return True
        except B2Error as e:
            logger.error(f"B2 authentication error: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error connecting to B2: {str(e)}")
            return False

    @retry(B2Error, delay=1, tries=3)
    def upload_pdf_bytes(self, content: bytes, file_path: str) -> Optional[str]:
        """
        Upload PDF content directly to B2
        
        Args:
            content: PDF content as bytes
            file_path: B2 destination path
            
        Returns:
            str: B2 file ID if successful, None otherwise
        """
        if not self.api or not self.bucket:
            self.authenticate()

        try:
            if file_path.startswith('/'):
                file_path = file_path[1:]

            file_info = self.bucket.upload_bytes(
                data_bytes=content,
                file_name=file_path
            )
            return file_info.id_
        except B2Error as e:
            logger.error(f"B2 error uploading file: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error uploading file: {str(e)}")
            return None

    @retry(B2Error, delay=1, tries=3)
    def upload_pdf(self, file_path: str, b2_path: str = None) -> Optional[str]:
        """
        Upload a PDF file to B2
        
        Args:
            file_path: Local path to PDF file
            b2_path: B2 destination path (optional)
            
        Returns:
            str: B2 file ID if successful, None otherwise
        """
        if not self.api or not self.bucket:
            self.authenticate()

        try:
            if not b2_path:
                b2_path = os.path.basename(file_path)
            elif b2_path.startswith('/'):
                b2_path = b2_path[1:]

            with open(file_path, 'rb') as f:
                content = f.read()
                return self.upload_pdf_bytes(content, b2_path)
        except Exception as e:
            logger.error(f"Error reading file: {str(e)}")
            return None

    @retry(B2Error, delay=1, tries=3)
    def download_pdf(self, file_path: str, download_path: str) -> bool:
        """
        Download a PDF file from B2
        
        Args:
            file_path: B2 file path
            download_path: Local path to save file
            
        Returns:
            bool: True if download successful, False otherwise
        """
        if not self.api or not self.bucket:
            self.authenticate()

        try:
            if file_path.startswith('/'):
                file_path = file_path[1:]

            download_dest = open(download_path, 'wb')
            self.bucket.download_file_by_name(file_path, download_dest)
            download_dest.close()
            return True
        except B2Error as e:
            logger.error(f"B2 error downloading file: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error downloading file: {str(e)}")
            return False

    @retry(B2Error, delay=1, tries=3)
    def list_folder_contents(self, folder_path: str = "") -> List[Dict[str, Union[str, int]]]:
        """
        List contents of a B2 folder
        
        Args:
            folder_path: B2 folder path (optional)
            
        Returns:
            List[Dict]: List of items in folder with their details
        """
        if not self.api or not self.bucket:
            self.authenticate()

        try:
            if folder_path.startswith('/'):
                folder_path = folder_path[1:]

            items = []
            for file_version, folder_name in self.bucket.ls(folder_path):
                item = {
                    'id': file_version.id_,
                    'name': os.path.basename(file_version.file_name),
                    'path': file_version.file_name,
                    'type': 'file',
                    'size': file_version.size
                }
                items.append(item)

            return items
        except B2Error as e:
            logger.error(f"B2 error listing folder contents: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Error listing folder contents: {str(e)}")
            return []

    @retry(B2Error, delay=1, tries=3)
    def delete_file(self, file_path: str) -> bool:
        """
        Delete a file from B2
        
        Args:
            file_path: B2 file path
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        if not self.api or not self.bucket:
            self.authenticate()

        try:
            if file_path.startswith('/'):
                file_path = file_path[1:]

            file_version = self.bucket.get_file_info_by_name(file_path)
            self.bucket.delete_file_version(file_version.id_, file_path)
            return True
        except B2Error as e:
            logger.error(f"B2 error deleting file: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error deleting file: {str(e)}")
            return False

    @retry(B2Error, delay=1, tries=3)
    def move_file(self, from_path: str, to_path: str) -> bool:
        """
        Move a file within B2
        
        Args:
            from_path: Source path in B2
            to_path: Target path in B2
            
        Returns:
            bool: True if move successful, False otherwise
        """
        if not self.api or not self.bucket:
            self.authenticate()

        try:
            if from_path.startswith('/'):
                from_path = from_path[1:]
            if to_path.startswith('/'):
                to_path = to_path[1:]

            # B2 doesn't have a direct move operation, so we need to copy and delete
            file_version = self.bucket.get_file_info_by_name(from_path)
            self.bucket.copy_file(file_version.id_, to_path)
            self.bucket.delete_file_version(file_version.id_, from_path)
            return True
        except B2Error as e:
            logger.error(f"B2 error moving file: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error moving file: {str(e)}")
            return False
