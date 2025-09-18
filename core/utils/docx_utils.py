"""DOCX parsing utilities shared across modules."""

import zipfile
import re
from typing import Dict, List, Optional
from xml.etree import ElementTree as ET

from .xml_constants import NS, DEFAULT_HEADING_PATTERNS
from core.numbering.heading_numbering import SERVICE_HEADINGS


def read_docx_part(zip_file: zipfile.ZipFile, part_name: str) -> Optional[bytes]:
    """Read a part from DOCX archive, returning None if not found.
    
    Args:
        zip_file: Open zipfile.ZipFile object for the DOCX archive.
        part_name: Name of the part to read (e.g., 'word/document.xml').
        
    Returns:
        Optional[bytes]: Content of the part or None if not found.
    """
    return zip_file.read(part_name) if part_name in zip_file.namelist() else None


def styles_map(styles_xml: Optional[bytes]) -> Dict[str, str]:
    """Map styleId -> human-readable name from styles.xml.
    
    Args:
        styles_xml: Raw XML bytes from word/styles.xml or None.
        
    Returns:
        Dict[str, str]: Mapping from style ID to human-readable style name.
    """
    if not styles_xml:
        return {}
        
    root = ET.fromstring(styles_xml)
    result: Dict[str, str] = {}
    
    for style in root.findall(".//w:style", NS):
        style_id = style.attrib.get(f"{{{NS['w']}}}styleId")
        name_element = style.find("w:name", NS)
        name = name_element.attrib.get(f"{{{NS['w']}}}val") if name_element is not None else style_id
        if style_id:
            result[style_id] = name
            
    return result


def heading_level(paragraph: ET.Element, style_map: Dict[str, str], 
                  heading_patterns: Optional[List[str]] = None) -> Optional[int]:
    """Return heading level (1..9) or None if not a heading.
    
    Args:
        paragraph: XML paragraph element to analyze.
        style_map: Mapping from style ID to style name.
        heading_patterns: List of regex patterns to match heading styles.
        
    Returns:
        Optional[int]: Heading level 1-9 or None if not a heading.
    """
    if heading_patterns is None:
        heading_patterns = DEFAULT_HEADING_PATTERNS
        
    # Filter out known service headings by their text content (e.g., "Содержание")
    try:
        full_text = "".join((t.text or "") for t in paragraph.findall(".//w:t", NS)).strip()
    except Exception:
        full_text = ""
    if full_text:
        # Remove leading numbering like 1, 1.2, 1.2.3., optional dot and spaces
        cleaned_text = re.sub(r'^\d+(?:\.\d+)*\.?\s*', '', full_text).strip().lower()
        if cleaned_text in SERVICE_HEADINGS:
            return None

    pPr = paragraph.find("w:pPr", NS)
    if pPr is None:
        return None
    
    # Prefer outlineLvl when present
    outlineLvl = pPr.find("w:outlineLvl", NS)
    if outlineLvl is not None:
        val = outlineLvl.attrib.get(f"{{{NS['w']}}}val")
        if val is not None and val.isdigit():
            level = int(val) + 1  # outlineLvl is 0-based
            return level if 1 <= level <= 9 else None
    
    # Fall back to style-based detection
    pStyle = pPr.find("w:pStyle", NS)
    if pStyle is not None:
        style_id = pStyle.attrib.get(f"{{{NS['w']}}}val")
        if style_id and style_id in style_map:
            style_name = style_map[style_id]
            
            # Check against heading patterns
            for pattern in heading_patterns:
                match = re.match(pattern, style_name, re.IGNORECASE)
                if match:
                    try:
                        # Special case for ROSA styles (no number group)
                        if any(rosa_style in pattern.upper() for rosa_style in ["ROSA_ПРИЛОЖЕНИЕ", "ROSAA", "ROSAFB"]):
                            return 1  # Top-level heading
                        level = int(match.group(1))
                        return level if 1 <= level <= 9 else None
                    except (ValueError, IndexError):
                        # If no group 1, might be special ROSA patterns
                        if any(rosa_style in style_name.upper() for rosa_style in ["ROSA_ПРИЛОЖЕНИЕ", "ROSAA", "ROSAFB"]):
                            return 1
                        continue
                        
            # Also try styleId like Heading1
            match = re.match(r"^Heading(\d)$", style_id, re.IGNORECASE)
            if match:
                return int(match.group(1))
    
    return None


def style_num_map(styles_xml: Optional[bytes]) -> Dict[str, str]:
    """Map styleId -> numId for list styles.
    
    Args:
        styles_xml: Raw XML bytes from word/styles.xml or None.
        
    Returns:
        Dict[str, str]: Mapping from style ID to numbering ID.
    """
    if not styles_xml:
        return {}
        
    root = ET.fromstring(styles_xml)
    result: Dict[str, str] = {}
    
    for style in root.findall(".//w:style", NS):
        style_id = style.attrib.get(f"{{{NS['w']}}}styleId")
        numPr = style.find("w:pPr/w:numPr", NS)
        if style_id and numPr is not None:
            numId = numPr.find("w:numId", NS)
            if numId is not None:
                result[style_id] = numId.attrib.get(f"{{{NS['w']}}}val", "")
                
    return result


def numbering_formats(numbering_xml: Optional[bytes]) -> Dict[str, str]:
    """Map numId -> numFmt (e.g., bullet, decimal).
    
    Args:
        numbering_xml: Raw XML bytes from word/numbering.xml or None.
        
    Returns:
        Dict[str, str]: Mapping from numbering ID to format type.
    """
    if not numbering_xml:
        return {}
        
    root = ET.fromstring(numbering_xml)
    abstract_map: Dict[str, str] = {}
    
    # First pass: map abstractNumId -> numFmt
    for abs_num in root.findall("w:abstractNum", NS):
        abs_id = abs_num.attrib.get(f"{{{NS['w']}}}abstractNumId")
        lvl = abs_num.find("w:lvl", NS)
        if abs_id and lvl is not None:
            numFmt = lvl.find("w:numFmt", NS)
            if numFmt is not None:
                abstract_map[abs_id] = numFmt.attrib.get(f"{{{NS['w']}}}val", "")
    
    # Second pass: map numId -> abstractNumId -> numFmt
    result: Dict[str, str] = {}
    for num in root.findall("w:num", NS):
        num_id = num.attrib.get(f"{{{NS['w']}}}numId")
        abstractNumId = num.find("w:abstractNumId", NS)
        if num_id and abstractNumId is not None:
            abs_id = abstractNumId.attrib.get(f"{{{NS['w']}}}val")
            if abs_id and abs_id in abstract_map:
                result[num_id] = abstract_map[abs_id]
                
    return result