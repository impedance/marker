"""Text processing utilities for document parsing."""

import re
from typing import Tuple


def clean_heading_text(text: str) -> str:
    """Remove numbering prefixes like '1', '1.2', '1.2.3', 'Б.1', 'Приложение А', optional dots/brackets/dashes.

    Examples:
        "3.7 Настройка" -> "Настройка"
        "3.4.3 — Функции" -> "Функции" 
        "1) Введение" -> "Введение"
        "(2.1) - Описание" -> "Описание"
        "Б.1 Протоколы" -> "Протоколы"
        "Приложение А. Конфигурация" -> "Конфигурация"
        "A.1 Configuration" -> "Configuration"

    Args:
        text (str): Text to clean from numbering prefixes.

    Returns:
        str: Text with numbering prefixes removed.
    """
    # Try structured extraction first (more reliable)
    number, title = extract_heading_number_and_title(text)
    if number and title:
        return title
    
    # Fallback to regex patterns for edge cases
    patterns = [
        r"^\s*(?:\(?\d+(?:[.\-]\d+)*\)?\.?\)?\s*(?:[-–—]\s*)?)",  # Original numeric
        r"^\s*[IVXLCDM]+\.\s*",  # Roman numerals
        r"^\s*[А-ЯЁA-Z]\.\d+(?:\.\d+)*\s*(?:[-–—]\s*)?",  # Letter.Number
        r"^\s*(?:Приложение|Appendix)\s+[А-ЯЁA-Z]\s*[.\s]*(?:[-–—]\s*)?"  # Appendix patterns
    ]
    
    for pattern in patterns:
        result = re.sub(pattern, "", text, flags=re.IGNORECASE).strip()
        if result != text:  # If pattern matched and changed the text
            return result
            
    return text.strip()


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
        "Б.1 Протоколы" -> ("Б.1", "Протоколы")
        "Приложение А. Конфигурация" -> ("Приложение А", "Конфигурация")
        "A.1 Configuration" -> ("A.1", "Configuration")
        "Appendix B Implementation" -> ("Appendix B", "Implementation")
    """
    # Try alphanumeric patterns first (more specific)
    
    # Pattern for "Приложение X[.] Title" format
    appendix_pattern = r"^\s*(Приложение\s+[А-ЯЁA-Z])\s*[.\s]*(?:[-–—]\s*)?(.*)"
    match = re.match(appendix_pattern, text.strip(), re.IGNORECASE)
    if match:
        number = match.group(1).strip()
        title = match.group(2).strip()
        return number, title
    
    # Pattern for "Appendix X Title" format (English)
    appendix_en_pattern = r"^\s*(Appendix\s+[A-Z])\s*(?:[-–—]\s*)?(.*)"
    match = re.match(appendix_en_pattern, text.strip(), re.IGNORECASE)
    if match:
        number = match.group(1).strip()
        title = match.group(2).strip()
        return number, title
        
    # Pattern for "X.N Title" format where X is a letter
    letter_dot_pattern = r"^\s*([А-ЯЁA-Z]\.\d+(?:\.\d+)*)\s*\.?\s*(?:[-–—]\s*)?(.*)"
    match = re.match(letter_dot_pattern, text.strip(), re.IGNORECASE)
    if match:
        number = match.group(1)
        title = match.group(2).strip()
        return number, title
    
    # Original numeric pattern for compatibility
    numeric_pattern = r"^\s*(?:\()?(\d+(?:[.\-]\d+)*)\)?\.?\s*(?:[-–—]\s*)?(.*)"
    match = re.match(numeric_pattern, text.strip())
    
    if match:
        number = match.group(1)
        title = match.group(2).strip()
        return number, title
    else:
        return "", text.strip()


def extract_letter_index(number_str: str) -> int:
    """Extract numeric index from letter-based numbering.
    
    Args:
        number_str (str): Number string like "Б.1", "Приложение А", "A.1"
        
    Returns:
        int: Numeric index based on letter position in alphabet (А=1, Б=2, etc.)
             Returns 0 if no letter found.
             
    Examples:
        "Б.1" -> 2
        "Приложение А" -> 1
        "В.2.3" -> 3
        "A.1" -> 1
        "Appendix B" -> 2
    """
    if not number_str:
        return 0
        
    # Extract single letter from various patterns
    patterns = [
        r"([А-ЯЁ])\.\d+",      # Б.1, В.2.3
        r"Приложение\s+([А-ЯЁ])",  # Приложение А
        r"([A-Z])\.\d+",       # A.1, B.2.3  
        r"Appendix\s+([A-Z])"  # Appendix B
    ]
    
    for pattern in patterns:
        match = re.search(pattern, number_str, re.IGNORECASE)
        if match:
            letter = match.group(1).upper()
            
            # Convert Cyrillic letters to index
            cyrillic_alphabet = "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
            if letter in cyrillic_alphabet:
                return cyrillic_alphabet.index(letter) + 1
                
            # Convert Latin letters to index  
            latin_alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            if letter in latin_alphabet:
                return latin_alphabet.index(letter) + 1
    
    return 0


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