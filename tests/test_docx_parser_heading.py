"""Tests for heading rendering in DOCX parser."""
from core.adapters.document_parser import parse_document
from core.model.internal_doc import Heading

def test_top_level_heading_unnumbered():
    """First heading should be level 1 without numbering."""
    doc, _ = parse_document('real-docs/dev-portal-user.docx')
    first_heading = next(b for b in doc.blocks if isinstance(b, Heading))
    assert first_heading.level == 1
    assert first_heading.text == 'Общие сведения'
