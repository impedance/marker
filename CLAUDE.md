# CLAUDE.md

This file provides comprehensive guidance to Claude Code when working with Python code in this repository.

## Core Development Philosophy

- **KISS (Keep It Simple, Stupid)**: Simplicity should be a key goal in design. Choose straightforward solutions over complex ones whenever possible.
- **YAGNI (You Aren't Gonna Need It)**: Avoid building functionality on speculation. Implement features only when they are needed.
- **Fail Fast**: Check for potential errors early and raise exceptions immediately when issues occur.

## Design Principles

- **Single Responsibility**: Each function, class, and module should have one clear purpose.
- **Dependency Inversion**: High-level modules should not depend on low-level modules. Both should depend on abstractions.
- **Open/Closed Principle**: Software entities should be open for extension but closed for modification.

---

### 🔄 Project Awareness & Context
- **Always read `GEMINI.md` and `architecture.md`** at the start of a new conversation to understand the project's architecture, goals, style, and constraints.
- **Use consistent naming conventions, file structure, and architecture patterns** as described in `architecture.md`.
- **Use the virtual environment** (`.venv`) whenever executing Python commands, including for unit tests.

### 🧱 Code Structure & Modularity
- **Never create a file longer than 500 lines of code.** If a file approaches this limit, refactor by splitting it into modules or helper files.
- **Functions should be under 50 lines** with a single, clear responsibility.
- **Classes should be under 100 lines** and represent a single concept or entity.
- **Organize code into clearly separated modules**, grouped by feature or responsibility as outlined in `architecture.md`.
- **Use clear, consistent imports** (prefer relative imports within packages).
- **Use python_dotenv and load_env()** for environment variables if configuration requires it.

### 🧪 Testing & Reliability
- **Follow a Test-Driven Development (TDD) approach**:
  1. Write the test first, defining expected behavior.
  2. Watch it fail to ensure it's testing something.
  3. Write the minimal code to make the test pass.
  4. Refactor the code while keeping tests green.
- **Always create Pytest unit tests for new features** (functions, classes, etc.).
- **After updating any logic**, check whether existing unit tests need to be updated. If so, do it.
- **Tests should live in the `/tests` folder** mirroring the main app structure.
  - Include at least:
    - 1 test for the expected use case (happy path)
    - 1 test for a known edge case
    - 1 test for a failure case (e.g., invalid input)
- **Use pytest fixtures** for setup and teardown to keep tests clean and DRY.

### ✅ Task Completion
- **Mark completed tasks** immediately after finishing them.
- Add new sub-tasks or TODOs discovered during development to a "Discovered During Work" section in the plan.

### 📎 Style & Conventions
- **Use Python** as the primary language.
- **Follow PEP8**, use type hints, and format code consistently.
- **Use `pydantic` for data validation** and defining the `InternalDoc` model.
- **Use `typer`** for the command-line interface.
- **Write docstrings for every public function and class** using the Google style:
  ```python
  def example(param1: str) -> bool:
      """Brief summary of the function's purpose.

      Args:
          param1 (str): Description of the first parameter.

      Returns:
          bool: Description of the return value.
          
      Raises:
          ValueError: If the input is invalid.
      """
  ```
- **Naming Conventions**:
  - Variables and functions: `snake_case`
  - Classes: `PascalCase`
  - Constants: `UPPER_SNAKE_CASE`
  - Private attributes/methods: `_leading_underscore`

### 📂 Current Project Structure
```
/home/spec/work/rosa/marker/
├── core/
│   ├── adapters/
│   │   ├── document_parser.py        # ✅ Main document parsing router
│   │   ├── docx_parser.py            # ✅ Specialized XML-based DOCX parser
│   │   └── chapter_extractor.py      # ✅ Hierarchical chapter structure extraction
│   ├── model/
│   │   ├── config.py                 # ✅ Configuration models
│   │   ├── internal_doc.py           # ✅ Complete AST models
│   │   ├── metadata.py               # ✅ Document metadata
│   │   └── resource_ref.py           # ✅ Binary resource handling
│   ├── transforms/
│   │   ├── normalize.py              # ✅ Content normalization
│   │   ├── structure_fixes.py        # ✅ Structure fixes
│   │   └── content_reorder.py        # ✅ Content reordering transform
│   ├── split/
│   │   └── chapter_splitter.py       # ✅ Chapter splitting logic
│   ├── render/
│   │   ├── markdown_renderer.py      # ✅ AST to Markdown rendering
│   │   └── assets_exporter.py        # ✅ Asset extraction and saving
│   ├── output/
│   │   ├── file_naming.py            # ✅ Deterministic file naming
│   │   ├── toc_builder.py            # ✅ TOC and manifest generation
│   │   ├── writer.py                 # ✅ File writing operations
│   │   └── hierarchical_writer.py    # ✅ Hierarchical file structure writing
│   ├── numbering/                    # ✅ Complete numbering subsystem
│   │   ├── auto_numberer.py          # ✅ Automatic heading numbering
│   │   ├── heading_numbering.py      # ✅ Complex XML numbering extraction
│   │   ├── md_numbering.py           # ✅ Markdown numbering utilities
│   │   ├── validators.py             # ✅ Numbering validation
│   │   └── __init__.py               # ✅ Package init
│   ├── utils/                        # ✅ Utility modules
│   │   ├── docx_utils.py             # ✅ DOCX processing utilities
│   │   ├── text_processing.py        # ✅ Text manipulation utilities
│   │   ├── xml_constants.py          # ✅ XML namespace and element constants
│   │   └── __init__.py               # ✅ Package init
│   └── pipeline.py                   # ✅ Pipeline orchestrator
├── tests/
│   ├── test_adapter.py               # ✅ Adapter tests
│   ├── test_integration.py           # ✅ End-to-end tests
│   ├── test_model.py                 # ✅ Model tests
│   ├── test_render.py                # ✅ Rendering tests
│   ├── test_splitter.py              # ✅ Chapter splitting tests
│   ├── test_numbering.py             # ✅ Numbering subsystem tests
│   ├── test_toc_builder.py           # ✅ TOC builder tests
│   └── test_placeholder.py           # ✅ Placeholder tests
├── samples/                          # ✅ Expected output examples
├── real-docs/                        # ✅ Real document samples for testing
├── output/                           # ✅ Generated output directory
├── doc2chapmd.py                     # ✅ CLI entry point (Typer-based with rich output)
├── config.yaml                       # ✅ Default configuration
├── requirements.txt                  # ✅ Dependencies defined
├── GEMINI.md                         # ✅ Project overview documentation
├── architecture.md                  # ✅ Detailed architecture documentation
└── [debug/test files]                # ✅ Various debugging utilities
```

### 🔍 Project Architecture & Implementation Details

#### **Document Parsing System:**
- **100% Custom XML parsing** - no external document libraries used
- **Document parsing router** via `core/adapters/document_parser.py`
- **Advanced XML-based DOCX parsing** via `core/adapters/docx_parser.py`
- **WordprocessingML XML parsing** - direct extraction from DOCX ZIP archives
- **Specialized numbering extraction** from `word/numbering.xml` and `word/styles.xml`
- **Sophisticated content detection** - code blocks, tables, images with auto-caption detection

#### **Numbering System Architecture:**
- **Complex numbering subsystem** in `core/numbering/` (not just auto-numbering)
- **`heading_numbering.py`** - extracts existing numbering from Word documents
- **Multiple format support** - decimal, roman numerals, letters
- **Hierarchical numbering** - supports 1, 1.1, 1.1.1, etc.
- **Multi-language support** - Russian, English, German, French, Spanish

#### **Chapter Structure Processing:**
- **`chapter_extractor.py`** - builds hierarchical document structure
- **XML-based heading detection** via `w:outlineLvl` and paragraph styles
- **Pattern-based style matching** for different languages
- **Content reordering** via `content_reorder.py` for misplaced sections

#### **Utility Modules:**
- **`core/utils/docx_utils.py`** - DOCX file handling and XML processing utilities
- **`core/utils/text_processing.py`** - Text manipulation and normalization utilities
- **`core/utils/xml_constants.py`** - XML namespace constants and element definitions

#### **Key Processing Flow:**
1. **DOCX XML Extraction** → Parse ZIP archive, extract XML files using custom parsers
2. **Numbering Analysis** → Parse Word's complex numbering system from XML
3. **Content Structure** → Build hierarchical heading structure via chapter_extractor
4. **Advanced Content Detection** → Detect code blocks, tables, images with captions
5. **Transform Pipeline** → Normalize, fix structure, reorder content
6. **Chapter Splitting** → Split by heading levels into separate documents
7. **Asset Export** → Extract and save binary resources (images, etc.) with deduplication
8. **Markdown Rendering** → Convert AST to clean Markdown with asset references

### 📚 Documentation & Explainability
- **Update `README.md`** when new features are added, dependencies change, or setup steps are modified.
- **Comment non-obvious code**. When writing complex logic, **add an inline `# Reason:` comment** explaining the *why*, not just the *what*.

### 🚨 Error Handling
- **Create custom exceptions** for your domain where appropriate (e.g., `class ParsingError(Exception):`).
- **Use specific exception handling**. Avoid broad `except Exception:` clauses.
- **Use context managers** (`with ...`) for resource management to ensure cleanup.

### 🧠 AI Behavior Rules
- **Never assume missing context. Ask questions if uncertain.**
- **Never hallucinate libraries or functions** – only use known, verified Python packages from `requirements.txt`.
- **Always confirm file paths and module names** exist before referencing them in code or tests.
- **Never delete or overwrite existing code** unless explicitly instructed to or as part of a planned refactoring.

### 📦 Verified Dependencies (from requirements.txt)
- **`typer`** - CLI framework ✅ actively used
- **`pydantic`** - Data validation ✅ actively used for models
- **`pyyaml`** - YAML configuration ✅ actively used
- **`pytest`** - Testing framework ✅ actively used
- **`lxml`** - XML processing ✅ potential use for XML parsing
- **`beautifulsoup4`** - HTML/XML parsing ✅ potential use
- **`python-slugify`** - URL slug generation ✅ actively used for file naming
- **`rich`** - Terminal formatting ✅ actively used for CLI output
- **`docling`** - Universal document parser ❌ **NOT USED** (listed but no actual imports)

### 🔧 Document Processing Stack
- **`xml.etree.ElementTree`** - Core XML parsing (built-in Python) ✅ actively used
- **`zipfile`** - DOCX archive handling (built-in Python) ✅ actively used
- **`re`** - Regular expressions for pattern matching (built-in Python) ✅ actively used
- **Custom XML parsers** - 100% custom DOCX processing with specialized numbering extraction
- **No external document libraries** - self-contained WordprocessingML parsing

### 🔄 Git Workflow
- **Branch Strategy**:
  - `master` - Production-ready code (main branch)
  - `develop` - Integration branch for features
  - `feature/*` - New features
  - `fix/*` - Bug fixes
- **Commit Message Format**:
  ```
  <type>(<scope>): <subject>
  
  <body>
  ```
  - **Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`.
  - **Never include "claude code" or "written by claude"** in commit messages.

---
_This document is a living guide. Update it as the project evolves and new patterns emerge._