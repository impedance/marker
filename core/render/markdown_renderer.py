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

def _render_block(block: Block, asset_map: Dict[str, str]) -> str:
    """Renders a single block element to its Markdown representation."""
    type = block.type
    if type == "heading":
        return f"{'#' * block.level} {block.text}"
    if type == "paragraph":
        text = "".join(_render_inline(inline) for inline in block.inlines)
        stripped = text.lstrip()
        match = re.match(r"(?:[-*]\s+|\d+[.)]\s+)?#\s+(.*)", stripped)
        if match:
            command = match.group(1)
            return f"```bash\n{command}\n```"
        return text
    if type == "image":
        path = asset_map.get(block.resource_id, "about:blank")
        return f"![{block.alt}]({path})"
    # Other block types (List, Table) would be handled here.
    raise ValueError(f"Unknown block type: {type}")

def render_markdown(doc: InternalDoc, asset_map: Dict[str, str]) -> str:
    """

    Renders an InternalDoc object into a Markdown string.

    Args:
        doc: The InternalDoc object to render.
        asset_map: A dictionary mapping resource IDs to their file paths.

    Returns:
        A string containing the rendered Markdown document.
    """
    markdown_lines = []
    prev_list = False
    for block in doc.blocks:
        rendered = _render_block(block, asset_map)
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
