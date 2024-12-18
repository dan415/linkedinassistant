"""
Custom exceptions for the vault module.
These exceptions are used to handle specific error cases when interacting with the HashiCorp Vault.
"""

class VaultError(Exception):
    """Base exception class for all vault-related errors."""
    def __init__(self, message: str = None, response = None):
        self.message = message or "An error occurred while interacting with the vault"
        self.response = response
        super().__init__(self.message)


class AuthenticationError(VaultError):
    """
    Raised when authentication with the vault fails.
    
    This can happen when:
    - The access token is invalid or expired
    - The client credentials are incorrect
    - The authentication service is unavailable
    """
    def __init__(self, message: str = None, response = None):
        super().__init__(
            message or "Failed to authenticate with the vault. Please check your credentials.",
            response
        )


class ResourceNotFoundException(VaultError):
    """
    Raised when a requested secret or resource is not found in the vault.
    
    This can happen when:
    - The secret key does not exist
    - The path to the secret is incorrect
    - The user doesn't have permission to access the secret
    """
    def __init__(self, message: str = None, response = None):
        super().__init__(
            message or "The requested resource was not found in the vault",
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


class RateLimitError(VaultError):
    """
    Raised when the vault API rate limit is exceeded.
    
    This can happen when:
    - Too many requests are made in a short time period
    - The API quota has been exceeded
    """
    def __init__(self, message: str = None, response = None):
        super().__init__(
            message or "Rate limit exceeded. Please reduce the frequency of requests.",
            response
        )