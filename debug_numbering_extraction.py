#!/usr/bin/env python3
"""Utility script to inspect headings extracted during numbering analysis."""

from pathlib import Path
from typing import Iterable

from core.adapters.docx_parser import parse_docx_to_internal_doc
from core.model.internal_doc import Block


DEFAULT_DOCX = Path("real-docs/dev-portal-admin.docx")


def _iter_heading_blocks(blocks: Iterable[Block]) -> Iterable[Block]:
    """Yield heading-like blocks from the provided block sequence."""
    for block in blocks:
        if hasattr(block, "level") and block.level is not None:
            yield block


def inspect_numbering_extraction(docx_file: Path = DEFAULT_DOCX) -> None:
    """Print the first few headings extracted from the provided DOCX file."""
    print(f"Testing numbering extraction from: {docx_file}")
    print("=" * 60)

    try:
        internal_doc, _ = parse_docx_to_internal_doc(str(docx_file))
    except Exception as exc:  # pragma: no cover - debugging helper
        print(f"Error: {exc}")
        import traceback

        traceback.print_exc()
        return

    print("Extracted headings:")
    for index, block in enumerate(_iter_heading_blocks(internal_doc.blocks)):
        if block.level > 3:
            continue
        print(f"  H{block.level}: '{getattr(block, 'text', '')}'")
        if index >= 14:
            print("  ... (truncated)")
            break


if __name__ == "__main__":
    inspect_numbering_extraction()
