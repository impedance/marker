#!/usr/bin/env python3
"""
Test the current table parsing to see what the actual output looks like.
"""

from core.adapters.docx_parser import parse_docx_to_internal_doc
from core.render.markdown_renderer import render_markdown
from core.model.internal_doc import Table
import json

def test_table_parsing():
    docx_path = "/home/spec/work/rosa/marker/real-docs/hrom-12-admin-foundations.docx"
    
    # Parse the document
    print("Parsing document...")
    internal_doc, resources = parse_docx_to_internal_doc(docx_path)
    
    # Find the first table
    table_blocks = [block for block in internal_doc.blocks if isinstance(block, Table)]
    
    print(f"Found {len(table_blocks)} tables")
    
    if table_blocks:
        first_table = table_blocks[0]
        print("\n=== FIRST TABLE STRUCTURE ===")
        
        # Print header
        print("Header row:")
        for i, cell in enumerate(first_table.header.cells):
            print(f"  Cell {i}: {len(cell.blocks)} blocks")
            for j, block in enumerate(cell.blocks):
                print(f"    Block {j}: {type(block).__name__} - {repr(getattr(block, 'inlines', getattr(block, 'content', str(block))))}")
        
        # Print body rows
        print(f"\nBody rows ({len(first_table.rows)}):")
        for row_idx, row in enumerate(first_table.rows):
            print(f"  Row {row_idx}:")
            for cell_idx, cell in enumerate(row.cells):
                print(f"    Cell {cell_idx}: {len(cell.blocks)} blocks")
                for block_idx, block in enumerate(cell.blocks):
                    if hasattr(block, 'inlines'):
                        content = ''.join(inline.content for inline in block.inlines if hasattr(inline, 'content'))
                    else:
                        content = str(block)
                    print(f"      Block {block_idx}: {type(block).__name__} - '{content}'")
        
        # Test markdown rendering
        print("\n=== MARKDOWN RENDERING ===")
        asset_map = {}  # Empty asset map for testing
        markdown = render_markdown(internal_doc, asset_map)
        
        # Find the table in markdown
        lines = markdown.split('\n')
        table_start = -1
        table_end = -1
        
        for i, line in enumerate(lines):
            if '|' in line and ('Команда' in line or 'команда1' in line):
                if table_start == -1:
                    table_start = max(0, i-2)  # Include a bit of context
                table_end = i + 10  # Include some lines after
        
        if table_start != -1:
            print("Table in markdown:")
            for i in range(table_start, min(table_end, len(lines))):
                print(f"{i:3}: {lines[i]}")
        else:
            print("Table not found in markdown")
    
    else:
        print("No tables found!")

if __name__ == "__main__":
    test_table_parsing()