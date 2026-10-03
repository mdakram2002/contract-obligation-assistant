import pytest
from app.services.document_parser import DocumentParser


class TestDocumentParser:
    """Tests for document parsing functionality."""

    def test_validate_pdf_file_type(self):
        """Test PDF file type validation."""
        # Valid PDF
        pdf_content = b"%PDF-1.4\nsome content"
        file_type = DocumentParser.validate_file_type("test.pdf", pdf_content)
        assert file_type == "pdf"

    def test_validate_docx_file_type(self):
        """Test DOCX file type validation."""
        # Valid DOCX (starts with PK signature)
        docx_content = b"PK\x03\x04\n\x00\x00\x00"
        file_type = DocumentParser.validate_file_type("test.docx", docx_content)
        assert file_type == "docx"

    def test_validate_invalid_file_type(self):
        """Test invalid file type raises error."""
        invalid_content = b"not a valid file"
        with pytest.raises(ValueError, match="Unsupported file type"):
            DocumentParser.validate_file_type("test.txt", invalid_content)

    def test_validate_pdf_with_wrong_extension(self):
        """Test PDF content with wrong extension is rejected."""
        pdf_content = b"%PDF-1.4\nsome content"
        with pytest.raises(ValueError, match="File extension does not match content"):
            DocumentParser.validate_file_type("test.docx", pdf_content)

    def test_parse_text(self):
        """Test text parsing."""
        text = "Sample contract text\nLine 2\nLine 3"
        parsed_text, metadata = DocumentParser.parse_text(text)

        assert parsed_text == text
        assert metadata is not None
        assert "char_count" in metadata
        assert metadata["char_count"] == len(text)

    def test_parse_empty_text(self):
        """Test empty text parsing."""
        with pytest.raises(ValueError, match="Text cannot be empty"):
            DocumentParser.parse_text("")

    def test_parse_text_whitespace_only(self):
        """Test whitespace-only text parsing."""
        with pytest.raises(ValueError, match="Text cannot be empty"):
            DocumentParser.parse_text("   \n\n   ")

    def test_parse_pdf_not_implemented(self):
        """Test PDF parsing (mock test - actual parsing requires PyMuPDF)."""
        # This is a placeholder test - actual PDF parsing would require sample PDF files
        # In a real test suite, you would use fixture PDF files
        pdf_content = b"%PDF-1.4\nsome content"
        with pytest.raises(Exception):
            DocumentParser.parse_document(pdf_content, "pdf")

    def test_parse_docx_not_implemented(self):
        """Test DOCX parsing (mock test - actual parsing requires python-docx)."""
        # This is a placeholder test - actual DOCX parsing would require sample DOCX files
        docx_content = b"PK\x03\x04\n\x00\x00\x00"
        with pytest.raises(Exception):
            DocumentParser.parse_document(docx_content, "docx")
