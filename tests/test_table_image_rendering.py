"""Tests for image rendering in table cells."""

import pytest
from core.model.internal_doc import InternalDoc, Table, TableRow, TableCell, Image, Paragraph, Text
from core.render.markdown_renderer import render_markdown


class TestTableImageRendering:
    """Tests for image rendering within table cells."""

    def test_image_in_table_cell_uses_inline_format(self):
        """Test that images in table cells use inline markdown format."""
        # Create an image block in a table cell
        image_block = Image(
            type="image",
            resource_id="table_image",
            alt="Table Image Alt",
            caption="Изменить панель"
        )
        
        # Create table with image in cell
        cell_with_image = TableCell(blocks=[image_block])
        cell_with_text = TableCell(blocks=[Paragraph(inlines=[Text(content="Описание действия")])])
        
        row = TableRow(cells=[cell_with_image, cell_with_text])
        header = TableRow(cells=[
            TableCell(blocks=[Paragraph(inlines=[Text(content="Действие")])]),
            TableCell(blocks=[Paragraph(inlines=[Text(content="Описание")])])
        ])
        
        table = Table(header=header, rows=[row])
        doc = InternalDoc(blocks=[table])
        asset_map = {"table_image": "/assets/table_image.png"}
        
        result = render_markdown(doc, asset_map)
        
        # Should use inline markdown image format, not ::sign-image blocks
        assert "![Изменить панель](/table_image.png)" in result
        assert "::sign-image" not in result
        
        # Should maintain table structure
        assert "| ![Изменить панель](/table_image.png) | Описание действия |" in result

    def test_table_with_multiple_images(self):
        """Test table with multiple images in different cells."""
        image1 = Image(
            type="image",
            resource_id="icon1",
            alt="Icon 1",
            caption="Кнопка сохранения"
        )
        
        image2 = Image(
            type="image", 
            resource_id="icon2",
            alt="Icon 2",
            caption="Кнопка отмены"
        )
        
        cell1 = TableCell(blocks=[image1])
        cell2 = TableCell(blocks=[Paragraph(inlines=[Text(content="Сохранить изменения")])])
        cell3 = TableCell(blocks=[image2])
        cell4 = TableCell(blocks=[Paragraph(inlines=[Text(content="Отменить изменения")])])
        
        row1 = TableRow(cells=[cell1, cell2])
        row2 = TableRow(cells=[cell3, cell4])
        header = TableRow(cells=[
            TableCell(blocks=[Paragraph(inlines=[Text(content="Кнопка")])]),
            TableCell(blocks=[Paragraph(inlines=[Text(content="Действие")])])
        ])
        
        table = Table(header=header, rows=[row1, row2])
        doc = InternalDoc(blocks=[table])
        asset_map = {"icon1": "/assets/icon1.png", "icon2": "/assets/icon2.png"}
        
        result = render_markdown(doc, asset_map)
        
        # Both images should use inline format
        assert "![Кнопка сохранения](/icon1.png)" in result
        assert "![Кнопка отмены](/icon2.png)" in result
        assert "::sign-image" not in result
        
        # Table structure should be preserved
        lines = result.strip().split('\n')
        table_lines = [line for line in lines if line.startswith('|')]
        assert len(table_lines) == 4  # header + separator + 2 rows

    def test_image_with_special_characters_in_caption(self):
        """Test that image captions with special characters are properly escaped in tables."""
        image_block = Image(
            type="image",
            resource_id="special_image",
            alt="Special Image",
            caption="Кнопка | с символом |"
        )
        
        cell = TableCell(blocks=[image_block])
        row = TableRow(cells=[cell, TableCell(blocks=[Paragraph(inlines=[Text(content="Описание")])])])
        header = TableRow(cells=[
            TableCell(blocks=[Paragraph(inlines=[Text(content="Действие")])]),
            TableCell(blocks=[Paragraph(inlines=[Text(content="Описание")])])
        ])
        
        table = Table(header=header, rows=[row])
        doc = InternalDoc(blocks=[table])
        asset_map = {"special_image": "/assets/special_image.png"}
        
        result = render_markdown(doc, asset_map)
        
        # Pipe characters should be escaped in table cells
        assert "![Кнопка \\| с символом \\|](/special_image.png)" in result
        assert "::sign-image" not in result