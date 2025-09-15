#!/usr/bin/env python3
"""
Document to Chapter Markdown Converter

CLI tool to convert DOCX documents into structured Markdown chapters using docling.
"""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from core.model.config import load_config, PipelineConfig
from core.output.hierarchical_writer import export_docx_hierarchy, export_docx_hierarchy_centralized


app = typer.Typer(
    name="doc2chapmd",
    help="Convert DOCX documents to structured Markdown chapters"
)
console = Console()




@app.command()
def config_show(
    config_file: Optional[Path] = typer.Option(
        None,
        "--config", "-c",
        help="Path to configuration file"
    )
):
    """Show current configuration values."""
    try:
        config = load_config(config_file)
        console.print("[blue]Current configuration:[/blue]")
        for field_name, field_info in config.model_fields.items():
            value = getattr(config, field_name)
            description = field_info.description or "No description"
            console.print(f"  {field_name}: {value} ({description})")
    except Exception as e:
        console.print(f"[red]Error loading configuration:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def config_create(
    output_file: Path = typer.Option(
        Path("config.yaml"),
        "--output", "-o", 
        help="Path for new configuration file"
    ),
    force: bool = typer.Option(
        False,
        "--force", "-f",
        help="Overwrite existing configuration file"
    )
):
    """Create a default configuration file."""
    if output_file.exists() and not force:
        console.print(f"[red]Configuration file '{output_file}' already exists. Use --force to overwrite.[/red]")
        raise typer.Exit(1)
    
    try:
        config = PipelineConfig()
        config.to_yaml(output_file)
        console.print(f"[green]✓[/green] Created configuration file: {output_file}")
    except Exception as e:
        console.print(f"[red]Error creating configuration file:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def build(
    docx: Path = typer.Argument(..., help="Path to DOCX file"),
    out: Path = typer.Option(
        Path("out"), "--out", "-o", help="Output directory for chapter hierarchy"
    ),
    centralized_images: bool = typer.Option(
        True, "--centralized-images/--distributed-images", 
        help="Use centralized images structure (one images/ folder) vs distributed (images/ in each section)"
    ),
):
    """Export DOCX into hierarchical chapter structure."""
    if centralized_images:
        written = export_docx_hierarchy_centralized(docx, out)
    else:
        written = export_docx_hierarchy(docx, out)
    for path in written:
        console.print(f"\u2713 {path}")


if __name__ == "__main__":
    app()
