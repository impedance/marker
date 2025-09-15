"""Tests for content reordering transform."""

import pytest
from core.transforms.content_reorder import run, _identify_content_moves, _find_next_section_after, _apply_content_move
from core.model.internal_doc import InternalDoc, Heading, Paragraph, Text


class TestContentReorderRun:
    """Test the main run function."""
    
    def test_empty_document(self):
        """Test reordering empty document."""
        doc = InternalDoc(blocks=[])
        result = run(doc)
        assert result.blocks == []
    
    def test_document_without_targeted_content(self):
        """Test document without the specific content that needs reordering."""
        doc = InternalDoc(blocks=[
            Heading(level=1, text="Introduction"),
            Paragraph(inlines=[Text(content="Some general content")]),
            Heading(level=2, text="Overview"),
            Paragraph(inlines=[Text(content="More general content")])
        ])
        
        result = run(doc)
        
        # Should return unchanged document
        assert len(result.blocks) == 4
        assert result.blocks[0].text == "Introduction"
        assert result.blocks[1].inlines[0].content == "Some general content"
        assert result.blocks[2].text == "Overview"
        assert result.blocks[3].inlines[0].content == "More general content"
    
    def test_document_with_correct_content_placement(self):
        """Test document where content is already correctly placed."""
        doc = InternalDoc(blocks=[
            Heading(level=2, text="Chapter 2"),
            Heading(level=3, text="2.1 Основные компоненты"),
            Paragraph(inlines=[Text(content="CMS-сервер (Winter CMS) — основной элемент серверной части")]),
            Heading(level=3, text="2.2 Other section")
        ])
        
        result = run(doc)
        
        # Should return unchanged since content is already in correct place
        assert len(result.blocks) == 4
        assert result.blocks[2].inlines[0].content == "CMS-сервер (Winter CMS) — основной элемент серверной части"


class TestIdentifyContentMoves:
    """Test the _identify_content_moves function."""
    
    def test_no_target_section(self):
        """Test when target section doesn't exist."""
        blocks = [
            Heading(level=2, text="Other Chapter"),
            Paragraph(inlines=[Text(content="CMS-сервер (Winter CMS) — основной элемент серверной части")])
        ]
        
        moves = _identify_content_moves(blocks)
        assert moves == []
    
    def test_content_already_in_correct_place(self):
        """Test when content is already correctly placed."""
        blocks = [
            Heading(level=3, text="2.1 Основные компоненты"),
            Paragraph(inlines=[Text(content="CMS-сервер (Winter CMS) — основной элемент серверной части")]),
            Heading(level=3, text="2.2 Next section")
        ]
        
        moves = _identify_content_moves(blocks)
        assert moves == []
    
    def test_misplaced_content_identification(self):
        """Test identification of misplaced content."""
        blocks = [
            Heading(level=3, text="2.1 Основные компоненты"),
            Paragraph(inlines=[Text(content="Some other content")]),
            Heading(level=3, text="2.2 Next section"),
            Paragraph(inlines=[Text(content="CMS-сервер (Winter CMS) — основной элемент серверной части")])
        ]
        
        moves = _identify_content_moves(blocks)
        
        assert len(moves) == 1
        assert moves[0]['block_idx'] == 3
        assert moves[0]['target_section_idx'] == 0
        assert moves[0]['move_type'] == 'to_section_end'
        assert "CMS-сервер" in moves[0]['content_preview']
    
    def test_multiple_misplaced_content_blocks(self):
        """Test identification of multiple misplaced content blocks."""
        blocks = [
            Heading(level=3, text="2.1 Основные компоненты"),
            Paragraph(inlines=[Text(content="Correct content here")]),
            Heading(level=3, text="2.2 Next section"),
            Paragraph(inlines=[Text(content="CMS-сервер (Winter CMS) — основной элемент серверной части")]),
            Paragraph(inlines=[Text(content="СУБД PostgreSQL — хранение основной структурированной информации")])
        ]
        
        moves = _identify_content_moves(blocks)
        
        assert len(moves) == 2
        assert moves[0]['block_idx'] == 3
        assert moves[1]['block_idx'] == 4
        assert all(move['target_section_idx'] == 0 for move in moves)
    
    def test_paragraph_without_inlines(self):
        """Test handling paragraphs without inlines."""
        blocks = [
            Heading(level=3, text="2.1 Основные компоненты"),
            Paragraph(inlines=[]),  # Empty paragraph
            Heading(level=3, text="2.2 Next section"),
            Paragraph(inlines=[Text(content="CMS-сервер (Winter CMS) — основной элемент серверной части")])
        ]
        
        moves = _identify_content_moves(blocks)
        
        # Should still find the misplaced content, ignore empty paragraph
        assert len(moves) == 1
        assert moves[0]['block_idx'] == 3


class TestFindNextSectionAfter:
    """Test the _find_next_section_after function."""
    
    def test_find_next_section_level_3(self):
        """Test finding next level 3 section."""
        blocks = [
            Heading(level=3, text="Section 1"),
            Paragraph(inlines=[Text(content="Content")]),
            Heading(level=3, text="Section 2")
        ]
        
        next_idx = _find_next_section_after(blocks, 0)
        assert next_idx == 2
    
    def test_find_next_section_higher_level(self):
        """Test finding next section of higher level (level 2)."""
        blocks = [
            Heading(level=3, text="Section 3.1"),
            Paragraph(inlines=[Text(content="Content")]),
            Heading(level=2, text="Chapter 2")
        ]
        
        next_idx = _find_next_section_after(blocks, 0)
        assert next_idx == 2
    
    def test_no_next_section(self):
        """Test when there's no next section."""
        blocks = [
            Heading(level=3, text="Last Section"),
            Paragraph(inlines=[Text(content="Content")])
        ]
        
        next_idx = _find_next_section_after(blocks, 0)
        assert next_idx == 2  # Length of blocks
    
    def test_ignore_deeper_levels(self):
        """Test that deeper level headings are ignored."""
        blocks = [
            Heading(level=3, text="Section 1"),
            Heading(level=4, text="Subsection 1.1"),
            Paragraph(inlines=[Text(content="Content")]),
            Heading(level=3, text="Section 2")
        ]
        
        next_idx = _find_next_section_after(blocks, 0)
        assert next_idx == 3  # Should skip level 4 heading
    
    def test_section_at_end(self):
        """Test when section is at the end of document."""
        blocks = [
            Paragraph(inlines=[Text(content="Content")]),
            Heading(level=3, text="Last Section")
        ]
        
        next_idx = _find_next_section_after(blocks, 1)
        assert next_idx == 2  # Length of blocks


class TestApplyContentMove:
    """Test the _apply_content_move function."""
    
    def test_move_to_section_end(self):
        """Test moving content to end of section."""
        blocks = [
            Heading(level=3, text="Target Section"),
            Paragraph(inlines=[Text(content="Existing content")]),
            Heading(level=3, text="Next Section"),
            Paragraph(inlines=[Text(content="Content to move")])
        ]
        
        move = {
            'block_idx': 3,
            'target_section_idx': 0,
            'move_type': 'to_section_end'
        }
        
        result = _apply_content_move(blocks, move)
        
        # Should move paragraph to before "Next Section"
        assert len(result) == 4
        assert result[0].text == "Target Section"
        assert result[1].inlines[0].content == "Existing content"
        assert result[2].inlines[0].content == "Content to move"
        assert result[3].text == "Next Section"
    
    def test_move_after_section_heading(self):
        """Test moving content right after section heading."""
        blocks = [
            Heading(level=3, text="Target Section"),
            Paragraph(inlines=[Text(content="Existing content")]),
            Heading(level=3, text="Next Section"),
            Paragraph(inlines=[Text(content="Content to move")])
        ]
        
        move = {
            'block_idx': 3,
            'target_section_idx': 0,
            'move_type': 'after_heading'
        }
        
        result = _apply_content_move(blocks, move)
        
        # Should move paragraph right after "Target Section"
        assert len(result) == 4
        assert result[0].text == "Target Section"
        assert result[1].inlines[0].content == "Content to move"
        assert result[2].inlines[0].content == "Existing content"
        assert result[3].text == "Next Section"
    
    def test_move_from_before_target(self):
        """Test moving content from before target section."""
        blocks = [
            Paragraph(inlines=[Text(content="Content to move")]),
            Heading(level=3, text="Target Section"),
            Paragraph(inlines=[Text(content="Existing content")]),
            Heading(level=3, text="Next Section")
        ]
        
        move = {
            'block_idx': 0,
            'target_section_idx': 1,
            'move_type': 'to_section_end'
        }
        
        result = _apply_content_move(blocks, move)
        
        # Should move paragraph to before "Next Section"
        assert len(result) == 4
        assert result[0].text == "Target Section"
        assert result[1].inlines[0].content == "Existing content"
        assert result[2].inlines[0].content == "Content to move"
        assert result[3].text == "Next Section"
    
    def test_move_to_document_end(self):
        """Test moving content when target section is at document end."""
        blocks = [
            Heading(level=3, text="Other Section"),
            Paragraph(inlines=[Text(content="Content to move")]),
            Heading(level=3, text="Target Section"),
            Paragraph(inlines=[Text(content="Existing content")])
        ]
        
        move = {
            'block_idx': 1,
            'target_section_idx': 2,
            'move_type': 'to_section_end'
        }
        
        result = _apply_content_move(blocks, move)
        
        # Should move paragraph to end of document
        assert len(result) == 4
        assert result[0].text == "Other Section"
        assert result[1].text == "Target Section"
        assert result[2].inlines[0].content == "Existing content"
        assert result[3].inlines[0].content == "Content to move"