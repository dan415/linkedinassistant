import os
from abc import ABC

from src.core.constants import SecretKeys
from src.information.sources.information_source import ContentSearchEngine
from src.core.vault.hvault import VaultClient
import src.core.utils.functions as F

FILE = os.path.basename(__file__)
logger = F.get_logger(dump_to=FILE)


class RapidSource(ContentSearchEngine, ABC):
    """
    At the begginnin, I thought that the counter of requests should be shared between all the rapidapi sources, but it seems that
    every api subscription has its own request limit (so I made them inherit from a singleton, so I will leave this code here just in case. Anyhow it serves for any common behaviour
    rapid api sources might share.
    """

    def __init__(self, information_source):
        super().__init__(information_source)

    def get_api_key(self):
        return VaultClient().get_secret(SecretKeys.RAPID_API_KEY)
