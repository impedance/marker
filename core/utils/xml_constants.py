"""XML constants and patterns used across DOCX parsing modules."""

# XML namespaces for Word documents
NS = {
    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'rel': 'http://schemas.openxmlformats.org/package/2006/relationships',
    'wp': 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'pic': 'http://schemas.openxmlformats.org/drawingml/2006/picture'
}

# Default heading patterns for various languages
DEFAULT_HEADING_PATTERNS = [
    r"^Heading\s*(\d)$",           # English
    r"^Заголовок\s*(\d)$",         # Russian exact
    r".*Заголовок\s*(\d)$",        # Russian with prefixes like 'ROSA_Заголовок 1'
    r"^Titre\s*(\d)$",             # French
    r"^Überschrift\s*(\d)$",       # German
    r"^Encabezado\s*(\d)$",        # Spanish
    r".*\bheading\s*(\d)$",        # fallback lowercase '... heading 2'
    r"^ROSA_ПРИЛОЖЕНИЕ$",          # Special ROSA appendix style (level 1)
    r"^ROSAa$",                    # ROSA table of contents style (level 1)  
    r"^ROSAfb$",                   # ROSA appendix style (level 1)
]