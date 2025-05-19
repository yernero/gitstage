"""
Change Request (CR) Management Package

This package provides functionality for managing Change Requests (CRs) in the GitStage system.
It handles CR creation, editing, viewing, and listing, with proper stage management and 
editor integration.

Features:
- CR Creation: Create new CRs with structured markdown format
- CR Editing: Edit CRs with stage-based permissions
- CR Viewing: View formatted CR content
- CR Listing: List all CRs with their metadata
- Stage Management: Prevent editing of CRs in terminal stages
- Audit Logging: Track all CR edits with user and timestamp
- Version History: Keep historical snapshots of CRs
- Diff Preview: Show changes before saving

Editor Support:
- Cross-platform editor integration (Windows/Unix)
- Environment variable support (EDITOR/VISUAL)
- Notepad++ auto-detection on Windows
- Proper handling of multiline content
"""

import typer
from pathlib import Path
from typing import Optional
from datetime import datetime
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from git import Repo
import json

from gitstage.commands.utils import require_git_repo
from .edit import app as edit_app
from .utils import (
    get_next_cr_number,
    normalize_cr_id,
    get_cr_number,
    get_git_user_name,
    load_cr_file,
    save_cr_changes,
    parse_cr_metadata,
    setup_cr_branch,
    save_cr_to_branch,
    create_cr_file
)

# Create the main CR command group
app = typer.Typer(help="Manage Change Requests (CRs)")
console = Console()

# Register subcommands
app.add_typer(edit_app, name="edit")

@app.command()
def add(
    summary: str = typer.Option(None, "--summary", "-s", help="CR summary"),
    motivation: str = typer.Option(None, "--motivation", "-m", help="CR motivation"),
    dependencies: str = typer.Option(None, "--dependencies", "-d", help="CR dependencies"),
    acceptance: str = typer.Option(None, "--acceptance", "-a", help="CR acceptance criteria"),
    notes: str = typer.Option(None, "--notes", "-n", help="Additional notes")
):
    """Create a new Change Request."""
    try:
        # Set up CR branch if needed
        repo = Repo(".")
        setup_cr_branch(repo)
        
        # Get next CR number
        cr_number = get_next_cr_number()
        
        # If no arguments provided, prompt interactively
        if not any([summary, motivation, dependencies, acceptance, notes]):
            console.print("\n[bold]Create New Change Request[/bold]")
            summary = Prompt.ask("Summary")
            motivation = Prompt.ask("Motivation")
            dependencies = Prompt.ask("Dependencies")
            acceptance = Prompt.ask("Acceptance Criteria")
            notes = Prompt.ask("Notes (optional)", default="")
        
        # Create CR file
        cr_file = create_cr_file(
            cr_number=cr_number,
            summary=summary,
            motivation=motivation,
            dependencies=dependencies,
            acceptance=acceptance,
            notes=notes
        )
        
        # Save to CR branch
        save_cr_to_branch(cr_file, summary, cr_number)
        
        console.print(f"\n[green]✓ Created CR-{cr_number}[/green]")
        console.print(f"[dim]View with: gitstage cr show {cr_number}[/dim]")
        
    except Exception as e:
        console.print(f"[red]❌ Failed to create CR: {str(e)}[/red]")
        raise typer.Exit(1)

@app.command()
def show(cr_id: str):
    """Show a Change Request."""
    try:
        cr_number = get_cr_number(cr_id)
        content = load_cr_file(cr_number)
        
        if content:
            console.print(Panel(Markdown(content), title=f"CR-{cr_number}"))
        else:
            raise typer.Exit(1)
            
    except Exception as e:
        console.print(f"[red]❌ Failed to show CR: {str(e)}[/red]")
        raise typer.Exit(1)

@app.command(name="list")
def list_crs():
    """List all Change Requests."""
    try:
        repo = Repo(".")
        original_branch = repo.active_branch.name
        
        try:
            repo.git.checkout("gitstage/cr-log")
            cr_dir = Path(".gitstage/change_requests")
            
            if not cr_dir.exists():
                console.print("[yellow]No CRs found.[/yellow]")
                return
            
            table = Table(title="Change Requests", show_header=True, header_style="bold")
            table.add_column("CR", style="cyan", justify="left")
            table.add_column("Summary")
            table.add_column("Stage", style="blue")
            table.add_column("Status")
            table.add_column("Created", style="yellow")
            table.add_column("Author", style="magenta")
            
            status_colors = {
                "In Progress": "green",
                "Testing": "yellow",
                "Main Review": "magenta",
                "Complete": "red"
            }
            
            for cr_file in sorted(cr_dir.glob("CR-*.md")):
                content = cr_file.read_text()
                metadata = parse_cr_metadata(content)
                cr_id = f"[link=file://{cr_file}][blue underline]CR-{metadata['number']}[/blue underline][/link]"
                stage = f"[blue]{metadata['stage']}[/blue]"
                status = metadata["status"]
                status_color = status_colors.get(status, "white")
                status_str = f"[{status_color}]{status}[/{status_color}]"
                created = f"[yellow]{metadata['created']}[/yellow]"
                author = f"[magenta]{metadata['author']}[/magenta]"
                table.add_row(
                    cr_id,
                    metadata["summary"],
                    stage,
                    status_str,
                    created,
                    author
                )
            
            console.print(table)
            
        finally:
            repo.git.checkout(original_branch)
            
    except Exception as e:
        console.print(f"[red]❌ Failed to list CRs: {str(e)}[/red]")
        raise typer.Exit(1)

@app.command()
def history(cr_id: str):
    """Show edit history for a Change Request."""
    try:
        cr_number = get_cr_number(cr_id)
        repo = Repo(".")
        
        # Get commit history for the CR file
        commits = list(repo.iter_commits(
            "gitstage/cr-log",
            paths=[f".gitstage/change_requests/CR-{cr_number}.md"]
        ))
        
        if not commits:
            console.print(f"[yellow]No history found for CR-{cr_number}[/yellow]")
            return
        
        table = Table(show_header=True, header_style="bold")
        table.add_column("Version")
        table.add_column("Date")
        table.add_column("Author")
        table.add_column("Message")
        
        for i, commit in enumerate(commits):
            table.add_row(
                f"v{i+1}",
                datetime.fromtimestamp(commit.committed_date).strftime("%Y-%m-%d %H:%M"),
                commit.author.name,
                commit.message.split("\n")[0]
            )
        
        console.print(table)
        
        # Ask if user wants to see a specific version
        version = Prompt.ask(
            "\nEnter version number to view (or press Enter to exit)",
            default=""
        )
        
        if version:
            try:
                version_num = int(version)
                if 1 <= version_num <= len(commits):
                    commit = commits[version_num - 1]
                    content = commit.tree[f".gitstage/change_requests/CR-{cr_number}.md"].data_stream.read().decode()
                    console.print(Panel(Markdown(content), title=f"CR-{cr_number} (v{version_num})"))
                else:
                    console.print("[red]❌ Invalid version number[/red]")
            except ValueError:
                console.print("[red]❌ Invalid version number[/red]")
        
    except Exception as e:
        console.print(f"[red]❌ Failed to show CR history: {str(e)}[/red]")
        raise typer.Exit(1)

# Re-export commonly used functions
__all__ = [
    "app",
    "get_next_cr_number",
    "normalize_cr_id",
    "get_cr_number",
    "load_cr_file",
    "save_cr_changes",
    "parse_cr_metadata"
] 