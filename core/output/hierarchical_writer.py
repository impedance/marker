from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from ..adapters.document_parser import parse_document
from ..render.markdown_renderer import render_markdown
from .writer import Writer

_HEADING_RE = re.compile(r"^(\d+(?:\.\d+)*)\s+(.+)$")
_HEADING_RE_DOT = re.compile(r"^(\d+(?:\.\d+)*)\.\s+(.+)$")
_HEADING_RE_DASH = re.compile(r"^(\d+(?:\.\d+)*)\s*[-–—]\s*(.+)$")


def _split_number_and_title(text: str) -> Tuple[List[int], str]:
    """Splits heading text into numbering and title."""
    s = text.strip()
    for rx in (_HEADING_RE_DOT, _HEADING_RE_DASH, _HEADING_RE):
        m = rx.match(s)
        if m:
            nums = [int(x) for x in m.group(1).split(".")]
            return nums, m.group(2).strip()
    return [], s


def _clean_filename(title: str) -> str:
    """Removes filesystem reserved characters."""
    title = re.sub(r"[/\\:*?\"<>|]", " ", title).strip()
    return re.sub(r"\s{2,}", " ", title)


def _code_for_levels(nums: List[int]) -> str:
    """Builds a six-digit code based on heading levels."""
    a = f"{(nums[0] if len(nums) >= 1 else 0):02d}"
    b = f"{(nums[1] if len(nums) >= 2 else 0):02d}"
    c = f"{(nums[2] if len(nums) >= 3 else 0):02d}"
    return f"{a}{b}{c}"


@dataclass
class _Section:
    level: int
    number: List[int]
    title: str
    blocks: list


def _collect_sections(blocks: list) -> List[_Section]:
    """Breaks blocks into hierarchical sections."""
    sections: List[_Section] = []
    cur_h1: Optional[_Section] = None
    cur_h2_intro: Optional[_Section] = None
    cur_h3: Optional[_Section] = None
    base_level: Optional[int] = None

    def flush_h3() -> None:
        nonlocal cur_h3
        if cur_h3 and cur_h3.blocks:
            sections.append(cur_h3)
        cur_h3 = None

    def flush_h2() -> None:
        nonlocal cur_h2_intro
        if cur_h2_intro and cur_h2_intro.blocks:
            sections.append(cur_h2_intro)
        cur_h2_intro = None

    for blk in blocks:
        if getattr(blk, "type", None) == "heading":
            text = blk.text or ""
            lvl = blk.level
            nums, ttl = _split_number_and_title(text)
            if not nums:
                target = cur_h3 or cur_h2_intro or cur_h1
                if target:
                    target.blocks.append(blk)
                continue

            if base_level is None:
                base_level = lvl
            adj_level = lvl - base_level + 1

            if adj_level == 1:
                flush_h3()
                flush_h2()
                cur_h1 = _Section(1, [nums[0]], ttl, [blk])
                sections.append(cur_h1)
                continue
            if adj_level == 2 and cur_h1:
                flush_h3()
                flush_h2()
                cur_h2_intro = _Section(2, [nums[0], nums[1]], ttl, [blk])
                continue
            if adj_level == 3 and cur_h1:
                flush_h3()
                if cur_h2_intro:
                    sections.append(cur_h2_intro)
                    cur_h2_intro = None
                cur_h3 = _Section(3, [nums[0], nums[1], nums[2]], ttl, [blk])
                continue
            target = cur_h3 or cur_h2_intro or cur_h1
            if target:
                target.blocks.append(blk)
            continue
        target = cur_h3 or cur_h2_intro or cur_h1
        if target:
            target.blocks.append(blk)

    flush_h3()
    flush_h2()
    return sections


def export_docx_hierarchy(docx_path: str | os.PathLike, out_root: str | os.PathLike) -> List[Path]:
    """Exports a DOCX into a folder hierarchy by headings."""
    writer = Writer()
    out_root = Path(out_root)
    out_root.mkdir(parents=True, exist_ok=True)
    docx_path = Path(docx_path)
    doc_dir = out_root / docx_path.stem
    doc_dir.mkdir(parents=True, exist_ok=True)

    doc, _ = parse_document(str(docx_path))
    sections = _collect_sections(doc.blocks)
    written: List[Path] = []
    h1_dir: Optional[Path] = None
    last_h1_num: Optional[int] = None
    for sec in sections:
        code = _code_for_levels(sec.number)
        safe_title = _clean_filename(sec.title)
        if sec.level == 1:
            last_h1_num = sec.number[0]
            h1_dir = doc_dir / f"{code}.{safe_title}"
            writer.ensure_dir(h1_dir)
            writer.ensure_dir(h1_dir / "images")
            md = render_markdown(type("Doc", (), {"blocks": sec.blocks}), asset_map={})
            path = h1_dir / "index.md"
            writer.write_text(path, md)
            written.append(path)
        elif sec.level == 2:
            assert h1_dir is not None and last_h1_num == sec.number[0]
            md = render_markdown(type("Doc", (), {"blocks": sec.blocks}), asset_map={})
            path = h1_dir / f"{code}.{safe_title}.md"
            writer.write_text(path, md)
            written.append(path)
        elif sec.level == 3:
            assert h1_dir is not None and last_h1_num == sec.number[0]
            md = render_markdown(type("Doc", (), {"blocks": sec.blocks}), asset_map={})
            path = h1_dir / f"{code}.{safe_title}.md"
            writer.write_text(path, md)
            written.append(path)
        else:
            md = render_markdown(type("Doc", (), {"blocks": sec.blocks}), asset_map={})
            fallback_code = _code_for_levels(sec.number[:3])
            if h1_dir:
                path = h1_dir / f"{fallback_code}.{safe_title}.md"
            else:
                path = doc_dir / f"{fallback_code}.{safe_title}.md"
            writer.write_text(path, md)
            written.append(path)
    return written
