#!/usr/bin/env python3
"""Utility script for exploring the current table parsing output."""

from pathlib import Path

from core.adapters.docx_parser import parse_docx_to_internal_doc
from core.model.internal_doc import Table
from core.render.markdown_renderer import render_markdown


DEFAULT_DOCX = Path("real-docs/hrom-12-admin-foundations.docx")


def _describe_block_content(block) -> str:
    """Return a human-readable summary of a table cell block."""
    if hasattr(block, "inlines"):
        return "".join(
            inline.content for inline in block.inlines if hasattr(inline, "content")
        )
    if hasattr(block, "content"):
        return str(block.content)
    return str(block)


def describe_table_parsing(docx_path: Path = DEFAULT_DOCX) -> None:
    """Print details about parsed tables and their Markdown rendering."""
    print(f"Parsing document: {docx_path}")
    internal_doc, _ = parse_docx_to_internal_doc(str(docx_path))

    table_blocks = [block for block in internal_doc.blocks if isinstance(block, Table)]
    print(f"Found {len(table_blocks)} tables")

    if not table_blocks:
        print("No tables found!")
        return

    first_table = table_blocks[0]
    print("\n=== FIRST TABLE STRUCTURE ===")

    print("Header row:")
    for cell_index, cell in enumerate(first_table.header.cells):
        print(f"  Cell {cell_index}: {len(cell.blocks)} blocks")
        for block_index, block in enumerate(cell.blocks):
            content = _describe_block_content(block)
            print(f"    Block {block_index}: {type(block).__name__} - '{content}'")

    print(f"\nBody rows ({len(first_table.rows)}):")
    for row_index, row in enumerate(first_table.rows):
        print(f"  Row {row_index}:")
        for cell_index, cell in enumerate(row.cells):
            print(f"    Cell {cell_index}: {len(cell.blocks)} blocks")
            for block_index, block in enumerate(cell.blocks):
                content = _describe_block_content(block)
                print(f"      Block {block_index}: {type(block).__name__} - '{content}'")

    print("\n=== MARKDOWN RENDERING ===")
    markdown = render_markdown(internal_doc, asset_map={})
    lines = markdown.split("\n")

    table_start = -1
    table_end = -1
    for index, line in enumerate(lines):
        if "|" in line and ("Команда" in line or "команда1" in line):
            if table_start == -1:
                table_start = max(0, index - 2)
            table_end = index + 10

    if table_start == -1:
        print("Table not found in markdown")
        return

    print("Table in markdown:")
    for index in range(table_start, min(table_end, len(lines))):
        print(f"{index:3}: {lines[index]}")


if __name__ == "__main__":
    describe_table_parsing()
