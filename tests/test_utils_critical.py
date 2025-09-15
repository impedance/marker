"""Critical unit tests for core.utils modules.

These tests cover the essential functions that were moved during refactoring
and must work correctly to avoid system failures.
"""

import pytest
from xml.etree import ElementTree as ET
from core.utils.xml_constants import NS, DEFAULT_HEADING_PATTERNS
from core.utils.text_processing import extract_heading_number_and_title, clean_heading_text
from core.utils.docx_utils import styles_map, heading_level


class TestHeadingPatterns:
    """Test DEFAULT_HEADING_PATTERNS have proper capture groups."""

    def test_all_patterns_have_capture_groups(self):
        """Each pattern must have a capture group (\d) to extract heading level."""
        for pattern in DEFAULT_HEADING_PATTERNS:
            # Each pattern should contain (\d) for capturing the level
            assert r"(\d)" in pattern, f"Pattern '{pattern}' missing capture group (\d)"

    def test_patterns_match_common_heading_styles(self):
        """Test patterns match real Word heading styles."""
        import re
        
        test_cases = [
            # (style_name, expected_level)
            ("Heading 1", 1),
            ("Heading 2", 2), 
            ("Заголовок 1", 1),
            ("Заголовок 3", 3),
            ("ROSA_Заголовок 1", 1),
            ("Custom_Заголовок 2", 2),
        ]
        
        for style_name, expected_level in test_cases:
            matched = False
            for pattern in DEFAULT_HEADING_PATTERNS:
                match = re.match(pattern, style_name, re.IGNORECASE)
                if match:
                    level = int(match.group(1))
                    assert level == expected_level, f"Pattern '{pattern}' extracted level {level}, expected {expected_level} for style '{style_name}'"
                    matched = True
                    break
            
            assert matched, f"No pattern matched style '{style_name}'"

    def test_patterns_dont_match_non_headings(self):
        """Test patterns don't match non-heading styles."""
        import re
        
        non_heading_styles = [
            "Normal",
            "Body Text", 
            "Caption",
            "Table Normal",
            "List Paragraph",
            "Footer"
        ]
        
        for style_name in non_heading_styles:
            for pattern in DEFAULT_HEADING_PATTERNS:
                match = re.match(pattern, style_name, re.IGNORECASE)
                assert not match, f"Pattern '{pattern}' incorrectly matched non-heading style '{style_name}'"


class TestTextProcessing:
    """Test text processing utilities."""

    def test_extract_heading_number_and_title(self):
        """Test extraction of numbers and titles from heading text."""
        test_cases = [
            # (input_text, expected_number, expected_title)
            ("1.2.3 Installation Guide", "1.2.3", "Installation Guide"),
            ("4 Overview", "4", "Overview"),
            ("2.1 — System Requirements", "2.1", "System Requirements"), 
            ("3.4.5. Configuration Steps", "3.4.5", "Configuration Steps"),
            ("Installation Guide", "", "Installation Guide"),  # No numbering
            ("(1.2) Setup Process", "1.2", "Setup Process"),
            ("  2.3   Advanced Topics  ", "2.3", "Advanced Topics"),  # Extra whitespace
        ]
        
        for input_text, expected_number, expected_title in test_cases:
            number, title = extract_heading_number_and_title(input_text)
            assert number == expected_number, f"Input '{input_text}': expected number '{expected_number}', got '{number}'"
            assert title == expected_title, f"Input '{input_text}': expected title '{expected_title}', got '{title}'"

    def test_clean_heading_text(self):
        """Test removal of numbering prefixes from headings."""
        test_cases = [
            # (input_text, expected_output)
            ("3.7 Configuration", "Configuration"),
            ("3.4.3 — Functions", "Functions"),
            ("1) Introduction", "Introduction"),
            ("(2.1) - Description", "Description"),
            ("IV. Chapter Four", "Chapter Four"),
            ("Configuration", "Configuration"),  # No numbering to remove
            ("  1.2.3  Advanced Setup  ", "Advanced Setup"),  # Extra whitespace
        ]
        
        for input_text, expected_output in test_cases:
            result = clean_heading_text(input_text)
            assert result == expected_output, f"Input '{input_text}': expected '{expected_output}', got '{result}'"


class TestStylesMap:
    """Test styles_map() function with XML data."""

    def test_styles_map_with_none_input(self):
        """Test styles_map returns empty dict when input is None."""
        result = styles_map(None)
        assert result == {}

    def test_styles_map_with_empty_xml(self):
        """Test styles_map with minimal XML."""
        xml_content = '''<?xml version="1.0"?>
        <w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
        </w:styles>'''
        
        result = styles_map(xml_content.encode('utf-8'))
        assert result == {}

    def test_styles_map_with_real_styles(self):
        """Test styles_map with realistic Word styles XML."""
        xml_content = '''<?xml version="1.0"?>
        <w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
            <w:style w:styleId="Heading1">
                <w:name w:val="Heading 1"/>
            </w:style>
            <w:style w:styleId="Heading2">
                <w:name w:val="Heading 2"/>
            </w:style>
            <w:style w:styleId="Normal">
                <w:name w:val="Normal"/>
            </w:style>
        </w:styles>'''
        
        result = styles_map(xml_content.encode('utf-8'))
        
        expected = {
            "Heading1": "Heading 1",
            "Heading2": "Heading 2", 
            "Normal": "Normal"
        }
        
        assert result == expected


class TestHeadingLevel:
    """Test heading_level() function with real XML elements."""
    
    def _create_paragraph_xml(self, outline_level=None, style_id=None):
        """Helper to create paragraph XML with optional outline level and style."""
        para_xml = f'<w:p xmlns:w="{NS["w"]}">'
        
        if outline_level is not None or style_id is not None:
            para_xml += '<w:pPr>'
            if outline_level is not None:
                para_xml += f'<w:outlineLvl w:val="{outline_level}"/>'
            if style_id is not None:
                para_xml += f'<w:pStyle w:val="{style_id}"/>'
            para_xml += '</w:pPr>'
            
        para_xml += '</w:p>'
        
        return ET.fromstring(para_xml)

    def test_heading_level_with_outline_level(self):
        """Test heading level detection using w:outlineLvl."""
        test_cases = [
            (0, 1),  # outlineLvl 0 -> H1
            (1, 2),  # outlineLvl 1 -> H2  
            (2, 3),  # outlineLvl 2 -> H3
            (5, 6),  # outlineLvl 5 -> H6
        ]
        
        style_map = {}
        
        for outline_val, expected_level in test_cases:
            para = self._create_paragraph_xml(outline_level=outline_val)
            level = heading_level(para, style_map)
            assert level == expected_level, f"outlineLvl {outline_val} should give level {expected_level}, got {level}"

    def test_heading_level_with_style_names(self):
        """Test heading level detection using style names."""
        style_map = {
            "Heading1": "Heading 1",
            "Heading2": "Heading 2",
            "CustomHeading3": "Заголовок 3",  
            "Normal": "Normal"
        }
        
        test_cases = [
            ("Heading1", 1),
            ("Heading2", 2),
            ("CustomHeading3", 3),
            ("Normal", None),  # Should not be detected as heading
        ]
        
        for style_id, expected_level in test_cases:
            para = self._create_paragraph_xml(style_id=style_id)
            level = heading_level(para, style_map)
            assert level == expected_level, f"Style '{style_id}' should give level {expected_level}, got {level}"

    def test_heading_level_outline_overrides_style(self):
        """Test that outline level takes precedence over style-based detection."""
        style_map = {"Normal": "Normal"}
        
        # Paragraph has both outline level and style, outline should win
        para = self._create_paragraph_xml(outline_level=1, style_id="Normal")
        level = heading_level(para, style_map)
        assert level == 2, f"Outline level should override style, expected 2, got {level}"

    def test_heading_level_no_ppr(self):
        """Test with paragraph that has no paragraph properties."""
        para_xml = f'<w:p xmlns:w="{NS["w"]}"><w:r><w:t>Some text</w:t></w:r></w:p>'
        para = ET.fromstring(para_xml)
        
        level = heading_level(para, {})
        assert level is None, f"Paragraph without pPr should return None, got {level}"

    def test_heading_level_styleid_fallback(self):
        """Test fallback to styleId pattern matching (Heading1, Heading2, etc.)."""
        style_map = {"Heading1": "Some Custom Name"}
        
        para = self._create_paragraph_xml(style_id="Heading1")
        level = heading_level(para, style_map)
        # Should match via styleId "Heading1" pattern, not the style name
        assert level == 1, f"StyleId 'Heading1' should match via fallback pattern, got {level}"


class TestIntegrationCritical:
    """Integration tests for critical function combinations."""
    
    def test_heading_detection_end_to_end(self):
        """Test the complete heading detection pipeline."""
        # Create a realistic styles.xml content
        styles_xml = '''<?xml version="1.0"?>
        <w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
            <w:style w:styleId="Heading1">
                <w:name w:val="Heading 1"/>
            </w:style>
            <w:style w:styleId="CustomHeading">
                <w:name w:val="Заголовок 2"/>
            </w:style>
        </w:styles>'''
        
        # Parse styles
        style_map = styles_map(styles_xml.encode('utf-8'))
        
        # Test paragraph with style-based heading
        para = self._create_paragraph_xml(style_id="CustomHeading")
        level = heading_level(para, style_map)
        
        assert level == 2, f"End-to-end heading detection failed, expected level 2, got {level}"
    
    def _create_paragraph_xml(self, outline_level=None, style_id=None):
        """Helper method (duplicate from TestHeadingLevel for clarity)."""
        para_xml = f'<w:p xmlns:w="{NS["w"]}">'
        
        if outline_level is not None or style_id is not None:
            para_xml += '<w:pPr>'
            if outline_level is not None:
                para_xml += f'<w:outlineLvl w:val="{outline_level}"/>'
            if style_id is not None:
                para_xml += f'<w:pStyle w:val="{style_id}"/>'
            para_xml += '</w:pPr>'
            
        para_xml += '</w:p>'
        
        return ET.fromstring(para_xml)