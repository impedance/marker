import re
from typing import Dict, List, Tuple

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

ParentContext = Tuple[str, ...]


def _render_block_for_table(
    block: Block,
    asset_map: Dict[str, str],
    document_name: str = "",
    parent_stack: ParentContext = (),
) -> str:
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
    # For other block types, render normally with table context and escape
    rendered = _render_block(block, asset_map, document_name, parent_stack + ("table",))
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
    parent_stack: ParentContext = (),
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
                rendered_child = _render_list_block(
                    child,
                    asset_map,
                    level + 1,
                    document_name,
                    parent_stack + ("list_item",),
                )
                if rendered_child:
                    lines.extend(rendered_child.splitlines())
                continue
            rendered_child = _render_block(
                child,
                asset_map,
                document_name,
                parent_stack + ("list_item",),
            )
            child_lines = rendered_child.splitlines() if rendered_child else [""]
            for child_line in child_lines:
                if child_line:
                    lines.append(f"{prefix}  {child_line}")
                else:
                    lines.append("")
    return "\n".join(lines)

INLINE_CONTEXTS = {"paragraph", "table", "list_item"}


def _image_sign_text(block: Block) -> str:
    """Return the descriptive text for an image."""
    return block.caption if block.caption else (block.alt if block.alt else f"Рисунок {block.resource_id}")


def _render_image(block: Block, parent_stack: ParentContext) -> str:
    """Render an image block depending on its parent context."""
    sign_text = _image_sign_text(block)
    if any(context in INLINE_CONTEXTS for context in parent_stack):
        return f"[{sign_text}](/{block.resource_id}.png)"
    return (
        f"::sign-image\n"
        f"---\n"
        f"src: /{block.resource_id}.png\n"
        f"sign: {sign_text}\n"
        f"---\n"
        f"::"
    )


def _render_block(
    block: Block,
    asset_map: Dict[str, str],
    document_name: str = "",
    parent_stack: ParentContext = (),
) -> str:
    """Renders a single block element to its Markdown representation."""
    type = block.type
    if type == "heading":
        adjusted_level = max(1, block.level - 1)
        clean_text = _clean_heading_text(block.text)
        return f"{'#' * adjusted_level} {clean_text}"
    if type == "list":
        return _render_list_block(block, asset_map, 0, document_name, parent_stack + ("list",))
    if type == "paragraph":
        text = "".join(_render_inline(inline) for inline in block.inlines)
        stripped = text.lstrip()
        match = re.match(r"(?:[-*]\s+|\d+[.)]\s+)?#\s+(.*)", stripped)
        if match:
            command = match.group(1)
            return f"```bash Terminal\n{command}\n```"
        return text
    if type == "image":
        return _render_image(block, parent_stack)
    if type == "code":
        info = []
        if block.language:
            info.append(block.language)
        if block.title:
            info.append(block.title)
        fence = " ".join(info)
        return f"```{fence}\n{block.code}\n```"
    if type == "table":
        def _render_image_action_list(cell) -> str | None:
            blocks = list(cell.blocks)
            if not blocks:
                return None
            images = []
            index = 0
            for block in blocks:
                if getattr(block, "type", None) != "image":
                    break
                rendered_image = _render_block(
                    block,
                    asset_map,
                    document_name,
                    parent_stack + ("table",),
                )
                if rendered_image.startswith("::sign-image"):
                    return None
                images.append(block)
                index += 1
            if not images:
                return None
            tail_blocks = blocks[index:]
            if len(tail_blocks) != 1:
                return None
            last_block = tail_blocks[0]
            if getattr(last_block, "type", None) != "paragraph":
                return None
            paragraph_text = "".join(
                _render_inline_for_table(inline) for inline in last_block.inlines
            )
            dash_pattern = re.compile(r"(?:(?<=^)|(?<=\s))[–—]\s*")
            matches = dash_pattern.findall(paragraph_text)
            if not matches:
                return None
            if len(matches) != len(images):
                return None
            parts = dash_pattern.split(paragraph_text)
            if len(parts) != len(images) + 1:
                return None
            intro_text = parts[0].strip()
            descriptions: List[str] = []
            for segment in parts[1:]:
                stripped = segment.strip()
                if not stripped:
                    return None
                descriptions.append(stripped)
            list_lines: List[str] = []
            if intro_text:
                list_lines.append(intro_text)
            for image, description in zip(images, descriptions):
                caption = _escape_table_content(_image_sign_text(image))
                item = f"- [{caption}](/{image.resource_id}.png)"
                if description:
                    item = f"{item} {description}"
                list_lines.append(item)
            return "\n".join(list_lines)

        def _render_cell(cell) -> str:
            special = _render_image_action_list(cell)
            if special is not None:
                return special
            cell_parts = [
                _render_block_for_table(
                    b,
                    asset_map,
                    document_name,
                    parent_stack,
                )
                for b in cell.blocks
            ]
            return " ".join(cell_parts).strip()

        def _row(r) -> str:
            rendered_cells = [_render_cell(cell) for cell in r.cells]
            if any("\n" in cell for cell in rendered_cells):
                split_cells = [cell.splitlines() for cell in rendered_cells]
                max_lines = max(len(lines) for lines in split_cells)
                padded_cells: List[List[str]] = [
                    lines + [""] * (max_lines - len(lines)) for lines in split_cells
                ]
                assembled_lines = []
                for line_index in range(max_lines):
                    line_cells = [cells[line_index] for cells in padded_cells]
                    assembled_lines.append("| " + " | ".join(line_cells) + " |")
                return "\n".join(assembled_lines)
            return "| " + " | ".join(rendered_cells) + " |"

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
