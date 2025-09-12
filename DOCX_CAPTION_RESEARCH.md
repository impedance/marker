# DOCX Image Caption Extraction Research

## Overview

This document provides comprehensive guidance on extracting image captions from Microsoft Word DOCX files using XML parsing techniques. Based on analysis of real DOCX files and Microsoft Word documentation.

## Key Findings from Analysis

### 1. Caption Storage Patterns

Based on analysis of real DOCX files (`cu-admin-install.docx`, `rrm-admin.docx`, etc.), image captions in DOCX follow these patterns:

#### Common Caption Structures:
- **Image paragraph**: Contains the `w:drawing` element (usually empty text)
- **Caption paragraph**: Follows immediately after the image paragraph
- **Reference paragraphs**: Previous paragraphs that mention the figure (e.g., "см. рисунок 1")

#### Caption Text Patterns:
Russian documents commonly use:
- `"Рисунок N"` - Figure N
- `"Рис. N"` - Fig. N  
- `"Изображение N"` - Image N
- `"Схема N"` - Scheme/Diagram N
- `"Диаграмма N"` - Chart/Diagram N

English documents use:
- `"Figure N"`
- `"Fig. N"`

### 2. XML Structure Analysis

#### Image Paragraphs:
```xml
<w:p>
  <w:pPr>
    <w:pStyle w:val="ROSA_Рисунок"/>
  </w:pPr>
  <w:r>
    <w:drawing>
      <!-- Image content -->
    </w:drawing>
  </w:r>
</w:p>
```

#### Caption Paragraphs:
```xml
<w:p>
  <w:pPr>
    <w:pStyle w:val="ROSA_Рисунок_Номер"/>
  </w:pPr>
  <w:r>
    <w:t>Общая схема конфигурации РОСА Центр Управления</w:t>
  </w:r>
</w:p>
```

#### Field-Based Captions (Advanced):
```xml
<w:p>
  <w:pPr>
    <w:pStyle w:val="caption"/>
  </w:pPr>
  <w:r>
    <w:t>Figure </w:t>
  </w:r>
  <w:r>
    <w:fldChar w:fldCharType="begin"/>
  </w:r>
  <w:r>
    <w:instrText> SEQ Figure \* ARABIC </w:instrText>
  </w:r>
  <w:r>
    <w:fldChar w:fldCharType="end"/>
  </w:r>
  <w:r>
    <w:t> - Network topology diagram</w:t>
  </w:r>
</w:p>
```

### 3. Style-Based Caption Detection

From the DOCX analysis, key caption styles found:

#### ROSA Document Templates:
- `"ROSA_Рисунок"` - Image container style
- `"ROSA_Рисунок_Номер"` - Figure number/title style  
- `"ROSA_Рисунок_Подпись"` - Figure caption style
- `"ROSA_Таблица_Номер"` - Table number style

#### Standard Word Styles:
- `"caption"` - Built-in caption style
- `"Caption"` - Alternative caption style
- `"Figure"` - Figure-specific caption style

### 4. Field Code Analysis

Microsoft Word uses SEQ (sequence) field codes for automatic caption numbering:

#### Basic SEQ Field:
- `{ SEQ Figure \* ARABIC }` - Sequential figure numbering in Arabic numerals
- `{ SEQ Table \* ARABIC }` - Sequential table numbering
- `{ SEQ Equation \* ARABIC }` - Sequential equation numbering

#### Chapter-Based Numbering:
- `{ STYLEREF 1 \s }-{ SEQ Figure \* ARABIC \s 1 }` - Chapter-figure numbering (e.g., "2-1")

## Practical Implementation Guide

### 1. Caption Detection Strategy

```python
def detect_caption_paragraph(p, style_map, all_paragraphs, paragraph_index):
    """
    Multi-strategy caption detection for a paragraph.
    
    Args:
        p: XML paragraph element
        style_map: Dictionary mapping style IDs to style names
        all_paragraphs: List of all document paragraphs
        paragraph_index: Index of current paragraph
    
    Returns:
        CaptionInfo or None
    """
    # Strategy 1: Style-based detection
    style = get_paragraph_style(p, style_map)
    if is_caption_style(style):
        return extract_caption_from_style(p, style)
    
    # Strategy 2: Pattern-based detection
    text = get_paragraph_text(p)
    if is_caption_pattern(text):
        return extract_caption_from_text(p, text)
    
    # Strategy 3: Field-based detection
    if has_seq_field(p):
        return extract_caption_from_fields(p)
    
    # Strategy 4: Context-based detection (near images)
    if is_near_image(all_paragraphs, paragraph_index):
        return extract_contextual_caption(p, text)
    
    return None
```

### 2. Image-Caption Association

```python
def associate_images_with_captions(body, style_map):
    """
    Associate images with their captions based on document structure.
    
    Args:
        body: XML body element
        style_map: Style ID to name mapping
        
    Returns:
        List of ImageCaptionPair objects
    """
    all_paragraphs = body.findall(".//w:p", NS)
    image_caption_pairs = []
    
    for i, p in enumerate(all_paragraphs):
        # Check if paragraph contains an image
        if has_image(p):
            image_info = extract_image_info(p)
            caption_info = None
            
            # Look for caption in next 3 paragraphs
            for offset in range(1, 4):
                if i + offset < len(all_paragraphs):
                    next_p = all_paragraphs[i + offset]
                    caption_info = detect_caption_paragraph(
                        next_p, style_map, all_paragraphs, i + offset
                    )
                    if caption_info:
                        break
            
            # Look for caption in previous paragraph (less common)
            if not caption_info and i > 0:
                prev_p = all_paragraphs[i - 1]
                caption_info = detect_caption_paragraph(
                    prev_p, style_map, all_paragraphs, i - 1
                )
            
            image_caption_pairs.append(
                ImageCaptionPair(
                    image=image_info,
                    caption=caption_info,
                    context_paragraphs=get_context_paragraphs(all_paragraphs, i)
                )
            )
    
    return image_caption_pairs
```

### 3. Field Code Processing

```python
def extract_seq_field_number(p):
    """
    Extract SEQ field numbering from field codes in paragraph.
    
    Args:
        p: XML paragraph element
        
    Returns:
        Tuple of (field_type, number) or (None, None)
    """
    # Look for field characters and instruction text
    field_chars = p.findall(".//w:fldChar", NS)
    instr_texts = p.findall(".//w:instrText", NS)
    
    if not field_chars or not instr_texts:
        return None, None
    
    # Parse instruction text for SEQ fields
    for instr in instr_texts:
        if instr.text:
            instr_text = instr.text.strip()
            # Pattern: " SEQ Figure \* ARABIC "
            seq_match = re.match(r'\s*SEQ\s+(\w+)\s*\\?\*?\s*(\w+)?\s*', instr_text)
            if seq_match:
                field_type = seq_match.group(1)  # "Figure", "Table", etc.
                format_type = seq_match.group(2) or "ARABIC"
                
                # Extract the actual number from field result
                # This requires looking at the field result text
                field_result = extract_field_result(p, field_chars, instr_texts)
                return field_type, field_result
    
    return None, None

def extract_field_result(p, field_chars, instr_texts):
    """
    Extract the actual field result (number) from field code structure.
    """
    # Field structure: begin -> instrText -> end -> result
    # The result text comes after the 'end' field character
    end_found = False
    
    for run in p.findall(".//w:r", NS):
        if run.find("w:fldChar[@w:fldCharType='end']", NS) is not None:
            end_found = True
            continue
        
        if end_found:
            text_elem = run.find("w:t", NS)
            if text_elem is not None and text_elem.text:
                # This should be the field result (the actual number)
                return text_elem.text.strip()
    
    return None
```

### 4. Caption Pattern Recognition

```python
def is_caption_pattern(text):
    """
    Check if text matches common caption patterns.
    
    Args:
        text: Paragraph text
        
    Returns:
        Boolean indicating if text looks like a caption
    """
    text_lower = text.strip().lower()
    
    caption_patterns = [
        # Russian patterns
        r'рисунок\s+\d+',           # "Рисунок 1"
        r'рис\.\s*\d+',             # "Рис. 1"
        r'изображение\s+\d+',       # "Изображение 1"
        r'схема\s+\d+',             # "Схема 1"
        r'диаграмма\s+\d+',         # "Диаграмма 1"
        r'таблица\s+\d+',           # "Таблица 1"
        
        # English patterns
        r'figure\s+\d+',            # "Figure 1"
        r'fig\.\s*\d+',             # "Fig. 1"
        r'table\s+\d+',             # "Table 1"
        r'diagram\s+\d+',           # "Diagram 1"
        r'chart\s+\d+',             # "Chart 1"
        r'image\s+\d+',             # "Image 1"
        
        # Pattern with separators
        r'(рисунок|figure|рис\.|fig\.)\s*\d+\s*[-–—]\s*.+',  # "Figure 1 - Description"
    ]
    
    for pattern in caption_patterns:
        if re.search(pattern, text_lower):
            return True
    
    return False

def is_caption_style(style_name):
    """
    Check if style name indicates a caption style.
    
    Args:
        style_name: Style name from DOCX
        
    Returns:
        Boolean indicating if style is caption-related
    """
    caption_style_patterns = [
        # Standard Word caption styles
        r'caption',
        r'figure',
        r'table.*caption',
        
        # ROSA template styles
        r'rosa.*рисунок.*номер',
        r'rosa.*рисунок.*подпись',
        r'rosa.*таблица.*номер',
        r'rosa.*figure',
        r'rosa.*caption',
    ]
    
    style_lower = style_name.lower()
    for pattern in caption_style_patterns:
        if re.search(pattern, style_lower):
            return True
    
    return False
```

### 5. Data Model for Captions

```python
from dataclasses import dataclass
from typing import Optional, List, Dict

@dataclass
class CaptionInfo:
    """Information about an image caption."""
    text: str
    number: Optional[str] = None
    label: Optional[str] = None  # "Figure", "Table", etc.
    description: Optional[str] = None
    style: Optional[str] = None
    is_field_based: bool = False

@dataclass
class ImageCaptionPair:
    """Represents an image and its associated caption."""
    image: Image  # From existing Image model
    caption: Optional[CaptionInfo]
    context_paragraphs: List[str]  # Surrounding context for reference
    reference_mentions: List[str]  # Paragraphs that reference this figure

def parse_caption_text(text: str) -> CaptionInfo:
    """
    Parse caption text into structured components.
    
    Args:
        text: Raw caption text
        
    Returns:
        CaptionInfo with parsed components
    """
    # Pattern to extract: "Figure 1 - Network topology diagram"
    full_pattern = r'(рисунок|figure|рис\.|fig\.|таблица|table)\s*(\d+(?:\.\d+)*)\s*[-–—]?\s*(.*)'
    
    match = re.match(full_pattern, text.strip(), re.IGNORECASE)
    if match:
        label = match.group(1)
        number = match.group(2)
        description = match.group(3).strip()
        
        return CaptionInfo(
            text=text,
            label=label,
            number=number,
            description=description if description else None
        )
    
    # Fallback: treat entire text as description
    return CaptionInfo(text=text, description=text)
```

## Integration with Existing Code

### Extending the DOCX Parser

To integrate caption extraction into the existing `docx_parser.py`:

```python
# Add to imports
from dataclasses import dataclass
from typing import Optional

# Add new function
def _find_captions_for_images(body, relationships, media_images, style_map):
    """
    Find captions associated with images in document.
    
    Returns:
        Dict mapping image resource_id to CaptionInfo
    """
    all_paragraphs = body.findall(".//w:p", NS)
    image_captions = {}
    
    for i, p in enumerate(all_paragraphs):
        # Check if paragraph contains an image
        images = _find_images_in_paragraph(p, relationships, media_images)
        
        for image in images:
            caption_info = None
            
            # Look for caption in next few paragraphs
            for offset in range(1, 4):
                if i + offset < len(all_paragraphs):
                    next_p = all_paragraphs[i + offset]
                    text = _text_of(next_p)
                    style = _get_paragraph_style(next_p, style_map)
                    
                    if _is_likely_caption(text, style):
                        caption_info = _parse_caption_text(text, style)
                        break
            
            if caption_info:
                image_captions[image.resource_id] = caption_info
    
    return image_captions

# Modify parse_docx_to_internal_doc function
def parse_docx_to_internal_doc(docx_path: str) -> Tuple[InternalDoc, List[ResourceRef]]:
    # ... existing code ...
    
    # Extract captions (add after extracting media_images)
    image_captions = _find_captions_for_images(body, relationships, media_images, styles_map)
    
    # ... rest of existing code ...
    
    # When creating Image blocks, include caption
    for el in list(body):
        if el.tag == f"{{{NS['w']}}}p":
            paragraph_images = _find_images_in_paragraph(p, relationships, media_images)
            for image in paragraph_images:
                # Add caption if available
                if image.resource_id in image_captions:
                    caption_info = image_captions[image.resource_id]
                    # Extend Image model to include caption or create separate caption block
                    image.caption = caption_info.text  # If Image model supports caption
                    # OR create a separate paragraph for the caption
                    blocks.append(image)
                    if caption_info.text:
                        blocks.append(Paragraph(inlines=[InlineText(content=caption_info.text)]))
                else:
                    blocks.append(image)
```

## Advanced Features

### 1. Cross-Reference Detection

Find paragraphs that reference figures (e.g., "see Figure 1"):

```python
def find_figure_references(body, image_captions):
    """
    Find paragraphs that reference figures.
    
    Returns:
        Dict mapping figure numbers to list of referencing paragraph texts
    """
    references = {}
    figure_numbers = {cap.number for cap in image_captions.values() if cap.number}
    
    for p in body.findall(".//w:p", NS):
        text = _text_of(p)
        
        for fig_num in figure_numbers:
            # Look for references like "рисунок 1", "figure 1", "(рис. 1)"
            ref_patterns = [
                rf'\(?\s*(рисунок|рис\.|figure|fig\.)\s*{re.escape(fig_num)}\s*\)?',
            ]
            
            for pattern in ref_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    if fig_num not in references:
                        references[fig_num] = []
                    references[fig_num].append(text)
                    break
    
    return references
```

### 2. Table Caption Support

Extend the system to handle table captions:

```python
def _find_table_captions(body, style_map):
    """
    Find captions for tables in the document.
    """
    # Similar logic but looking for table elements and table-specific caption styles
    pass
```

## Testing Strategy

1. **Unit Tests**: Test individual caption detection functions
2. **Integration Tests**: Test full caption extraction pipeline
3. **Real Document Tests**: Test against actual DOCX files with known captions
4. **Edge Cases**: Test malformed captions, missing captions, multiple captions per image

## Conclusion

This research provides a comprehensive foundation for extracting image captions from DOCX files. The multi-strategy approach (style-based, pattern-based, field-based, and context-based) ensures robust caption detection across different document types and authoring styles.

The key insights are:
1. **Multiple detection strategies** are needed for robust caption extraction
2. **Style analysis** is crucial for template-based documents (like ROSA docs)
3. **Positional analysis** (captions typically follow images) is reliable
4. **Field code parsing** handles advanced Word numbering features
5. **Pattern matching** catches manually-typed captions

This approach can be incrementally implemented, starting with the most common patterns and expanding to handle edge cases.