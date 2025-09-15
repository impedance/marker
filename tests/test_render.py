import hashlib
from pathlib import Path

from core.model.internal_doc import InternalDoc, Heading, Paragraph, Text, Bold, Image, CodeBlock
from core.model.resource_ref import ResourceRef
from core.render.assets_exporter import export_assets
from core.render.markdown_renderer import render_markdown

def test_export_assets(tmp_path: Path):
    """
    Tests the assets exporter, including deduplication.
    """
    # Arrange
    assets_dir = tmp_path / "assets"
    content1 = b"image data one"
    hash1 = hashlib.sha256(content1).hexdigest()
    content2 = b"image data two"
    hash2 = hashlib.sha256(content2).hexdigest()

    resources = [
        ResourceRef(id="img1", mime_type="image/png", content=content1, sha256=hash1),
        ResourceRef(id="img2", mime_type="image/jpeg", content=content2, sha256=hash2),
        # This is a duplicate of img1 in terms of content
        ResourceRef(id="img3", mime_type="image/png", content=content1, sha256=hash1),
    ]

    # Act
    asset_map = export_assets(resources, str(assets_dir))

    # Assert
    # Check that the correct files were written
    assert (assets_dir / "img1.png").exists()
    assert (assets_dir / "img2.jpg").exists()
    # Check that the duplicate file was NOT written
    assert not (assets_dir / "img3.png").exists()

    # Check that the file content is correct
    assert (assets_dir / "img1.png").read_bytes() == content1

    # Check that the returned asset_map is correct
    assert asset_map == {
        "img1": "assets/img1.png",
        "img2": "assets/img2.jpg",
        "img3": "assets/img1.png",  # img3 should point to the file from img1
    }

def test_render_markdown():
    """
    Tests that the Markdown renderer correctly converts an InternalDoc AST to a string.
    """
    # Arrange
    doc = InternalDoc(blocks=[
        Heading(level=1, text="Document Title"),
        Paragraph(inlines=[
            Text(content="This is a "),
            Bold(content="sample"),
            Text(content=" paragraph."),
        ]),
        Image(resource_id="img_1", alt="An example image"),
    ])
    asset_map = {"img_1": "assets/img_1.png"}

    # Act
    markdown_output = render_markdown(doc, asset_map)

    # Assert
    expected_markdown = (
        "# Document Title\n\n"
        "This is a **sample** paragraph.\n\n"
        "::sign-image\n"
        "---\n"
        "src: /img_1.png\n"
        "sign: An example image\n"
        "---\n"
        "::"
    )
    assert markdown_output == expected_markdown


def test_render_bash_command():
    """Ensures shell commands are wrapped in bash code blocks with terminal label."""
    doc = InternalDoc(blocks=[Paragraph(inlines=[Text(content="# mkdir -p /var/www/html/media")])])
    markdown_output = render_markdown(doc, {})
    expected = "```bash Terminal\nmkdir -p /var/www/html/media\n```"
    assert markdown_output == expected


def test_render_bash_command_in_list():
    """Shell command prefixed by a list marker becomes a code block with terminal label."""
    doc = InternalDoc(
        blocks=[Paragraph(inlines=[Text(content="- # dnf install -y rosa-release-postgres-16")])]
    )
    markdown_output = render_markdown(doc, {})
    expected = "```bash Terminal\ndnf install -y rosa-release-postgres-16\n```"
    assert markdown_output == expected


def test_render_code_block_with_filename():
    """Renders a code block with language and filename."""
    doc = InternalDoc(
        blocks=[
            CodeBlock(code="version: '3'\nservices:\n  web:\n    image: nginx", language="yaml", title="docker-compose.yaml")
        ]
    )
    markdown_output = render_markdown(doc, {})
    expected = (
        "```yaml docker-compose.yaml\n"
        "version: '3'\nservices:\n  web:\n    image: nginx\n"
        "```"
    )
    assert markdown_output == expected


def test_render_shebang_code_block():
    """Renders a bash script code block using a shebang."""
    doc = InternalDoc(
        blocks=[CodeBlock(code="#!/bin/bash\necho hi", language="bash")]
    )
    markdown_output = render_markdown(doc, {})
    expected = "```bash\n#!/bin/bash\necho hi\n```"
    assert markdown_output == expected


def test_render_image_with_sign_format():
    """Tests that images are rendered in the new sign-image format with proper structure."""
    # Arrange
    doc = InternalDoc(blocks=[
        Image(resource_id="img_1", alt="Image 1", caption="Рисунок 1 – Описание изображения"),
    ])
    asset_map = {"img_1": "original.png"}
    
    # Act
    markdown_output = render_markdown(doc, asset_map)
    
    # Assert
    expected_markdown = (
        "::sign-image\n"
        "---\n"
        "src: /img_1.png\n"
        "sign: Рисунок 1 – Описание изображения\n"
        "---\n"
        "::"
    )
    assert markdown_output == expected_markdown


def test_render_image_without_caption():
    """Tests that images without captions use traditional format."""
    # Arrange
    doc = InternalDoc(blocks=[
        Image(resource_id="img_1", alt="Image without caption"),
    ])
    asset_map = {"img_1": "image1.png"}
    
    # Act
    markdown_output = render_markdown(doc, asset_map)
    
    # Assert
    expected_markdown = (
        "::sign-image\n"
        "---\n"
        "src: /img_1.png\n"
        "sign: Image without caption\n"
        "---\n"
        "::"
    )
    assert markdown_output == expected_markdown


def test_render_multiple_images_with_numbering():
    """Tests that multiple images use their resource_id for paths."""
    # Arrange
    doc = InternalDoc(blocks=[
        Image(resource_id="img_1", alt="Image 1", caption="Рисунок 1 – Первое изображение"),
        Paragraph(inlines=[Text(content="Some text between images")]),
        Image(resource_id="img_2", alt="Image 2", caption="Рисунок 2 – Второе изображение"),
    ])
    asset_map = {"img_1": "original1.png", "img_2": "original2.png"}
    
    # Act
    markdown_output = render_markdown(doc, asset_map)
    
    # Assert - should use resource_id for paths
    assert "src: /img_1.png" in markdown_output
    assert "src: /img_2.png" in markdown_output
    assert "sign: Рисунок 1 – Первое изображение" in markdown_output
    assert "sign: Рисунок 2 – Второе изображение" in markdown_output




def test_render_images_use_resource_id_for_paths():
    """Tests that image paths use resource_id instead of extracted numbers from captions."""
    # Arrange - simulate real DOCX structure where resource_id comes from original filename
    doc = InternalDoc(blocks=[
        Image(resource_id="image2", alt="First image", caption="Рисунок 1 – Описание первого изображения"),
        Image(resource_id="image15", alt="Second image", caption="Рисунок 2 – Описание второго изображения"),
        Image(resource_id="image7", alt="Third image", caption="Схема работы системы"),  # No number in caption
    ])
    asset_map = {
        "image2": "images/chapter1/image2.png", 
        "image15": "images/chapter2/image15.png",
        "image7": "images/chapter1/image7.png"
    }
    
    # Act
    markdown_output = render_markdown(doc, asset_map)
    
    # Assert - paths should use resource_id, not numbers from captions
    assert "src: /image2.png" in markdown_output
    assert "src: /image15.png" in markdown_output  
    assert "src: /image7.png" in markdown_output
    
    # Captions should be preserved as-is
    assert "sign: Рисунок 1 – Описание первого изображения" in markdown_output
    assert "sign: Рисунок 2 – Описание второго изображения" in markdown_output
    assert "sign: Схема работы системы" in markdown_output
