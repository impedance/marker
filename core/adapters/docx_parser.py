
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

def _paragraph_list_type(p: ET.Element, style_nums: Dict[str, str], num_fmts: Dict[str, str]) -> str | None:
    """Return list format if paragraph is part of a list."""
    pPr = p.find("w:pPr", NS)
    if pPr is None:
        return None
    numPr = pPr.find("w:numPr", NS)
    if numPr is not None:
        numId_el = numPr.find("w:numId", NS)
        if numId_el is not None:
            num_id = numId_el.attrib.get(f"{{{NS['w']}}}val", "")
            return num_fmts.get(num_id)
    pStyle = pPr.find("w:pStyle", NS)
    if pStyle is not None:
        sid = pStyle.attrib.get(f"{{{NS['w']}}}val", "")
        num_id = style_nums.get(sid)
        if num_id:
            return num_fmts.get(num_id)
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

def _text_of(p: ET.Element) -> str:
    """Extract text from paragraph, including any manual numbering."""
    texts: List[str] = []
    for t in p.findall(".//w:t", NS):
        texts.append(t.text or "")
    full_text = "".join(texts).strip()
    
    return full_text

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
                             all_paragraphs: List[ET.Element], style_map: Dict[str, str]) -> List[Image]:
    """Find all images referenced in a paragraph and return Image blocks with captions."""
    images = []
    
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
                    caption = _find_caption_for_image(p, all_paragraphs, style_map, image_name)
                    
                    # Create Image block
                    image = Image(
                        alt=f"Image {resource_ref.id}",  # Simple alt text
                        resource_id=resource_ref.id,
                        caption=caption
                    )
                    images.append(image)
    
    return images


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


def _find_caption_for_image(image_para: ET.Element, all_paragraphs: List[ET.Element], style_map: Dict[str, str], image_name: str = "") -> str:
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
                images = _find_images_in_paragraph(p, relationships, media_images, all_paragraphs, style_map)
                for img in images:
                    blocks.append(img)
                text = _text_of(p)
                if text:
                    blocks.append(Paragraph(inlines=[InlineText(content=text)]))
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
    
    patterns = DEFAULT_HEADING_PATTERNS
    blocks: List[Block] = []
    resources: List[ResourceRef] = list(media_images.values())  # Extract all images as resources
    heading_iter = iter(numbered_headings)
    
    # Get all paragraphs for caption detection
    all_paragraphs = body.findall(".//w:p", NS)

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
        return bool(re.match(r'^\s*Примечание\s*–', text.strip()))
    
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
    for el in list(body):
        if el.tag == f"{{{NS['w']}}}p":
            p = el
            lvl = heading_level(p, style_map, patterns)
            text = _text_of(p)
            list_type = _paragraph_list_type(p, style_nums, num_fmts)
            paragraph_images = _find_images_in_paragraph(p, relationships, media_images, all_paragraphs, style_map)
            for image in paragraph_images:
                blocks.append(image)
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
                    continue

                # If we are inside a code block, try to continue it
                if code_lang == "yaml":
                    if belongs_to_yaml(text):
                        code_acc.append(text.strip())
                        prev_text = text
                        continue
                    else:
                        flush_code()
                elif code_lang == "bash":
                    if belongs_to_bash(text):
                        code_acc.append((_clean_bash_prefix(text)).strip())
                        prev_text = text
                        continue
                    else:
                        flush_code()
                elif code_lang == "sql":
                    if belongs_to_sql(text) or text.strip().endswith(";"):
                        code_acc.append(text.strip())
                        prev_text = text
                        continue
                    else:
                        flush_code()

                if lvl:
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
                        continue

                    if list_type and not is_table_caption(text):
                        text = f"- {text}"
                    elif is_note_paragraph(text):
                        text = f"> {text}"
                    inlines = [InlineText(content=text)]
                    blocks.append(Paragraph(inlines=inlines))
            elif paragraph_images:
                pass
            prev_text = text
        elif el.tag == f"{{{NS['w']}}}tbl":
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
