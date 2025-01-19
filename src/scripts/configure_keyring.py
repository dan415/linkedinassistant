import sys
from dotenv import load_dotenv
from src.core.exceptions import ConfigurationError
from src.core.vault.hashicorp import VaultConfig
from pydantic import ValidationError

load_dotenv()


def configure_keyring():
    vault_config = None
    try:
        vault_config = VaultConfig.from_keyring()
    except ConfigurationError:
        print("Necessary Vault keys not found on keyring, attempting loading from environment to save them"
              "on the keyring")
    if vault_config:
        print("Vault config keys found on keyring")
        return

    try:
        vault_config = VaultConfig.from_environment()
        vault_config.save_on_keyring()
        print("Vault config keys saved on keyring")
    except ValidationError:
        print("ERROR: Could not save Vault Keys on keyring", file=sys.stderr)
        raise


if __name__ == '__main__':
    print("Configuring keyring")
    configure_keyring()
    print("Keyring configured successfully")
