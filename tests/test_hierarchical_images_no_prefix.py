import pytest
import tempfile
import shutil
from pathlib import Path

from core.render.assets_exporter import AssetsExporter
from core.model.resource_ref import ResourceRef
from core.model.internal_doc import InternalDoc, Heading, Image, Paragraph


class TestHierarchicalImagesNoPrefix:
    """Test hierarchical image folder structure without numeric prefixes."""
    
    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary output directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def sample_doc_with_images(self):
        """Create a sample document with hierarchical structure and images."""
        return InternalDoc(blocks=[
            Heading(level=1, text="Общие сведения"),
            Heading(level=2, text="АННОТАЦИЯ"),
            Paragraph(inlines=[]),
            Image(resource_id="img1", alt="Annotation diagram"),
            
            Heading(level=1, text="Начало работы с порталом"),
            Heading(level=2, text="Установка СИПА"),
            Paragraph(inlines=[]),
            Image(resource_id="img2", alt="SIPA setup"),
            Image(resource_id="img3", alt="SIPA config"),
            
            Heading(level=2, text="Установка РОСА Центр Управления"),
            Paragraph(inlines=[]),
            Image(resource_id="img4", alt="ROSA setup"),
            Image(resource_id="img5", alt="ROSA config"),
            
            Heading(level=1, text="Компоненты пользовательского интерфейса"),
            Heading(level=2, text="Интеграция с мобильными устройствами"),
            Paragraph(inlines=[]),
            Image(resource_id="img6", alt="Mobile integration"),
        ])
    
    @pytest.fixture
    def sample_resources(self):
        """Create sample image resources."""
        return [
            ResourceRef(id="img1", content=b"fake_png1", mime_type="image/png", sha256="hash1"),
            ResourceRef(id="img2", content=b"fake_png2", mime_type="image/png", sha256="hash2"),
            ResourceRef(id="img3", content=b"fake_png3", mime_type="image/png", sha256="hash3"),
            ResourceRef(id="img4", content=b"fake_png4", mime_type="image/png", sha256="hash4"),
            ResourceRef(id="img5", content=b"fake_png5", mime_type="image/png", sha256="hash5"),
            ResourceRef(id="img6", content=b"fake_png6", mime_type="image/png", sha256="hash6"),
        ]
    
    def test_hierarchical_image_structure_without_prefixes(self, temp_output_dir, sample_doc_with_images, sample_resources):
        """Test that images are organized in hierarchical structure without numeric prefixes."""
        
        output_dir = Path(temp_output_dir)
        assets_dir = output_dir / "images"
        
        # Create assets exporter and export images
        exporter = AssetsExporter(assets_dir)
        
        # Export all images with hierarchical structure
        exporter.export_hierarchical_images(sample_doc_with_images, sample_resources)
        
        # Verify main images directory exists
        assert assets_dir.exists()
        
        # Verify hierarchical structure without numeric prefixes
        # Level 1: Main sections (lowercase after _transliterate fix)
        general_section = assets_dir / "obshchie-svedeniya"
        portal_section = assets_dir / "nachalo-raboty-s-portalom"
        ui_section = assets_dir / "komponenty-polzovatelskogo-interfeisa"
        
        assert general_section.exists()
        assert portal_section.exists()  
        assert ui_section.exists()
        
        # Level 2: Subsections
        annotation_subsection = general_section / "annotatsiya"  # lowercase after _transliterate fix
        sipa_subsection = portal_section / "ustanovka-sipa"  # lowercase after _transliterate fix
        rosa_subsection = portal_section / "ustanovka-rosa-tsentr-upravleniya"  # lowercase after _transliterate fix
        mobile_subsection = ui_section / "integratsiya-s-mobilnymi-ustroistvami"  # lowercase after _transliterate fix
        
        assert annotation_subsection.exists()
        assert sipa_subsection.exists()
        assert rosa_subsection.exists()
        assert mobile_subsection.exists()
        
        # Verify images are in correct locations with converted names
        # img1 -> image2.png, img2 -> image3.png, etc.
        assert (annotation_subsection / "image2.png").exists()
        assert (sipa_subsection / "image3.png").exists()
        assert (sipa_subsection / "image4.png").exists()
        assert (rosa_subsection / "image5.png").exists()
        assert (rosa_subsection / "image6.png").exists()
        assert (mobile_subsection / "image7.png").exists()
    
    def test_hierarchical_structure_handles_sections_without_images(self, temp_output_dir):
        """Test that sections without images don't create empty directories."""
        
        doc = InternalDoc(blocks=[
            Heading(level=1, text="Раздел без изображений"),
            Paragraph(inlines=[]),
            
            Heading(level=1, text="Раздел с изображениями"), 
            Heading(level=2, text="Подраздел с изображением"),
            Image(resource_id="img1", alt="Test image"),
        ])
        
        resources = [
            ResourceRef(id="img1", content=b"fake_png", mime_type="image/png", sha256="hash1"),
        ]
        
        output_dir = Path(temp_output_dir)
        assets_dir = output_dir / "images"
        
        exporter = AssetsExporter(assets_dir)
        exporter.export_hierarchical_images(doc, resources)
        
        # Should NOT create directory for section without images
        empty_section = assets_dir / "razdel-bez-izobrazhenii"  # lowercase after _transliterate fix
        assert not empty_section.exists()
        
        # Should create directory for section with images
        with_images = assets_dir / "razdel-s-izobrazheniyami" / "podrazdel-s-izobrazheniem"  # lowercase after _transliterate fix
        assert with_images.exists()
        assert (with_images / "image2.png").exists()  # img1 -> image2.png
    
    def test_image_filename_preservation(self, temp_output_dir):
        """Test that original image filenames are preserved."""
        
        doc = InternalDoc(blocks=[
            Heading(level=1, text="Тест"),
            Heading(level=2, text="Подтест"),
            Image(resource_id="special_image_41", alt="Special image"),
        ])
        
        resources = [
            ResourceRef(id="special_image_41", content=b"fake_jpg", mime_type="image/jpeg", sha256="hash1"),
        ]
        
        output_dir = Path(temp_output_dir)
        assets_dir = output_dir / "images"
        
        exporter = AssetsExporter(assets_dir)
        exporter.export_hierarchical_images(doc, resources)
        
        # Verify filename conversion (special_image_41 -> image41.jpg)
        image_path = assets_dir / "test" / "podtest" / "image41.jpg"  # lowercase after _transliterate fix
        assert image_path.exists()
    
    def test_expected_cu_admin_install_structure(self, temp_output_dir):
        """Test the expected structure for cu-admin-install.docx based on our requirements."""
        
        # This mimics the actual structure we expect from cu-admin-install.docx
        doc = InternalDoc(blocks=[
            Heading(level=1, text="Общие сведения"),
            Heading(level=2, text="АННОТАЦИЯ"),
            Image(resource_id="img1", alt="annotation"),
            
            Heading(level=1, text="Начало работы с порталом"),
            Heading(level=2, text="Установка СИПА"),
            Image(resource_id="img2", alt="sipa1"),
            Image(resource_id="img3", alt="sipa2"),
            
            Heading(level=2, text="Установка РОСА Центр Управления"),
            Image(resource_id="img4", alt="rosa"),
        ])
        
        resources = [
            ResourceRef(id="img1", content=b"fake1", mime_type="image/png", sha256="h1"),
            ResourceRef(id="img2", content=b"fake2", mime_type="image/png", sha256="h2"),
            ResourceRef(id="img3", content=b"fake3", mime_type="image/png", sha256="h3"),
            ResourceRef(id="img4", content=b"fake4", mime_type="image/png", sha256="h4"),
        ]
        
        output_dir = Path(temp_output_dir)
        assets_dir = output_dir / "images"
        
        exporter = AssetsExporter(assets_dir)
        exporter.export_hierarchical_images(doc, resources)
        
        # Verify the exact structure we want:
        # images/
        # ├── Общие сведения/
        # │   └── АННОТАЦИЯ/
        # │       └── image2.png
        # ├── Начало работы с порталом/
        # │   ├── Установка СИПА/
        # │   │   ├── image3.png
        # │   │   └── image4.png
        # │   └── Установка РОСА Центр Управления/
        # │       └── image5.png
        
        assert (assets_dir / "obshchie-svedeniya" / "annotatsiya" / "image2.png").exists()  # lowercase after _transliterate fix
        assert (assets_dir / "nachalo-raboty-s-portalom" / "ustanovka-sipa" / "image3.png").exists()  # lowercase after _transliterate fix
        assert (assets_dir / "nachalo-raboty-s-portalom" / "ustanovka-sipa" / "image4.png").exists()  # lowercase after _transliterate fix
        assert (assets_dir / "nachalo-raboty-s-portalom" / "ustanovka-rosa-tsentr-upravleniya" / "image5.png").exists()  # lowercase after _transliterate fix