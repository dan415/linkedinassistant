import io
import os
from abc import ABC, abstractmethod

import PyPDF2
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.types.io import DocumentStream

import src.core.utils.functions as F
from src.core.config.manager import ConfigManager

FILE = os.path.basename(__file__)
logger = F.get_logger(dump_to=FILE)


class PDFExtractor(ABC):
    """Extracts text from PDF files using PyPDF2."""

    @abstractmethod
    def extract(self, pdf_bytes):
        """Extracts text from PDF file using PyPDF2.
        
        :param pdf_bytes: PDF file content as bytes
        :return: Extracted text as string
        """
        pass


class PyPDFE2xtractor(PDFExtractor):
    """Extracts text from PDF files using PyPDF2."""

    def __init__(self):
        pass

    def extract(self, pdf_bytes):
        """Extracts text from PDF file using PyPDF2.

        :param pdf_bytes: PDF file content as bytes
        :return: Extracted text as string
        """
        logger.info("Extracting text from PDF file using PyPDF2")

        try:
            pdf_file = io.BytesIO(pdf_bytes)
            pdf_reader = PyPDF2.PdfReader(pdf_file)

            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"

            return text

        except Exception as e:
            logger.error(f"Error extracting text from PDF: {str(e)}")
            raise


class DoclingExtractor(PDFExtractor):
    """Extracts text from PDF files using PyPDF2."""

    _CONFIG_SCHEMA = "docling"

    def __init__(self):
        config_manager = ConfigManager()
        config = config_manager.load_config(self._CONFIG_SCHEMA)
        table_former_mode = F.get_enum_from_value(config.pop("table_former_mode", "fast"), TableFormerMode)

        pipeline_options = PdfPipelineOptions(**config)
        pipeline_options.table_structure_options.mode = table_former_mode

        self.doc_converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )

    def extract(self, pdf_bytes):
        """Extracts text from PDF file using PyPDF2.

        :param pdf_bytes: PDF file content as bytes
        :return: Extracted text as string
        """
        logger.info("Extracting text from PDF file using PyPDF2")

        try:
            result = self.doc_converter.convert(pdf_bytes)
            return result.document.export_to_markdown()

        except Exception as e:
            logger.error(f"Error extracting text from PDF: {str(e)}")
            raise



