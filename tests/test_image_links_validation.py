"""Tests for validating ::sign-image format in generated Markdown files.

This test focuses ONLY on the format correctness of image references,
not on whether the referenced files actually exist.
"""

import re
from pathlib import Path
from typing import List

import pytest


class TestSignImageFormatValidation:
    """Tests for validating ::sign-image block format in Markdown files."""

    def _validate_sign_image_block(self, lines: List[str], start_index: int, filename: str) -> List[str]:
        """Validate a single ::sign-image block format.
        
        Args:
            lines: All lines from the markdown file
            start_index: Index where ::sign-image starts
            filename: Name of the file for error reporting
            
        Returns:
            List of error messages (empty if no errors)
        """
        errors = []
        i = start_index
        
        # Line 1: should be "::sign-image"
        if i >= len(lines) or lines[i].strip() != "::sign-image":
            errors.append(f"{filename}:{i+1}: Expected '::sign-image', got '{lines[i].strip() if i < len(lines) else 'EOF'}'")
            return errors
        
        # Line 2: should be "---"
        i += 1
        if i >= len(lines) or lines[i].strip() != "---":
            errors.append(f"{filename}:{i+1}: Expected '---' after ::sign-image, got '{lines[i].strip() if i < len(lines) else 'EOF'}'")
            return errors
        
        # Look for src: line
        src_found = False
        sign_found = False
        closing_dash_found = False
        
        for j in range(i + 1, min(i + 10, len(lines))):  # Look in next few lines
            line = lines[j].strip()
            
            if line == "---":
                closing_dash_found = True
                i = j
                break
            elif line.startswith("src:"):
                src_found = True
                # Validate src format: should be "src: /imageXXX.png" or similar
                if not re.match(r"src:\s*/\w+\.(png|jpg|jpeg|gif)", line):
                    errors.append(f"{filename}:{j+1}: Invalid src format: '{line}'. Expected 'src: /imageXXX.png'")
            elif line.startswith("sign:"):
                sign_found = True
                # Sign can be any text, just check it exists
                if len(line) <= 5:  # "sign:" is 5 chars
                    errors.append(f"{filename}:{j+1}: Sign should have content: '{line}'")
        
        if not src_found:
            errors.append(f"{filename}: ::sign-image block missing 'src:' line")
        if not sign_found:
            errors.append(f"{filename}: ::sign-image block missing 'sign:' line")  
        if not closing_dash_found:
            errors.append(f"{filename}: ::sign-image block missing closing '---'")
            return errors
        
        # Look for closing "::"
        i += 1
        if i >= len(lines) or lines[i].strip() != "::":
            errors.append(f"{filename}:{i+1}: Expected closing '::', got '{lines[i].strip() if i < len(lines) else 'EOF'}'")
        
        return errors

    def test_sign_image_format_correctness(self):
        """Test that all ::sign-image blocks in generated MD files have correct format."""
        output_dir = Path("output")

        # Skip if output directory doesn't exist
        if not output_dir.exists():
            pytest.skip("Output directory 'output' not found")

        md_files = list(output_dir.rglob("*.md"))
        if not md_files:
            pytest.skip("No markdown files found in output directory")

        format_errors = []
        sign_image_found = False

        for md_file in md_files:
            try:
                content = md_file.read_text(encoding='utf-8')
            except Exception as e:
                format_errors.append(f"Could not read {md_file}: {e}")
                continue

            # Find all ::sign-image blocks
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if line.strip() == "::sign-image":
                    sign_image_found = True
                    errors = self._validate_sign_image_block(lines, i, md_file.name)
                    format_errors.extend(errors)

        # If we found sign-image blocks, they should all be correctly formatted
        if sign_image_found:
            assert not format_errors, f"Sign-image format errors found:\n" + "\n".join(format_errors)
        else:
            # If no sign-image blocks found, just report it (may be OK for some documents)
            print("No ::sign-image blocks found in any markdown files")

    def test_sign_image_pattern_extraction(self):
        """Test that we can correctly extract sign-image references from valid format."""
        # Test with valid sign-image block
        md_content = """
# Some heading

::sign-image
---
src: /image123.png
sign: This is a test image
---
::

Some other content.

::sign-image
---
src: /image456.jpg
sign: Another test image with longer description
---
::
"""
        
        # Extract sign-image blocks
        pattern = r'::sign-image\s*---\s*src:\s*(/[^/\s]+\.(png|jpg|jpeg|gif))\s*sign:\s*([^\n]*)\s*---\s*::'
        matches = re.findall(pattern, md_content, re.DOTALL | re.MULTILINE)
        
        assert len(matches) == 2, f"Should find 2 sign-image blocks, found {len(matches)}"
        
        # Check first match
        src1, ext1, sign1 = matches[0]
        assert src1 == "/image123.png"
        assert ext1 == "png"
        assert "test image" in sign1.lower()
        
        # Check second match
        src2, ext2, sign2 = matches[1]
        assert src2 == "/image456.jpg"
        assert ext2 == "jpg"
        assert "another test image" in sign2.lower()

    def test_no_false_positives_in_pattern(self):
        """Test that our pattern doesn't match invalid sign-image blocks."""
        invalid_blocks = [
            # Missing closing ::
            """::sign-image
---
src: /image123.png
sign: Test
---""",
            
            # Missing opening ---
            """::sign-image
src: /image123.png
sign: Test
---
::""",
            
            # Invalid src format
            """::sign-image
---
src: image123.png
sign: Test
---
::""",
            
            # Missing sign
            """::sign-image
---
src: /image123.png
---
::"""
        ]
        
        pattern = r'::sign-image\s*---\s*src:\s*(/[^/\s]+\.(png|jpg|jpeg|gif))\s*sign:\s*([^\n]*)\s*---\s*::'
        
        for invalid_block in invalid_blocks:
            matches = re.findall(pattern, invalid_block, re.DOTALL | re.MULTILINE)
            assert len(matches) == 0, f"Pattern should not match invalid block: {invalid_block[:50]}..."

    @pytest.mark.parametrize("directory_name", [
        "output/Rrm-admin", 
        "output/Dev-portal-user"
    ])
    def test_specific_directory_image_consistency(self, directory_name):
        """Test sign-image format consistency in specific directories."""
        directory = Path(directory_name)
        
        if not directory.exists():
            pytest.skip(f"Directory {directory_name} not found")
            
        md_files = list(directory.rglob("*.md"))
        
        if not md_files:
            pytest.skip(f"No markdown files found in {directory_name}")
        
        sign_image_blocks = []
        
        for md_file in md_files:
            try:
                content = md_file.read_text(encoding='utf-8')
                
                # Find sign-image blocks
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if line.strip() == "::sign-image":
                        # Extract this block for validation
                        block_lines = []
                        for j in range(i, min(i + 10, len(lines))):
                            block_lines.append(lines[j])
                            if j > i and lines[j].strip() == "::":
                                break
                        sign_image_blocks.append("\n".join(block_lines))
                        
            except Exception as e:
                print(f"Could not read {md_file}: {e}")
                continue
        
        # All sign-image blocks should follow same format pattern
        for block in sign_image_blocks:
            # Should contain all required components
            assert "::sign-image" in block
            assert "---" in block  
            assert "src:" in block
            assert "sign:" in block
            assert block.count("::") == 2  # Opening and closing