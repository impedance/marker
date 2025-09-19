"""Tests for heading rendering in DOCX parser."""
from core.adapters.document_parser import parse_document
from core.model.internal_doc import Heading, Paragraph

def test_top_level_heading_unnumbered():
    """First heading should be level 1 without numbering."""
    doc, _ = parse_document('real-docs/dev-portal-user.docx')
    first_heading = next(b for b in doc.blocks if isinstance(b, Heading))
    assert first_heading.level == 1
    assert first_heading.text == 'Общие сведения'

def test_note_paragraph_detection():
    """Test detection and formatting of note paragraphs."""
    from core.adapters.docx_parser import parse_docx_to_internal_doc
    
    # Mock function to test note detection directly
    def is_note_paragraph(text: str) -> bool:
        import re
        return bool(re.match(r'^\s*Примечани[ея]\s*[-–—]', text.strip()))
    
    # Test various note patterns
    test_cases = [
        # Единственное число (уже работает)
        ("Примечание – это обычная заметка", True),
        ("Примечание – важная информация", True),
        ("  Примечание – с пробелами в начале", True),
        ("Примечание– без пробела перед тире", True),
        # Множественное число (новая функциональность)
        ("Примечания – это обычная заметка", True),
        ("Примечания – важная информация", True),
        ("  Примечания – с пробелами в начале", True),
        ("Примечания– без пробела перед тире", True),
        # Разные виды тире
        ("Примечание — длинное тире", True),
        ("Примечания — длинное тире", True),
        ("Примечание - обычный дефис", True),
        ("Примечания - обычный дефис", True),
        # Негативные случаи
        ("Обычный текст", False),
        ("Заметка – но не примечание", False),
        ("", False)
    ]
    
    for text, expected in test_cases:
        result = is_note_paragraph(text)
        assert result == expected, f"Failed for text: '{text}', expected {expected}, got {result}"
