import os
import re
from pathlib import Path
from typing import List, Dict, Tuple

from core.model.resource_ref import ResourceRef
from core.model.internal_doc import InternalDoc, Image

# A simple map to get file extensions from mime types
MIME_TYPE_EXTENSIONS = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/gif": ".gif",
}

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
    
    # Create base images directory
    images_base_dir = Path(base_output_dir) / "images"
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
            relative_path = f"images/{safe_chapter_name}/{filename}"
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
    
    Args:
        name: The original name string.
        
    Returns:
        A sanitized string safe for directory names.
    """
    # Remove or replace problematic characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', name)
    # Remove leading/trailing whitespace and dots
    sanitized = sanitized.strip('. ')
    # Limit length to avoid filesystem issues
    if len(sanitized) > 100:
        sanitized = sanitized[:100].rstrip('. ')
    # Ensure it's not empty
    if not sanitized:
        sanitized = "unnamed"
    
    return sanitized
