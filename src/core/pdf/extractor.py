import base64
import io
from abc import ABC, abstractmethod
import pypdf
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    TableFormerMode,
    AcceleratorOptions,
)
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.types.io import DocumentStream
import src.core.utils.functions as F
from src.core.config.manager import ConfigManager


class PDFExtractor(ABC):
    """Abstract base class for extracting text from PDF files."""

    def __int__(self):
        self.extracted_images = []

    @abstractmethod
    def extract(self, pdf_bytes):
        """Extracts text from a PDF file.

        :param pdf_bytes: PDF file content as bytes
        :return: Extracted text as string
        """
        pass


class PyPDFExtractor(PDFExtractor):
    """Extracts text from PDF files using PyPDF2."""

    def extract(self, pdf_bytes):
        """Extracts text from a PDF file using PyPDF2.

        :param pdf_bytes: PDF file content as bytes
        :return: Extracted text as string
        """

        pdf_file = io.BytesIO(pdf_bytes)
        pdf_reader = pypdf.PdfReader(pdf_file)

        text = "".join(page.extract_text() + "\n" for page in pdf_reader.pages)
        return text


class DoclingExtractor(PDFExtractor):
    """Extracts text from PDF files using Docling's DocumentConverter."""

    _CONFIG_SCHEMA = "docling"

    def __init__(self):
        super().__init__()
        config_manager = ConfigManager()
        config = config_manager.load_config(self._CONFIG_SCHEMA)

        table_former_mode = F.get_enum_from_value(
            config.pop("table_former_mode", "fast"), TableFormerMode
        )

        accelerator_options = AcceleratorOptions(
            **config.pop("accelerator_options", {})
        )
        pipeline_options = PdfPipelineOptions(**config)
        pipeline_options.accelerator_options = accelerator_options
        pipeline_options.table_structure_options.mode = table_former_mode

        self.doc_converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=pipeline_options
                )
            }
        )

    def extract(self, pdf_bytes):
        """Extracts text from a PDF file using Docling's DocumentConverter.

        :param pdf_bytes: PDF file content as bytes
        :return: Extracted text as string
        """

        buf = io.BytesIO(pdf_bytes)
        source = DocumentStream(name="tmp.pdf", stream=buf)
        result = self.doc_converter.convert(source)
        self.extracted_images = list(
            map(
                lambda x: base64.b64decode(
                    x.image.uri.unicode_string().split(",")[1]
                ),
                filter(lambda y: len(y.captions) > 0, result.document.pictures),
            )
        )
        return result.document.export_to_markdown()
