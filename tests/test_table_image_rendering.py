"""Tests for image rendering in structured contexts."""

import pytest
from core.model.internal_doc import (
    InternalDoc,
    Table,
    TableRow,
    TableCell,
    Image,
    Paragraph,
    Text,
    ListBlock,
    ListItem,
)
from core.render.markdown_renderer import render_markdown


class TestTableImageRendering:
    """Tests for image rendering within structured elements."""

    def test_image_in_table_cell_uses_link_format(self):
        """Images in table cells should use simple link format."""
        image_block = Image(
            type="image",
            resource_id="table_image",
            alt="Table Image Alt",
            caption="Изменить панель",
        )

        cell_with_image = TableCell(blocks=[image_block])
        cell_with_text = TableCell(blocks=[Paragraph(inlines=[Text(content="Описание действия")])])

        row = TableRow(cells=[cell_with_image, cell_with_text])
        header = TableRow(
            cells=[
                TableCell(blocks=[Paragraph(inlines=[Text(content="Действие")])]),
                TableCell(blocks=[Paragraph(inlines=[Text(content="Описание")])]),
            ]
        )

        table = Table(header=header, rows=[row])
        doc = InternalDoc(blocks=[table])
        asset_map = {"table_image": "/assets/table_image.png"}

        result = render_markdown(doc, asset_map)

        assert "[Изменить панель](/table_image.png)" in result
        assert "::sign-image" not in result
        assert "| [Изменить панель](/table_image.png) | Описание действия |" in result

    def test_table_with_multiple_images(self):
        """Tables with multiple images should render each image as a link."""
        image1 = Image(
            type="image",
            resource_id="icon1",
            alt="Icon 1",
            caption="Кнопка сохранения",
        )

        image2 = Image(
            type="image",
            resource_id="icon2",
            alt="Icon 2",
            caption="Кнопка отмены",
        )

        cell1 = TableCell(blocks=[image1])
        cell2 = TableCell(blocks=[Paragraph(inlines=[Text(content="Сохранить изменения")])])
        cell3 = TableCell(blocks=[image2])
        cell4 = TableCell(blocks=[Paragraph(inlines=[Text(content="Отменить изменения")])])

        row1 = TableRow(cells=[cell1, cell2])
        row2 = TableRow(cells=[cell3, cell4])
        header = TableRow(
            cells=[
                TableCell(blocks=[Paragraph(inlines=[Text(content="Кнопка")])]),
                TableCell(blocks=[Paragraph(inlines=[Text(content="Действие")])]),
            ]
        )

        table = Table(header=header, rows=[row1, row2])
        doc = InternalDoc(blocks=[table])
        asset_map = {"icon1": "/assets/icon1.png", "icon2": "/assets/icon2.png"}

        result = render_markdown(doc, asset_map)

        assert "[Кнопка сохранения](/icon1.png)" in result
        assert "[Кнопка отмены](/icon2.png)" in result
        assert "::sign-image" not in result

        lines = result.strip().split("\n")
        table_lines = [line for line in lines if line.startswith("|")]
        assert len(table_lines) == 4

    def test_image_with_special_characters_in_caption(self):
        """Captions with special characters should be escaped in tables."""
        image_block = Image(
            type="image",
            resource_id="special_image",
            alt="Special Image",
            caption="Кнопка | с символом |",
        )

        cell = TableCell(blocks=[image_block])
        row = TableRow(
            cells=[
                cell,
                TableCell(blocks=[Paragraph(inlines=[Text(content="Описание")])]),
            ]
        )
        header = TableRow(
            cells=[
                TableCell(blocks=[Paragraph(inlines=[Text(content="Действие")])]),
                TableCell(blocks=[Paragraph(inlines=[Text(content="Описание")])]),
            ]
        )

        table = Table(header=header, rows=[row])
        doc = InternalDoc(blocks=[table])
        asset_map = {"special_image": "/assets/special_image.png"}

        result = render_markdown(doc, asset_map)

        assert "[Кнопка \\| с символом \\|](/special_image.png)" in result
        assert "::sign-image" not in result

    def test_image_in_list_item_uses_link_format(self):
        """Images inside list items should render as links."""
        image_block = Image(
            type="image",
            resource_id="list_image",
            alt="List Image Alt",
            caption="Изображение в списке",
        )

        list_item = ListItem(
            blocks=[
                Paragraph(inlines=[Text(content="Первый пункт")]),
                image_block,
            ]
        )
        list_block = ListBlock(items=[list_item])
        doc = InternalDoc(blocks=[list_block])
        asset_map = {"list_image": "/assets/list_image.png"}

        result = render_markdown(doc, asset_map)

        assert "[Изображение в списке](/list_image.png)" in result
        assert "::sign-image" not in result

    def test_list_item_with_leading_image_inlines_description(self):
        """Images that start a list item should be rendered on the same line as the text."""
        image_block = Image(
            type="image",
            resource_id="image47",
            alt="Рисунок 52",
            caption="Рисунок 52",
        )

        description_block = Paragraph(
            inlines=[Text(content="– отображение страницы в режиме киоска")]
        )

        list_item = ListItem(blocks=[image_block, description_block])
        list_block = ListBlock(items=[list_item])
        doc = InternalDoc(blocks=[list_block])

        result = render_markdown(doc, {})

        expected = "- [Рисунок 52](/image47.png) – отображение страницы в режиме киоска"
        assert result == expected

    def test_list_item_with_multiple_leading_images_only_inlines_first(self):
        """Only the first leading image should join the bullet line; others render separately."""
        first_image = Image(
            type="image",
            resource_id="image10",
            alt="Рисунок 10",
            caption="Рисунок 10",
        )

        second_image = Image(
            type="image",
            resource_id="image11",
            alt="Рисунок 11",
            caption="Рисунок 11",
        )

        description_block = Paragraph(
            inlines=[Text(content="– описание шага")]
        )

        list_item = ListItem(blocks=[first_image, second_image, description_block])
        list_block = ListBlock(items=[list_item])
        doc = InternalDoc(blocks=[list_block])

        result = render_markdown(
            doc,
            {"image10": "/assets/image10.png", "image11": "/assets/image11.png"},
        )

        lines = result.splitlines()
        assert lines[0] == "- [Рисунок 10](/image10.png) – описание шага"
        assert lines[1] == "  [Рисунок 11](/image11.png)"
