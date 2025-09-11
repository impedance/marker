# Repository Guidelines for AI Agents

This project converts DOCX documents into chaptered Markdown files with accompanying assets. It uses a modern architecture with XML-based parsing, hierarchical document structure, and sophisticated numbering systems.

## Project Overview

**Mission**: Convert DOCX documents into structured Markdown chapters with extracted assets, maintaining document hierarchy and numbering.

**Core Technologies**:
- **Python** - Primary programming language
- **Pydantic** - Data validation and AST models (`InternalDoc`)  
- **Typer** - CLI framework
- **Pytest** - Testing framework
- **XML Processing** - Custom DOCX parsing 
- **python-slugify** - File naming
- **PyYAML** - Configuration

## Architecture Overview

The system uses a multi-stage pipeline operating on an `InternalDoc` AST:

1. **DOCX XML Extraction** → Parse ZIP archive, extract XML files
2. **Numbering Analysis** → Parse Word's numbering system from XML  
3. **Content Structure** → Build hierarchical heading structure
4. **Transform Pipeline** → Normalize, fix structure, reorder content
5. **Chapter Splitting** → Split by heading levels into separate documents
6. **Markdown Rendering** → Convert AST to clean Markdown

### Key Components

```
core/
├── adapters/
│   ├── document_parser.py     # Main document parsing router
│   ├── docx_parser.py         # XML-based DOCX parser 
│   └── chapter_extractor.py   # Hierarchical chapter structure
├── model/
│   ├── internal_doc.py        # Complete AST models
│   ├── config.py             # Configuration models  
│   ├── metadata.py           # Document metadata
│   └── resource_ref.py       # Binary resource handling
├── transforms/
│   ├── normalize.py          # Content normalization
│   ├── structure_fixes.py    # Structure fixes
│   └── content_reorder.py    # Content reordering
├── numbering/               # ✅ CRITICAL: Complex numbering subsystem
│   ├── heading_numbering.py  # XML numbering extraction from Word
│   ├── auto_numberer.py      # Automatic heading numbering
│   ├── md_numbering.py       # Markdown numbering utilities
│   └── validators.py         # Numbering validation
├── split/
│   └── chapter_splitter.py   # Chapter splitting logic
├── render/
│   ├── markdown_renderer.py  # AST to Markdown rendering
│   └── assets_exporter.py    # Asset extraction and saving
├── output/
│   ├── file_naming.py        # Deterministic file naming
│   ├── toc_builder.py        # TOC and manifest generation
│   └── writer.py             # File writing operations
└── pipeline.py              # Pipeline orchestrator
```

## Development Principles

### Core Philosophy
- **KISS (Keep It Simple)**: Choose straightforward solutions over complex ones
- **YAGNI (You Aren't Gonna Need It)**: Implement features only when needed
- **Fail Fast**: Check for errors early, raise exceptions immediately
- **Single Responsibility**: Each function/class has one clear purpose
- **Test-Driven Development**: Write tests first, then implement

### Code Structure Rules
- **Files**: Never exceed 500 lines of code
- **Functions**: Keep under 50 lines with single responsibility
- **Classes**: Keep under 100 lines representing single concepts
- **Modules**: Organize by feature/responsibility per `architecture.md`

### Testing Requirements
- **TDD Approach**: Test first → fail → implement → pass → refactor
- **Test Coverage**: Every new feature needs Pytest unit tests
- **Test Structure**: Mirror main app structure in `/tests` folder
- **Required Tests**: Happy path, edge case, failure case
- **Use pytest fixtures** for setup/teardown

## Key Technical Details

### Numbering System (Critical)
- **Complex numbering subsystem** in `core/numbering/`
- **XML-based extraction** from `word/numbering.xml` and `word/styles.xml`
- **Multiple formats**: decimal, roman numerals, letters
- **Hierarchical support**: 1, 1.1, 1.1.1, etc.
- **Multi-language**: Russian, English, German, French, Spanish

### Document Processing Flow
- **XML Parsing**: Direct DOCX ZIP extraction and WordprocessingML parsing
- **Heading Detection**: Via `w:outlineLvl` and paragraph styles
- **Pattern Matching**: Language-specific style patterns
- **Content Reordering**: Handle misplaced sections via `content_reorder.py`

### Virtual Environment Usage
- **ALWAYS use `.venv`** for Python commands and tests
- Commands: `.venv/bin/python`, `.venv/bin/pip`, `.venv/bin/pytest`

## File Conventions

### Naming Conventions
- Variables/functions: `snake_case`
- Classes: `PascalCase`  
- Constants: `UPPER_SNAKE_CASE`
- Private members: `_leading_underscore`

### Code Style
- **Follow PEP8** with type hints
- **Google-style docstrings** for all public functions/classes
- **Relative imports** within packages
- **No comments in code** unless specifically requested
- **No "claude code" references** in commits

### Dependencies (Verified)
```
typer          # CLI framework - actively used
pydantic       # Data validation - actively used for models  
pyyaml         # YAML config - actively used
pytest         # Testing - actively used
python-slugify # File naming - actively used
lxml           # XML processing - potential use
beautifulsoup4 # HTML/XML parsing - potential use
rich           # Terminal formatting - potential use
```

## Workflow Guidelines

### Development Process
1. **Read project context**: Always check `GEMINI.md`, `architecture.md`, `CLAUDE.md`
2. **Write failing tests** describing new functionality
3. **Implement minimal code** to make tests pass
4. **Refactor** while keeping tests green
5. **Run `pytest`** before committing
6. **Keep repository clean** after each commit

### Task Management
- **Mark tasks completed** immediately after finishing
- **Add discovered sub-tasks** to "Discovered During Work" section
- **Update tests** when logic changes

### Error Handling
- **Create custom exceptions** for domain-specific errors
- **Use specific exception handling** (avoid broad `except Exception`)
- **Use context managers** for resource cleanup

## Configuration

The project uses `config.yaml` for settings:
- Split level configuration (H1, H2, H3)
- Numbering preferences
- Output formatting options
- Asset handling preferences

## Testing Strategy

- **TDD mandatory** for all new features
- **Tests in `/tests`** mirroring main structure  
- **Pytest fixtures** for clean setup/teardown
- **Integration tests** for end-to-end scenarios
- **Unit tests** for individual components

## AI Agent Guidelines

### Context Awareness
- **Read architecture files first** in new conversations
- **Follow existing patterns** in codebase
- **Use consistent naming/structure** per `architecture.md`
- **Never assume libraries exist** - check `requirements.txt` first

### Code Quality  
- **Never hallucinate functions** - only use verified packages
- **Confirm paths exist** before referencing in code
- **Don't delete code** without explicit instruction
- **Ask questions** when context is unclear

### Restrictions
- **No documentation creation** unless explicitly requested
- **No "claude code" mentions** in any output
- **Prefer editing existing files** over creating new ones
- **Virtual environment required** for all Python operations

This repository implements a sophisticated document conversion system with emphasis on structure preservation, numbering accuracy, and clean Markdown output. The XML-based parsing approach and complex numbering subsystem are key differentiators from simpler conversion tools.

