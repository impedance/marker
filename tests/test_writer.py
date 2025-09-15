"""Tests for the Writer class."""

import pytest
import tempfile
from pathlib import Path
from core.output.writer import Writer


class TestWriter:
    """Test the Writer class."""
    
    def test_ensure_dir_creates_directory(self):
        """Test that ensure_dir creates a directory."""
        writer = Writer()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            test_dir = Path(temp_dir) / "new_directory"
            assert not test_dir.exists()
            
            writer.ensure_dir(test_dir)
            
            assert test_dir.exists()
            assert test_dir.is_dir()
    
    def test_ensure_dir_creates_nested_directories(self):
        """Test that ensure_dir creates nested directories."""
        writer = Writer()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            nested_dir = Path(temp_dir) / "level1" / "level2" / "level3"
            assert not nested_dir.exists()
            
            writer.ensure_dir(nested_dir)
            
            assert nested_dir.exists()
            assert nested_dir.is_dir()
            assert nested_dir.parent.exists()
            assert nested_dir.parent.parent.exists()
    
    def test_ensure_dir_existing_directory(self):
        """Test that ensure_dir handles existing directories."""
        writer = Writer()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            test_dir = Path(temp_dir)
            assert test_dir.exists()
            
            # Should not raise an error
            writer.ensure_dir(test_dir)
            
            assert test_dir.exists()
            assert test_dir.is_dir()
    
    def test_write_text_creates_file(self):
        """Test that write_text creates a text file with content."""
        writer = Writer()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.txt"
            content = "Hello, World!\nThis is a test file."
            
            writer.write_text(test_file, content)
            
            assert test_file.exists()
            assert test_file.is_file()
            
            # Verify content
            with open(test_file, "r", encoding="utf-8") as f:
                read_content = f.read()
            assert read_content == content
    
    def test_write_text_overwrites_existing_file(self):
        """Test that write_text overwrites existing files."""
        writer = Writer()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.txt"
            
            # Write initial content
            writer.write_text(test_file, "Initial content")
            
            # Overwrite with new content
            new_content = "New content"
            writer.write_text(test_file, new_content)
            
            # Verify new content
            with open(test_file, "r", encoding="utf-8") as f:
                read_content = f.read()
            assert read_content == new_content
    
    def test_write_text_handles_unicode(self):
        """Test that write_text handles Unicode characters."""
        writer = Writer()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "unicode_test.txt"
            content = "Тест с русским текстом 🌟 és kínai 中文"
            
            writer.write_text(test_file, content)
            
            # Verify Unicode content
            with open(test_file, "r", encoding="utf-8") as f:
                read_content = f.read()
            assert read_content == content
    
    def test_write_binary_creates_file(self):
        """Test that write_binary creates a binary file."""
        writer = Writer()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.bin"
            content = b"Binary content \x00\x01\x02\xFF"
            
            writer.write_binary(test_file, content)
            
            assert test_file.exists()
            assert test_file.is_file()
            
            # Verify binary content
            with open(test_file, "rb") as f:
                read_content = f.read()
            assert read_content == content
    
    def test_write_binary_overwrites_existing_file(self):
        """Test that write_binary overwrites existing files."""
        writer = Writer()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "test.bin"
            
            # Write initial content
            writer.write_binary(test_file, b"Initial binary")
            
            # Overwrite with new content
            new_content = b"New binary content"
            writer.write_binary(test_file, new_content)
            
            # Verify new content
            with open(test_file, "rb") as f:
                read_content = f.read()
            assert read_content == new_content