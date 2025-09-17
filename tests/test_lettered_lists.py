import pytest

from core.model.internal_doc import InternalDoc, ListBlock, ListItem, Paragraph, Text
from core.render.markdown_renderer import render_markdown


def test_render_lettered_list():
    """
    Tests that a ListBlock with list_style 'lowerLetter' is rendered
    into the custom ::letter-list format.
    """
    # 1. Create an InternalDoc with a lettered list
    doc = InternalDoc(
        blocks=[
            ListBlock(
                level=0,
                list_style="lowerLetter",  # The new attribute to indicate list type
                items=[
                    ListItem(
                        level=0,
                        blocks=[Paragraph(inlines=[Text(content="первый способ")])],
                    ),
                    ListItem(
                        level=0,
                        blocks=[Paragraph(inlines=[Text(content="второй способ")])],
                    ),
                ],
            )
        ]
    )

    # 2. Render the document to Markdown
    markdown_output = render_markdown(doc, {})

    # 3. Assert the output is in the correct format
    expected_output = (
        "::letter-list\n"
        "- первый способ\n"
        "- второй способ\n"
        "::\n"
    )

    assert markdown_output.strip() == expected_output.strip()
