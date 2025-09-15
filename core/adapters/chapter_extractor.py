"""
Chapter Extractor for DOCX XML

Extracts hierarchical chapter structure from DOCX files with numbering preservation.
Creates structured JSON representation of document outline.
"""
from __future__ import annotations
import zipfile
import re
from typing import Dict, List, Tuple, Optional
from xml.etree import ElementTree as ET
from pathlib import Path
from dataclasses import dataclass

# Import shared constants and utilities
from core.utils.xml_constants import NS, DEFAULT_HEADING_PATTERNS
from core.utils.text_processing import extract_heading_number_and_title
from core.utils.docx_utils import read_docx_part, styles_map, heading_level


@dataclass
class ChapterNode:
    """Represents a chapter/section node with hierarchical structure."""
    level: int
    title: str
    number: str = ""
    full_text: str = ""
    children: List['ChapterNode'] = None
    
    def __post_init__(self):
        if self.children is None:
            self.children = []
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "level": self.level,
            "title": self.title,
            "number": self.number,
            "full_text": self.full_text,
            "children": [child.to_dict() for child in self.children]
        }


# Function moved to core.utils.docx_utils


# Function moved to core.utils.docx_utils (renamed to styles_map)


def _extract_paragraph_text(paragraph: ET.Element) -> str:
    """Extract text from paragraph element."""
    texts: List[str] = []
    for text_el in paragraph.findall(".//w:t", NS):
        texts.append(text_el.text or "")
    return "".join(texts).strip()


# Function moved to core.utils.text_processing


# Function moved to core.utils.docx_utils (renamed to heading_level)


def extract_chapter_structure(docx_path: str | Path) -> List[ChapterNode]:
    """
    Extract hierarchical chapter structure from DOCX file.
    
    Args:
        docx_path: Path to the DOCX file
        
    Returns:
        List of top-level ChapterNode objects with nested structure
    """
    docx_path = Path(docx_path)
    
    with zipfile.ZipFile(docx_path) as z:
        doc_xml = read_docx_part(z, "word/document.xml")
        styles_xml = read_docx_part(z, "word/styles.xml")
    
    if not doc_xml:
        raise RuntimeError("word/document.xml not found")
    
    style_map = styles_map(styles_xml)
    body = ET.fromstring(doc_xml).find(".//w:body", NS)
    if body is None:
        raise RuntimeError("No <w:body> found")
    
    patterns = DEFAULT_HEADING_PATTERNS
    headings: List[ChapterNode] = []
    
    # Extract all headings first
    for paragraph in body.findall("w:p", NS):
        level = heading_level(paragraph, style_map, patterns)
        if level:
            text = _extract_paragraph_text(paragraph)
            if text:  # Only process non-empty headings
                number, title = extract_heading_number_and_title(text)
                node = ChapterNode(
                    level=level,
                    title=title or text,
                    number=number,
                    full_text=text
                )
                headings.append(node)
    
    # Build hierarchical structure
    return _build_hierarchy(headings)


def _build_hierarchy(headings: List[ChapterNode]) -> List[ChapterNode]:
    """Build hierarchical structure from flat list of headings."""
    if not headings:
        return []
    
    root_nodes: List[ChapterNode] = []
    stack: List[ChapterNode] = []
    
    for heading in headings:
        # Pop stack until we find a valid parent (lower level number)
        while stack and stack[-1].level >= heading.level:
            stack.pop()
        
        if stack:
            # Add as child to the last item in stack
            stack[-1].children.append(heading)
        else:
            # Add as root node
            root_nodes.append(heading)
        
        # Push current heading to stack
        stack.append(heading)
    
    return root_nodes


def export_chapter_map_json(chapter_nodes: List[ChapterNode]) -> Dict:
    """
    Export chapter structure as JSON-serializable dictionary.
    
    Args:
        chapter_nodes: List of top-level chapter nodes
        
    Returns:
        Dictionary suitable for JSON serialization
    """
    return {
        "document_structure": {
            "chapters": [node.to_dict() for node in chapter_nodes],
            "total_chapters": len(chapter_nodes),
            "max_depth": _calculate_max_depth(chapter_nodes)
        }
    }


def _calculate_max_depth(nodes: List[ChapterNode], current_depth: int = 1) -> int:
    """Calculate maximum depth of the hierarchy."""
    if not nodes:
        return current_depth - 1
    
    max_depth = current_depth
    for node in nodes:
        if node.children:
            depth = _calculate_max_depth(node.children, current_depth + 1)
            max_depth = max(max_depth, depth)
    
    return max_depth


def extract_and_export_chapter_map(docx_path: str | Path) -> Dict:
    """
    Extract chapter structure and export as JSON-ready dictionary.
    
    Args:
        docx_path: Path to the DOCX file
        
    Returns:
        JSON-serializable dictionary with hierarchical chapter structure
    """
    chapter_nodes = extract_chapter_structure(docx_path)
    return export_chapter_map_json(chapter_nodes)