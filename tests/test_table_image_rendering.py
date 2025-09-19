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

    def test_action_cell_renders_image_list(self):
        """Cells with multiple images followed by dash descriptions render as lists."""
        image_one = Image(
            type="image",
            resource_id="action_edit",
            alt="Icon edit",
            caption="Рисунок 64",
        )
        image_two = Image(
            type="image",
            resource_id="action_widget",
            alt="Icon widget",
            caption="Рисунок 181",
        )
        action_paragraph = Paragraph(
            inlines=[
                Text(content="– Переключиться в режим редактирования панели."),
                Text(content=" – Режим редактирования также открывается при создании новой панели."),
            ]
        )
        action_cell = TableCell(blocks=[image_one, image_two, action_paragraph])
        header = TableRow(
            cells=[TableCell(blocks=[Paragraph(inlines=[Text(content="Действия")])])]
        )
        row = TableRow(cells=[action_cell])
        table = Table(header=header, rows=[row])
        doc = InternalDoc(blocks=[table])

        asset_map = {
            "action_edit": "/assets/action_edit.png",
            "action_widget": "/assets/action_widget.png",
        }

        result = render_markdown(doc, asset_map)

        list_lines = [line for line in result.splitlines() if line.startswith("| - [")]
        assert len(list_lines) == 2
        assert "- [Рисунок 64](/action_edit.png) Переключиться в режим редактирования панели." in list_lines[0]
        assert "- [Рисунок 181](/action_widget.png) Режим редактирования также открывается при создании новой панели." in list_lines[1]

    def test_action_cell_with_intro_text_keeps_intro_line(self):
        """Introductory text before dash segments is preserved above the list."""
        icon_one = Image(
            type="image",
            resource_id="history_added",
            caption="Рисунок 64",
        )
        icon_two = Image(
            type="image",
            resource_id="history_removed",
            caption="Рисунок 65",
        )
        paragraph = Paragraph(
            inlines=[
                Text(content="История изменений:"),
                Text(content=" – Добавлены комментарии."),
                Text(content=" – Удалены комментарии."),
            ]
        )
        cell = TableCell(blocks=[icon_one, icon_two, paragraph])
        header = TableRow(
            cells=[TableCell(blocks=[Paragraph(inlines=[Text(content="Действия")])])]
        )
        row = TableRow(cells=[cell])
        table = Table(header=header, rows=[row])
        doc = InternalDoc(blocks=[table])
        asset_map = {
            "history_added": "/assets/history_added.png",
            "history_removed": "/assets/history_removed.png",
        }

        result = render_markdown(doc, asset_map)
        table_lines = [line for line in result.splitlines() if line.startswith("|")]

        assert "| История изменений: |" in table_lines
        assert "- [Рисунок 64](/history_added.png) Добавлены комментарии." in "\n".join(table_lines)
        assert "- [Рисунок 65](/history_removed.png) Удалены комментарии." in "\n".join(table_lines)

    def test_paragraph_before_images_does_not_trigger_action_list(self):
        """Cells with text before images keep default rendering."""
        lead_paragraph = Paragraph(
            inlines=[Text(content="- До изображения")] 
        )
        icon = Image(
            type="image",
            resource_id="before_action",
            caption="Рисунок 77",
        )
        tail_paragraph = Paragraph(
            inlines=[Text(content="– После изображения.")]
        )
        cell = TableCell(blocks=[lead_paragraph, icon, tail_paragraph])
        header = TableRow(
            cells=[TableCell(blocks=[Paragraph(inlines=[Text(content="Описание")])])]
        )
        row = TableRow(cells=[cell])
        table = Table(header=header, rows=[row])
        doc = InternalDoc(blocks=[table])
        asset_map = {"before_action": "/assets/before_action.png"}

        result = render_markdown(doc, asset_map)
        lines = result.splitlines()

        assert not any(line.startswith("| - [") for line in lines)
        assert "| - До изображения [Рисунок 77](/before_action.png) – После изображения. |" in lines

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
