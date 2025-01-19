from enum import Enum
import src.core.utils.functions as F
from src.core.pdf.extractor import PyPDFExtractor, DoclingExtractor


class Provider(Enum):
    PYPDF = "pypdf"
    DOCLING = "docling"


class PDFExtractorProvider:

    @classmethod
    def build(cls, provider: Provider | str):
        """Get a content search engine for the information source."""
        if isinstance(provider, str):
            provider = F.get_enum_from_value(provider, Provider)

        if provider == Provider.PYPDF:
            return PyPDFExtractor()
        if provider == Provider.DOCLING:
            return DoclingExtractor()
        else:
            raise ValueError("PDF provider not supported")
