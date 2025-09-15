from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from ..adapters.document_parser import parse_document
from ..render.markdown_renderer import render_markdown
from ..render.assets_exporter import AssetsExporter, _transliterate
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
    """Sanitize and transliterate title for filesystem use."""
    title = re.sub(r"[/\\:*?\"<>|]", " ", title).strip()
    title = re.sub(r"\s{2,}", " ", title)
    parts = [_transliterate(p) for p in title.split('.')]
    return '.'.join(p for p in parts if p)


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


def _find_min_heading_level(blocks: list) -> int:
    """Find the minimum heading level in the document."""
    min_level = float('inf')
    for blk in blocks:
        if getattr(blk, "type", None) == "heading":
            min_level = min(min_level, blk.level)
    return int(min_level) if min_level != float('inf') else 1


def _collect_sections(blocks: list) -> List[_Section]:
    """Breaks blocks into hierarchical sections."""
    sections: List[_Section] = []
    cur_h1: Optional[_Section] = None
    cur_h2_intro: Optional[_Section] = None
    h1_counter = 0

    min_level = _find_min_heading_level(blocks)

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
            normalized_lvl = lvl - min_level + 1

            if normalized_lvl == 1:
                flush_h2()
                if nums:
                    number = [nums[0]]
                    title = ttl
                else:
                    h1_counter += 1
                    number = [h1_counter]
                    title = text
                cur_h1 = _Section(normalized_lvl, number, title, [blk])
                sections.append(cur_h1)
                continue
            if normalized_lvl == 2 and nums:
                flush_h2()
                if len(nums) >= 2:
                    cur_h2_intro = _Section(normalized_lvl, [nums[0], nums[1]], ttl, [blk])
                else:
                    cur_h2_intro = _Section(normalized_lvl, nums + [0], ttl, [blk])
                continue
            if normalized_lvl >= 3 and nums:
                target = cur_h2_intro or cur_h1
                if target:
                    target.blocks.append(blk)
                continue
            target = cur_h2_intro or cur_h1
            if target:
                target.blocks.append(blk)
            continue
        target = cur_h2_intro or cur_h1
        if target:
            target.blocks.append(blk)

    flush_h2()
    return sections


def _copy_section_images(blocks: list, asset_map: dict, temp_dir: Path, target_dir: Path, writer) -> dict:
    """Copy images used in this section to the target images directory and return updated asset_map."""
    import shutil
    
    section_asset_map = {}
    used_image_ids = set()
    
    # Find all image blocks in this section
    for block in blocks:
        if getattr(block, "type", None) == "image":
            resource_id = getattr(block, "resource_id", None)
            if resource_id:
                used_image_ids.add(resource_id)
    
    # Copy relevant images to target directory
    for resource_id, relative_path in asset_map.items():
        if resource_id in used_image_ids:
            # Source file in temp directory
            source_file = temp_dir / Path(relative_path).name
            if source_file.exists():
                # Target file in section's images directory
                filename = source_file.name
                target_file = target_dir / filename
                
                # Copy file
                shutil.copy2(source_file, target_file)
                
                # Update asset map to point to images/ subdirectory
                section_asset_map[resource_id] = f"images/{filename}"
    
    return section_asset_map


def export_docx_hierarchy(docx_path: str | os.PathLike, out_root: str | os.PathLike) -> List[Path]:
    """Exports a DOCX into a folder hierarchy by headings."""
    writer = Writer()
    out_root = Path(out_root)
    out_root.mkdir(parents=True, exist_ok=True)
    
    # Extract document name from path and create document folder
    docx_path = Path(docx_path)
    doc_name = _clean_filename(docx_path.stem)
    doc_root = out_root / doc_name
    doc_root.mkdir(parents=True, exist_ok=True)
    
    doc, resources = parse_document(str(docx_path))
    
    # Export assets to a temporary location and get asset_map
    temp_assets_dir = doc_root / "temp_assets"
    asset_map = export_assets(resources, str(temp_assets_dir)) if resources else {}
    
    sections = _collect_sections(doc.blocks)
    written: List[Path] = []
    h1_dir: Optional[Path] = None
    last_h1_num: Optional[int] = None
    current_images_dir: Optional[Path] = None
    
    for sec in sections:
        code = _code_for_levels(sec.number)
        safe_title = _clean_filename(sec.title)
        if sec.level == 1:
            last_h1_num = sec.number[0]
            h1_dir = doc_root / f"{code}.{safe_title}"
            writer.ensure_dir(h1_dir)
            current_images_dir = h1_dir / "images"
            writer.ensure_dir(current_images_dir)
            
            # Copy relevant images to this section's images directory
            section_asset_map = _copy_section_images(sec.blocks, asset_map, temp_assets_dir, current_images_dir, writer)
            
            md = render_markdown(type("Doc", (), {"blocks": sec.blocks}), section_asset_map)
            path = h1_dir / "index.md"
            writer.write_text(path, md)
            written.append(path)
        elif sec.level == 2:
            # Handle orphaned level 2 sections (no matching H1 parent)
            if h1_dir is None or last_h1_num != sec.number[0]:
                # Create a fallback directory structure for orphaned sections
                fallback_dir = doc_root / f"{code}.{safe_title}"
                writer.ensure_dir(fallback_dir)
                current_images_dir = fallback_dir / "images"
                writer.ensure_dir(current_images_dir)
                
                # Copy relevant images to this section's images directory
                section_asset_map = _copy_section_images(sec.blocks, asset_map, temp_assets_dir, current_images_dir, writer)
                
                md = render_markdown(type("Doc", (), {"blocks": sec.blocks}), section_asset_map)
                path = fallback_dir / "index.md"
                writer.write_text(path, md)
                written.append(path)
            else:
                # Normal case: level 2 section under existing H1
                # Copy relevant images to the current H1's images directory
                section_asset_map = _copy_section_images(sec.blocks, asset_map, temp_assets_dir, current_images_dir, writer)
                
                md = render_markdown(type("Doc", (), {"blocks": sec.blocks}), section_asset_map)
                path = h1_dir / f"{code}.{safe_title}.md"
                writer.write_text(path, md)
                written.append(path)
        else:
            # For level 3+ sections, use current images directory or create fallback
            target_images_dir = current_images_dir if current_images_dir else doc_root / "images"
            if not current_images_dir:
                writer.ensure_dir(target_images_dir)
            
            section_asset_map = _copy_section_images(sec.blocks, asset_map, temp_assets_dir, target_images_dir, writer)
            
            md = render_markdown(type("Doc", (), {"blocks": sec.blocks}), section_asset_map)
            fallback_code = _code_for_levels(sec.number[:3])
            if h1_dir:
                path = h1_dir / f"{fallback_code}.{safe_title}.md"
            else:
                path = doc_root / f"{fallback_code}.{safe_title}.md"
            writer.write_text(path, md)
            written.append(path)
    
    # Clean up temporary assets directory
    if temp_assets_dir.exists():
        import shutil
        shutil.rmtree(temp_assets_dir)
    
    return written


def _sanitize_dir_name(name: str) -> str:
    """Sanitize a string to be safe for use as a directory name."""
    import re
    # Remove or replace problematic characters
    sanitized = re.sub(r'[<>:"/\\|?*]', ' ', name)
    # Remove leading/trailing whitespace and dots
    sanitized = sanitized.strip('. ')
    # Collapse multiple spaces
    sanitized = re.sub(r'\s{2,}', ' ', sanitized)
    # Limit length to avoid filesystem issues
    if len(sanitized) > 100:
        sanitized = sanitized[:100].rstrip('. ')
    # Ensure it's not empty
    if not sanitized:
        sanitized = "unnamed"
    
    return sanitized


def export_docx_hierarchy_centralized(docx_path: str | os.PathLike, out_root: str | os.PathLike) -> List[Path]:
    """
    Exports a DOCX into a folder hierarchy by headings with centralized images structure.

    Instead of creating an images/ folder in each section, creates one central folder named
    after the document itself with subdirectories for each section.

    Structure:
    document_name/
    ├── document_name/
    │   ├── section1_name/
    │   └── section2_name/
    ├── section1_dir/
    │   └── index.md (references ../document_name/section1_name/...)
    └── section2_dir/
        └── index.md (references ../document_name/section2_name/...)
    """
    from ..render.assets_exporter import AssetsExporter
    
    writer = Writer()
    out_root = Path(out_root)
    out_root.mkdir(parents=True, exist_ok=True)
    
    # Extract document name from path and create document folder
    docx_path = Path(docx_path)
    doc_name = _clean_filename(docx_path.stem)
    doc_root = out_root / doc_name
    doc_root.mkdir(parents=True, exist_ok=True)
    
    doc, resources = parse_document(str(docx_path))
    
    # Use new hierarchical assets exporter
    central_images_dir = doc_root / doc_name
    exporter = AssetsExporter(central_images_dir)
    final_asset_map = exporter.export_hierarchical_images(doc, resources)
    
    sections = _collect_sections(doc.blocks)
    written: List[Path] = []
    
    # Generate markdown files using the hierarchical asset map
    h1_dir: Optional[Path] = None
    last_h1_num: Optional[int] = None
    
    for sec in sections:
        code = _code_for_levels(sec.number)
        safe_title = _clean_filename(sec.title)
        
        if sec.level == 1:
            last_h1_num = sec.number[0]
            h1_dir = doc_root / f"{code}.{safe_title}"
            writer.ensure_dir(h1_dir)
            
            md = render_markdown(type("Doc", (), {"blocks": sec.blocks}), final_asset_map)
            path = h1_dir / "index.md"
            writer.write_text(path, md)
            written.append(path)
            
        elif sec.level == 2:
            # Handle orphaned level 2 sections (no matching H1 parent)
            if h1_dir is None or last_h1_num != sec.number[0]:
                # Create a fallback directory structure for orphaned sections
                fallback_dir = doc_root / f"{code}.{safe_title}"
                writer.ensure_dir(fallback_dir)
                
                md = render_markdown(type("Doc", (), {"blocks": sec.blocks}), final_asset_map)
                path = fallback_dir / "index.md"
                writer.write_text(path, md)
                written.append(path)
            else:
                # Normal case: level 2 section under existing H1
                md = render_markdown(type("Doc", (), {"blocks": sec.blocks}), final_asset_map)
                path = h1_dir / f"{code}.{safe_title}.md"
                writer.write_text(path, md)
                written.append(path)
        else:
            # For level 3+ sections
            md = render_markdown(type("Doc", (), {"blocks": sec.blocks}), final_asset_map)
            fallback_code = _code_for_levels(sec.number[:3])
            if h1_dir:
                path = h1_dir / f"{fallback_code}.{safe_title}.md"
            else:
                path = doc_root / f"{fallback_code}.{safe_title}.md"
            writer.write_text(path, md)
            written.append(path)
    
    return written
