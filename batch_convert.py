#!/usr/bin/env python3
"""
Batch DOCX to Chapter Markdown Converter

Converts all DOCX files in the real-docs directory using the doc2chapmd converter
and packages the results into zip archives in the out-ready directory.
"""

import os
import shutil
import subprocess
import zipfile
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.progress import Progress, TaskID


app = typer.Typer(
    name="batch-convert",
    help="Batch convert DOCX files to Markdown chapters and package as archives"
)
console = Console()


def find_docx_files(search_dir: Path) -> List[Path]:
    """Find all DOCX files in the directory, excluding temporary files."""
    docx_files = []
    for docx_path in search_dir.rglob("*.docx"):
        # Skip temporary Word files (start with ~$)
        if docx_path.name.startswith("~$"):
            continue
        # Skip template files
        if "template" in str(docx_path).lower():
            continue
        docx_files.append(docx_path)
    
    return sorted(docx_files)


def create_safe_name(docx_path: Path) -> str:
    """Create a safe archive name from the DOCX file path."""
    # Remove extension and clean up the name
    name = docx_path.stem
    # Replace problematic characters
    safe_name = name.replace(" ", "_").replace("(", "").replace(")", "").replace("-", "_")
    return safe_name


def convert_single_docx(
    docx_path: Path, 
    temp_output_dir: Path, 
    converter_script: Path
) -> bool:
    """Convert a single DOCX file using the doc2chapmd converter."""
    try:
        # Ensure output directory exists
        temp_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Run the converter
        cmd = [
            ".venv/bin/python",
            str(converter_script),
            "build",
            str(docx_path),
            "--out", str(temp_output_dir),
            "--centralized-images"
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=Path.cwd()
        )
        
        if result.returncode != 0:
            console.print(f"[red]Error converting {docx_path.name}:[/red]")
            console.print(f"[red]STDOUT:[/red] {result.stdout}")
            console.print(f"[red]STDERR:[/red] {result.stderr}")
            return False
        
        return True
        
    except Exception as e:
        console.print(f"[red]Exception converting {docx_path.name}:[/red] {e}")
        return False


def create_archive(source_dir: Path, archive_path: Path) -> bool:
    """Create a zip archive from the source directory contents."""
    try:
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Check if source_dir has a single subdirectory with the same name
            # If so, archive the contents of that subdirectory instead
            subdirs = list(source_dir.iterdir())
            
            if len(subdirs) == 1 and subdirs[0].is_dir():
                # Archive contents of the single subdirectory
                actual_source = subdirs[0]
                for file_path in actual_source.rglob('*'):
                    if file_path.is_file():
                        # Calculate relative path from the subdirectory
                        arc_name = file_path.relative_to(actual_source)
                        zipf.write(file_path, arc_name)
            else:
                # Archive all contents normally
                for file_path in source_dir.rglob('*'):
                    if file_path.is_file():
                        # Calculate relative path for archive
                        arc_name = file_path.relative_to(source_dir)
                        zipf.write(file_path, arc_name)
        return True
    except Exception as e:
        console.print(f"[red]Error creating archive {archive_path}:[/red] {e}")
        return False


@app.command()
def convert(
    input_dir: Path = typer.Option(
        Path("real-docs"), "--input", "-i",
        help="Input directory containing DOCX files"
    ),
    output_dir: Path = typer.Option(
        Path("out-ready"), "--output", "-o",
        help="Output directory for zip archives"
    ),
    temp_dir: Path = typer.Option(
        Path("temp-conversions"), "--temp", "-t",
        help="Temporary directory for conversions"
    ),
    converter: Path = typer.Option(
        Path("doc2chapmd.py"), "--converter", "-c",
        help="Path to the doc2chapmd converter script"
    ),
    clean_temp: bool = typer.Option(
        True, "--clean-temp/--keep-temp",
        help="Clean temporary files after conversion"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run",
        help="Show what would be done without actually doing it"
    )
):
    """Convert all DOCX files to Markdown archives."""
    
    # Validate paths
    if not input_dir.exists():
        console.print(f"[red]Input directory {input_dir} does not exist[/red]")
        raise typer.Exit(1)
    
    if not converter.exists():
        console.print(f"[red]Converter script {converter} does not exist[/red]")
        raise typer.Exit(1)
    
    # Find all DOCX files
    docx_files = find_docx_files(input_dir)
    
    if not docx_files:
        console.print(f"[yellow]No DOCX files found in {input_dir}[/yellow]")
        return
    
    console.print(f"[blue]Found {len(docx_files)} DOCX files to convert[/blue]")
    
    if dry_run:
        console.print("\n[yellow]DRY RUN - Would process:[/yellow]")
        for docx_path in docx_files:
            safe_name = create_safe_name(docx_path)
            console.print(f"  {docx_path.relative_to(input_dir)} → {safe_name}.zip")
        return
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Process each file
    successful_conversions = 0
    failed_conversions = 0
    
    with Progress() as progress:
        task = progress.add_task("Converting files...", total=len(docx_files))
        
        for docx_path in docx_files:
            progress.update(task, description=f"Converting {docx_path.name}")
            
            safe_name = create_safe_name(docx_path)
            temp_conversion_dir = temp_dir / safe_name
            archive_path = output_dir / f"{safe_name}.zip"
            
            # Clean up any existing temp directory
            if temp_conversion_dir.exists():
                shutil.rmtree(temp_conversion_dir)
            
            # Convert the DOCX file
            success = convert_single_docx(docx_path, temp_conversion_dir, converter)
            
            if success and temp_conversion_dir.exists():
                # Create the archive
                if create_archive(temp_conversion_dir, archive_path):
                    successful_conversions += 1
                    console.print(f"[green]✓[/green] {docx_path.name} → {archive_path.name}")
                else:
                    failed_conversions += 1
            else:
                failed_conversions += 1
                console.print(f"[red]✗[/red] Failed to convert {docx_path.name}")
            
            # Clean up temp directory if requested
            if clean_temp and temp_conversion_dir.exists():
                shutil.rmtree(temp_conversion_dir)
            
            progress.advance(task)
    
    # Summary
    console.print(f"\n[blue]Conversion Summary:[/blue]")
    console.print(f"  [green]Successful:[/green] {successful_conversions}")
    console.print(f"  [red]Failed:[/red] {failed_conversions}")
    console.print(f"  [blue]Output directory:[/blue] {output_dir}")


@app.command()
def list_files(
    input_dir: Path = typer.Option(
        Path("real-docs"), "--input", "-i",
        help="Input directory to scan for DOCX files"
    )
):
    """List all DOCX files that would be processed."""
    docx_files = find_docx_files(input_dir)
    
    if not docx_files:
        console.print(f"[yellow]No DOCX files found in {input_dir}[/yellow]")
        return
    
    console.print(f"[blue]Found {len(docx_files)} DOCX files:[/blue]")
    for docx_path in docx_files:
        safe_name = create_safe_name(docx_path)
        relative_path = docx_path.relative_to(input_dir)
        console.print(f"  {relative_path} → {safe_name}.zip")


if __name__ == "__main__":
    app()