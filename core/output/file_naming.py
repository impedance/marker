import re
from slugify import slugify
from ..utils.text_processing import extract_heading_number_and_title, extract_letter_index

def chapter_index_from_h1(heading_line: str) -> int:
    """Extract chapter index from H1 heading line.
    
    Args:
        heading_line: Heading text like "1.2 Technical Requirements", "3 Installation",
                     "Б.1 Протоколы", "Приложение А. Конфигурация"
        
    Returns:
        Integer index from the first component of the number, defaulting to 1.
        For alphabetic numbering: А=1, Б=2, В=3, etc.
    """
    # Remove markdown hashes if present
    text = re.sub(r'^#+\s*', '', heading_line.strip())
    
    # Try to extract structured number and title first
    number, title = extract_heading_number_and_title(text)
    
    if number:
        # Check for alphabetic patterns first
        letter_index = extract_letter_index(number)
        if letter_index > 0:
            return letter_index

        if not title.strip():
            return 1

        # Fall back to numeric extraction
        first = re.split(r'[.\-]', number)[0]
        try:
            return int(first)
        except ValueError:
            return 1
    
    # Legacy fallback for old format
    m = re.match(r'^([^\s]+)\s+.*$', text.strip())
    if not m:
        return 1
    num = m.group(1)  # e.g., "3" or "3.1"
    first = re.split(r'[.\-]', num)[0]
    try:
        return int(first)
    except ValueError:
        return 1

def generate_chapter_filename(index: int, title: str, pattern: str = "{index:02d}-{slug}.md") -> str:
    """
    Generates a deterministic filename for a chapter.
    Extracts the chapter number from the heading text if available.
    Index 0 is for title page/TOC, chapters start from index 1.

    Args:
        index: The 0-based index (0 for title page, 1+ for chapters).
        title: The title of the chapter (may include numbering like "1.2 Title").
        pattern: The pattern for the filename.

    Returns:
        A safe, deterministic filename string.
    """
    # Extract the first line of the title in case it's multiline
    first_line_title = title.split('\n')[0]
    
    # For title page (index 0), always use 00
    if index == 0:
        chapter_index = 0
    else:
        # Try to extract chapter index from the title
        extracted_index = chapter_index_from_h1(first_line_title)
        # Use extracted index if it's different from the default (1), otherwise use provided index
        chapter_index = extracted_index if extracted_index > 1 else index
    
    # Clean title for slug (remove the number part if present)
    # Handle both numeric and alphabetic numbering patterns
    number, extracted_title = extract_heading_number_and_title(first_line_title)
    clean_title = extracted_title if extracted_title else first_line_title
    
    # Legacy fallback for old numeric patterns
    if not extracted_title:
        clean_title = re.sub(r'^[\dIVXLCDM]+(?:[.\-]\d+)*\s+', '', first_line_title, flags=re.IGNORECASE)
    
    # Slugify the clean title
    slug = slugify(clean_title, max_length=60, word_boundary=True)
    
    return pattern.format(index=chapter_index, slug=slug)

