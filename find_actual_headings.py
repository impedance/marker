#!/usr/bin/env python3
"""
Find actual headings (not table of contents) in DOCX file
"""

import zipfile, re
from xml.etree import ElementTree as ET

# Import shared constants and utilities
from core.utils.xml_constants import NS, DEFAULT_HEADING_PATTERNS
from core.utils.docx_utils import read_docx_part, styles_map, heading_level

def _styles_map(styles_xml):
    """Map styleId -> human-readable name from styles.xml."""
    if not styles_xml: return {}
    root = ET.fromstring(styles_xml)
    out = {}
    for s in root.findall(".//w:style", NS):
        sid = s.attrib.get(f"{{{NS['w']}}}styleId")
        name_el = s.find("w:name", NS)
        name = name_el.attrib.get(f"{{{NS['w']}}}val") if name_el is not None else sid
        if sid: out[sid] = name
    return out

def _heading_level(p, styles_map, heading_patterns):
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

def find_actual_headings():
    docx_file = "docs-docx-pdfs/dev-portal-admin.docx"
    
    print(f"Finding actual headings in: {docx_file}")
    print("=" * 60)
    
    with zipfile.ZipFile(docx_file) as z:
        doc_xml = z.read("word/document.xml")
        styles_xml = z.read("word/styles.xml") if "word/styles.xml" in z.namelist() else None
        body = ET.fromstring(doc_xml).find(".//w:body", NS)
        
        styles_map = _styles_map(styles_xml)
        patterns = DEFAULT_HEADING_PATTERNS
        
        print("Actual headings (detected by style/outline level):")
        found_count = 0
        
        for i, p in enumerate(body.findall("w:p", NS)):
            lvl = _heading_level(p, styles_map, patterns)
            if lvl:  # This is a heading
                # Get text content
                texts = []
                for t in p.findall(".//w:t", NS):
                    texts.append(t.text or "")
                full_text = "".join(texts).strip()
                
                if full_text:
                    print(f"  H{lvl} (para {i+1}): '{full_text}'")
                    
                    # Check for numbering in the text
                    if re.match(r'^\d+(\.\d+)*\s+', full_text):
                        print(f"    -> Contains numbering!")
                    
                    # Check paragraph properties
                    pPr = p.find("w:pPr", NS)
                    if pPr is not None:
                        # Check for numbering properties
                        numPr = pPr.find("w:numPr", NS)
                        if numPr is not None:
                            numId_el = numPr.find("w:numId", NS)
                            ilvl_el = numPr.find("w:ilvl", NS)
                            numId = numId_el.attrib.get(f"{{{NS['w']}}}val", "") if numId_el is not None else ""
                            ilvl = ilvl_el.attrib.get(f"{{{NS['w']}}}val", "") if ilvl_el is not None else ""
                            print(f"    -> Has automatic numbering: numId={numId}, ilvl={ilvl}")
                    
                    found_count += 1
                    if found_count >= 15:  # Limit output
                        print("  ... (showing first 15 headings)")
                        break

if __name__ == "__main__":
    find_actual_headings()