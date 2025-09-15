"""Text processing utilities for document parsing."""

import re
from typing import Tuple


def clean_heading_text(text: str) -> str:
    """Remove numbering prefixes like '1', '1.2', '1.2.3', optional dots/brackets/dashes.

    Examples:
        "3.7 Настройка" -> "Настройка"
        "3.4.3 — Функции" -> "Функции" 
        "1) Введение" -> "Введение"
        "(2.1) - Описание" -> "Описание"

    Args:
        text (str): Text to clean from numbering prefixes.

    Returns:
        str: Text with numbering prefixes removed.
    """
    pattern = r"^\s*(?:\(?\d+(?:[.\-]\d+)*\)?\.?\)?\s*(?:[-–—]\s*)?|[IVXLCDM]+\.\s*)"
    return re.sub(pattern, "", text, flags=re.IGNORECASE).strip()


def extract_heading_number_and_title(text: str) -> Tuple[str, str]:
    """Extract number and title from heading text.
    
    Args:
        text (str): Full heading text potentially containing numbers.
        
    Returns:
        Tuple[str, str]: (number, title) where number can be empty string.
        
    Examples:
        "1.2 Introduction" -> ("1.2", "Introduction")
        "Introduction" -> ("", "Introduction")
        "3.4.5 — Configuration" -> ("3.4.5", "Configuration")
    """
    # Pattern to match various numbering formats at start of text
    pattern = r"^\s*(?:\()?(\d+(?:[.\-]\d+)*)\)?\.?\s*(?:[-–—]\s*)?(.*)"
    match = re.match(pattern, text.strip())
    
    if match:
        number = match.group(1)
        title = match.group(2).strip()
        return number, title
    else:
        return "", text.strip()


def create_slug(text: str, max_length: int = 50) -> str:
    """Create URL-safe slug from text.
    
    Args:
        text (str): Text to convert to slug.
        max_length (int): Maximum length of resulting slug.
        
    Returns:
        str: URL-safe slug.
    """
    # Convert to lowercase and replace spaces/punctuation with hyphens
    slug = re.sub(r'[^\w\s-]', '', text.lower())
    slug = re.sub(r'[-\s]+', '-', slug)
    
    # Remove leading/trailing hyphens and truncate
    slug = slug.strip('-')[:max_length]
    
    return slug or 'untitled'