import re
from typing import Dict, List

from core.model.internal_doc import (
    InternalDoc,
    Block,
    Inline,
    ListBlock,
)

def _escape_table_content(text: str) -> str:
    """Escape markdown special characters in table cells."""
    # Escape pipe characters that would break table structure
    text = text.replace('|', '\\|')
    return text

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
    if type == "code":
        return f"`{inline.content}`"
    raise ValueError(f"Unknown inline type: {type}")

def _render_inline_for_table(inline: Inline) -> str:
    """Renders a single inline element for table cells with proper escaping."""
    rendered = _render_inline(inline)
    return _escape_table_content(rendered)

def _render_block_for_table(block: Block, asset_map: Dict[str, str], document_name: str = "") -> str:
    """Renders a block element for table cells with proper escaping."""
    type = block.type
    if type == "paragraph":
        text = "".join(_render_inline_for_table(inline) for inline in block.inlines)
        stripped = text.lstrip()
        match = re.match(r"(?:[-*]\s+|\d+[.)]\s+)?#\s+(.*)", stripped)
        if match:
            command = match.group(1)
            return f"```bash Terminal\n{command}\n```"
        return text
    # For other block types, render normally and then escape
    rendered = _render_block(block, asset_map, document_name)
    return _escape_table_content(rendered)

def _clean_heading_text(text: str) -> str:
    """Remove leading numbering like '1', '1.2', '1.2.3', optional dots/brackets/dashes.

    Examples:
    - "3.7 Настройка" -> "Настройка"
    - "3.4.3 — Функции" -> "Функции"
    - "1) Введение" -> "Введение"
    - "(2.1) - Описание" -> "Описание"
    """
    pattern = r"^\s*(?:\(?\d+(?:[.\-]\d+)*\)?|[IVXLCDM]+(?=[.\s]))\.?\)?\s*(?:[-–—]\s*)?"
    return re.sub(pattern, "", text, flags=re.IGNORECASE).strip()

def _escape_list_item_text(text: str) -> str:
    """Escape leading blockquote markers inside list items."""
    stripped = text.lstrip()
    if not stripped:
        return text
    if stripped.startswith(">") and not stripped.startswith("\\>"):
        leading = text[: len(text) - len(stripped)]
        return f"{leading}\\{stripped}"
    return text

def _render_list_block(
    list_block: ListBlock,
    asset_map: Dict[str, str],
    level: int = 0,
    document_name: str = "",
) -> str:
    """Render a list block with proper indentation and nested items."""
    lines: List[str] = []
    for index, item in enumerate(list_block.items, start=1):
        marker = f"{index}. " if list_block.ordered else "- "
        prefix = "  " * level
        item_blocks = list(item.blocks)
        first_line = ""
        if item_blocks and getattr(item_blocks[0], "type", None) == "paragraph":
            first_paragraph = item_blocks.pop(0)
            first_line = "".join(_render_inline(inline) for inline in first_paragraph.inlines).strip()
            first_line = _escape_list_item_text(first_line)
        lines.append(f"{prefix}{marker}{first_line}".rstrip())
        for child in item_blocks:
            if getattr(child, "type", None) == "list":
                rendered_child = _render_list_block(child, asset_map, level + 1, document_name)
                if rendered_child:
                    lines.extend(rendered_child.splitlines())
                continue
            rendered_child = _render_block(child, asset_map, document_name)
            child_lines = rendered_child.splitlines() if rendered_child else [""]
            for child_line in child_lines:
                if child_line:
                    lines.append(f"{prefix}  {child_line}")
                else:
                    lines.append("")
    return "\n".join(lines)

def _render_block(block: Block, asset_map: Dict[str, str], document_name: str = "") -> str:
    """Renders a single block element to its Markdown representation."""
    type = block.type
    if type == "heading":
        adjusted_level = max(1, block.level - 1)
        clean_text = _clean_heading_text(block.text)
        return f"{'#' * adjusted_level} {clean_text}"
    if type == "list":
        return _render_list_block(block, asset_map, 0, document_name)
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
        # Always use ::sign-image format for all images
        sign_text = block.caption if block.caption else (block.alt if block.alt else f"Рисунок {block.resource_id}")
        return (f"::sign-image\n"
               f"---\n"
               f"src: /{block.resource_id}.png\n"
               f"sign: {sign_text}\n"
               f"---\n"
               f"::")
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
                cell_parts = [_render_block_for_table(b, asset_map, document_name) for b in cell.blocks]
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
        is_list = getattr(block, "type", None) == "list"
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
