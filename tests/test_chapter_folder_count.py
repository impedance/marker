"""Test for verifying that the number of documentation folders matches the number of main chapters."""

import os
import tempfile
import pytest
from pathlib import Path

from core.adapters.chapter_extractor import extract_chapter_structure
from core.output.hierarchical_writer import export_docx_hierarchy_centralized, _clean_filename


class TestChapterFolderCount:
    """Test that folder count matches main chapter count."""

    def test_cu_admin_install_folder_count_matches_main_chapters(self):
        """Test that cu-admin-install.docx generates correct number of folders."""
        # Path to the test document
        docx_path = Path("real-docs/cu-admin-install.docx")
        
        # Skip test if document doesn't exist
        if not docx_path.exists():
            pytest.skip(f"Test document {docx_path} not found")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            # Process the document using hierarchical writer
            export_docx_hierarchy_centralized(docx_path, output_dir)
            
            # Get the generated directories - use the same cleaning as the function
            doc_name = _clean_filename(docx_path.stem)  # transliterated version
            doc_output_dir = output_dir / doc_name
            
            # Count folders excluding 'images' folder and centralized images directory
            folders = [
                d for d in doc_output_dir.iterdir() 
                if d.is_dir() and d.name != 'images' and d.name != doc_name
            ]
            folder_count = len(folders)
            
            # Parse document to get main chapters using chapter extractor
            chapters = extract_chapter_structure(docx_path)
            
            # Count main chapters (level 1 headings)
            main_chapters = [
                chapter for chapter in chapters 
                if chapter.level == 1
            ]
            main_chapter_count = len(main_chapters)
            
            # Assert that folder count matches main chapter count
            assert folder_count == main_chapter_count, (
                f"Folder count ({folder_count}) does not match main chapter count ({main_chapter_count}). "
                f"Folders: {[f.name for f in folders]}, "
                f"Main chapters: {[ch.title for ch in main_chapters]}"
            )

    def test_folder_count_matches_chapters_generic(self):
        """Generic test for any DOCX document folder/chapter count matching."""
        # This can be used for other documents
        test_docs = [
            "real-docs/cu-admin-install.docx",
            # Add other test documents here as needed
        ]
        
        for doc_path_str in test_docs:
            doc_path = Path(doc_path_str)
            
            if not doc_path.exists():
                continue  # Skip missing documents
                
            with tempfile.TemporaryDirectory() as temp_dir:
                output_dir = Path(temp_dir)
                
                # Process the document using hierarchical writer
                export_docx_hierarchy_centralized(doc_path, output_dir)
                
                # Get the generated directories - use the same cleaning as the function
                doc_name = _clean_filename(doc_path.stem)
                doc_output_dir = output_dir / doc_name
                
                # Count folders excluding 'images' folder and centralized images directory
                folders = [
                    d for d in doc_output_dir.iterdir() 
                    if d.is_dir() and d.name != 'images' and d.name != doc_name
                ]
                folder_count = len(folders)
                
                # Parse document to get main chapters using chapter extractor
                chapters = extract_chapter_structure(doc_path)
                
                # Count main chapters (level 1 headings)
                main_chapters = [
                    chapter for chapter in chapters 
                    if chapter.level == 1
                ]
                main_chapter_count = len(main_chapters)
                
                # Assert that folder count matches main chapter count
                assert folder_count == main_chapter_count, (
                    f"Document {doc_path.name}: Folder count ({folder_count}) does not match "
                    f"main chapter count ({main_chapter_count}). "
                    f"Folders: {[f.name for f in folders]}, "
                    f"Main chapters: {[ch.title for ch in main_chapters]}"
                )

    def test_images_folder_excluded_from_count(self):
        """Test that images folder is properly excluded from the count."""
        docx_path = Path("real-docs/cu-admin-install.docx")
        
        if not docx_path.exists():
            pytest.skip(f"Test document {docx_path} not found")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            
            # Process the document using hierarchical writer
            export_docx_hierarchy_centralized(docx_path, output_dir)
            
            # Get the generated directories - use the same cleaning as the function
            doc_name = _clean_filename(docx_path.stem)
            doc_output_dir = output_dir / doc_name
            
            # Check that centralized images folder exists but is excluded from count  
            centralized_images_folder = doc_output_dir / doc_name
            assert centralized_images_folder.exists(), "Centralized images folder should exist"
            assert centralized_images_folder.is_dir(), "Centralized images should be a directory"
            
            # Count all folders
            all_folders = [d for d in doc_output_dir.iterdir() if d.is_dir()]
            
            # Count folders excluding centralized images directory
            content_folders = [
                d for d in doc_output_dir.iterdir() 
                if d.is_dir() and d.name != doc_name
            ]
            
            # Centralized images folder should be excluded
            assert len(all_folders) == len(content_folders) + 1, (
                "Images folder should be excluded from content folder count"
            )
            
            # Verify images folder is not in content folders
            content_folder_names = [f.name for f in content_folders]
            assert 'images' not in content_folder_names, (
                "Images folder should not be in content folder list"
            )