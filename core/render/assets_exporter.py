import os
import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional

from core.model.resource_ref import ResourceRef
from core.model.internal_doc import InternalDoc, Image, Heading

# A simple map to get file extensions from mime types
MIME_TYPE_EXTENSIONS = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/gif": ".gif",
}


_RU_TRANS = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "ё": "e",
    "ж": "zh",
    "з": "z",
    "и": "i",
    "й": "i",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "kh",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "shch",
    "ъ": "",
    "ы": "y",
    "ь": "",
    "э": "e",
    "ю": "yu",
    "я": "ya",
}


def _transliterate(text: str) -> str:
    """Convert Cyrillic text to a slug-friendly Latin representation."""
    text = text.lower()
    result = "".join(_RU_TRANS.get(ch, ch) for ch in text)
    result = re.sub(r"[^a-z0-9\s-]", "", result)
    result = re.sub(r"\s+", "-", result.strip())
    # Keep all lowercase - removed uppercase conversion
    return result

def export_assets(resources: List[ResourceRef], output_dir: str) -> Dict[str, str]:
    """
    Saves binary resources to disk, avoiding duplicates based on SHA256 hash.

    Args:
        resources: A list of ResourceRef objects to be exported.
        output_dir: The path to the directory where assets will be saved.

    Returns:
        A dictionary mapping resource IDs to their new relative file paths.
    """
    asset_map: Dict[str, str] = {}
    hashes_written: Dict[str, str] = {}  # {sha256: relative_path}

    # Ensure the output directory exists
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    for resource in resources:
        if resource.sha256 in hashes_written:
            # This resource is a duplicate of one we've already saved.
            # Map its ID to the path of the existing file.
            asset_map[resource.id] = hashes_written[resource.sha256]
            continue

        # This is a new resource, so we save it.
        ext = MIME_TYPE_EXTENSIONS.get(resource.mime_type, "")
        filename = f"{resource.id}{ext}"
        relative_path = os.path.join(Path(output_dir).name, filename)
        absolute_path = Path(output_dir) / filename

        with open(absolute_path, "wb") as f:
            f.write(resource.content)

        # Store the mapping for this new file
        asset_map[resource.id] = relative_path
        hashes_written[resource.sha256] = relative_path

    return asset_map


def export_assets_by_chapter(
    resources: List[ResourceRef], 
    chapters: List[Tuple[InternalDoc, str]], 
    base_output_dir: str
) -> Dict[str, str]:
    """
    Saves binary resources organized by chapter directories.
    
    Args:
        resources: A list of ResourceRef objects to be exported.
        chapters: List of tuples (chapter_doc, chapter_title).
        base_output_dir: The base path where images directory will be created.
        
    Returns:
        A dictionary mapping resource IDs to their relative file paths.
    """
    asset_map: Dict[str, str] = {}
    hashes_written: Dict[str, str] = {}  # {sha256: relative_path}
    
    # Create mapping of resource_id to chapter title
    resource_to_chapter: Dict[str, str] = {}
    
    for chapter_doc, chapter_title in chapters:
        for block in chapter_doc.blocks:
            if isinstance(block, Image) and block.resource_id:
                resource_to_chapter[block.resource_id] = chapter_title
    
    # Group resources by chapter
    chapter_resources: Dict[str, List[ResourceRef]] = {}
    for resource in resources:
        chapter_title = resource_to_chapter.get(resource.id)
        if chapter_title:  # Only process resources that are used in chapters
            if chapter_title not in chapter_resources:
                chapter_resources[chapter_title] = []
            chapter_resources[chapter_title].append(resource)
    
    # Create base images directory named after document
    base_path = Path(base_output_dir)
    base_folder = base_path.name
    images_base_dir = base_path / base_folder
    images_base_dir.mkdir(parents=True, exist_ok=True)
    
    # Process each chapter's resources
    for chapter_title, chapter_resource_list in chapter_resources.items():
        # Sanitize chapter title for directory name
        safe_chapter_name = _sanitize_filename(chapter_title)
        chapter_images_dir = images_base_dir / safe_chapter_name
        chapter_images_dir.mkdir(parents=True, exist_ok=True)
        
        for resource in chapter_resource_list:
            if resource.sha256 in hashes_written:
                # This resource is a duplicate - reuse existing file
                asset_map[resource.id] = hashes_written[resource.sha256]
                continue
            
            # Save new resource
            ext = MIME_TYPE_EXTENSIONS.get(resource.mime_type, "")
            filename = f"{resource.id}{ext}"
            relative_path = f"{base_folder}/{safe_chapter_name}/{filename}"
            absolute_path = chapter_images_dir / filename
            
            with open(absolute_path, "wb") as f:
                f.write(resource.content)
            
            # Store mappings
            asset_map[resource.id] = relative_path
            hashes_written[resource.sha256] = relative_path
    
    return asset_map


def _sanitize_filename(name: str) -> str:
    """
    Sanitize a string to be safe for use as a directory name.
    Removes numeric prefixes from folder names for images directory.
    
    Args:
        name: The original name string.
        
    Returns:
        A sanitized string safe for directory names.
    """
    # Remove numeric prefixes like "01000.", "12345.", "1 ", "2 ", etc.
    name = re.sub(r'^\d+(\.\d+)*\.?\s*', '', name)

    # Remove or replace problematic characters
    sanitized = re.sub(r'[<>:"/\\|?*]', ' ', name)
    # Remove leading/trailing whitespace and dots
    sanitized = sanitized.strip('. ')
    # Limit length to avoid filesystem issues
    if len(sanitized) > 100:
        sanitized = sanitized[:100].rstrip('. ')
    # Ensure it's not empty
    if not sanitized:
        sanitized = "unnamed"

    return _transliterate(sanitized)


class AssetsExporter:
    """Handles exporting assets with different organizational strategies."""
    
    def __init__(self, assets_dir: Path):
        self.assets_dir = Path(assets_dir)
        self.hashes_written: Dict[str, str] = {}  # {sha256: relative_path}
        
    def export_hierarchical_images(self, doc: InternalDoc, resources: List[ResourceRef]) -> Dict[str, str]:
        """
        Export images organized in hierarchical folder structure without numeric prefixes.
        
        Creates structure like:
        {document}/
        ├── Section Name/
        │   └── Subsection Name/
        │       ├── image1.png
        │       └── image2.jpg
        
        Args:
            doc: The document containing hierarchical structure
            resources: List of image resources to export
            
        Returns:
            Dictionary mapping resource IDs to their relative file paths
        """
        asset_map: Dict[str, str] = {}
        
        # Build hierarchical structure from document
        hierarchy = self._build_hierarchical_structure(doc)
        
        # Create resource mapping
        resource_map = {r.id: r for r in resources}
        
        # Export each image to its hierarchical location
        for resource_id, path_info in hierarchy.items():
            if resource_id not in resource_map:
                continue
                
            resource = resource_map[resource_id]
            
            # Check for duplicate content
            if resource.sha256 in self.hashes_written:
                asset_map[resource.id] = self.hashes_written[resource.sha256]
                continue
            
            # Build hierarchical directory path
            dir_parts = [self._sanitize_for_hierarchy(part) for part in path_info["path_parts"]]
            target_dir = self.assets_dir
            for part in dir_parts:
                target_dir = target_dir / part
            
            # Ensure directory exists
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate filename (convert resource_id to image number + extension)
            ext = MIME_TYPE_EXTENSIONS.get(resource.mime_type, "")
            filename = self._convert_resource_id_to_filename(resource.id, ext)
            target_path = target_dir / filename
            
            # Write file
            with open(target_path, "wb") as f:
                f.write(resource.content)
            
            # Build relative path for asset map
            relative_parts = [self.assets_dir.name] + dir_parts + [filename]
            relative_path = "/".join(relative_parts)
            
            # Store mappings
            asset_map[resource.id] = relative_path
            self.hashes_written[resource.sha256] = relative_path
            
        return asset_map
    
    def _build_hierarchical_structure(self, doc: InternalDoc) -> Dict[str, Dict]:
        """
        Build hierarchical structure mapping from document blocks.
        
        Returns:
            Dict mapping resource_id to {"path_parts": [section, subsection, ...]}
        """
        hierarchy = {}
        current_sections = []  # Stack of current section names by level
        
        for block in doc.blocks:
            if isinstance(block, Heading):
                # Update the sections stack based on heading level
                level = block.level
                title = self._clean_heading_text(block.text)
                
                # Truncate sections stack to current level-1
                current_sections = current_sections[:level-1]
                
                # Add current heading at its level
                if len(current_sections) == level - 1:
                    current_sections.append(title)
                else:
                    # Fill gaps if needed
                    while len(current_sections) < level - 1:
                        current_sections.append("Unnamed")
                    current_sections.append(title)
                    
            elif isinstance(block, Image) and block.resource_id:
                # Assign image to current section path (minimum 2 levels for hierarchy)
                if len(current_sections) >= 2:
                    hierarchy[block.resource_id] = {
                        "path_parts": current_sections[:2]
                    }
                elif len(current_sections) == 1:
                    hierarchy[block.resource_id] = {
                        "path_parts": [current_sections[0]]
                    }
                else:
                    hierarchy[block.resource_id] = {
                        "path_parts": ["Без раздела"]
                    }
        
        return hierarchy
    
    def _clean_heading_text(self, text: str) -> str:
        """Clean heading text by removing numeric prefixes."""
        # Remove numeric prefixes like "1.", "1.1", "12345.", etc.
        cleaned = re.sub(r'^\d+(\.\d+)*\.?\s*', '', text)
        return cleaned.strip() if cleaned.strip() else "Unnamed"
    
    def _sanitize_for_hierarchy(self, name: str) -> str:
        """Sanitize name for use in directory hierarchy."""
        # Remove or replace problematic characters
        sanitized = re.sub(r'[<>:"/\\|?*]', ' ', name)
        # Remove leading/trailing whitespace and dots
        sanitized = sanitized.strip('. ')
        # Limit length
        if len(sanitized) > 80:
            sanitized = sanitized[:80].rstrip('. ')
        # Ensure it's not empty
        if not sanitized:
            sanitized = "Unnamed"
        return _transliterate(sanitized)
    
    def _convert_resource_id_to_filename(self, resource_id: str, extension: str) -> str:
        """
        Convert resource ID to a standard image filename.
        
        Examples: 
            img1 -> image2.png (increment by 1)
            special_image_41 -> image41.jpg
            random_id -> random_id.png (fallback)
        """
        # Try to extract number from common patterns
        number_match = re.search(r'(\d+)$', resource_id)
        if number_match:
            number = int(number_match.group(1))
            # For img1, img2, etc., convert to image2, image3 (increment by 1)
            if resource_id.startswith('img'):
                return f"image{number + 1}{extension}"
            else:
                return f"image{number}{extension}"
        
        # Fallback: use resource_id as filename
        return f"{resource_id}{extension}"
