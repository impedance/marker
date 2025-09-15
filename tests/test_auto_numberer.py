"""Tests for automatic numbering functionality."""

import pytest
from core.numbering.auto_numberer import AutoNumberer, add_automatic_numbering, add_numbering_to_chapters
from core.model.internal_doc import InternalDoc, Heading, Paragraph, Text


class TestAutoNumberer:
    """Test the AutoNumberer class."""
    
    def test_init_creates_empty_counters(self):
        """Test that initialization creates empty counters."""
        numberer = AutoNumberer()
        assert numberer.counters == {}
    
    def test_reset_clears_counters(self):
        """Test that reset clears all counters."""
        numberer = AutoNumberer()
        numberer.counters = {1: 2, 2: 3}
        numberer.reset()
        assert numberer.counters == {}
    
    def test_get_number_for_level_single_level(self):
        """Test numbering for a single level."""
        numberer = AutoNumberer()
        
        assert numberer.get_number_for_level(1) == "1"
        assert numberer.get_number_for_level(1) == "2"
        assert numberer.get_number_for_level(1) == "3"
    
    def test_get_number_for_level_hierarchical(self):
        """Test hierarchical numbering."""
        numberer = AutoNumberer()
        
        # Level 1
        assert numberer.get_number_for_level(1) == "1"
        
        # Level 2 under 1
        assert numberer.get_number_for_level(2) == "1.1"
        assert numberer.get_number_for_level(2) == "1.2"
        
        # Level 3 under 1.2
        assert numberer.get_number_for_level(3) == "1.2.1"
        assert numberer.get_number_for_level(3) == "1.2.2"
        
        # Back to level 1 - should reset deeper levels
        assert numberer.get_number_for_level(1) == "2"
        
        # New level 2 under 2
        assert numberer.get_number_for_level(2) == "2.1"
    
    def test_get_number_for_level_reset_deeper_levels(self):
        """Test that going to a higher level resets deeper level counters."""
        numberer = AutoNumberer()
        
        # Build up some deep nesting
        numberer.get_number_for_level(1)  # "1"
        numberer.get_number_for_level(2)  # "1.1"
        numberer.get_number_for_level(3)  # "1.1.1"
        numberer.get_number_for_level(4)  # "1.1.1.1"
        
        # Go back to level 2 - should reset levels 3 and 4
        assert numberer.get_number_for_level(2) == "1.2"
        
        # New level 3 should start from 1
        assert numberer.get_number_for_level(3) == "1.2.1"


class TestAddAutomaticNumbering:
    """Test the add_automatic_numbering function."""
    
    def test_empty_document(self):
        """Test numbering an empty document."""
        doc = InternalDoc(blocks=[])
        result = add_automatic_numbering(doc)
        assert result.blocks == []
    
    def test_document_without_headings(self):
        """Test document with no headings."""
        doc = InternalDoc(blocks=[
            Paragraph(inlines=[Text(content="Just some text")])
        ])
        result = add_automatic_numbering(doc)
        assert len(result.blocks) == 1
        assert result.blocks[0].type == "paragraph"
    
    def test_single_heading_level_1(self):
        """Test document with single level 1 heading."""
        doc = InternalDoc(blocks=[
            Heading(level=1, text="Introduction")
        ])
        result = add_automatic_numbering(doc)
        
        assert len(result.blocks) == 1
        heading = result.blocks[0]
        assert heading.type == "heading"
        assert heading.level == 1
        assert heading.text == "Introduction"  # Level 1 headings don't get numbered
    
    def test_single_heading_level_2(self):
        """Test document with single level 2 heading."""
        doc = InternalDoc(blocks=[
            Heading(level=2, text="Overview")
        ])
        result = add_automatic_numbering(doc)
        
        assert len(result.blocks) == 1
        heading = result.blocks[0]
        assert heading.type == "heading"
        assert heading.level == 2
        assert heading.text == "1 Overview"  # Level 2+ get numbered
    
    def test_multiple_headings_hierarchical(self):
        """Test document with hierarchical headings."""
        doc = InternalDoc(blocks=[
            Heading(level=1, text="Chapter 1"),
            Heading(level=2, text="Section A"),
            Heading(level=2, text="Section B"),
            Heading(level=3, text="Subsection 1"),
            Heading(level=1, text="Chapter 2"),
            Heading(level=2, text="Section C")
        ])
        result = add_automatic_numbering(doc)
        
        headings = [block for block in result.blocks if block.type == "heading"]
        assert len(headings) == 6
        
        assert headings[0].text == "Chapter 1"
        assert headings[1].text == "1.1 Section A"
        assert headings[2].text == "1.2 Section B"
        assert headings[3].text == "1.2.1 Subsection 1"
        assert headings[4].text == "Chapter 2"
        assert headings[5].text == "2.1 Section C"
    
    def test_headings_with_existing_numbers(self):
        """Test headings that already have numbers."""
        doc = InternalDoc(blocks=[
            Heading(level=1, text="1. Chapter 1"),
            Heading(level=2, text="1.1 Section A"),
            Heading(level=2, text="Some unnumbered section")
        ])
        result = add_automatic_numbering(doc)
        
        headings = [block for block in result.blocks if block.type == "heading"]
        assert len(headings) == 3
        
        assert headings[0].text == "Chapter 1"  # Cleaned
        assert headings[1].text == "1.1 Section A"  # Re-numbered
        assert headings[2].text == "1.2 Some unnumbered section"  # Numbered
    
    def test_mixed_content(self):
        """Test document with mixed headings and other content."""
        doc = InternalDoc(blocks=[
            Heading(level=1, text="Introduction"),
            Paragraph(inlines=[Text(content="Some intro text")]),
            Heading(level=2, text="Overview"),
            Paragraph(inlines=[Text(content="More text")])
        ])
        result = add_automatic_numbering(doc)
        
        assert len(result.blocks) == 4
        assert result.blocks[0].text == "Introduction"
        assert result.blocks[1].type == "paragraph"
        assert result.blocks[2].text == "1.1 Overview"
        assert result.blocks[3].type == "paragraph"
    
    def test_headings_without_regex_match(self):
        """Test headings that don't match regex patterns."""
        doc = InternalDoc(blocks=[
            Heading(level=2, text="Simple"),  # No numbers, no regex match
            Heading(level=2, text="!@#$%"),   # Special chars, no regex match
        ])
        result = add_automatic_numbering(doc)
        
        headings = [block for block in result.blocks if block.type == "heading"]
        assert len(headings) == 2
        
        # Should get numbered with fallback logic
        assert headings[0].text == "1 Simple"
        assert headings[1].text == "2 !@#$%"


class TestAddNumberingToChapters:
    """Test the add_numbering_to_chapters function."""
    
    def test_empty_chapters_list(self):
        """Test with empty chapters list."""
        result = add_numbering_to_chapters([])
        assert result == []
    
    def test_single_chapter(self):
        """Test with single chapter."""
        chapter = InternalDoc(blocks=[
            Heading(level=1, text="Chapter 1"),
            Heading(level=2, text="Section A")
        ])
        result = add_numbering_to_chapters([chapter])
        
        assert len(result) == 1
        headings = [block for block in result[0].blocks if block.type == "heading"]
        assert headings[0].text == "Chapter 1"
        assert headings[1].text == "1.1 Section A"
    
    def test_multiple_chapters_continuous_numbering(self):
        """Test that numbering continues across chapters."""
        chapter1 = InternalDoc(blocks=[
            Heading(level=1, text="First Chapter"),
            Heading(level=2, text="Section A")
        ])
        chapter2 = InternalDoc(blocks=[
            Heading(level=1, text="Second Chapter"),
            Heading(level=2, text="Section B"),
            Heading(level=2, text="Section C")
        ])
        
        result = add_numbering_to_chapters([chapter1, chapter2])
        
        assert len(result) == 2
        
        # Check first chapter
        headings1 = [block for block in result[0].blocks if block.type == "heading"]
        assert headings1[0].text == "First Chapter"
        assert headings1[1].text == "1.1 Section A"
        
        # Check second chapter - numbering should continue
        headings2 = [block for block in result[1].blocks if block.type == "heading"]
        assert headings2[0].text == "Second Chapter"
        assert headings2[1].text == "2.1 Section B"
        assert headings2[2].text == "2.2 Section C"
    
    def test_chapters_with_different_heading_levels(self):
        """Test chapters with various heading levels."""
        chapter1 = InternalDoc(blocks=[
            Heading(level=1, text="Chapter 1"),
            Heading(level=2, text="Section 1.1"),
            Heading(level=3, text="Subsection 1.1.1")
        ])
        chapter2 = InternalDoc(blocks=[
            Heading(level=1, text="Chapter 2"),
            Heading(level=3, text="Direct subsection")  # Skip level 2
        ])
        
        result = add_numbering_to_chapters([chapter1, chapter2])
        
        # Check first chapter
        headings1 = [block for block in result[0].blocks if block.type == "heading"]
        assert headings1[0].text == "Chapter 1"
        assert headings1[1].text == "1.1 Section 1.1"
        assert headings1[2].text == "1.1.1 Subsection 1.1.1"
        
        # Check second chapter
        headings2 = [block for block in result[1].blocks if block.type == "heading"]
        assert headings2[0].text == "Chapter 2"
        assert headings2[1].text == "2.1 Direct subsection"
    
    def test_chapters_with_regex_fallback_cases(self):
        """Test chapters with headings that don't match regex."""
        chapter1 = InternalDoc(blocks=[
            Heading(level=1, text="Chapter 1"),
            Heading(level=2, text="Simple section")  # No regex match
        ])
        chapter2 = InternalDoc(blocks=[
            Heading(level=1, text="Chapter 2"),  
            Heading(level=2, text="!Special chars!")  # No regex match
        ])
        
        result = add_numbering_to_chapters([chapter1, chapter2])
        
        # Check first chapter
        headings1 = [block for block in result[0].blocks if block.type == "heading"]
        assert headings1[0].text == "Chapter 1"
        assert headings1[1].text == "1.1 Simple section"
        
        # Check second chapter
        headings2 = [block for block in result[1].blocks if block.type == "heading"]
        assert headings2[0].text == "Chapter 2"
        assert headings2[1].text == "2.1 !Special chars!"