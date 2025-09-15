"""Tests for file naming utilities."""

import pytest
from core.output.file_naming import chapter_index_from_h1, generate_chapter_filename


class TestChapterIndexFromH1:
    """Test the chapter_index_from_h1 function."""
    
    def test_simple_number(self):
        """Test extraction from simple numbered heading."""
        assert chapter_index_from_h1("3 Installation") == 3
        assert chapter_index_from_h1("1 Introduction") == 1
        assert chapter_index_from_h1("10 Advanced Topics") == 10
    
    def test_decimal_number(self):
        """Test extraction from decimal numbered heading."""
        assert chapter_index_from_h1("3.1 Requirements") == 3
        assert chapter_index_from_h1("1.2.3 Technical Details") == 1
        assert chapter_index_from_h1("5.0 Overview") == 5
    
    def test_with_markdown_hashes(self):
        """Test extraction from markdown formatted headings."""
        assert chapter_index_from_h1("# 2 Getting Started") == 2
        assert chapter_index_from_h1("## 4.1 Configuration") == 4
        assert chapter_index_from_h1("### 7.2.1 Details") == 7
    
    def test_with_dashes(self):
        """Test extraction from headings with dashes."""
        assert chapter_index_from_h1("2-1 Section A") == 2
        assert chapter_index_from_h1("3-2-1 Subsection") == 3
    
    def test_no_number(self):
        """Test headings without numbers return default."""
        assert chapter_index_from_h1("Introduction") == 1
        assert chapter_index_from_h1("Getting Started") == 1
        assert chapter_index_from_h1("# Overview") == 1
    
    def test_invalid_numbers(self):
        """Test headings with invalid numbers return default."""
        assert chapter_index_from_h1("abc Introduction") == 1
        assert chapter_index_from_h1("I.V Introduction") == 1  # Roman numerals not supported
        assert chapter_index_from_h1("@#$ Invalid") == 1
    
    def test_empty_or_whitespace(self):
        """Test empty or whitespace-only headings."""
        assert chapter_index_from_h1("") == 1
        assert chapter_index_from_h1("   ") == 1
        assert chapter_index_from_h1("###   ") == 1
    
    def test_number_without_text(self):
        """Test headings that are just numbers."""
        assert chapter_index_from_h1("5") == 1  # No text after number
        assert chapter_index_from_h1("3.2") == 1  # No text after number


class TestGenerateChapterFilename:
    """Test the generate_chapter_filename function."""
    
    def test_title_page_index_zero(self):
        """Test that index 0 always generates 00 prefix."""
        result = generate_chapter_filename(0, "Table of Contents")
        assert result.startswith("00-")
        assert "table-of-contents" in result
        
        result = generate_chapter_filename(0, "5 Should Be Ignored")
        assert result.startswith("00-")
    
    def test_simple_numbered_title(self):
        """Test with simple numbered titles."""
        result = generate_chapter_filename(1, "3 Installation Guide")
        assert result.startswith("03-")
        assert "installation-guide" in result
        
        # When extracted index is 1 (not > 1), use provided index
        result = generate_chapter_filename(2, "1 Introduction")
        assert result.startswith("02-")
        assert "introduction" in result
    
    def test_decimal_numbered_title(self):
        """Test with decimal numbered titles."""
        result = generate_chapter_filename(1, "2.1 System Requirements")
        assert result.startswith("02-")
        assert "system-requirements" in result
    
    def test_title_without_number(self):
        """Test titles without numbers use provided index."""
        result = generate_chapter_filename(5, "Getting Started")
        assert result.startswith("05-")
        assert "getting-started" in result
    
    def test_multiline_title(self):
        """Test multiline titles use only first line."""
        title = "1 Introduction\nThis is a detailed description\nWith multiple lines"
        result = generate_chapter_filename(1, title)
        assert result.startswith("01-")
        assert "introduction" in result
        assert "detailed" not in result
    
    def test_title_with_special_characters(self):
        """Test titles with special characters get slugified."""
        result = generate_chapter_filename(1, "2 Настройка & Configuration!")
        assert result.startswith("02-")
        # Should be slugified
        assert "nastroika-configuration" in result or "configuration" in result
    
    def test_custom_pattern(self):
        """Test with custom filename patterns."""
        result = generate_chapter_filename(1, "2 Setup", pattern="chapter-{index}-{slug}.txt")
        assert result.startswith("chapter-2-")  # Custom pattern doesn't zero-pad
        assert result.endswith(".txt")
        assert "setup" in result
    
    def test_long_title_truncation(self):
        """Test very long titles get truncated appropriately."""
        long_title = "1 " + "Very " * 20 + "Long Title That Should Be Truncated"
        result = generate_chapter_filename(1, long_title)
        assert result.startswith("01-")
        # Should be truncated to reasonable length
        assert len(result) < 100
    
    def test_edge_case_numbers(self):
        """Test edge cases with number extraction."""
        # Large numbers
        result = generate_chapter_filename(1, "999 Large Number")
        assert result.startswith("999-")
        
        # Number equals provided index (should use extracted)
        result = generate_chapter_filename(1, "1 Same Number")
        assert result.startswith("01-")
    
    def test_roman_numerals_ignored(self):
        """Test that Roman numerals are ignored and index is used."""
        result = generate_chapter_filename(3, "IV Roman Numeral Chapter")
        assert result.startswith("03-")
        assert "roman-numeral-chapter" in result
    
    def test_default_pattern(self):
        """Test the default pattern format."""
        result = generate_chapter_filename(7, "Test Chapter")
        assert result == "07-test-chapter.md"
    
    def test_empty_title(self):
        """Test handling of empty or whitespace-only titles."""
        result = generate_chapter_filename(1, "")
        assert result.startswith("01-")
        
        result = generate_chapter_filename(1, "   ")
        assert result.startswith("01-")
        
        result = generate_chapter_filename(1, "1   ")  # Just number and spaces
        assert result.startswith("01-")