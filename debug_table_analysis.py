#!/usr/bin/env python3
"""
Debug script to analyze table structure in DOCX file.
Specifically looks for "Использование двух команд" (Table 1) structure.
"""

import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
import re

# XML namespaces used in DOCX files
NS = {
    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'rel': 'http://schemas.openxmlformats.org/package/2006/relationships',
    'wp': 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
}

def extract_text_from_element(elem):
    """Extract all text content from an XML element."""
    texts = []
    for t in elem.findall('.//w:t', NS):
        if t.text:
            texts.append(t.text)
    return ''.join(texts)

def analyze_table_cell_structure(tc):
    """Analyze the structure of a table cell."""
    cell_info = {
        'paragraphs': [],
        'raw_xml': ET.tostring(tc, encoding='unicode')[:500] + '...'  # First 500 chars
    }
    
    # Extract paragraphs in this cell
    paragraphs = tc.findall('w:p', NS)
    for i, p in enumerate(paragraphs):
        para_info = {
            'index': i,
            'text': extract_text_from_element(p),
            'style_info': {},
            'formatting': {}
        }
        
        # Check paragraph properties
        pPr = p.find('w:pPr', NS)
        if pPr is not None:
            # Check for style
            pStyle = pPr.find('w:pStyle', NS)
            if pStyle is not None:
                para_info['style_info']['style_id'] = pStyle.get(f"{{{NS['w']}}}val", '')
            
            # Check for shading (highlighting)
            shd = pPr.find('w:shd', NS)
            if shd is not None:
                para_info['formatting']['shading'] = {
                    'fill': shd.get(f"{{{NS['w']}}}fill", ''),
                    'val': shd.get(f"{{{NS['w']}}}val", ''),
                    'color': shd.get(f"{{{NS['w']}}}color", '')
                }
        
        # Check run-level formatting
        runs = p.findall('w:r', NS)
        run_info = []
        for j, run in enumerate(runs):
            run_text = extract_text_from_element(run)
            run_format = {}
            
            rPr = run.find('w:rPr', NS)
            if rPr is not None:
                # Check for fonts
                rFonts = rPr.find('w:rFonts', NS)
                if rFonts is not None:
                    run_format['fonts'] = {
                        'ascii': rFonts.get(f"{{{NS['w']}}}ascii", ''),
                        'hAnsi': rFonts.get(f"{{{NS['w']}}}hAnsi", ''),
                        'cs': rFonts.get(f"{{{NS['w']}}}cs", '')
                    }
                
                # Check for shading at run level
                shd = rPr.find('w:shd', NS)
                if shd is not None:
                    run_format['shading'] = {
                        'fill': shd.get(f"{{{NS['w']}}}fill", ''),
                        'val': shd.get(f"{{{NS['w']}}}val", ''),
                        'color': shd.get(f"{{{NS['w']}}}color", '')
                    }
                
                # Check for bold, italic, etc.
                if rPr.find('w:b', NS) is not None:
                    run_format['bold'] = True
                if rPr.find('w:i', NS) is not None:
                    run_format['italic'] = True
            
            run_info.append({
                'index': j,
                'text': run_text,
                'formatting': run_format
            })
        
        para_info['runs'] = run_info
        cell_info['paragraphs'].append(para_info)
    
    return cell_info

def find_target_table(docx_path):
    """Find and analyze the table containing 'Использование двух команд'."""
    
    with zipfile.ZipFile(docx_path) as z:
        # Read the main document
        doc_xml = z.read("word/document.xml")
        
        # Parse the XML
        root = ET.fromstring(doc_xml)
        body = root.find('.//w:body', NS)
        
        # Look for tables
        tables = body.findall('.//w:tbl', NS)
        print(f"Found {len(tables)} tables in the document")
        
        target_table = None
        table_context = []
        
        # Search for the table with "Использование двух команд"
        for i, table in enumerate(tables):
            print(f"\n=== Analyzing Table {i+1} ===")
            
            # Get the first few rows to check content
            rows = table.findall('w:tr', NS)
            table_texts = []
            
            for row_idx, row in enumerate(rows[:3]):  # Check first 3 rows
                cells = row.findall('w:tc', NS)
                row_texts = []
                for cell in cells:
                    cell_text = extract_text_from_element(cell)
                    row_texts.append(cell_text)
                table_texts.append(row_texts)
            
            # Print table preview
            print("Table preview:")
            for row_idx, row_texts in enumerate(table_texts):
                print(f"  Row {row_idx}: {row_texts}")
            
            # Check if this table contains our target text
            all_table_text = ' '.join([' '.join(row) for row in table_texts])
            if 'Использование двух команд' in all_table_text or 'команда1' in all_table_text or '||' in all_table_text:
                print(f"*** FOUND TARGET TABLE {i+1} ***")
                target_table = table
                
                # Get some context around this table
                print("\nContext around the table:")
                # Find table position in body
                all_elements = list(body)
                table_index = -1
                for idx, elem in enumerate(all_elements):
                    if elem == table:
                        table_index = idx
                        break
                
                # Get paragraphs before and after
                for offset in range(-3, 4):
                    elem_idx = table_index + offset
                    if 0 <= elem_idx < len(all_elements):
                        elem = all_elements[elem_idx]
                        if elem.tag == f"{{{NS['w']}}}p":
                            text = extract_text_from_element(elem)
                            if text.strip():
                                if elem_idx == table_index:
                                    print(f"  {offset:+2}: [TABLE]")
                                else:
                                    print(f"  {offset:+2}: {text[:100]}")
                break
        
        if target_table is None:
            print("Target table not found!")
            return None
        
        # Detailed analysis of the target table
        print(f"\n=== DETAILED ANALYSIS OF TARGET TABLE ===")
        
        rows = target_table.findall('w:tr', NS)
        print(f"Table has {len(rows)} rows")
        
        for row_idx, row in enumerate(rows):
            print(f"\n--- Row {row_idx} ---")
            cells = row.findall('w:tc', NS)
            print(f"Row has {len(cells)} cells")
            
            for cell_idx, cell in enumerate(cells):
                print(f"\n  Cell {row_idx},{cell_idx}:")
                cell_info = analyze_table_cell_structure(cell)
                
                print(f"    Text: '{extract_text_from_element(cell)}'")
                print(f"    Paragraphs: {len(cell_info['paragraphs'])}")
                
                for para in cell_info['paragraphs']:
                    if para['text'].strip():
                        print(f"      Para: '{para['text']}'")
                        if para['style_info']:
                            print(f"        Style: {para['style_info']}")
                        if para['formatting']:
                            print(f"        Formatting: {para['formatting']}")
                        
                        # Check runs for detailed formatting
                        for run in para['runs']:
                            if run['text'].strip() and run['formatting']:
                                print(f"          Run: '{run['text']}' -> {run['formatting']}")
        
        return target_table

def main():
    docx_path = "/home/spec/work/rosa/marker/real-docs/hrom-12-admin-foundations.docx"
    
    if not Path(docx_path).exists():
        print(f"File not found: {docx_path}")
        return
    
    print(f"Analyzing: {docx_path}")
    find_target_table(docx_path)

if __name__ == "__main__":
    main()