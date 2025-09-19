"""Tests for image caption handling in documents with and without caption styles."""

import pytest
from core.model.internal_doc import InternalDoc, Image
from core.render.markdown_renderer import render_markdown


class TestImageCaptionStyles:
    """Tests for image caption processing in different document types."""

    def test_image_caption_without_separate_style(self):
        """Test image caption extracted from ROSA_Рисунок_Номер style (description only)."""
        # Simulate image block with caption extracted from ROSA_Рисунок_Номер style
        # containing only descriptive text (like cu-admin-install.docx)
        image_block = Image(
            type="image",
            resource_id="image001",
            alt="Screenshot",
            caption="Получение ссылки"  # Already clean caption
        )
        
        doc = InternalDoc(blocks=[image_block])
        asset_map = {"image001": "/assets/image001.png"}
        
        result = render_markdown(doc, asset_map)
        
        expected = (
            "::sign-image\n"
            "---\n"
            "src: /image001.png\n"
            "sign: Получение ссылки\n"
            "---\n"
            "::"
        )
        
        assert result == expected

    def test_image_caption_with_full_caption(self):
        """Test full image caption extracted from ROSA_Рисунок_Номер style."""
        # Simulate image block with caption extracted from ROSA_Рисунок_Номер style
        # containing complete caption with numbering (like dev-portal-user.docx)
        image_block = Image(
            type="image",
            resource_id="image002",
            alt="Screenshot",
            caption='Рисунок 4 – Раздел "РОСА Мобайл"'  # Complete caption with description
        )
        
        doc = InternalDoc(blocks=[image_block])
        asset_map = {"image002": "/assets/image002.png"}
        
        # Test with caption extracted from ROSA_Рисунок_Номер style
        result = render_markdown(doc, asset_map)
        
        expected = (
            "::sign-image\n"
            "---\n"
            "src: /image002.png\n"
            'sign: Рисунок 4 – Раздел "РОСА Мобайл"\n'  # Should keep full caption
            "---\n"
            "::"
        )
        
        assert result == expected

    def test_image_caption_description_only_from_rosa_style(self):
        """Test description-only captions extracted from ROSA_Рисунок_Номер style."""
        test_cases = [
            "Выбор варианта установки",
            "Параметры регистрации узла", 
            "Configuration screen",
            "Короткое название",
            "Описание с тире",
        ]
        
        for description_caption in test_cases:
            image_block = Image(
                type="image",
                resource_id="test_image",
                alt="Test Alt",
                caption=description_caption
            )
            
            doc = InternalDoc(blocks=[image_block])
            asset_map = {"test_image": "/assets/test_image.png"}
            
            result = render_markdown(doc, asset_map)
            
            expected = (
                "::sign-image\n"
                "---\n"
                "src: /test_image.png\n"
                f"sign: {description_caption}\n"  # Keep description as-is
                "---\n"
                "::"
            )
            
            assert result == expected, f"Failed for description caption: {description_caption}"

    def test_image_caption_various_complete_patterns_from_rosa_style(self):
        """Test different complete caption patterns extracted from ROSA_Рисунок_Номер style."""
        test_cases = [
            'Рисунок 4 – Раздел "РОСА Мобайл"',
            "Рисунок 1 — Описание системы",
            "Figure 5 -- Configuration screen", 
            "Рис. 7 -- Короткое название",
            "Рисунок 42 – Описание с тире",
        ]
        
        for complete_caption in test_cases:
            image_block = Image(
                type="image",
                resource_id="test_image",
                alt="Test",
                caption=complete_caption
            )
            
            doc = InternalDoc(blocks=[image_block])
            asset_map = {"test_image": "/assets/test_image.png"}
            
            result = render_markdown(doc, asset_map)
            
            expected = (
                "::sign-image\n"
                "---\n"
                "src: /test_image.png\n"
                f"sign: {complete_caption}\n"  # Keep complete caption as-is
                "---\n"
                "::"
            )
            
            assert result == expected, f"Failed for complete caption: {complete_caption}"

    def test_image_without_caption_uses_fallback(self):
        """Test image without caption uses fallback text."""
        image_block = Image(
            type="image",
            resource_id="image003",
            alt="Alt text",
            caption=""  # No caption
        )
        
        doc = InternalDoc(blocks=[image_block])
        asset_map = {"image003": "/assets/image003.png"}
        
        result = render_markdown(doc, asset_map)
        
        expected = (
            "::sign-image\n"
            "---\n"
            "src: /image003.png\n"
            "sign: Alt text\n"  # Falls back to alt text
            "---\n"
            "::"
        )
        
        assert result == expected

    def test_image_without_caption_or_alt_uses_resource_id(self):
        """Test image without caption or alt uses resource ID fallback."""
        image_block = Image(
            type="image",
            resource_id="image004",
            alt="",  # No alt text
            caption=""  # No caption
        )
        
        doc = InternalDoc(blocks=[image_block])
        asset_map = {"image004": "/assets/image004.png"}
        
        result = render_markdown(doc, asset_map)
        
        expected = (
            "::sign-image\n"
            "---\n"
            "src: /image004.png\n"
            "sign: Рисунок image004\n"  # Falls back to resource ID
            "---\n"
            "::"
        )
        
        assert result == expected