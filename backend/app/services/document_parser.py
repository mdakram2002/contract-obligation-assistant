import fitz  # PyMuPDF
from docx import Document
from io import BytesIO
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class DocumentParser:
    """Parse PDF, DOCX, and plain text documents."""

    @staticmethod
    def parse_pdf(file_bytes: bytes) -> Tuple[str, Optional[dict]]:
        """
        Extract text from PDF with page information.
        Returns (text, metadata) where metadata contains page information.
        """
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            text_parts = []
            page_info = []

            for page_num in range(len(doc)):
                page = doc[page_num]
                page_text = page.get_text()
                if page_text.strip():
                    text_parts.append(f"[PAGE {page_num + 1}]\n{page_text}")
                    page_info.append({
                        "page_number": page_num + 1,
                        "char_count": len(page_text)
                    })

            full_text = "\n\n".join(text_parts)
            if not full_text.strip():
                raise ValueError("PDF contains no extractable text")
            metadata = {
                "type": "pdf",
                "total_pages": len(doc),
                "pages": page_info
            }

            logger.info(f"PDF parsed: {len(doc)} pages")
            doc.close()
            return full_text, metadata

        except Exception as e:
            logger.error(f"PDF parsing failed: {str(e)}")
            raise ValueError(f"Failed to parse PDF: {str(e)}")

    @staticmethod
    def parse_docx(file_bytes: bytes) -> Tuple[str, Optional[dict]]:
        """
        Extract text from DOCX with paragraph/heading information.
        Returns (text, metadata) where metadata contains structure information.
        """
        try:
            doc = Document(BytesIO(file_bytes))
            text_parts = []
            paragraph_info = []

            for i, para in enumerate(doc.paragraphs):
                if para.text.strip():
                    text_parts.append(para.text)
                    paragraph_info.append({
                        "index": i,
                        "style": para.style.name if para.style else "Normal",
                        "length": len(para.text)
                    })

            for table in doc.tables:
                for row in table.rows:
                    cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                    if cells:
                        text_parts.append(" | ".join(cells))

            full_text = "\n\n".join(text_parts)
            if not full_text.strip():
                raise ValueError("DOCX contains no extractable text")
            metadata = {
                "type": "docx",
                "total_paragraphs": len(doc.paragraphs),
                "paragraphs": paragraph_info
            }

            logger.info(f"DOCX parsed: {len(doc.paragraphs)} paragraphs")
            return full_text, metadata

        except Exception as e:
            logger.error(f"DOCX parsing failed: {str(e)}")
            raise ValueError(f"Failed to parse DOCX: {str(e)}")

    @staticmethod
    def parse_text(text: str) -> Tuple[str, Optional[dict]]:
        """
        Process pasted text with deterministic section identifiers.
        Returns (text, metadata) where metadata contains structure information.
        """
        try:
            if not text or not text.strip():
                raise ValueError("Text cannot be empty")
            lines = text.split('\n')
            sections = []
            current_section = []
            section_count = 0

            for line in lines:
                if line.strip():
                    current_section.append(line)
                else:
                    if current_section:
                        sections.append('\n'.join(current_section))
                        current_section = []
                        section_count += 1

            if current_section:
                sections.append('\n'.join(current_section))
                section_count += 1

            # If no empty lines, treat entire text as one section
            if not sections and text.strip():
                sections = [text]
                section_count = 1

            full_text = '\n\n'.join(sections)
            metadata = {
                "type": "text",
                "char_count": len(full_text),
                "total_sections": section_count,
                "sections": [{"index": i, "length": len(s)} for i, s in enumerate(sections)]
            }

            logger.info(f"Text parsed: {section_count} sections")
            return full_text, metadata

        except Exception as e:
            logger.error(f"Text parsing failed: {str(e)}")
            raise ValueError(f"Failed to parse text: {str(e)}")

    @staticmethod
    def parse_document(file_bytes: bytes, file_type: str) -> Tuple[str, Optional[dict]]:
        """
        Parse document based on file type.
        Returns (text, metadata).
        """
        if file_type == 'pdf':
            return DocumentParser.parse_pdf(file_bytes)
        elif file_type == 'docx':
            return DocumentParser.parse_docx(file_bytes)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

    @staticmethod
    def validate_file_type(filename: str, file_bytes: bytes) -> str:
        """
        Validate file type and return extension.
        Raises ValueError for unsupported types.
        """
        filename_lower = filename.lower()

        if filename_lower.endswith('.pdf'):
            # Quick validation: check PDF signature
            if file_bytes[:4] == b'PK\x03\x04':
                raise ValueError("File extension does not match content")
            if file_bytes[:4] != b'%PDF':
                raise ValueError("Invalid PDF file")
            return 'pdf'
        elif filename_lower.endswith('.docx'):
            # Quick validation: check DOCX signature
            if file_bytes[:4] == b'%PDF':
                raise ValueError("File extension does not match content")
            if file_bytes[:4] != b'PK\x03\x04':
                raise ValueError("Invalid DOCX file")
            return 'docx'
        else:
            raise ValueError(f"Unsupported file type: {filename}")
