import re
from typing import Dict

from core.model.internal_doc import (
    InternalDoc,
    Block,
    Inline,
)

def _render_inline(inline: Inline) -> str:
    """Renders a single inline element to its Markdown representation."""
    type = inline.type
    if type == "text":
        return inline.content
    if type == "bold":
        return f"**{inline.content}**"
    if type == "italic":
        return f"*{inline.content}*"
    if type == "link":
        return f"[{inline.content}]({inline.href})"
    raise ValueError(f"Unknown inline type: {type}")

def _clean_heading_text(text: str) -> str:
    """Remove leading numbering like '1', '1.2', '1.2.3', optional dots/brackets/dashes.

    Examples:
    - "3.7 Настройка" -> "Настройка"
    - "3.4.3 — Функции" -> "Функции"
    - "1) Введение" -> "Введение"
    - "(2.1) - Описание" -> "Описание"
    """
    pattern = r"^\s*(?:\(?\d+(?:[.\-]\d+)*\)?|[IVXLCDM]+)\.?\)?\s*(?:[-–—]\s*)?"
    return re.sub(pattern, "", text, flags=re.IGNORECASE).strip()

def _render_block(block: Block, asset_map: Dict[str, str], document_name: str = "") -> str:
    """Renders a single block element to its Markdown representation."""
    type = block.type
    if type == "heading":
        adjusted_level = max(1, block.level - 1)
        clean_text = _clean_heading_text(block.text)
        return f"{'#' * adjusted_level} {clean_text}"
    if type == "paragraph":
        text = "".join(_render_inline(inline) for inline in block.inlines)
        stripped = text.lstrip()
        match = re.match(r"(?:[-*]\s+|\d+[.)]\s+)?#\s+(.*)", stripped)
        if match:
            command = match.group(1)
            return f"```bash Terminal\n{command}\n```"
        return text
    if type == "image":
        path = asset_map.get(block.resource_id, "about:blank")
        if block.caption:
            # Use resource_id as the image filename (e.g., "image2" -> "/image2.png")
            # This matches the actual filenames extracted from DOCX
            return (f"::sign-image\n"
                   f"---\n"
                   f"src: /{block.resource_id}.png\n"
                   f"sign: {block.caption}\n"
                   f"---\n"
                   f"::")
        return f"![{block.alt}]({path})"
    if type == "code":
        info = []
        if block.language:
            info.append(block.language)
        if block.title:
            info.append(block.title)
        fence = " ".join(info)
        return f"```{fence}\n{block.code}\n```"
    if type == "table":
        def _row(r) -> str:
            cells = []
            for cell in r.cells:
                cell_parts = [_render_block(b, asset_map, document_name) for b in cell.blocks]
                cells.append(" ".join(cell_parts).strip())
            return "| " + " | ".join(cells) + " |"

        header = _row(block.header)
        sep = "| " + " | ".join(["---"] * len(block.header.cells)) + " |"
        rows = [_row(r) for r in block.rows]
        return "\n".join([header, sep, *rows])
    raise ValueError(f"Unknown block type: {type}")

def render_markdown(doc: InternalDoc, asset_map: Dict[str, str], document_name: str = "") -> str:
    """

    Renders an InternalDoc object into a Markdown string.

    Args:
        doc: The InternalDoc object to render.
        asset_map: A dictionary mapping resource IDs to their file paths.
        document_name: The document name for image path generation.

    Returns:
        A string containing the rendered Markdown document.
    """
    markdown_lines = []
    prev_list = False
    for block in doc.blocks:
        rendered = _render_block(block, asset_map, document_name)
        is_list = rendered.lstrip().startswith("- ")
        if is_list:
            if not prev_list and markdown_lines:
                markdown_lines.append("")
            markdown_lines.append(rendered)
        else:
            if markdown_lines:
                markdown_lines.append("")
            markdown_lines.append(rendered)
        prev_list = is_list

    return "\n".join(markdown_lines)
