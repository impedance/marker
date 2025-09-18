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


def test_letter_appendix_references_are_replaced() -> None:
    doc, _ = parse_document("docs-work/rukovod_adminis_32eks-_monit-2.3.0.docx")
    paragraphs = [
        _paragraph_text(block)
        for block in doc.blocks
        if isinstance(block, Paragraph)
    ]

    appendix_g_reference = next(
        text
        for text in paragraphs
        if "Пассивные и активные проверки Агентов" in text and "п." in text
    )
    appendix_d_reference = next(
        text
        for text in paragraphs
        if "Траппер-элементы данных" in text and "п." in text
    )

    assert "п.Г.3" not in appendix_g_reference
    assert "п. Пассивные и активные проверки Агентов" in appendix_g_reference

    assert "п.Д.12" not in appendix_d_reference
    assert "п. Траппер-элементы данных" in appendix_d_reference


def test_cross_reference_page_numbers_removed() -> None:
    doc, _ = parse_document("docs-work/rukovod_adminis_32eks-_monit-2.3.0.docx")
    paragraphs = [
        _paragraph_text(block)
        for block in doc.blocks
        if isinstance(block, Paragraph)
    ]

    foreach_reference = next(
        text
        for text in paragraphs
        if "foreach" in text and "п." in text
    )

    assert "339" not in foreach_reference
