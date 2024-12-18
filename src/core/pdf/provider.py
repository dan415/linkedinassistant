import os
from enum import Enum
import src.core.utils.functions as F
from src.core.pdf.extractor import PyPDFE2xtractor, DoclingExtractor

FILE = os.path.basename(__file__)
logger = F.get_logger(dump_to=FILE)


class Provider(Enum):
    PYPDF = "pypdf"
    DOCLING = "docling"


class PDFExtractorProvider:

    @classmethod
    def build(cls, provider: Provider | str):
        """Get a content search engine for the information source."""
        if isinstance(provider, str):
            provider = F.get_enum_from_value(provider, Provider)

        logger.info("Getting pdf provider engine for %s", provider)

        if provider == Provider.PYPDF:
            return PyPDFE2xtractor()
        if provider == Provider.DOCLING:
            return DoclingExtractor()
        else:
            raise ValueError("PDF provider not supported")

