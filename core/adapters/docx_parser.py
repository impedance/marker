
"""
docx_parser.py
Parse DOCX files using WordprocessingML (DOCX XML) to extract structured content.
- Detects headings via w:outlineLvl (preferred) or paragraph style names.
- Extracts all text content with proper heading levels.
- Extracts images from word/media/ directory and references from document.xml.
- Returns structured data compatible with InternalDoc AST format.

This module provides specialized DOCX parsing to ensure
proper chapter extraction and heading numbering preservation.
"""
from __future__ import annotations
import zipfile, re, argparse, hashlib, os
from pathlib import Path
from typing import Dict, List, Tuple
from xml.etree import ElementTree as ET

# Internal model imports
from core.model.internal_doc import (
    InternalDoc,
    Block,
    Heading,
    Paragraph,
    CodeBlock,
    Text as InlineText,
    Image,
    Table,
    TableRow,
    TableCell,
    ListBlock,
    ListItem,
)
from core.model.resource_ref import ResourceRef

# Import shared constants and utilities
from core.utils.xml_constants import NS, DEFAULT_HEADING_PATTERNS
from core.utils.text_processing import clean_heading_text, extract_heading_number_and_title
from core.utils.docx_utils import read_docx_part, styles_map, heading_level, style_num_map, numbering_formats

# Use shared utility read_docx_part instead of local _read function

# Function moved to core.utils.text_processing

# Function moved to core.utils.docx_utils

# Function moved to core.utils.docx_utils

# Function moved to core.utils.docx_utils

def _style_list_level(style_id: str, style_name: str) -> int:
    """Infer list nesting level from style identifier or name."""
    for value in (style_name, style_id):
        if not value:
            continue
        match = re.search(r"(\d+)$", value.strip())
        if match:
            try:
                number = int(match.group(1))
                if number > 0:
                    return max(0, number - 1)
            except ValueError:
                continue
    return 0


def _paragraph_list_info(
    p: ET.Element,
    style_nums: Dict[str, str],
    num_fmts: Dict[str, str],
    style_map: Dict[str, str],
) -> tuple[str, int] | None:
    """Return list format and nesting level if paragraph is part of a list."""
    pPr = p.find("w:pPr", NS)
    if pPr is None:
        return None
    numPr = pPr.find("w:numPr", NS)
    if numPr is not None:
        numId_el = numPr.find("w:numId", NS)
        ilvl_el = numPr.find("w:ilvl", NS)
        if numId_el is not None:
            num_id = numId_el.attrib.get(f"{{{NS['w']}}}val", "")
            level = 0
            if ilvl_el is not None:
                level_val = ilvl_el.attrib.get(f"{{{NS['w']}}}val", "0")
                if isinstance(level_val, str) and level_val.isdigit():
                    level = int(level_val)
            fmt = num_fmts.get(num_id) if num_id else None
            return (fmt or "bullet", level)
    pStyle = pPr.find("w:pStyle", NS)
    if pStyle is not None:
        sid = pStyle.attrib.get(f"{{{NS['w']}}}val", "")
        num_id = style_nums.get(sid)
        if num_id:
            fmt = num_fmts.get(num_id)
            style_name = style_map.get(sid, "")
            level = _style_list_level(sid, style_name)
            return (fmt or "bullet", level)
    return None

def _get_paragraph_number(p: ET.Element, numbering_xml: bytes = None) -> str:
    """Extract paragraph numbering (e.g., '4.1.3') from Word's numbering system."""
    pPr = p.find("w:pPr", NS)
    if pPr is None:
        return ""
    
    numPr = pPr.find("w:numPr", NS)
    if numPr is None:
        return ""
    
    # Extract numId and ilvl
    numId_el = numPr.find("w:numId", NS)
    ilvl_el = numPr.find("w:ilvl", NS)
    
    if numId_el is None or ilvl_el is None:
        return ""
    
    numId = numId_el.attrib.get(f"{{{NS['w']}}}val", "")
    ilvl = ilvl_el.attrib.get(f"{{{NS['w']}}}val", "0")
    
    # For now, we'll use a simplified approach since parsing numbering.xml
    # is complex. We'll look for common numbering patterns in the text itself
    return ""

def _extract_numbering_from_runs(p: ET.Element) -> str:
    """Extract any numbering text from paragraph runs."""
    # Look for text that looks like numbering at the start of the paragraph
    runs = p.findall(".//w:r", NS)
    if not runs:
        return ""
    
    # Get text from the first few runs to check for numbering
    first_run_texts = []
    for run in runs[:3]:  # Check first 3 runs only
        texts = []
        for t in run.findall("w:t", NS):
            if t.text:
                texts.append(t.text)
        run_text = "".join(texts)
        if run_text.strip():
            first_run_texts.append(run_text)
    
    full_start = "".join(first_run_texts)
    
    # Pattern to match numbering at start: "4.1.3 " or "4.1 " or "4 "
    numbering_patterns = [
        r'^(\d+(?:\.\d+)*)\s+',  # "4.1.3 " 
        r'^(\d+(?:\.\d+)*)\.\s+',  # "4.1.3. "
    ]
    
    for pattern in numbering_patterns:
        match = re.match(pattern, full_start)
        if match:
            return match.group(1)
    
    return ""

def _extract_section_mapping(docx_root: ET.Element) -> Dict[str, str]:
    """Extract mapping from section numbers to section titles."""
    section_map = {}
    
    for para in docx_root.findall('.//w:p', NS):
        # Check if this is a heading paragraph
        pPr = para.find('w:pPr', NS)
        if pPr is not None:
            pStyle = pPr.find('w:pStyle', NS)
            outlineLvl = pPr.find('w:outlineLvl', NS)
            
            # Get all text from paragraph
            text_content = ''
            for t in para.findall('.//w:t', NS):
                if t.text:
                    text_content += t.text
            
            is_heading = False
            
            if pStyle is not None:
                style_val = pStyle.get(f"{{{NS['w']}}}val", '')
                if 'heading' in style_val.lower() or style_val.lower().startswith('toc'):
                    is_heading = True
            
            if outlineLvl is not None:
                is_heading = True
                
            # Check if text looks like a numbered heading
            if text_content and re.match(r'^\d+(\.\d+)*\s', text_content):
                is_heading = True
                
            if is_heading and text_content.strip():
                # Extract section number and title, removing page numbers
                match = re.match(r'^(\d+(?:\.\d+)*)\s+(.+)', text_content.strip())
                if match:
                    section_num = match.group(1)
                    section_title = match.group(2)
                    
                    # Clean up the title - remove trailing numbers (page numbers)
                    clean_title = re.sub(r'\d+$', '', section_title).strip()
                    
                    # Skip very generic titles like navigation elements
                    if len(clean_title) > 5 and not clean_title.startswith('–'):
                        section_map[section_num] = clean_title
    
    return section_map

def _replace_cross_references(text: str, section_map: Dict[str, str]) -> str:
    """Replace numeric cross-references with section titles when possible."""

    if not text or not section_map:
        return text

    patterns = [
        re.compile(r'(?<!\w)(?P<prefix>п\.\s*)(?P<number>\d+(?:\.\d+)*)', re.IGNORECASE),
        re.compile(r'(?<!\w)(?P<prefix>пункт[а-яё]*\s+)(?P<number>\d+(?:\.\d+)*)', re.IGNORECASE),
    ]

    def _replace(match: re.Match[str]) -> str:
        number = match.group('number')
        title = section_map.get(number)
        if not title:
            return match.group(0)

        prefix = match.group('prefix')
        prefix = re.sub(r'\s*$', ' ', prefix)
        return f"{prefix}{title}"

    result = text
    for pattern in patterns:
        result = pattern.sub(_replace, result)

    return result

def _text_of(p: ET.Element, section_map: Dict[str, str] = None) -> str:
    """Extract text from paragraph, including any manual numbering."""
    texts: List[str] = []
    for t in p.findall(".//w:t", NS):
        texts.append(t.text or "")
    full_text = "".join(texts).strip()
    
    # Apply cross-reference replacement if section_map is provided
    if section_map and full_text:
        full_text = _replace_cross_references(full_text, section_map)
    
    return full_text

def _extract_formatted_inlines(
    p: ET.Element, section_map: Dict[str, str] | None = None
) -> List:
    """Extract text with formatting information from paragraph runs."""
    from core.model.internal_doc import Text, Code, Bold, Italic

    segments: List[tuple[str, str]] = []

    for run in p.findall("w:r", NS):
        text_parts = [t.text for t in run.findall("w:t", NS) if t.text]
        if not text_parts:
            continue

        text_content = "".join(text_parts)
        rPr = run.find("w:rPr", NS)
        is_code = False
        is_bold = False
        is_italic = False

        if rPr is not None:
            rFonts = rPr.find("w:rFonts", NS)
            if rFonts is not None:
                for attr in ("ascii", "hAnsi", "cs"):
                    font_val = rFonts.attrib.get(f"{{{NS['w']}}}{attr}", "")
                    if "mono" in font_val.lower() or "courier" in font_val.lower():
                        is_code = True
                        break
            b_el = rPr.find("w:b", NS)
            if b_el is not None:
                bold_val = b_el.attrib.get(f"{{{NS['w']}}}val", "1")
                if bold_val != "0":
                    is_bold = True
            i_el = rPr.find("w:i", NS)
            if i_el is not None:
                italic_val = i_el.attrib.get(f"{{{NS['w']}}}val", "1")
                if italic_val != "0":
                    is_italic = True

        if is_code:
            style = "code"
        elif is_bold:
            style = "bold"
        elif is_italic:
            style = "italic"
        else:
            style = "text"

        if segments and segments[-1][0] == style:
            segments[-1] = (style, segments[-1][1] + text_content)
        else:
            segments.append((style, text_content))

    if not segments:
        return []

    while segments:
        style, content = segments[0]
        stripped = content.lstrip()
        if stripped:
            if stripped != content:
                segments[0] = (style, stripped)
            break
        segments.pop(0)

    while segments:
        style, content = segments[-1]
        stripped = content.rstrip()
        if stripped:
            if stripped != content:
                segments[-1] = (style, stripped)
            break
        segments.pop()

    inlines: List = []
    for style, content in segments:
        if not content:
            continue
        if section_map:
            content = _replace_cross_references(content, section_map)
        if style == "code":
            inlines.append(Code(content=content))
        elif style == "bold":
            inlines.append(Bold(content=content))
        elif style == "italic":
            inlines.append(Italic(content=content))
        else:
            inlines.append(Text(content=content))

    return inlines

def _text_with_numbering(p: ET.Element) -> str:
    """Extract text from paragraph, preserving any numbering."""
    # First try to extract automatic numbering
    auto_number = _get_paragraph_number(p)
    if auto_number:
        # Remove the numbering from the text if it's duplicated
        text = _text_of(p)
        number, title = extract_heading_number_and_title(text)
        if number:  # If text already has numbering, use the text as-is
            return text
        else:  # Add the automatic numbering to clean text
            return f"{auto_number} {text}" if text else auto_number
    
    # Fallback: try to extract numbering from text runs
    run_number = _extract_numbering_from_runs(p)
    text = _text_of(p)
    
    if run_number:
        # Check if the number is already in the text
        if text.startswith(run_number):
            return text
        else:
            return f"{run_number} {text}" if text else run_number
    
    return text

# Function moved to core.utils.text_processing

# Function moved to core.utils.docx_utils

def _slug(text: str, maxlen: int = 80) -> str:
    s = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    s = re.sub(r"\s+", "-", s).strip("-_").lower()
    return (s or "section")[:maxlen].rstrip("-_")

def _load_relationships(rels_xml: bytes | None) -> Dict[str, str]:
    """Parse relationships XML and return mapping of relationship ID to target path."""
    if not rels_xml:
        return {}
    
    relationships = {}
    root = ET.fromstring(rels_xml)
    
    for rel in root.findall('.//rel:Relationship', NS):
        rel_id = rel.attrib.get('Id')
        target = rel.attrib.get('Target')
        rel_type = rel.attrib.get('Type')
        
        if rel_id and target and 'image' in rel_type:
            relationships[rel_id] = target
    
    return relationships

def _extract_images_from_media(z: zipfile.ZipFile) -> Dict[str, ResourceRef]:
    """Extract all images from word/media/ directory and create ResourceRef objects."""
    images = {}
    
    # Get list of media files
    media_files = [name for name in z.namelist() if name.startswith('word/media/')]
    
    for media_file in media_files:
        # Read image content
        content = z.read(media_file)
        if not content:
            continue
            
        # Get filename and extension
        filename = os.path.basename(media_file)
        _, ext = os.path.splitext(filename)
        
        # Determine MIME type from extension
        mime_type = _get_mime_type_from_extension(ext.lower())
        
        # Create SHA256 hash for deduplication
        sha256_hash = hashlib.sha256(content).hexdigest()
        
        # Use filename without extension as resource ID
        resource_id = os.path.splitext(filename)[0]
        
        # Create ResourceRef
        resource_ref = ResourceRef(
            id=resource_id,
            mime_type=mime_type,
            content=content,
            sha256=sha256_hash
        )
        
        images[media_file] = resource_ref
    
    return images

def _get_mime_type_from_extension(ext: str) -> str:
    """Get MIME type from file extension."""
    mime_types = {
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.bmp': 'image/bmp',
        '.tiff': 'image/tiff',
        '.tif': 'image/tiff',
        '.svg': 'image/svg+xml'
    }
    return mime_types.get(ext, 'application/octet-stream')

def _find_images_in_paragraph(p: ET.Element, relationships: Dict[str, str], media_images: Dict[str, ResourceRef], 
                             all_paragraphs: List[ET.Element], style_map: Dict[str, str], 
                             used_caption_paragraphs: set = None) -> Tuple[List[Image], Set[ET.Element]]:
    """Find all images referenced in a paragraph and return Image blocks with captions and used caption paragraphs."""
    images = []
    if used_caption_paragraphs is None:
        used_caption_paragraphs = set()
    caption_paragraphs_for_this_image = set()
    
    # Look for drawing elements that contain image references
    for drawing in p.findall('.//w:drawing', NS):
        # Extract image name from docPr element
        image_name = ""
        for doc_pr in drawing.findall('.//wp:docPr', NS):
            image_name = doc_pr.attrib.get('name', '')
            break
        
        for blip in drawing.findall('.//*[@r:embed]', NS):
            embed_id = blip.attrib.get(f"{{{NS['r']}}}embed")
            if embed_id and embed_id in relationships:
                target_path = relationships[embed_id]
                full_path = f"word/{target_path}"
                
                if full_path in media_images:
                    resource_ref = media_images[full_path]
                    
                    # Find caption for this image, passing the image name
                    caption, caption_para = _find_caption_for_image_with_paragraph(p, all_paragraphs, style_map, image_name)
                    if caption_para:
                        caption_paragraphs_for_this_image.add(caption_para)
                    
                    # Create Image block
                    image = Image(
                        alt=f"Image {resource_ref.id}",  # Simple alt text
                        resource_id=resource_ref.id,
                        caption=caption
                    )
                    images.append(image)
    
    return images, caption_paragraphs_for_this_image


def _is_caption_paragraph(p: ET.Element, style_map: Dict[str, str]) -> bool:
    """Check if paragraph contains an image caption."""
    # Strategy 1: Check style names
    style_id = ""
    pPr = p.find("w:pPr", NS)
    if pPr is not None:
        pStyle = pPr.find("w:pStyle", NS)
        if pStyle is not None:
            style_id = pStyle.attrib.get(f"{{{NS['w']}}}val", "")
    
    style_name = style_map.get(style_id, "").lower()
    
    # Known caption style patterns
    caption_style_patterns = [
        r'caption', r'рисунок.*номер', r'рисунок.*подпись', r'figure'
    ]
    
    for pattern in caption_style_patterns:
        if re.search(pattern, style_name, re.IGNORECASE):
            return True
    
    # Strategy 2: Check text content patterns
    text_content = _extract_text_from_paragraph(p).strip()
    if text_content:
        caption_text_patterns = [
            r'(рисунок|figure|рис\.|fig\.)\s+\d+',
            r'(схема|diagram|диаграмма)\s+\d+',
            r'^рисунок\s+\d+\s*[-–—]\s*.+',
            r'^figure\s+\d+\s*[-–—]\s*.+'
        ]
        
        for pattern in caption_text_patterns:
            if re.search(pattern, text_content, re.IGNORECASE):
                return True
    
    return False


def _extract_text_from_paragraph(p: ET.Element) -> str:
    """Extract all text content from a paragraph element."""
    texts = []
    for t in p.findall('.//w:t', NS):
        if t.text:
            texts.append(t.text)
    return "".join(texts)


def _find_seq_picnum_in_paragraph(p: ET.Element) -> str:
    """Extract SEQ picnum field result from a paragraph."""
    # Look for SEQ picnum field instruction
    has_seq_picnum = False
    for instr in p.findall('.//w:instrText', NS):
        if instr.text and 'SEQ picnum' in instr.text:
            has_seq_picnum = True
            break
    
    if not has_seq_picnum:
        return ""
    
    # Find the field result (text after fldChar with type="separate")
    for r in p.findall('.//w:r', NS):
        found_separate = False
        for elem in r:
            w_ns = NS["w"]
            if (elem.tag == f'{{{w_ns}}}fldChar' and 
                elem.attrib.get(f'{{{w_ns}}}fldCharType') == 'separate'):
                found_separate = True
            elif found_separate and elem.tag == f'{{{w_ns}}}t' and elem.text:
                return elem.text.strip()
    
    return ""


def _find_caption_for_image_with_paragraph(image_para: ET.Element, all_paragraphs: List[ET.Element], style_map: Dict[str, str], image_name: str = "") -> Tuple[str, ET.Element | None]:
    """Find caption text for an image paragraph by looking for SEQ picnum fields and caption text. Returns (caption_text, caption_paragraph)."""
    try:
        img_index = all_paragraphs.index(image_para)
        
        # Strategy 1: Look for complete caption with number pattern in nearby paragraphs
        for offset in range(-2, 4):  # Search both before and after image
            para_index = img_index + offset
            if 0 <= para_index < len(all_paragraphs):
                para = all_paragraphs[para_index]
                text = _extract_text_from_paragraph(para).strip()
                
                # Check if this paragraph contains a complete figure caption
                figure_patterns = [
                    r'(рисунок\s+[-–—]?\s*\d+\s*[-–—]\s*.+)',
                    r'(рисунок\s+\d+\s*[-–—]\s*.+)',
                    r'(рис\.\s*\d+\s*[-–—]\s*.+)',
                    r'(figure\s+\d+\s*[-–—]\s*.+)',
                    r'(fig\.\s*\d+\s*[-–—]\s*.+)'
                ]
                
                for pattern in figure_patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        return match.group(1).strip(), para
        
        # Return original function result for fallback, without paragraph tracking
        caption = _find_caption_for_image_original(image_para, all_paragraphs, style_map, image_name)
        return caption, None
        
    except ValueError:
        # image_para not found in all_paragraphs
        pass
    
    return "", None

def _should_reorder_command_before_image(current_para: ET.Element, next_para: ET.Element, 
                                        current_text: str, style_map: Dict[str, str]) -> bool:
    """Check if current paragraph contains a command that should be moved before image in next paragraph."""
    # Check if next paragraph has an image
    next_drawings = next_para.findall('.//w:drawing', NS)
    if not next_drawings:
        return False
        
    # Check if current paragraph looks like a command
    command_patterns = [
        r'^\s*(sudo\s+)?(docker|wget|curl|psql|createdb|apt|apt-get|dnf|systemctl|sh\b|touch|chmod|chown|echo|ls|cat|kubectl|helm|tldr|man\s+)\b',
        r'^\s*[\w\.-]+\s+[\w\.-]+\s*$',  # Simple command pattern like "tldr tar"
        r'^\s*[a-zA-Z_][a-zA-Z0-9_]*\s+[a-zA-Z0-9_\.-]+\s*$'  # Command with argument
    ]
    
    if current_text:
        for pattern in command_patterns:
            if re.match(pattern, current_text.strip()):
                return True
                
    # Also check if paragraph has code-style formatting - need to implement this check here
    # Simplified code style check (copied from inside the function)
    pPr = current_para.find("w:pPr", NS)
    if pPr is not None:
        pStyle = pPr.find("w:pStyle", NS)
        if pStyle is not None:
            sid = pStyle.attrib.get(f"{{{NS['w']}}}val", "")
            style_name = style_map.get(sid, sid) or sid
            CODE_STYLE_NAME_PATTERNS = [
                r".*Команда.*",
                r".*Листинг.*", 
                r".*Code.*",
                r".*Код.*",
                r"ROSA_ТКом",
                r"ROSA_Команда_Таблица",
            ]
            for pattern in CODE_STYLE_NAME_PATTERNS:
                if re.match(pattern, style_name, re.IGNORECASE):
                    return True
                    
    return False

def _find_caption_for_image_original(image_para: ET.Element, all_paragraphs: List[ET.Element], style_map: Dict[str, str], image_name: str = "") -> str:
    """Find caption text for an image paragraph by looking for SEQ picnum fields and caption text."""
    try:
        img_index = all_paragraphs.index(image_para)
        
        # Strategy 1: Look for complete caption with number pattern in nearby paragraphs
        for offset in range(-2, 4):  # Search both before and after image
            para_index = img_index + offset
            if 0 <= para_index < len(all_paragraphs):
                para = all_paragraphs[para_index]
                text = _extract_text_from_paragraph(para).strip()
                
                # Check if this paragraph contains a complete figure caption
                figure_patterns = [
                    r'(рисунок\s+[-–—]?\s*\d+\s*[-–—]\s*.+)',
                    r'(рисунок\s+\d+\s*[-–—]\s*.+)',
                    r'(рис\.\s*\d+\s*[-–—]\s*.+)',
                    r'(figure\s+\d+\s*[-–—]\s*.+)',
                    r'(fig\.\s*\d+\s*[-–—]\s*.+)'
                ]
                
                for pattern in figure_patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        return match.group(1).strip()
        
        # Strategy 2: Look for separate number and caption parts (legacy approach)
        # First, look for SEQ picnum field in previous paragraphs (up to 3 paragraphs back)
        figure_number = ""
        for offset in range(1, 4):
            prev_index = img_index - offset
            if prev_index >= 0:
                prev_para = all_paragraphs[prev_index]
                seq_num = _find_seq_picnum_in_paragraph(prev_para)
                if seq_num:
                    figure_number = seq_num
                    break
        
        # Then, look for caption text in following paragraphs
        caption_text = ""
        for offset in range(1, 4):
            next_index = img_index + offset
            if next_index < len(all_paragraphs):
                next_para = all_paragraphs[next_index]
                
                if _is_caption_paragraph(next_para, style_map):
                    caption_text = _extract_text_from_paragraph(next_para).strip()
                    if caption_text:
                        break
                        
                # If we encounter another image, stop looking
                if next_para.findall('.//w:drawing', NS):
                    break
                    
                # If paragraph has significant content but isn't a caption, stop
                text = _extract_text_from_paragraph(next_para).strip()
                if len(text) > 50 and not _is_caption_paragraph(next_para, style_map):
                    break
        
        # Strategy 3: Try to extract figure number from image name attribute
        if not figure_number and image_name:
            # Look for number in image name like "Рисунок 1", "Picture 1", etc.
            name_patterns = [
                r'рисунок\s+(\d+)',
                r'рис\.\s*(\d+)', 
                r'figure\s+(\d+)',
                r'picture\s+(\d+)',
                r'fig\.\s*(\d+)'
            ]
            
            for pattern in name_patterns:
                match = re.search(pattern, image_name, re.IGNORECASE)
                if match:
                    figure_number = match.group(1)
                    break
        
        # Strategy 4: Try to extract figure number from text patterns in nearby paragraphs
        if not figure_number:
            for offset in range(-2, 4):
                para_index = img_index + offset
                if 0 <= para_index < len(all_paragraphs):
                    para = all_paragraphs[para_index]
                    text = _extract_text_from_paragraph(para).strip()
                    
                    # Look for figure number patterns
                    number_patterns = [
                        r'рисунок\s+[-–—]?\s*(\d+)',
                        r'рисунок\s+(\d+)',
                        r'рис\.\s*(\d+)',
                        r'figure\s+(\d+)',
                        r'fig\.\s*(\d+)'
                    ]
                    
                    for pattern in number_patterns:
                        match = re.search(pattern, text, re.IGNORECASE)
                        if match:
                            figure_number = match.group(1)
                            break
                    if figure_number:
                        break
        
        # Combine figure number and caption text
        if figure_number and caption_text:
            return f"Рисунок {figure_number} – {caption_text}"
        elif caption_text:
            # Check if caption already contains figure number
            if re.search(r'(рисунок|figure|рис\.|fig\.)\s+\d+', caption_text, re.IGNORECASE):
                return caption_text
            # Fallback to just caption text if no SEQ field found
            return caption_text
    
    except ValueError:
        # image_para not found in all_paragraphs
        pass
    
    return ""

def _parse_table(tbl: ET.Element, relationships: Dict[str, str], media_images: Dict[str, ResourceRef], 
                all_paragraphs: List[ET.Element], style_map: Dict[str, str]) -> Table:
    """Convert a DOCX table element into a Table block."""
    rows = tbl.findall('w:tr', NS)
    if not rows:
        return Table(header=TableRow(cells=[]), rows=[])

    def _row(tr: ET.Element) -> TableRow:
        cells: List[TableCell] = []
        for tc in tr.findall('w:tc', NS):
            blocks: List[Block] = []
            for p in tc.findall('w:p', NS):
                images, _ = _find_images_in_paragraph(p, relationships, media_images, all_paragraphs, style_map)
                for img in images:
                    blocks.append(img)
                
                # Extract formatted inlines from paragraph
                formatted_inlines = _extract_formatted_inlines(p)
                if formatted_inlines:
                    blocks.append(Paragraph(inlines=formatted_inlines))
            cells.append(TableCell(blocks=blocks))
        return TableRow(cells=cells)

    header = _row(rows[0])
    body = [_row(r) for r in rows[1:]]
    return Table(header=header, rows=body)

def split_docx_by_h1(
    docx_path: str | Path,
    out_dir: str | Path,
    heading_patterns: List[str] | None = None,
) -> Tuple[List[dict], List[Path]]:
    """
    Split DOCX by H1 into Markdown files.
    Returns: (sections, written_paths)
      sections: list of {"title": str, "lines": List[str]}
      written_paths: list of Paths written
    """
    docx_path = Path(docx_path)
    out_root = Path(out_dir) / docx_path.stem
    out_root.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(docx_path) as z:
        doc_xml = read_docx_part(z, "word/document.xml")
        styles_xml = read_docx_part(z, "word/styles.xml")
    if not doc_xml:
        raise RuntimeError("word/document.xml not found")

    style_map = styles_map(styles_xml)
    body = ET.fromstring(doc_xml).find(".//w:body", NS)
    if body is None:
        raise RuntimeError("No <w:body> found")

    patterns = heading_patterns or DEFAULT_HEADING_PATTERNS

    sections: List[dict] = []
    current = {"title": "front-matter", "lines": []}  # content before first H1

    for p in body.findall("w:p", NS):
        lvl = heading_level(p, style_map, patterns)
        if lvl:
            # For headings, use numbering-aware text extraction
            t = _text_with_numbering(p)
        else:
            # For regular paragraphs, use simple text extraction
            t = _text_of(p)
            
        if lvl == 1 and t:
            # Start new chapter
            if current["lines"]:
                sections.append(current)
            clean_t = clean_heading_text(t)
            current = {"title": clean_t, "lines": [f"# {clean_t}\n"]}
        else:
            if t:
                if lvl:
                    new_lvl = max(1, lvl - 1)
                    clean_t = clean_heading_text(t)
                    current["lines"].append(f"{'#'*new_lvl} {clean_t}\n")
                else:
                    current["lines"].append(t + "\n")

    if current["lines"]:
        sections.append(current)

    written: List[Path] = []
    for i, sec in enumerate(sections, 1):
        name = f"{i:02d}-{_slug(sec['title'])}.md"
        path = out_root / name
        path.write_text("".join(sec["lines"]), encoding="utf-8")
        written.append(path)

    return sections, written

def parse_docx_to_internal_doc(docx_path: str) -> Tuple[InternalDoc, List[ResourceRef]]:
    """
    Parse DOCX file and return InternalDoc AST format.
    Uses comprehensive XML-based heading numbering extraction.
    
    Args:
        docx_path: Path to the DOCX file
        
    Returns:
        Tuple of (InternalDoc, List[ResourceRef])
    """
    from core.numbering.heading_numbering import extract_headings_with_numbers
    
    docx_path = Path(docx_path)
    
    # Extract numbered headings using comprehensive XML parsing
    numbered_headings = extract_headings_with_numbers(str(docx_path))
    
    with zipfile.ZipFile(docx_path) as z:
        doc_xml = read_docx_part(z, "word/document.xml")
        styles_xml = read_docx_part(z, "word/styles.xml")
        rels_xml = read_docx_part(z, "word/_rels/document.xml.rels")
        numbering_xml = read_docx_part(z, "word/numbering.xml")
        
        # Extract images from media directory and create ResourceRef objects
        media_images = _extract_images_from_media(z)
    
    if not doc_xml:
        raise RuntimeError("word/document.xml not found")
    
    style_map = styles_map(styles_xml)
    style_nums = style_num_map(styles_xml)
    num_fmts = numbering_formats(numbering_xml)
    relationships = _load_relationships(rels_xml)
    body = ET.fromstring(doc_xml).find(".//w:body", NS)
    if body is None:
        raise RuntimeError("No <w:body> found")
    
    # Extract section mapping for cross-reference replacement
    docx_root = ET.fromstring(doc_xml)
    section_map = _extract_section_mapping(docx_root)
    
    patterns = DEFAULT_HEADING_PATTERNS
    blocks: List[Block] = []
    resources: List[ResourceRef] = list(media_images.values())  # Extract all images as resources
    heading_iter = iter(numbered_headings)
    
    # Get all paragraphs for caption detection
    all_paragraphs = body.findall(".//w:p", NS)
    
    # Track paragraphs that have been used as captions to avoid duplication
    used_caption_paragraphs = set()
    
    # Detect command-image patterns that need reordering
    commands_to_reorder = set()  # Set of paragraph indices that contain commands to reorder
    body_elements = list(body)
    
    for i, el in enumerate(body_elements):
        if el.tag == f"{{{NS['w']}}}p" and i + 1 < len(body_elements):
            current_para = el
            next_el = body_elements[i + 1]
            
            if next_el.tag == f"{{{NS['w']}}}p":  # Next element is also a paragraph
                next_para = next_el
                current_text = _text_of(current_para, section_map)
                
                if _should_reorder_command_before_image(current_para, next_para, current_text, style_map):
                    commands_to_reorder.add(i)

    # --- Heuristics for code block detection ---
    yaml_key_re = re.compile(r"^(?:-\s+.*|\s*[\w\./\[\]-]+\s*:\s*.*)$")
    yaml_start_hint_re = re.compile(r"\.(ya?ml)\b", re.IGNORECASE)
    yaml_first_line_re = re.compile(r"^(version|services|tls)\s*:\s*|^-\s+", re.IGNORECASE)

    bash_line_re = re.compile(r"^(?:sudo\s+)?(docker|wget|curl|psql|createdb|apt|apt-get|dnf|systemctl|sh\b|touch|chmod|chown|echo|ls|cat|kubectl|helm)\b")
    sql_line_re = re.compile(r"^(CREATE|GRANT|ALTER|INSERT|UPDATE|DELETE|DROP|TRUNCATE)\b", re.IGNORECASE)

    code_acc: List[str] = []
    code_lang: str | None = None
    code_title: str | None = None

    def flush_code():
        nonlocal code_acc, code_lang, code_title
        if code_acc:
            blocks.append(CodeBlock(code="\n".join(code_acc), language=code_lang, title=code_title))
        code_acc = []
        code_lang = None
        code_title = None

    def belongs_to_yaml(line: str) -> bool:
        return bool(yaml_key_re.match(line))

    def belongs_to_bash(line: str) -> bool:
        return bool(bash_line_re.match(line))

    def belongs_to_sql(line: str) -> bool:
        return bool(sql_line_re.match(line))

    # Code-style detection via paragraph style name, shading and monospaced fonts
    CODE_STYLE_NAME_PATTERNS = [
        r".*Команда.*",
        r".*Листинг.*",
        r".*Code.*",
        r".*Код.*",
        r"ROSA_ТКом",
        r"ROSA_Команда_Таблица",
    ]
    code_style_name_res = [re.compile(pat, re.IGNORECASE) for pat in CODE_STYLE_NAME_PATTERNS]

    MONO_FONTS = {"courier new", "consolas", "roboto mono", "menlo", "monaco", "lucida console"}

    def _para_style_name(p: ET.Element) -> str:
        pPr = p.find("w:pPr", NS)
        if pPr is None:
            return ""
        pStyle = pPr.find("w:pStyle", NS)
        if pStyle is None:
            return ""
        sid = pStyle.attrib.get(f"{{{NS['w']}}}val", "")
        return style_map.get(sid, sid) or sid

    def _has_gray_shading(p: ET.Element) -> bool:
        def has_shading(el: ET.Element | None) -> bool:
            if el is None:
                return False
            shd = el.find("w:shd", NS)
            if shd is None:
                return False
            fill = shd.attrib.get(f"{{{NS['w']}}}fill", "").lower()
            # D9D9D9 или любой серый оттенок
            return fill in {"d9d9d9", "e1dfdd", "ededed", "f2f2f2"} or bool(fill)

        pPr = p.find("w:pPr", NS)
        rPr = p.find("w:r/w:rPr", NS)
        return has_shading(pPr) or has_shading(rPr)

    def _uses_mono_font(p: ET.Element) -> bool:
        for r in p.findall(".//w:r", NS):
            rPr = r.find("w:rPr", NS)
            if rPr is None:
                continue
            rFonts = rPr.find("w:rFonts", NS)
            if rFonts is None:
                continue
            for attr in ("ascii", "hAnsi", "cs"):
                val = rFonts.attrib.get(f"{{{NS['w']}}}{attr}", "").lower()
                if val in MONO_FONTS:
                    return True
        return False

    def is_code_style_paragraph(p: ET.Element) -> bool:
        name = _para_style_name(p)
        if name and any(rx.match(name) for rx in code_style_name_res):
            return True
        if _has_gray_shading(p) and _uses_mono_font(p):
            return True
        return False

    def is_note_paragraph(text: str) -> bool:
        """Check if paragraph text starts with note pattern."""
        return bool(re.match(r'^\s*Примечани[ея]\s*[-–—]', text.strip()))
    
    
    def is_table_caption(text: str) -> bool:
        """Check if paragraph text is a table caption that should not have dash prefix."""
        # Pattern for table captions - common patterns found in documents
        table_patterns = [
            # Explicit table captions with numbers
            r'^\s*Таблица\s+\d+\s*[-–—]\s*.+',
            r'^\s*Table\s+\d+\s*[-–—]\s*.+',
            r'^\s*Таблица\s+\d+\s*.+',
            r'^\s*Table\s+\d+\s*.+',
            # Table descriptions/captions about requirements/parameters
            r'^\s*[Тт]ребования\s+к\s+аппаратным\s+средствам.+',
            r'^\s*[Тт]ребования\s+к\s+программным\s+средствам.+',  
            r'^\s*[Пп]араметры.+таблиц[еы].*',
            r'^\s*[Хх]арактеристики.+',
            # Generic patterns for table-like content descriptions
            r'^\s*[Оо]писание\s+(параметров|характеристик).+',
            r'^\s*[Сс]писок\s+(параметров|требований).+',
        ]
        text_stripped = text.strip()
        for pattern in table_patterns:
            if re.match(pattern, text_stripped, re.IGNORECASE):
                return True
        return False

    def _clean_bash_prefix(line: str) -> str:
        """Remove leading '# ' used in doc formatting before commands."""
        m = re.match(r"^\s*#\s+(.*)$", line)
        return m.group(1) if m else line

    prev_text: str = ""
    list_stack: List[tuple[ListBlock, int, bool]] = []

    def flush_lists() -> None:
        list_stack.clear()

    def ensure_list_block(level: int, ordered: bool) -> ListBlock:
        nonlocal list_stack
        while list_stack:
            current_block, current_level, current_ordered = list_stack[-1]
            if level < current_level or (level == current_level and current_ordered != ordered):
                list_stack.pop()
                continue
            break

        if not list_stack:
            new_block = ListBlock(ordered=ordered)
            blocks.append(new_block)
            list_stack.append((new_block, level, ordered))
            return new_block

        current_block, current_level, _ = list_stack[-1]
        if level == current_level:
            return current_block

        parent_block, _, _ = list_stack[-1]
        if parent_block.items:
            parent_item = parent_block.items[-1]
        else:
            parent_item = ListItem(blocks=[])
            parent_block.items.append(parent_item)
        new_block = ListBlock(ordered=ordered)
        parent_item.blocks.append(new_block)
        list_stack.append((new_block, level, ordered))
        return new_block
    
    for i, el in enumerate(body_elements):
        if el.tag == f"{{{NS['w']}}}p":
            p = el
            lvl = heading_level(p, style_map, patterns)
            text = _text_of(p, section_map)
            list_info = _paragraph_list_info(p, style_nums, num_fmts, style_map)
            paragraph_images, caption_paras = _find_images_in_paragraph(p, relationships, media_images, all_paragraphs, style_map, used_caption_paragraphs)
            used_caption_paragraphs.update(caption_paras)
            
            # Special handling for command-image reordering
            if i in commands_to_reorder and i + 1 < len(body_elements):
                next_para = body_elements[i + 1]
                if next_para.tag == f"{{{NS['w']}}}p":
                    next_images, next_caption_paras = _find_images_in_paragraph(next_para, relationships, media_images, all_paragraphs, style_map, used_caption_paragraphs)
                    used_caption_paragraphs.update(next_caption_paras)
                    
                    
                    # Flush any pending code block first
                    if code_acc:
                        blocks.append(CodeBlock(code="\n".join(code_acc), language=code_lang, title=code_title))
                        code_acc = []
                        code_lang = None
                        code_title = None
                    
                    # Add command as code block immediately
                    if text:
                        command_code = (_clean_bash_prefix(text)).strip()
                        blocks.append(CodeBlock(code=command_code, language="bash", title="Terminal"))
                    
                    # Add current paragraph images (if any)
                    for image in paragraph_images:
                        blocks.append(image)
                    
                    # Add images from next paragraph  
                    for next_image in next_images:
                        blocks.append(next_image)
                    
                    prev_text = text
                    continue
            
            # Skip paragraph if it was used as a caption
            if p in used_caption_paragraphs:
                # Add images even if text is skipped (to preserve order)
                for image in paragraph_images:
                    blocks.append(image)
                continue
                
            # Skip paragraph if its images were already processed by command reordering  
            if i > 0 and (i - 1) in commands_to_reorder and not text.strip():
                # This is likely an image-only paragraph that was processed by the previous command
                continue
                
            if text:
                # Style-based code detection (highest priority)
                if is_code_style_paragraph(p):
                    # Start or continue a code block; guess language from content
                    if code_lang is None:
                        if text.strip().startswith("#!/") or belongs_to_bash(text):
                            code_lang = "bash"
                            code_title = "Terminal"
                        elif belongs_to_yaml(text):
                            code_lang = "yaml"
                            code_title = None
                        elif belongs_to_sql(text):
                            code_lang = "sql"
                            code_title = None
                        else:
                            code_lang = "bash"  # default for command listings
                            code_title = "Terminal"
                    code_acc.append((_clean_bash_prefix(text)).strip())
                    prev_text = text
                    # Add images after processing code text (to preserve order)
                    for image in paragraph_images:
                        blocks.append(image)
                    continue

                # If we are inside a code block, try to continue it
                if code_lang == "yaml":
                    if belongs_to_yaml(text):
                        code_acc.append(text.strip())
                        prev_text = text
                        # Add images after processing yaml text (to preserve order)
                        for image in paragraph_images:
                            blocks.append(image)
                        continue
                    else:
                        flush_code()
                elif code_lang == "bash":
                    if belongs_to_bash(text):
                        code_acc.append((_clean_bash_prefix(text)).strip())
                        prev_text = text
                        # Add images after processing bash text (to preserve order)
                        for image in paragraph_images:
                            blocks.append(image)
                        continue
                    else:
                        flush_code()
                elif code_lang == "sql":
                    if belongs_to_sql(text) or text.strip().endswith(";"):
                        code_acc.append(text.strip())
                        prev_text = text
                        # Add images after processing sql text (to preserve order)
                        for image in paragraph_images:
                            blocks.append(image)
                        continue
                    else:
                        flush_code()

                if lvl:
                    if list_stack:
                        flush_lists()
                    try:
                        numbered_heading = next(heading_iter)
                        level = min(numbered_heading.level, 6)
                        if level == 1:
                            numbered_text = numbered_heading.text
                        else:
                            numbered_text = f"{numbered_heading.number} {numbered_heading.text}"
                        blocks.append(Heading(level=level, text=numbered_text))
                    except StopIteration:
                        level = min(lvl, 6)
                        blocks.append(Heading(level=level, text=text))
                else:
                    # Decide if a new code block should start
                    started_code = False
                    # YAML detection: hint in previous line about *.yml/.yaml or typical first YAML keys
                    if yaml_start_hint_re.search(prev_text) and yaml_first_line_re.search(text):
                        code_lang = "yaml"
                        m = re.search(r"([\w\./-]+\.(?:ya?ml))", prev_text, flags=re.IGNORECASE)
                        code_title = m.group(1) if m else None
                        code_acc.append(text.strip())
                        started_code = True
                    elif yaml_first_line_re.search(text) and belongs_to_yaml(text):
                        code_lang = "yaml"
                        code_title = None
                        code_acc.append(text.strip())
                        started_code = True
                    # Bash detection
                    elif belongs_to_bash(text):
                        code_lang = "bash"
                        code_title = "Terminal"
                        code_acc.append((_clean_bash_prefix(text)).strip())
                        started_code = True
                    # SQL detection
                    elif belongs_to_sql(text):
                        code_lang = "sql"
                        code_title = None
                        code_acc.append(text.strip())
                        started_code = True

                    if started_code:
                        prev_text = text
                        # Add images after processing started code text (to preserve order)
                        for image in paragraph_images:
                            blocks.append(image)
                        continue

                    if list_info and not is_table_caption(text):
                        fmt, list_level = list_info
                        ordered = fmt not in {"bullet", "none"}
                        target_list = ensure_list_block(list_level, ordered)
                        list_item = ListItem(blocks=[])
                        target_list.items.append(list_item)
                        formatted_inlines = _extract_formatted_inlines(p, section_map)
                        if formatted_inlines:
                            list_item.blocks.append(Paragraph(inlines=formatted_inlines))
                        else:
                            list_item.blocks.append(Paragraph(inlines=[InlineText(content=text)]))
                        for image in paragraph_images:
                            list_item.blocks.append(image)
                        prev_text = text
                        continue
                    else:
                        if list_stack:
                            flush_lists()

                    if is_note_paragraph(text):
                        text = f"> {text}"
                    inlines = [InlineText(content=text)]
                    blocks.append(Paragraph(inlines=inlines))
            else:
                if list_stack:
                    flush_lists()

            # Add images after processing text (to preserve order as in DOCX)
            for image in paragraph_images:
                blocks.append(image)
            prev_text = text
        elif el.tag == f"{{{NS['w']}}}tbl":
            if list_stack:
                flush_lists()
            # If a code block was open before a table, flush it
            flush_code()
            table_block = _parse_table(el, relationships, media_images, all_paragraphs, style_map)
            blocks.append(table_block)
    # Flush any pending code block at the end
    flush_code()
    internal_doc = InternalDoc(blocks=blocks)
    return internal_doc, resources

# Simple CLI
def _cli():
    ap = argparse.ArgumentParser(description="Split DOCX into Markdown chapters by H1")
    ap.add_argument("docx", help="Path to .docx")
    ap.add_argument("-o", "--out", default="out", help="Output directory (default: out)")
    args = ap.parse_args()
    sections, written = split_docx_by_h1(args.docx, args.out)
    print(f"Chapters: {len(sections)}")
    print("Written files:")
    for p in written:
        print(" -", p)

if __name__ == "__main__":
    _cli()
