
"""
docx_parser.py
Parse DOCX files using WordprocessingML (DOCX XML) to extract structured content.
- Detects headings via w:outlineLvl (preferred) or paragraph style names.
- Extracts all text content with proper heading levels.
- Extracts images from word/media/ directory and references from document.xml.
- Returns structured data compatible with InternalDoc AST format.

This module replaces the generic docling parsing for DOCX files to ensure
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
    Text as InlineText,
    Image,
    Table,
    TableRow,
    TableCell,
)
from core.model.resource_ref import ResourceRef

NS = {
    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'rel': 'http://schemas.openxmlformats.org/package/2006/relationships'
}

DEFAULT_HEADING_PATTERNS = [
    r"^Heading\s*(\d)$",           # English
    r"^Заголовок\s*(\d)$",         # Russian exact
    r".*Заголовок\s*(\d)$",        # Russian with prefixes like 'ROSA_Заголовок 1'
    r"^Titre\s*(\d)$",             # French
    r"^Überschrift\s*(\d)$",       # German
    r"^Encabezado\s*(\d)$",        # Spanish
    r".*\bheading\s*(\d)$",        # fallback lowercase '... heading 2'
]

def _read(z: zipfile.ZipFile, name: str) -> bytes | None:
    return z.read(name) if name in z.namelist() else None

def _styles_map(styles_xml: bytes | None) -> Dict[str, str]:
    """Map styleId -> human-readable name from styles.xml."""
    if not styles_xml: return {}
    root = ET.fromstring(styles_xml)
    out: Dict[str, str] = {}
    for s in root.findall(".//w:style", NS):
        sid = s.attrib.get(f"{{{NS['w']}}}styleId")
        name_el = s.find("w:name", NS)
        name = name_el.attrib.get(f"{{{NS['w']}}}val") if name_el is not None else sid
        if sid: out[sid] = name
    return out

def _style_num_map(styles_xml: bytes | None) -> Dict[str, str]:
    """Map styleId -> numId for list styles."""
    if not styles_xml:
        return {}
    root = ET.fromstring(styles_xml)
    out: Dict[str, str] = {}
    for s in root.findall(".//w:style", NS):
        sid = s.attrib.get(f"{{{NS['w']}}}styleId")
        numPr = s.find("w:pPr/w:numPr", NS)
        if sid and numPr is not None:
            numId = numPr.find("w:numId", NS)
            if numId is not None:
                out[sid] = numId.attrib.get(f"{{{NS['w']}}}val", "")
    return out

def _numbering_formats(numbering_xml: bytes | None) -> Dict[str, str]:
    """Map numId -> numFmt (e.g., bullet, decimal)."""
    if not numbering_xml:
        return {}
    root = ET.fromstring(numbering_xml)
    abstract_map: Dict[str, str] = {}
    for abs_num in root.findall("w:abstractNum", NS):
        abs_id = abs_num.attrib.get(f"{{{NS['w']}}}abstractNumId")
        lvl = abs_num.find("w:lvl", NS)
        if abs_id and lvl is not None:
            fmt_el = lvl.find("w:numFmt", NS)
            if fmt_el is not None:
                abstract_map[abs_id] = fmt_el.attrib.get(f"{{{NS['w']}}}val", "")
    out: Dict[str, str] = {}
    for num in root.findall("w:num", NS):
        num_id = num.attrib.get(f"{{{NS['w']}}}numId")
        abs_id_el = num.find("w:abstractNumId", NS)
        abs_id = abs_id_el.attrib.get(f"{{{NS['w']}}}val", "") if abs_id_el is not None else ""
        if num_id and abs_id in abstract_map:
            out[num_id] = abstract_map[abs_id]
    return out

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
        number, title = _extract_heading_number_and_title(text)
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

def _extract_heading_number_and_title(text: str) -> tuple[str, str]:
    """Extract chapter number and title from heading text.
    
    Args:
        text: Full heading text (e.g., "4.1.3 Installation and Setup")
        
    Returns:
        tuple of (number, title) where number might be empty if no numbering found
    """
    # Pattern to match various numbering formats
    number_patterns = [
        r'^(\d+(?:\.\d+)*)\s+(.+)$',  # "4.1.3 Title" or "2.1 Title" or "2 Title"
        r'^(\d+(?:\.\d+)*)\.\s+(.+)$',  # "4.1.3. Title" 
        r'^(\d+(?:\.\d+)*)\s*[-–—]\s*(.+)$',  # "4.1.3 - Title" or "4.1.3 – Title"
    ]
    
    for pattern in number_patterns:
        match = re.match(pattern, text.strip())
        if match:
            return match.group(1), match.group(2).strip()
    
    # No numbering found, return empty number and full text as title
    return "", text

def _heading_level(p: ET.Element, styles_map: Dict[str,str], heading_patterns: List[str]) -> int | None:
    """Return heading level (1..9) or None if not a heading."""
    pPr = p.find("w:pPr", NS)
    if pPr is None:
        return None
    # Prefer outlineLvl when present
    outline = pPr.find("w:outlineLvl", NS)
    if outline is not None:
        val = outline.attrib.get(f"{{{NS['w']}}}val")
        if val is not None:
            try:
                return int(val) + 1  # outlineLvl 0 => H1
            except ValueError:
                pass
    # Fallback: paragraph style name
    pStyle = pPr.find("w:pStyle", NS)
    if pStyle is not None:
        sid = pStyle.attrib.get(f"{{{NS['w']}}}val", "")
        sname = styles_map.get(sid, sid) or sid
        for pat in heading_patterns:
            m = re.match(pat, sname, flags=re.IGNORECASE)
            if m:
                try:
                    return int(m.group(1))
                except ValueError:
                    continue
        # Also try styleId like Heading1
        m = re.match(r"^Heading(\d)$", sid, flags=re.IGNORECASE)
        if m:
            return int(m.group(1))
    return None

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

def _find_images_in_paragraph(p: ET.Element, relationships: Dict[str, str], media_images: Dict[str, ResourceRef]) -> List[Image]:
    """Find all images referenced in a paragraph and return Image blocks."""
    images = []
    
    # Look for drawing elements that contain image references
    for drawing in p.findall('.//w:drawing', NS):
        for blip in drawing.findall('.//*[@r:embed]', NS):
            embed_id = blip.attrib.get(f"{{{NS['r']}}}embed")
            if embed_id and embed_id in relationships:
                target_path = relationships[embed_id]
                full_path = f"word/{target_path}"
                
                if full_path in media_images:
                    resource_ref = media_images[full_path]
                    # Create Image block
                    image = Image(
                        alt=f"Image {resource_ref.id}",  # Simple alt text
                        resource_id=resource_ref.id
                    )
                    images.append(image)
    
    return images

def _parse_table(tbl: ET.Element, relationships: Dict[str, str], media_images: Dict[str, ResourceRef]) -> Table:
    """Convert a DOCX table element into a Table block."""
    rows = tbl.findall('w:tr', NS)
    if not rows:
        return Table(header=TableRow(cells=[]), rows=[])

    def _row(tr: ET.Element) -> TableRow:
        cells: List[TableCell] = []
        for tc in tr.findall('w:tc', NS):
            blocks: List[Block] = []
            for p in tc.findall('w:p', NS):
                images = _find_images_in_paragraph(p, relationships, media_images)
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
        doc_xml = _read(z, "word/document.xml")
        styles_xml = _read(z, "word/styles.xml")
    if not doc_xml:
        raise RuntimeError("word/document.xml not found")

    styles_map = _styles_map(styles_xml)
    body = ET.fromstring(doc_xml).find(".//w:body", NS)
    if body is None:
        raise RuntimeError("No <w:body> found")

    patterns = heading_patterns or DEFAULT_HEADING_PATTERNS

    sections: List[dict] = []
    current = {"title": "front-matter", "lines": []}  # content before first H1

    for p in body.findall("w:p", NS):
        lvl = _heading_level(p, styles_map, patterns)
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
            current = {"title": t, "lines": [f"# {t}\n"]}
        else:
            if t:
                if lvl:
                    current["lines"].append(f"{'#'*lvl} {t}\n")
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
        doc_xml = _read(z, "word/document.xml")
        styles_xml = _read(z, "word/styles.xml")
        rels_xml = _read(z, "word/_rels/document.xml.rels")
        numbering_xml = _read(z, "word/numbering.xml")
        
        # Extract images from media directory and create ResourceRef objects
        media_images = _extract_images_from_media(z)
    
    if not doc_xml:
        raise RuntimeError("word/document.xml not found")
    
    styles_map = _styles_map(styles_xml)
    style_nums = _style_num_map(styles_xml)
    num_fmts = _numbering_formats(numbering_xml)
    relationships = _load_relationships(rels_xml)
    body = ET.fromstring(doc_xml).find(".//w:body", NS)
    if body is None:
        raise RuntimeError("No <w:body> found")
    
    patterns = DEFAULT_HEADING_PATTERNS
    blocks: List[Block] = []
    resources: List[ResourceRef] = list(media_images.values())  # Extract all images as resources
    heading_iter = iter(numbered_headings)

    for el in list(body):
        if el.tag == f"{{{NS['w']}}}p":
            p = el
            lvl = _heading_level(p, styles_map, patterns)
            text = _text_of(p)
            list_type = _paragraph_list_type(p, style_nums, num_fmts)
            paragraph_images = _find_images_in_paragraph(p, relationships, media_images)
            for image in paragraph_images:
                blocks.append(image)
            if text:
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
                    if list_type:
                        text = f"- {text}"
                    inlines = [InlineText(content=text)]
                    blocks.append(Paragraph(inlines=inlines))
            elif paragraph_images:
                pass
        elif el.tag == f"{{{NS['w']}}}tbl":
            table_block = _parse_table(el, relationships, media_images)
            blocks.append(table_block)
    
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
