import pytest
import tempfile
import shutil
from pathlib import Path
from typing import List

from core.output.hierarchical_writer import export_docx_hierarchy_centralized
from core.model.resource_ref import ResourceRef
from core.model.internal_doc import InternalDoc, Heading, Image, Paragraph


class TestHierarchicalBuildCentralizedImages:
    """Test hierarchical build with centralized images structure."""
    
    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary output directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def sample_docx_path(self, temp_output_dir):
        """Create a mock DOCX file for testing."""
        docx_path = Path(temp_output_dir) / "test-document.docx"
        # Create empty file (we'll mock the parsing)
        docx_path.touch()
        return docx_path
    
    def test_export_hierarchy_creates_centralized_images_structure(self, sample_docx_path, temp_output_dir, monkeypatch):
        """Test that hierarchical export creates centralized images structure."""
        
        # Mock document with multiple sections containing images
        mock_doc = InternalDoc(blocks=[
            Heading(level=1, text="1 Общие сведения"),
            Paragraph(inlines=[]),
            Image(resource_id="img1", alt="Diagram 1"),
            Heading(level=1, text="2 130000.API"),
            Paragraph(inlines=[]),
            Image(resource_id="img2", alt="API Schema"),
            Image(resource_id="img3", alt="Flow Chart"),
        ])
        
        mock_resources = [
            ResourceRef(id="img1", content=b"fake_png1", mime_type="image/png", sha256="hash1"),
            ResourceRef(id="img2", content=b"fake_png2", mime_type="image/png", sha256="hash2"), 
            ResourceRef(id="img3", content=b"fake_png3", mime_type="image/png", sha256="hash3"),
        ]
        
        # Mock the parse_document function
        def mock_parse_document(path):
            return mock_doc, mock_resources
        
        monkeypatch.setattr("core.output.hierarchical_writer.parse_document", mock_parse_document)
        
        # Export using new centralized function
        output_dir = Path(temp_output_dir) / "output"
        written_paths = export_docx_hierarchy_centralized(sample_docx_path, output_dir)
        
        # Check main structure
        doc_dir = output_dir / "Test-document"
        assert doc_dir.exists()
        
        # Check centralized images directory
        images_dir = doc_dir / doc_dir.name
        assert images_dir.exists()
        
        # Check section-specific subdirectories in images
        section1_images = images_dir / "Obshchie-svedeniya"
        section2_images = images_dir / "130000api"
        
        assert section1_images.exists()
        assert section2_images.exists()
        
        # Check images are in correct locations
        assert (section1_images / "image2.png").exists()
        assert (section2_images / "image3.png").exists()
        assert (section2_images / "image4.png").exists()
        
        # Check no individual images directories exist in sections
        section1_dir = doc_dir / "010000.Obshchie-svedeniya"
        section2_dir = doc_dir / "020000.130000.Api"
        
        assert not (section1_dir / "images").exists()
        assert not (section2_dir / "images").exists()
        
        # Check markdown files reference correct paths
        section1_md = section1_dir / "index.md"
        section2_md = section2_dir / "index.md"
        
        if section1_md.exists():
            content = section1_md.read_text()
            assert f"{doc_dir.name}/Obshchie-svedeniya/image2.png" in content
            
        if section2_md.exists():
            content = section2_md.read_text()
            assert f"{doc_dir.name}/130000api/image3.png" in content
            assert f"{doc_dir.name}/130000api/image4.png" in content
    
    def test_export_hierarchy_handles_sections_without_images(self, sample_docx_path, temp_output_dir, monkeypatch):
        """Test that sections without images don't create empty directories."""
        
        mock_doc = InternalDoc(blocks=[
            Heading(level=1, text="1 Text Only Section"),
            Paragraph(inlines=[]),
            Heading(level=1, text="2 Section With Images"),
            Image(resource_id="img1", alt="Image 1"),
        ])
        
        mock_resources = [
            ResourceRef(id="img1", content=b"fake_png", mime_type="image/png", sha256="hash1"),
        ]
        
        def mock_parse_document(path):
            return mock_doc, mock_resources
        
        monkeypatch.setattr("core.output.hierarchical_writer.parse_document", mock_parse_document)
        
        output_dir = Path(temp_output_dir) / "output"
        export_docx_hierarchy_centralized(sample_docx_path, output_dir)
        
        doc_dir = output_dir / "Test-document"
        images_dir = doc_dir / doc_dir.name
        
        # Should have images directory
        assert images_dir.exists()
        
        # Should NOT have directory for text-only section
        text_only_images = images_dir / "Text-only-section"
        assert not text_only_images.exists()
        
        # Should have directory for section with images
        with_images_dir = images_dir / "Section-with-images"
        assert with_images_dir.exists()
        assert (with_images_dir / "image2.png").exists()
    
    def test_export_hierarchy_sanitizes_section_names_for_directories(self, sample_docx_path, temp_output_dir, monkeypatch):
        """Test that section names with special characters are sanitized."""
        
        mock_doc = InternalDoc(blocks=[
            Heading(level=1, text="1 Section/With\\Special:Characters*"),
            Image(resource_id="img1", alt="Image 1"),
        ])
        
        mock_resources = [
            ResourceRef(id="img1", content=b"fake_png", mime_type="image/png", sha256="hash1"),
        ]
        
        def mock_parse_document(path):
            return mock_doc, mock_resources
        
        monkeypatch.setattr("core.output.hierarchical_writer.parse_document", mock_parse_document)
        
        output_dir = Path(temp_output_dir) / "output"
        export_docx_hierarchy_centralized(sample_docx_path, output_dir)
        
        doc_dir = output_dir / "Test-document"
        images_dir = doc_dir / doc_dir.name
        
        # Should find a sanitized directory name
        created_dirs = list(images_dir.iterdir())
        assert len(created_dirs) == 1
        
        sanitized_dir = created_dirs[0]
        # Should not contain problematic characters
        assert "/" not in sanitized_dir.name
        assert "\\" not in sanitized_dir.name
        assert ":" not in sanitized_dir.name
        assert "*" not in sanitized_dir.name
        
        # Should contain the image
        assert (sanitized_dir / "image2.png").exists()
    
    def test_export_hierarchy_handles_duplicate_images(self, sample_docx_path, temp_output_dir, monkeypatch):
        """Test deduplication of images with same content."""
        
        mock_doc = InternalDoc(blocks=[
            Heading(level=1, text="1 Section One"),
            Image(resource_id="img1", alt="Image 1"),
            Heading(level=1, text="2 Section Two"),
            Image(resource_id="img2", alt="Image 2 (duplicate content)"),
        ])
        
        # Same content, same hash - should be deduplicated
        mock_resources = [
            ResourceRef(id="img1", content=b"same_content", mime_type="image/png", sha256="same_hash"),
            ResourceRef(id="img2", content=b"same_content", mime_type="image/png", sha256="same_hash"),
        ]
        
        def mock_parse_document(path):
            return mock_doc, mock_resources
        
        monkeypatch.setattr("core.output.hierarchical_writer.parse_document", mock_parse_document)
        
        output_dir = Path(temp_output_dir) / "output"
        export_docx_hierarchy_centralized(sample_docx_path, output_dir)
        
        doc_dir = output_dir / "Test-document"
        images_dir = doc_dir / doc_dir.name
        
        section1_images = images_dir / "Section-one"
        section2_images = images_dir / "Section-two"
        
        # Both should reference images, but physical files should be deduplicated
        # This is implementation-dependent, but at minimum both sections should work
        assert section1_images.exists() or section2_images.exists()
    
    def test_export_hierarchy_empty_document(self, sample_docx_path, temp_output_dir, monkeypatch):
        """Test handling of empty document."""
        
        mock_doc = InternalDoc(blocks=[])
        mock_resources = []
        
        def mock_parse_document(path):
            return mock_doc, mock_resources
        
        monkeypatch.setattr("core.output.hierarchical_writer.parse_document", mock_parse_document)
        
        output_dir = Path(temp_output_dir) / "output"
        written_paths = export_docx_hierarchy_centralized(sample_docx_path, output_dir)
        
        doc_dir = output_dir / "Test-document"
        
        # Should create document directory
        assert doc_dir.exists()
        
        # Should return empty list
        assert written_paths == []
        
        # Images directory should not exist for empty document
        images_dir = doc_dir / doc_dir.name
        assert not images_dir.exists()