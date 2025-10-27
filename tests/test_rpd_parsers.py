"""
Tests for RPD parsers
"""

import pytest
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from rpd.parsers import (
    FileTypeDetector, BaseRPDParser, PDFRPDParser, WordRPDParser, 
    ExcelRPDParser, RPDParserFactory, RPDParsingError
)


class TestFileTypeDetector:
    """Test file type detection"""
    
    def test_detect_by_extension_pdf(self):
        """Test PDF detection by extension"""
        result = FileTypeDetector.detect_file_type("document.pdf")
        assert result == "pdf"
    
    def test_detect_by_extension_docx(self):
        """Test DOCX detection by extension"""
        result = FileTypeDetector.detect_file_type("document.docx")
        assert result == "docx"
    
    def test_detect_by_extension_xlsx(self):
        """Test XLSX detection by extension"""
        result = FileTypeDetector.detect_file_type("document.xlsx")
        assert result == "xlsx"
    
    def test_detect_unknown_extension(self):
        """Test unknown file type"""
        result = FileTypeDetector.detect_file_type("document.txt")
        assert result == "unknown"
    
    def test_detect_case_insensitive(self):
        """Test case insensitive detection"""
        result = FileTypeDetector.detect_file_type("DOCUMENT.PDF")
        assert result == "pdf"


class TestBaseRPDParser:
    """Test base parser functionality"""
    
    def test_base_parser_not_implemented(self):
        """Test that base parser raises NotImplementedError"""
        parser = BaseRPDParser()
        
        with pytest.raises(NotImplementedError):
            parser.parse("test.pdf")


class TestPDFRPDParser:
    """Test PDF parser"""
    
    def test_pdf_parser_initialization(self):
        """Test PDF parser can be initialized"""
        try:
            parser = PDFRPDParser()
            assert parser.supported_extensions == ['pdf']
        except ImportError:
            pytest.skip("PyPDF2 not available")
    
    def test_pdf_parser_can_parse_pdf(self):
        """Test PDF parser can handle PDF files"""
        try:
            parser = PDFRPDParser()
            assert parser.can_parse("document.pdf") == True
            assert parser.can_parse("document.docx") == False
        except ImportError:
            pytest.skip("PyPDF2 not available")
    
    def test_pdf_parser_file_not_found(self):
        """Test PDF parser handles missing files"""
        try:
            parser = PDFRPDParser()
            
            with pytest.raises(RPDParsingError, match="File not found"):
                parser.parse("nonexistent.pdf")
        except ImportError:
            pytest.skip("PyPDF2 not available")


class TestWordRPDParser:
    """Test Word document parser"""
    
    def test_word_parser_initialization(self):
        """Test Word parser can be initialized"""
        try:
            parser = WordRPDParser()
            assert parser.supported_extensions == ['docx', 'doc']
        except ImportError:
            pytest.skip("python-docx not available")
    
    def test_word_parser_can_parse_docx(self):
        """Test Word parser can handle DOCX files"""
        try:
            parser = WordRPDParser()
            assert parser.can_parse("document.docx") == True
            assert parser.can_parse("document.pdf") == False
        except ImportError:
            pytest.skip("python-docx not available")


class TestExcelRPDParser:
    """Test Excel parser"""
    
    def test_excel_parser_initialization(self):
        """Test Excel parser can be initialized"""
        try:
            parser = ExcelRPDParser()
            assert parser.supported_extensions == ['xlsx', 'xls']
        except ImportError:
            pytest.skip("pandas not available")
    
    def test_excel_parser_can_parse_xlsx(self):
        """Test Excel parser can handle XLSX files"""
        try:
            parser = ExcelRPDParser()
            assert parser.can_parse("document.xlsx") == True
            assert parser.can_parse("document.pdf") == False
        except ImportError:
            pytest.skip("pandas not available")


class TestRPDParserFactory:
    """Test parser factory"""
    
    def test_factory_initialization(self):
        """Test factory can be initialized"""
        factory = RPDParserFactory()
        assert isinstance(factory.parsers, dict)
    
    def test_factory_get_supported_formats(self):
        """Test getting supported formats"""
        factory = RPDParserFactory()
        formats = factory.get_supported_formats()
        
        expected_formats = ['pdf', 'docx', 'doc', 'xlsx', 'xls']
        for fmt in expected_formats:
            assert fmt in formats
    
    def test_factory_unsupported_format(self):
        """Test factory handles unsupported formats"""
        factory = RPDParserFactory()
        
        with pytest.raises(RPDParsingError, match="Unsupported file type"):
            factory.get_parser("document.txt")
    
    @patch('rpd.parsers.PDFRPDParser')
    def test_factory_get_pdf_parser(self, mock_pdf_parser):
        """Test factory returns PDF parser for PDF files"""
        factory = RPDParserFactory()
        
        # Mock the parser class
        mock_instance = Mock()
        mock_pdf_parser.return_value = mock_instance
        
        parser = factory.get_parser("document.pdf")
        
        mock_pdf_parser.assert_called_once()
        assert parser == mock_instance
    
    def test_factory_parse_rpd_integration(self):
        """Test factory parse_rpd method"""
        factory = RPDParserFactory()
        
        # This should raise an error for non-existent file
        with pytest.raises(RPDParsingError):
            factory.parse_rpd("nonexistent.pdf")


class TestRPDParsingIntegration:
    """Integration tests for RPD parsing"""
    
    def test_parse_rpd_document_function(self):
        """Test the convenience function"""
        from rpd.parsers import parse_rpd_document
        
        # Should raise error for non-existent file
        with pytest.raises(RPDParsingError):
            parse_rpd_document("nonexistent.pdf")
    
    def test_mock_pdf_parsing(self):
        """Test PDF parsing with mock data"""
        try:
            from rpd.parsers import PDFRPDParser
            
            # Create a mock PDF file for testing
            with patch('builtins.open'), \
                 patch('rpd.parsers.PyPDF2.PdfReader') as mock_reader:
                
                # Mock PDF reader
                mock_pdf = Mock()
                mock_pdf.metadata = {'/Title': 'Test RPD', '/Author': 'Test Author'}
                mock_pdf.pages = [Mock()]
                mock_pdf.pages[0].extract_text.return_value = "Test content"
                mock_reader.return_value = mock_pdf
                
                parser = PDFRPDParser()
                
                # Mock file existence
                with patch('pathlib.Path.exists', return_value=True):
                    result = parser.parse("test.pdf")
                
                assert result['file_type'] == 'pdf'
                assert result['metadata']['title'] == 'Test RPD'
                assert result['pages'] == 1
                assert 'Test content' in result['raw_text']
                
        except ImportError:
            pytest.skip("PyPDF2 not available")
    
    def test_mock_word_parsing(self):
        """Test Word parsing with mock data"""
        try:
            from rpd.parsers import WordRPDParser
            
            with patch('rpd.parsers.Document') as mock_document:
                # Mock Word document
                mock_doc = Mock()
                mock_doc.core_properties.title = 'Test RPD'
                mock_doc.core_properties.author = 'Test Author'
                mock_doc.core_properties.created = None
                mock_doc.core_properties.modified = None
                mock_doc.core_properties.subject = 'Test Subject'
                
                # Mock paragraphs
                mock_paragraph = Mock()
                mock_paragraph.text = 'Test paragraph content'
                mock_paragraph.style.name = 'Normal'
                mock_doc.paragraphs = [mock_paragraph]
                
                # Mock tables
                mock_doc.tables = []
                
                mock_document.return_value = mock_doc
                
                parser = WordRPDParser()
                
                # Mock file existence
                with patch('pathlib.Path.exists', return_value=True):
                    result = parser.parse("test.docx")
                
                assert result['file_type'] == 'docx'
                assert result['metadata']['title'] == 'Test RPD'
                assert len(result['paragraphs']) == 1
                assert 'Test paragraph content' in result['raw_text']
                
        except ImportError:
            pytest.skip("python-docx not available")