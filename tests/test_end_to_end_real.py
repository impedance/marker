"""Real end-to-end integration tests with actual DOCX files.

These tests use real DOCX documents to verify the complete pipeline
works correctly without mocks or fake data.
"""

import tempfile
from pathlib import Path
import pytest

from core.output.hierarchical_writer import export_docx_hierarchy_centralized
from core.adapters.chapter_extractor import extract_chapter_structure


class TestRealDocumentProcessing:
    """Integration tests using real DOCX files."""

    @pytest.fixture
    def cu_admin_docx(self):
        """Path to the cu-admin-install.docx test document."""
        docx_path = Path("real-docs/cu-admin-install.docx")
        if not docx_path.exists():
            pytest.skip(f"Test document {docx_path} not found")
        return docx_path

    def test_full_pipeline_creates_correct_structure(self, cu_admin_docx):
        """Test complete pipeline creates expected folder structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            # Run the full pipeline
            export_docx_hierarchy_centralized(cu_admin_docx, output_dir)
            
            # Verify basic structure exists
            doc_dir = output_dir / "Cu-admin-install"
            assert doc_dir.exists(), "Main document directory should be created"
            
            # Verify markdown files are created
            md_files = list(doc_dir.rglob("*.md"))
            assert len(md_files) > 0, "Should generate at least one markdown file"
            
            # Verify images directory exists
            images_dir = doc_dir / "Cu-admin-install"  # Images dir named like document
            assert images_dir.exists(), "Images directory should be created"
            
            # Verify some images are extracted
            image_files = list(images_dir.rglob("*.png")) + list(images_dir.rglob("*.jpg"))
            assert len(image_files) > 0, "Should extract at least one image"

    def test_chapter_structure_extraction(self, cu_admin_docx):
        """Test that chapter structure is correctly extracted."""
        chapters = extract_chapter_structure(cu_admin_docx)
        
        assert len(chapters) > 0, "Should extract at least one chapter"
        
        # Verify we have level 1 chapters (main sections)
        level_1_chapters = [ch for ch in chapters if ch.level == 1]
        assert len(level_1_chapters) > 0, "Should have at least one level 1 chapter"
        
        # Verify chapters have meaningful titles
        for chapter in chapters:
            assert chapter.title.strip() != "", f"Chapter at level {chapter.level} should have a title"
            assert len(chapter.title.strip()) > 1, f"Chapter title '{chapter.title}' too short"

    def test_markdown_files_have_correct_content(self, cu_admin_docx):
        """Test that generated markdown files contain expected content."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            # Run pipeline
            export_docx_hierarchy_centralized(cu_admin_docx, output_dir)
            
            # Find all markdown files
            doc_dir = output_dir / "Cu-admin-install"
            md_files = list(doc_dir.rglob("*.md"))
            
            content_found = False
            
            for md_file in md_files:
                content = md_file.read_text(encoding='utf-8')
                
                # Should have some actual content (not just heading)
                if len(content.strip()) > 10:
                    content_found = True
                    
                # If file has content, should start with heading
                if len(content.strip()) > 0:
                    lines = [line.strip() for line in content.split('\n') if line.strip()]
                    if lines:
                        # First non-empty line should be a heading
                        assert lines[0].startswith('#'), f"First line in {md_file.name} should be heading, got: {lines[0][:50]}"
            
            assert content_found, "At least one markdown file should have substantial content"

    def test_sign_image_format_in_generated_files(self, cu_admin_docx):
        """Test that generated markdown files use correct ::sign-image format."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            # Run pipeline
            export_docx_hierarchy_centralized(cu_admin_docx, output_dir)
            
            # Find all markdown files
            doc_dir = output_dir / "Cu-admin-install"
            md_files = list(doc_dir.rglob("*.md"))
            
            sign_image_found = False
            
            for md_file in md_files:
                content = md_file.read_text(encoding='utf-8')
                
                if "::sign-image" in content:
                    sign_image_found = True
                    
                    # Verify format is correct
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if line.strip() == "::sign-image":
                            # Next lines should be YAML-like format
                            if i + 1 < len(lines):
                                next_line = lines[i + 1].strip()
                                assert next_line == "---", f"Line after ::sign-image should be '---', got '{next_line}'"
                            
                            # Find closing ---
                            closing_found = False
                            for j in range(i + 2, min(i + 10, len(lines))):
                                if lines[j].strip() == "---":
                                    closing_found = True
                                    break
                            assert closing_found, "::sign-image block should have closing '---'"
                            
                            # Should have ::
                            closing_block_found = False
                            for j in range(i + 3, min(i + 12, len(lines))):
                                if lines[j].strip() == "::":
                                    closing_block_found = True
                                    break
                            assert closing_block_found, "::sign-image block should end with '::'"
            
            # If document has images, should have sign-image blocks
            images_dir = doc_dir / "Cu-admin-install"
            if images_dir.exists():
                image_files = list(images_dir.rglob("*.png")) + list(images_dir.rglob("*.jpg"))
                if len(image_files) > 0:
                    assert sign_image_found, "Documents with images should have ::sign-image blocks"

    def test_folder_naming_consistency(self, cu_admin_docx):
        """Test that folder names follow consistent naming conventions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            # Run pipeline
            export_docx_hierarchy_centralized(cu_admin_docx, output_dir)
            
            doc_dir = output_dir / "Cu-admin-install"
            
            # Get all directories (excluding images directory)
            all_dirs = [d for d in doc_dir.rglob("*") if d.is_dir()]
            content_dirs = [d for d in all_dirs if d.name != "Cu-admin-install"]  # Exclude images dir
            
            for directory in content_dirs:
                # Directory names should not have spaces
                assert " " not in directory.name, f"Directory '{directory.name}' should not contain spaces"
                
                # Content directories (with markdown files) should follow numbering pattern  
                if directory.name != "Cu-admin-install":  # Skip images directory
                    # Check if this directory contains markdown files (content directory)
                    md_files = list(directory.rglob("*.md"))
                    if len(md_files) > 0:
                        # Content directories should start with digits (chapter numbering)
                        assert directory.name[0].isdigit(), f"Content directory '{directory.name}' should start with chapter number"

    def test_no_empty_markdown_files(self, cu_admin_docx):
        """Test that no empty markdown files are generated."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            # Run pipeline
            export_docx_hierarchy_centralized(cu_admin_docx, output_dir)
            
            # Find all markdown files
            doc_dir = output_dir / "Cu-admin-install"
            md_files = list(doc_dir.rglob("*.md"))
            
            for md_file in md_files:
                content = md_file.read_text(encoding='utf-8').strip()
                assert len(content) > 0, f"Markdown file '{md_file.name}' should not be empty"
                
                # Should have at least a heading
                lines = [line.strip() for line in content.split('\n') if line.strip()]
                assert len(lines) > 0, f"Markdown file '{md_file.name}' should have at least one non-empty line"


class TestDocumentSpecificContent:
    """Tests specific to cu-admin-install.docx content."""

    @pytest.fixture
    def cu_admin_docx(self):
        """Path to the cu-admin-install.docx test document."""
        docx_path = Path("real-docs/cu-admin-install.docx")
        if not docx_path.exists():
            pytest.skip(f"Test document {docx_path} not found")
        return docx_path

    def test_known_sections_are_extracted(self, cu_admin_docx):
        """Test that known sections from cu-admin-install.docx are correctly extracted."""
        chapters = extract_chapter_structure(cu_admin_docx)
        
        # Get all chapter titles
        titles = [chapter.title.lower() for chapter in chapters]
        title_text = " ".join(titles)
        
        # Should contain expected major sections (case insensitive, partial matches)
        expected_sections = [
            "общие сведения",
            "условия выполнения установки", 
            "установка",
            "настройка"
        ]
        
        for section in expected_sections:
            assert any(section in title for title in titles), f"Should find section containing '{section}' in extracted chapters"

    def test_document_has_images(self, cu_admin_docx):
        """Test that the test document contains images as expected."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            # Run pipeline
            export_docx_hierarchy_centralized(cu_admin_docx, output_dir)
            
            # Check images directory
            images_dir = output_dir / "Cu-admin-install" / "Cu-admin-install"
            assert images_dir.exists(), "Images directory should exist for this document"
            
            # Should have multiple images
            image_files = list(images_dir.rglob("*.png")) + list(images_dir.rglob("*.jpg"))
            assert len(image_files) > 10, f"Expected many images in test document, found {len(image_files)}"