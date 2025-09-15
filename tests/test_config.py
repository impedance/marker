"""Tests for configuration models."""

import pytest
import tempfile
import yaml
from pathlib import Path
from core.model.config import PipelineConfig, load_config


class TestPipelineConfig:
    """Test the PipelineConfig class."""
    
    def test_default_values(self):
        """Test that default configuration values are set correctly."""
        config = PipelineConfig()
        
        assert config.split_level == 1
        assert config.assets_dir == "assets"
        assert config.chapter_pattern == "{index:02d}-{slug}.md"
        assert config.frontmatter_enabled is True
        assert config.locale == "en"
    
    def test_custom_values(self):
        """Test creating config with custom values."""
        config = PipelineConfig(
            split_level=2,
            assets_dir="images",
            chapter_pattern="{slug}.md",
            frontmatter_enabled=False,
            locale="ru"
        )
        
        assert config.split_level == 2
        assert config.assets_dir == "images"
        assert config.chapter_pattern == "{slug}.md"
        assert config.frontmatter_enabled is False
        assert config.locale == "ru"
    
    def test_from_dict(self):
        """Test creating config from dictionary."""
        config_data = {
            "split_level": 3,
            "assets_dir": "resources",
            "locale": "de"
        }
        config = PipelineConfig.from_dict(config_data)
        
        assert config.split_level == 3
        assert config.assets_dir == "resources"
        assert config.locale == "de"
        # Other values should be defaults
        assert config.chapter_pattern == "{index:02d}-{slug}.md"
        assert config.frontmatter_enabled is True
    
    def test_from_dict_empty(self):
        """Test creating config from empty dictionary."""
        config = PipelineConfig.from_dict({})
        
        # Should use all defaults
        assert config.split_level == 1
        assert config.assets_dir == "assets"
        assert config.chapter_pattern == "{index:02d}-{slug}.md"
        assert config.frontmatter_enabled is True
        assert config.locale == "en"
    
    def test_from_yaml_nonexistent_file(self):
        """Test loading from non-existent YAML file returns defaults."""
        non_existent_path = Path("/tmp/nonexistent_config.yaml")
        config = PipelineConfig.from_yaml(non_existent_path)
        
        # Should use all defaults
        assert config.split_level == 1
        assert config.assets_dir == "assets"
        assert config.chapter_pattern == "{index:02d}-{slug}.md"
        assert config.frontmatter_enabled is True
        assert config.locale == "en"
    
    def test_from_yaml_valid_file(self):
        """Test loading from valid YAML file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml_content = {
                "split_level": 2,
                "assets_dir": "media",
                "chapter_pattern": "chapter-{slug}.md",
                "frontmatter_enabled": False,
                "locale": "fr"
            }
            yaml.safe_dump(yaml_content, f)
            f.flush()
            
            config = PipelineConfig.from_yaml(Path(f.name))
            
            assert config.split_level == 2
            assert config.assets_dir == "media"
            assert config.chapter_pattern == "chapter-{slug}.md"
            assert config.frontmatter_enabled is False
            assert config.locale == "fr"
            
        # Clean up
        Path(f.name).unlink()
    
    def test_from_yaml_partial_file(self):
        """Test loading from YAML file with partial configuration."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml_content = {
                "split_level": 3,
                "locale": "es"
                # Other values not specified
            }
            yaml.safe_dump(yaml_content, f)
            f.flush()
            
            config = PipelineConfig.from_yaml(Path(f.name))
            
            # Specified values
            assert config.split_level == 3
            assert config.locale == "es"
            # Default values
            assert config.assets_dir == "assets"
            assert config.chapter_pattern == "{index:02d}-{slug}.md"
            assert config.frontmatter_enabled is True
            
        # Clean up
        Path(f.name).unlink()
    
    def test_from_yaml_empty_file(self):
        """Test loading from empty YAML file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("")  # Empty file
            f.flush()
            
            config = PipelineConfig.from_yaml(Path(f.name))
            
            # Should use all defaults
            assert config.split_level == 1
            assert config.assets_dir == "assets"
            assert config.chapter_pattern == "{index:02d}-{slug}.md"
            assert config.frontmatter_enabled is True
            assert config.locale == "en"
            
        # Clean up
        Path(f.name).unlink()
    
    def test_to_yaml(self):
        """Test saving configuration to YAML file."""
        config = PipelineConfig(
            split_level=2,
            assets_dir="files",
            chapter_pattern="{slug}-chapter.md",
            frontmatter_enabled=False,
            locale="it"
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "test_config.yaml"
            config.to_yaml(config_path)
            
            # Verify file was created
            assert config_path.exists()
            
            # Load and verify content
            with open(config_path, 'r', encoding='utf-8') as f:
                saved_data = yaml.safe_load(f)
            
            assert saved_data["split_level"] == 2
            assert saved_data["assets_dir"] == "files"
            assert saved_data["chapter_pattern"] == "{slug}-chapter.md"
            assert saved_data["frontmatter_enabled"] is False
            assert saved_data["locale"] == "it"
    
    def test_to_yaml_creates_directories(self):
        """Test that to_yaml creates parent directories if they don't exist."""
        config = PipelineConfig()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            nested_path = Path(temp_dir) / "nested" / "dirs" / "config.yaml"
            config.to_yaml(nested_path)
            
            # Verify file and directories were created
            assert nested_path.exists()
            assert nested_path.parent.exists()
    
    def test_roundtrip_yaml(self):
        """Test saving and loading configuration preserves values."""
        original_config = PipelineConfig(
            split_level=4,
            assets_dir="resources",
            chapter_pattern="ch-{index}-{slug}.md",
            frontmatter_enabled=True,
            locale="ja"
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "roundtrip_config.yaml"
            
            # Save
            original_config.to_yaml(config_path)
            
            # Load
            loaded_config = PipelineConfig.from_yaml(config_path)
            
            # Verify all values match
            assert loaded_config.split_level == original_config.split_level
            assert loaded_config.assets_dir == original_config.assets_dir
            assert loaded_config.chapter_pattern == original_config.chapter_pattern
            assert loaded_config.frontmatter_enabled == original_config.frontmatter_enabled
            assert loaded_config.locale == original_config.locale


class TestLoadConfig:
    """Test the load_config function."""
    
    def test_load_config_default_path(self):
        """Test load_config with default path."""
        # This should look for config.yaml in current directory
        config = load_config()
        
        # Should return a valid config (either from file or defaults)
        assert isinstance(config, PipelineConfig)
        assert hasattr(config, 'split_level')
        assert hasattr(config, 'assets_dir')
    
    def test_load_config_custom_path_nonexistent(self):
        """Test load_config with custom non-existent path."""
        custom_path = Path("/tmp/nonexistent_test_config.yaml")
        config = load_config(custom_path)
        
        # Should return default config
        assert isinstance(config, PipelineConfig)
        assert config.split_level == 1
        assert config.assets_dir == "assets"
    
    def test_load_config_custom_path_existing(self):
        """Test load_config with existing custom path."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml_content = {
                "split_level": 5,
                "assets_dir": "custom_assets",
                "locale": "zh"
            }
            yaml.safe_dump(yaml_content, f)
            f.flush()
            
            config = load_config(Path(f.name))
            
            assert config.split_level == 5
            assert config.assets_dir == "custom_assets"
            assert config.locale == "zh"
            
        # Clean up
        Path(f.name).unlink()