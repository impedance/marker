from pathlib import Path
from docx import Document

from core.adapters.document_parser import parse_document


def test_bullet_list_parsed(tmp_path: Path) -> None:
    """Ensure bullet lists become markdown list items."""
    doc = Document()
    doc.add_paragraph("First", style="List Bullet")
    doc.add_paragraph("Second", style="List Bullet")
    path = tmp_path / "list.docx"
    doc.save(path)

    internal_doc, _ = parse_document(str(path))
    paragraphs = [
        "".join(inl.content for inl in block.inlines)
        for block in internal_doc.blocks
        if block.type == "paragraph"
    ]
    assert paragraphs[:2] == ["- First", "- Second"]
