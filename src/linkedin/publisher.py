from typing import Optional, Dict, Any
import requests
from src.core.config.manager import ConfigManager
from src.core.vault.hashicorp import VaultClient
from src.core.exceptions import VaultError
from ..core.constants import SecretKeys
import logging
from ..core.utils.logging import ServiceLogger


class LinkedinPublisher:
    """
    Publishes content to LinkedIn.
    """

    _LINKEDIN_CONFIG_SCHEMA = "linkedin"
    _LINKEDIN_REGISTER_UPLOAD_URL = (
        "https://api.linkedin.com/v2/assets?action=registerUpload"
    )
    _LINKEDIN_SHARE_URL = "https://api.linkedin.com/v2/ugcPosts"

    def __init__(
        self, logger: Optional[logging.Logger] = ServiceLogger(__name__)
    ) -> None:
        # Initialize configuration and secrets for LinkedIn API access
        self.logger = logger
        self.client_id: str = ""
        self.client_secret: str = ""
        self.redirect_uri: str = ""
        self.linkedin_id: str = ""
        self.access_token: Optional[str] = None  # Token for API authentication
        self.footer: str = ""  # Footer added to posts
        self.config_client: ConfigManager = ConfigManager()
        self.vault_client: VaultClient = VaultClient()
        self.reload_config()

    def needs_auth(self) -> bool:
        """
        Check if the publisher needs to get the authorization.
        Returns True if the access token is not available.
        """
        self.reload_config()
        return not self.access_token

    def _build_post_data(
        self, content: str, asset: Optional[str]
    ) -> Dict[str, Any]:
        """
        Build the data payload for a LinkedIn post.
        :param content:  Text content of the post.
        :param asset:  Media asset ID for the post.
        :return: Dictionary of post data.
        """
        post_data: Dict[str, Any] = {
            "author": f"urn:li:person:{self.linkedin_id}",
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": f"{content}\n\n{self.footer}"},
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            },
        }

        # Add media if provided
        if asset:
            post_data["specificContent"]["com.linkedin.ugc.ShareContent"][
                "shareMediaCategory"
            ] = "IMAGE"
            post_data["specificContent"]["com.linkedin.ugc.ShareContent"][
                "media"
            ] = [
                {
                    "status": "READY",
                    "description": {"text": "Generated image for the post"},
                    "media": asset,
                }
            ]
        else:
            post_data["specificContent"]["com.linkedin.ugc.ShareContent"][
                "shareMediaCategory"
            ] = "NONE"

        return post_data

    def _post(self, content: str, asset: Optional[str]) -> bool:
        """
        Post content to LinkedIn. If no access token is present, it logs an error.

        :param content: Text content to post.
        :param asset: Optional media asset to include in the post.
        :return: True if successful, False otherwise.
        """
        self.reload_config()

        if not self.access_token:
            self.logger.error("No access token available")
            return False

        # Construct the data payload for the LinkedIn API
        post_data = self._build_post_data(content, asset)
        try:
            # Make the API call
            response = requests.post(
                self._LINKEDIN_SHARE_URL,
                headers=self.get_headers(),
                json=post_data,
                timeout=10,
            )
            if response.status_code == 201:
                self.logger.info("Posted to LinkedIn")
                return True
            else:
                self.logger.error(
                    f"Failed to post: {response.status_code} - {response.text}"
                )
                self.access_token = None  # Invalidate token on failure
                self.update_config()
                return False
        except Exception as e:
            self.logger.error(f"Failed to post: {str(e)}")
            return False

    def get_headers(
        self, content_type: Optional[str] = "application/json"
    ) -> Dict[str, str]:
        """
        Generate headers for the API request, including the access token.

        :param content_type: Content-Type header value.
        :return: Dictionary of headers.
        """
        res: Dict[str, str] = {"Authorization": f"Bearer {self.access_token}"}
        if content_type:
            res["Content-Type"] = content_type
        return res

    def register_image_upload(self) -> Dict[str, Any]:
        """
        Register an image upload with LinkedIn to get an upload URL.

        :return: JSON response containing the upload information.
        """
        register_upload_body: Dict[str, Any] = {
            "registerUploadRequest": {
                "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                "owner": f"urn:li:person:{self.linkedin_id}",
                "serviceRelationships": [
                    {
                        "relationshipType": "OWNER",
                        "identifier": "urn:li:userGeneratedContent",
                    }
                ],
            }
        }

        upload_response = requests.post(
            self._LINKEDIN_REGISTER_UPLOAD_URL,
            json=register_upload_body,
            headers=self.get_headers(),
        )
        upload_response.raise_for_status()  # Raise exception for HTTP errors
        return upload_response.json()

    def upload_image(self, image_data: bytes) -> str:
        """
        Upload an image to LinkedIn and return the asset ID.

        :param image_data: Binary data of the image to upload.
        :return: Asset ID of the uploaded image.
        """
        # Register the upload and get the upload URL
        upload_data = self.register_image_upload()

        # Extract upload details
        asset: str = upload_data["value"]["asset"]
        upload_url: str = upload_data["value"]["uploadMechanism"][
            ("com.linkedin.digitalmedia.uploading" ".MediaUploadHttpRequest")
        ]["uploadUrl"]

        # Perform the binary upload
        self.logger.debug(f"Uploading image to {upload_url}")
        binary_upload_response = requests.post(
            upload_url,
            data=image_data,
            headers=self.get_headers(content_type=None),
        )
        if binary_upload_response.status_code != 201:
            self.logger.error(
                f"Image upload failed: {binary_upload_response.status_code} - {binary_upload_response.text}"
            )
            binary_upload_response.raise_for_status()
        return asset

    def publish(self, content: str, image_data: Optional[bytes] = None) -> bool:
        """
        Publish content with an image to LinkedIn.

        :param content: The text content to post.
        :param image_data: Binary data of the image to upload.
        :return: True if successful, False otherwise.
        """
        if self.needs_auth():
            return False

        self.logger.info(
            f"Publishing post with image? {image_data is not None}"
        )
        asset = None
        try:
            if image_data:
                asset = self.upload_image(image_data)
            return self._post(content, asset)

        except Exception as e:
            self.logger.error(f"Failed to publish with image: {str(e)}")
            return False

    def update_config(self):
        """
        Update the configuration by saving current attributes to the config file.
        """
        self.logger.debug("Updating config")
        config = self.config_client.load_config(self._LINKEDIN_CONFIG_SCHEMA)
        new_config: Dict[str, Any] = {}
        for key in config.keys():
            new_config[key] = self.__getattribute__(key)

        self.config_client.save_config(self._LINKEDIN_CONFIG_SCHEMA, config)

    def reload_config(self):
        """
        Reload the configuration from the config file and update secrets.
        """
        self.logger.debug("Reloading config")
        config = self.config_client.load_config(self._LINKEDIN_CONFIG_SCHEMA)
        for key in config.keys():
            self.__setattr__(key, config[key])

        # Load secrets from the vault
        self.client_id = self.vault_client.get_secret(
            SecretKeys.LINKEDIN_CLIENT_ID
        )
        self.client_secret = self.vault_client.get_secret(
            SecretKeys.LINKEDIN_CLIENT_SECRET
        )
        self.redirect_uri = "https://" + self.vault_client.get_secret(
            SecretKeys.NGROK_DOMAIN
        )
        self.linkedin_id = self.vault_client.get_secret(SecretKeys.LINKEDIN_ID)
        try:
            self.access_token = self.vault_client.get_secret(
                SecretKeys.LINKEDIN_ACCESS_TOKEN
            )
        except VaultError as ex:
            self.logger.warning(f"Access token not found in vault: {ex}")
            self.access_token = None
