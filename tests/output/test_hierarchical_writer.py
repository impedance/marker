from pathlib import Path

import pytest
from typer.testing import CliRunner

from core.adapters.document_parser import parse_document
from core.model.internal_doc import InternalDoc, Heading, Paragraph, Text

# Import functions to be tested
from core.output.hierarchical_writer import (
    LETTER_NUMBER_BASE,
    _split_number_and_title,
    _code_for_levels,
    _collect_sections,
    export_docx_hierarchy,
)
from doc2chapmd import app


def test_split_number_and_title_variants():
    assert _split_number_and_title("1.2.3 Heading") == ([1, 2, 3], "Heading", False)
    assert _split_number_and_title("1.2.3. Heading") == ([1, 2, 3], "Heading", False)
    assert _split_number_and_title("1.2.3 - Heading") == ([1, 2, 3], "Heading", False)
    assert _split_number_and_title("Heading") == ([], "Heading", False)
    assert _split_number_and_title("Приложение Б. Тест") == ([LETTER_NUMBER_BASE + 2], "Тест", True)


def test_code_for_levels():
    assert _code_for_levels([1]) == "010000"
    assert _code_for_levels([1, 2]) == "010200"
    assert _code_for_levels([1, 2, 3]) == "010203"


def _sample_blocks():
    return [
        Heading(level=1, text="Chapter 1"),
        Paragraph(inlines=[Text(content="Intro H1")]),
        Heading(level=2, text="1.1 Section 1"),
        Paragraph(inlines=[Text(content="Intro Section")]),
        Heading(level=3, text="1.1.1 Topic A"),
        Paragraph(inlines=[Text(content="Content A")]),
        Heading(level=3, text="1.1.2 Topic B"),
        Paragraph(inlines=[Text(content="Content B")]),
        Heading(level=2, text="1.2 Section 2"),
        Paragraph(inlines=[Text(content="Section 2 content")]),
        Heading(level=1, text="Chapter 2"),
        Paragraph(inlines=[Text(content="Chapter 2 intro")]),
    ]


def test_collect_sections_splits_blocks_correctly():
    sections = _collect_sections(_sample_blocks())
    titles = [s.title for s in sections]
    assert titles == [
        "Chapter 1",
        "Section 1",
        "Section 2",
        "Chapter 2",
    ]
    numbers = [s.number for s in sections]
    assert numbers == [
        [1],
        [1, 1],
        [1, 2],
        [2],
    ]
    for sec in sections:
        heading = sec.blocks[0]
        assert isinstance(heading, Heading)
        if sec.level > 1:
            assert heading.text.startswith(".".join(map(str, sec.number)))
        else:
            assert heading.text == sec.title


def test_export_docx_hierarchy_creates_structure(tmp_path, monkeypatch):
    doc = InternalDoc(blocks=_sample_blocks())
    monkeypatch.setattr(
        "core.output.hierarchical_writer.parse_document", lambda path: (doc, {})
    )
    written = export_docx_hierarchy("dummy.docx", tmp_path)
    doc_dir = tmp_path / "dummy"  # lowercase after _transliterate fix
    expected = {
        doc_dir / "010000.chapter-1" / "0.index.md",  # lowercase after _transliterate fix
        doc_dir / "010000.chapter-1" / "010100.section-1.md",  # lowercase after _transliterate fix
        doc_dir / "010000.chapter-1" / "010200.section-2.md",  # lowercase after _transliterate fix
        doc_dir / "020000.chapter-2" / "0.index.md",  # lowercase after _transliterate fix
    }
    assert set(written) == expected
    index_content = Path(doc_dir / "010000.chapter-1" / "0.index.md").read_text()  # lowercase after _transliterate fix
    assert index_content.startswith("# Chapter 1")
    sec_content = Path(doc_dir / "010000.chapter-1" / "010100.section-1.md").read_text()  # lowercase after _transliterate fix
    assert sec_content.startswith("# Section 1")


def test_cli_build_invokes_export(monkeypatch, tmp_path):
    runner = CliRunner()
    called: dict[str, tuple[Path, Path]] = {}

    def fake_export_centralized(docx_path: Path, out_root: Path):
        called["args"] = (docx_path, out_root)
        return []

    # Mock both functions since the build command can use either
    monkeypatch.setattr("doc2chapmd.export_docx_hierarchy", fake_export_centralized)
    monkeypatch.setattr("doc2chapmd.export_docx_hierarchy_centralized", fake_export_centralized)

    result = runner.invoke(app, ["build", "file.docx", "--out", str(tmp_path)])
    assert result.exit_code == 0
    assert called["args"] == (Path("file.docx"), tmp_path)


def test_appendix_sections_do_not_absorb_previous_content() -> None:
    doc, _ = parse_document("docs-work/rukovod_adminis_32eks-_monit-2.3.0.docx")
    sections = _collect_sections(doc.blocks)

    h1_sections = {sec.title: sec for sec in sections if sec.level == 1}
    assert "Конфигурация демонов" in h1_sections
    assert "Протоколы" in h1_sections

    def _paragraph_texts(section):
        return [
            "".join(getattr(inline, "content", "") for inline in block.inlines)
            for block in section.blocks
            if isinstance(block, Paragraph)
        ]

    config_paragraphs = _paragraph_texts(h1_sections["Конфигурация демонов"])
    protocols_paragraphs = _paragraph_texts(h1_sections["Протоколы"])

    anchor = 'Обмен данными "Сервер ↔ Прокси"'
    assert any(anchor in text for text in config_paragraphs)
    assert not any(anchor in text for text in protocols_paragraphs)
