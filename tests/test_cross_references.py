"""Tests for replacing cross references with section titles."""
from core.adapters.document_parser import parse_document
from core.model.internal_doc import Paragraph


def _paragraph_text(paragraph: Paragraph) -> str:
    return "".join(getattr(inline, "content", "") for inline in paragraph.inlines)


def test_cross_references_replaced_with_section_titles() -> None:
    doc, _ = parse_document("real-docs/hrom-admin-found.docx")
    paragraphs = [
        _paragraph_text(block)
        for block in doc.blocks
        if isinstance(block, Paragraph)
    ]

    flows_reference = next(
        text
        for text in paragraphs
        if text.startswith("Более подробный разбор потоков")
    )
    gzip_reference = next(
        text
        for text in paragraphs
        if text.startswith("Опции утилиты bzip2 аналогичны опциям Gzip")
    )

    assert "п.14.2" not in flows_reference
    assert "п. Жизненный цикл процесса" in flows_reference

    assert "п.21.1" not in gzip_reference
    assert "п. Утилита Gzip" in gzip_reference
