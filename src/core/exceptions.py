"""
Custom exceptions for the vault module.
These exceptions are used to handle specific error cases when interacting with the HashiCorp Vault.
"""


class VaultError(Exception):
    def __init__(
            self, message=None, errors=None, method=None, url=None, text=None, json=None
    ):
        if errors:
            message = ", ".join(errors)

        self.errors = errors
        self.method = method
        self.url = url
        self.text = text
        self.json = json

        super().__init__(message)

    def __str__(self):
        return f"{self.args[0]}, on {self.method} {self.url}"

    @classmethod
    def from_status(cls, status_code: int, *args, **kwargs):
        _STATUS_EXCEPTION_MAP = {
            400: InvalidRequest,
            401: Unauthorized,
            403: Forbidden,
            404: InvalidPath,
            429: RateLimitExceeded,
            500: InternalServerError,
            501: VaultNotInitialized,
            502: BadGateway,
            503: VaultDown,
        }

        return _STATUS_EXCEPTION_MAP.get(status_code, UnexpectedError)(*args, **kwargs)


class InvalidRequest(VaultError):
    pass


class Unauthorized(VaultError):
    pass


class Forbidden(VaultError):
    pass


class InvalidPath(VaultError):
    pass


class UnsupportedOperation(VaultError):
    pass


class PreconditionFailed(VaultError):
    pass


class RateLimitExceeded(VaultError):
    pass


class InternalServerError(VaultError):
    pass


class VaultNotInitialized(VaultError):
    pass


class VaultDown(VaultError):
    pass


class UnexpectedError(VaultError):
    pass


class BadGateway(VaultError):
    pass


class ParamValidationError(VaultError):
    pass


class AuthenticationError(VaultError):
    """
    Raised when authentication with the vault fails.
    
    This can happen when:
    - The access token is invalid or expired
    - The client credentials are incorrect
    - The authentication service is unavailable
    """

    def __init__(self, message: str = None, response=None):
        super().__init__(
            message or "Failed to authenticate with the vault. Please check your credentials.",
            response
        )


class ConfigurationError(VaultError):
    """
    Raised when there are issues with the vault configuration.
    
    This can happen when:
    - Required environment variables are missing
    - Configuration values are invalid
    - The vault endpoint URL is incorrect
    """

    def __init__(self, message: str = None):
        super().__init__(
            message or "Invalid vault configuration. Please check your environment variables and settings."
        )


class FetchFileException(Exception):
    """
    Raised when a file fetch operation from Telegram fails.
    """

    def __init__(self, result):
        self.result = result
        self.message = f"Failed to fetch file from Telegram: {result}"
        super().__init__(self.message)


class DownloadFileException(Exception):
    """
    Raised when a file download operation from Telegram fails.
    """

    def __init__(self, result):
        self.result = result
        self.message = f"Failed to download file from Telegram: {result}"
        super().__init__(self.message)
