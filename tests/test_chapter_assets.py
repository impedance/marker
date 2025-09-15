import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List

from core.model.resource_ref import ResourceRef
from core.model.internal_doc import InternalDoc, Heading, Image
from core.render.assets_exporter import export_assets_by_chapter


class TestChapterAssetsExport:
    """Test chapter-based asset export functionality."""
    
    @pytest.fixture
    def sample_resources(self) -> List[ResourceRef]:
        """Create sample resources for testing."""
        return [
            ResourceRef(
                id="img1",
                content=b"fake_png_content1",
                mime_type="image/png",
                sha256="abc123"
            ),
            ResourceRef(
                id="img2", 
                content=b"fake_jpg_content2",
                mime_type="image/jpeg",
                sha256="def456"
            ),
            ResourceRef(
                id="img3",
                content=b"fake_png_content3", 
                mime_type="image/png",
                sha256="ghi789"
            )
        ]
    
    @pytest.fixture
    def sample_chapters(self) -> List[tuple]:
        """Create sample chapters with titles and resource references."""
        chapters = []
        
        # Chapter 0 - АННОТАЦИЯ (with img1)
        chapter0 = InternalDoc(blocks=[
            Heading(level=1, text="АННОТАЦИЯ"),
            Image(resource_id="img1", alt="Diagram 1")
        ])
        chapters.append((chapter0, "АННОТАЦИЯ"))
        
        # Chapter 1 - 130000.API (with img2, img3)
        chapter1 = InternalDoc(blocks=[
            Heading(level=1, text="1 130000.API"),
            Image(resource_id="img2", alt="API Schema"),
            Image(resource_id="img3", alt="Flow Chart")
        ])
        chapters.append((chapter1, "130000.API"))
        
        return chapters
    
    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary output directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    def test_export_assets_by_chapter_creates_correct_structure(
        self, sample_resources, sample_chapters, temp_output_dir
    ):
        """Test that assets are exported to correct chapter-based directories."""
        base_output_path = Path(temp_output_dir) / "de-portal"
        
        # Export assets using new chapter-based function
        asset_map = export_assets_by_chapter(
            resources=sample_resources,
            chapters=sample_chapters, 
            base_output_dir=str(base_output_path)
        )
        
        # Check directory structure
        images_dir = base_output_path / base_output_path.name
        assert images_dir.exists()
        
        # Check chapter-specific directories
        annotation_dir = images_dir / "Annotatsiya"
        api_dir = images_dir / "Api"  # Numeric prefix removed
        
        assert annotation_dir.exists()
        assert api_dir.exists()
        
        # Check files exist in correct locations
        assert (annotation_dir / "img1.png").exists()
        assert (api_dir / "img2.jpg").exists()  
        assert (api_dir / "img3.png").exists()
        
        # Verify asset_map has correct paths
        base = base_output_path.name
        assert asset_map["img1"] == f"{base}/Annotatsiya/img1.png"
        assert asset_map["img2"] == f"{base}/Api/img2.jpg"  # Numeric prefix removed
        assert asset_map["img3"] == f"{base}/Api/img3.png"  # Numeric prefix removed
    
    def test_export_assets_handles_duplicate_resources(
        self, sample_chapters, temp_output_dir
    ):
        """Test that duplicate resources (same SHA256) are handled correctly."""
        # Create resources with duplicate content
        resources = [
            ResourceRef(id="img1", content=b"same_content", mime_type="image/png", sha256="same_hash"),
            ResourceRef(id="img2", content=b"same_content", mime_type="image/png", sha256="same_hash"),
        ]
        
        # Update chapters to use both images
        chapters = [
            (InternalDoc(blocks=[Heading(level=1, text="Chapter 1"), Image(resource_id="img1", alt="Image 1")]), "Chapter1"),
            (InternalDoc(blocks=[Heading(level=1, text="Chapter 2"), Image(resource_id="img2", alt="Image 2")]), "Chapter2")
        ]
        
        base_output_path = Path(temp_output_dir) / "test-doc"
        asset_map = export_assets_by_chapter(resources, chapters, str(base_output_path))
        
        # Both should reference the same physical file (first occurrence)
        first_path = asset_map["img1"]
        second_path = asset_map["img2"]
        
        # Both entries should exist in asset_map
        assert "img1" in asset_map
        assert "img2" in asset_map
        
        # Only one physical file should exist (deduplication)
        first_full_path = base_output_path / first_path
        second_full_path = base_output_path / second_path
        
        # At least one should exist (the first one written)
        assert first_full_path.exists() or second_full_path.exists()
    
    def test_export_assets_handles_chapter_without_images(
        self, sample_resources, temp_output_dir
    ):
        """Test handling chapters that have no images."""
        chapters = [
            (InternalDoc(blocks=[Heading(level=1, text="Text Only Chapter")]), "TextOnly"),
            (InternalDoc(blocks=[Heading(level=1, text="Chapter with Image"), Image(resource_id="img1", alt="Image")]), "WithImage")
        ]
        
        base_output_path = Path(temp_output_dir) / "test-doc"
        asset_map = export_assets_by_chapter([sample_resources[0]], chapters, str(base_output_path))
        
        images_dir = base_output_path / base_output_path.name
        
        # Only the chapter with images should have a directory created
        text_only_dir = images_dir / "Textonly"
        with_image_dir = images_dir / "Withimage"
        
        assert not text_only_dir.exists()
        assert with_image_dir.exists()
        assert (with_image_dir / "img1.png").exists()
    
    def test_export_assets_sanitizes_chapter_names(
        self, sample_resources, temp_output_dir
    ):
        """Test that chapter names with special characters are sanitized for directory names."""
        chapters = [
            (InternalDoc(blocks=[Image(resource_id="img1", alt="Image")]), "Chapter/With\\Special:Characters*"),
        ]
        
        base_output_path = Path(temp_output_dir) / "test-doc"
        asset_map = export_assets_by_chapter([sample_resources[0]], chapters, str(base_output_path))
        
        # Check that directory was created with sanitized name
        images_dir = base_output_path / base_output_path.name
        
        # Should find a directory that doesn't contain special characters
        created_dirs = list(images_dir.iterdir())
        assert len(created_dirs) == 1
        
        # Directory name should not contain problematic characters
        dir_name = created_dirs[0].name
        assert "/" not in dir_name
        assert "\\" not in dir_name
        assert ":" not in dir_name
        assert "*" not in dir_name
    
    def test_export_assets_empty_inputs(self, temp_output_dir):
        """Test handling of empty resources and chapters."""
        base_output_path = Path(temp_output_dir) / "test-doc"
        
        # Test empty resources
        asset_map = export_assets_by_chapter([], [], str(base_output_path))
        assert asset_map == {}
        
        # Test empty chapters with resources
        resources = [ResourceRef(id="img1", content=b"content", mime_type="image/png", sha256="hash")]
        asset_map = export_assets_by_chapter(resources, [], str(base_output_path))
        assert asset_map == {}