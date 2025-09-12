from pathlib import Path
from docx import Document

from core.adapters.document_parser import parse_document
from core.render.markdown_renderer import render_markdown


def test_table_parsed_and_rendered(tmp_path: Path) -> None:
    """Tables from DOCX are preserved and rendered as Markdown."""
    doc = Document()
    table = doc.add_table(rows=2, cols=3)
    hdr = table.rows[0].cells
    hdr[0].text = "A"
    hdr[1].text = "B"
    hdr[2].text = "C"
    row = table.rows[1].cells
    row[0].text = "1"
    row[1].text = "2"
    row[2].text = "3"
    path = tmp_path / "table.docx"
    doc.save(path)

    internal_doc, _ = parse_document(str(path))
    assert internal_doc.blocks and internal_doc.blocks[0].type == "table"

    markdown = render_markdown(internal_doc, {})
    expected = "| A | B | C |\n| --- | --- | --- |\n| 1 | 2 | 3 |"
    assert markdown == expected
