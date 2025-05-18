"""
Change Request (CR) Management Module

This module provides functionality for managing Change Requests (CRs) in the GitStage system.
It handles CR creation, editing, viewing, and listing, with proper stage management and 
editor integration.

Features:
- CR Creation: Create new CRs with structured markdown format
- CR Editing: Edit CRs with stage-based permissions
- CR Viewing: View formatted CR content
- CR Listing: List all CRs with their metadata
- Stage Management: Prevent editing of CRs in terminal stages

Editor Support:
- Cross-platform editor integration (Windows/Unix)
- Environment variable support (EDITOR/VISUAL)
- Notepad++ integration on Windows
- UTF-8 encoding handling
- Temporary file management

Completed Tasks:
✓ Basic CR creation with markdown structure
✓ CR number management and incrementation
✓ CR branch management (gitstage/cr-log)
✓ Stage-based editing permissions
✓ Cross-platform editor support
✓ Proper encoding handling
✓ Temporary file management
✓ CR listing with rich formatting
✓ CR viewing with markdown rendering
✓ Editor override support
✓ Notepad++ integration
✓ Error handling and user feedback
✓ Branch state preservation
✓ Content change detection

Todo:
- Add CR deletion command
- Add CR stage transition command
- Add CR search functionality
- Add CR export functionality
- Add CR template customization
- Add CR validation rules
- Add CR review workflow
- Add CR statistics
"""

import typer
from git import Repo
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from pathlib import Path
import datetime
import os
import re
import json
import platform
import shlex
import subprocess
import tempfile
from typing import Optional, Dict, Tuple
from functools import lru_cache

from gitstage.commands.utils import require_git_repo

app = typer.Typer()
console = Console()

# CR Management Functions
def get_next_cr_number() -> str:
    """
    Get the next CR number from .gitstage/next_cr.txt.
    Ensures proper number formatting and incrementation.
    
    Returns:
        str: Next available CR number in 4-digit format (e.g., "0001")
    """
    cr_file = Path(".gitstage/next_cr.txt")
    if not cr_file.exists():
        cr_file.parent.mkdir(parents=True, exist_ok=True)
        cr_file.write_text("0001")
        return "0001"
    
    return cr_file.read_text().strip()

def normalize_cr_id(input_id: str) -> str:
    """
    Normalize CR ID to standard format (CR-XXXX).
    Accepts both XXXX and CR-XXXX formats.
    
    Args:
        input_id: CR ID in either XXXX or CR-XXXX format
        
    Returns:
        str: Normalized CR ID in CR-XXXX format
        
    Raises:
        ValueError: If input_id format is invalid
    """
    if re.fullmatch(r"\d{4}", input_id):
        return f"CR-{input_id}"
    elif re.fullmatch(r"CR-\d{4}", input_id):
        return input_id
    else:
        raise ValueError("Invalid CR ID format. Use CR-0001 or 0001")

def get_cr_number(cr_id: str) -> str:
    """
    Extract the 4-digit number from a CR ID.
    Handles both XXXX and CR-XXXX formats.
    
    Args:
        cr_id: CR ID in either XXXX or CR-XXXX format
        
    Returns:
        str: 4-digit CR number
        
    Raises:
        ValueError: If cr_id format is invalid
    """
    try:
        normalized = normalize_cr_id(cr_id)
        return normalized.split("-")[1]
    except Exception:
        raise ValueError("Invalid CR ID format. Use CR-0001 or 0001")

def get_git_user_name() -> str:
    """
    Get the Git user name from config.
    Falls back to system user if Git config is not available.
    
    Returns:
        str: Git user name or system username
    """
    repo = Repo(".")
    try:
        return repo.config_reader().get_value("user", "name")
    except:
        return os.getenv("USER", "Unknown")

# CR Content Management
def create_cr_file(
    cr_number: str,
    summary: str,
    motivation: str,
    dependencies: str,
    acceptance: str,
    notes: Optional[str] = None
) -> Path:
    """
    Create a CR markdown file with structured content.
    
    Args:
        cr_number: The CR number (e.g., "0001")
        summary: Brief description of the change
        motivation: Reason for the change
        dependencies: Required dependencies
        acceptance: Acceptance criteria
        notes: Optional additional notes
        
    Returns:
        Path: Path to the created CR file
    """
    author = get_git_user_name()
    stage = Repo(".").active_branch.name
    created = datetime.datetime.now().strftime("%Y-%m-%d")
    
    content = f"""### CR-{cr_number}: {summary}

**Status**: In Progress  
**Stage**: {stage}  
**Created**: {created}  
**Author**: {author}

**Summary**:  
{summary}

**Motivation**:  
{motivation}

**Dependencies**:  
{dependencies}

**Acceptance Criteria**:  
{acceptance}

**Notes**:  
{notes or "None"}
"""
    
    cr_dir = Path(".gitstage/change_requests")
    cr_dir.mkdir(parents=True, exist_ok=True)
    cr_file = cr_dir / f"CR-{cr_number}.md"
    cr_file.write_text(content)
    return cr_file

def load_cr_file(cr_number: str) -> Optional[str]:
    """
    Load a CR file from the gitstage/cr-log branch.
    Handles branch switching and file reading.
    
    Args:
        cr_number: The CR number to load
        
    Returns:
        Optional[str]: CR content if found, None otherwise
    """
    repo = Repo(".")
    original_branch = repo.active_branch.name
    
    try:
        repo.git.checkout("gitstage/cr-log")
        cr_file = Path(f".gitstage/change_requests/CR-{cr_number}.md")
        
        if not cr_file.exists():
            console.print(f"[red]❌ CR-{cr_number} not found[/red]")
            return None
        
        return cr_file.read_text()
        
    except Exception as e:
        console.print(f"[red]❌ Failed to load CR: {str(e)}[/red]")
        return None
    finally:
        repo.git.checkout(original_branch)

def parse_cr_metadata(content: str) -> dict:
    """
    Parse CR metadata from markdown content.
    Extracts number, summary, status, stage, created date, and author.
    
    Args:
        content: CR markdown content
        
    Returns:
        dict: Parsed metadata fields
    """
    metadata = {
        "number": "",
        "summary": "",
        "status": "",
        "stage": "",
        "created": "",
        "author": ""
    }
    
    header_match = re.match(r"### CR-(\d+): (.*)", content.split("\n")[0])
    if header_match:
        metadata["number"] = header_match.group(1)
        metadata["summary"] = header_match.group(2)
    
    for line in content.split("\n"):
        if "**Status**:" in line:
            metadata["status"] = line.split(":", 1)[1].strip()
        elif "**Stage**:" in line:
            metadata["stage"] = line.split(":", 1)[1].strip()
        elif "**Created**:" in line:
            metadata["created"] = line.split(":", 1)[1].strip()
        elif "**Author**:" in line:
            metadata["author"] = line.split(":", 1)[1].strip()
    
    return metadata

# Stage Management
@lru_cache(maxsize=1)
def load_stageflow_config() -> Dict[str, Dict[str, bool]]:
    """
    Load and cache the stageflow configuration from JSON.
    Developers can customize CR stage rules by modifying gitstage/config/stageflow.json.
    
    Returns:
        Dict: Stage names mapped to their configuration
    """
    try:
        config_path = Path("gitstage/config/stageflow.json")
        if config_path.exists():
            with open(config_path) as f:
                return json.load(f)
    except Exception as e:
        console.print(f"[yellow]⚠ Failed to load stageflow config: {str(e)}[/yellow]")
    
    return {
        "In Progress": {"editable": True},
        "Testing": {"editable": True},
        "Main Review": {"editable": True},
        "Complete": {"editable": False}
    }

def is_stage_editable(stage: str) -> bool:
    """
    Check if a given CR stage is editable according to stageflow config.
    
    Args:
        stage: The stage name to check
        
    Returns:
        bool: True if the stage is editable
    """
    config = load_stageflow_config()
    stage_config = config.get(stage, {"editable": True})
    return stage_config["editable"]

# Editor Integration
def open_editor(file_path: str, editor_override: Optional[str] = None) -> bool:
    """
    Open a file in the user's preferred editor and wait for it to close.
    Supports multiple editors and platforms with proper argument handling.
    
    Args:
        file_path: Path to the file to edit
        editor_override: Optional editor command to override defaults
        
    Returns:
        bool: True if editing was successful
        
    Raises:
        RuntimeError: If editor launch fails
    """
    try:
        editor = editor_override or os.environ.get("EDITOR") or os.environ.get("VISUAL")
        
        if not editor:
            if platform.system() == "Windows":
                npp_paths = [
                    r"C:\Program Files\Notepad++\notepad++.exe",
                    r"C:\Program Files (x86)\Notepad++\notepad++.exe"
                ]
                for npp in npp_paths:
                    if os.path.exists(npp):
                        editor = f'"{npp}" -multiInst -notabbar -nosession -noPlugin -notepadStyleCmdline'
                        break
                if not editor:
                    editor = "notepad"
            else:
                for ed in ["nano", "vim", "vi"]:
                    if subprocess.run(["which", ed], capture_output=True).returncode == 0:
                        editor = ed
                        break
                if not editor:
                    raise RuntimeError("No suitable editor found. Please set EDITOR environment variable.")
        
        if platform.system() == "Windows":
            if editor.startswith('"') and '"' in editor[1:]:
                path_end = editor.find('"', 1)
                editor_path = editor[1:path_end]
                editor_args = shlex.split(editor[path_end + 1:])
                args = [editor_path, *editor_args, file_path]
            else:
                args = [*shlex.split(editor), file_path]
        else:
            args = [*shlex.split(editor), file_path]
        
        result = subprocess.run(args)
        return result.returncode == 0
        
    except Exception as e:
        raise RuntimeError(f"Failed to launch editor: {str(e)}")

def has_content_changed(original: str, edited: str) -> bool:
    """
    Compare original and edited content, ignoring line ending differences.
    
    Args:
        original: Original content
        edited: Edited content
        
    Returns:
        bool: True if content has meaningful changes
    """
    def normalize(text: str) -> str:
        return "\n".join(line.rstrip() for line in text.splitlines()).strip()
    
    return normalize(original) != normalize(edited)

# Git Operations
def save_cr_changes(cr_number: str, content: str) -> bool:
    """
    Save changes to a CR file and commit them to the cr-log branch.
    
    Args:
        cr_number: The CR number to update
        content: New content to save
        
    Returns:
        bool: True if save was successful
    """
    repo = Repo(".")
    original_branch = repo.active_branch.name
    
    try:
        repo.git.checkout("gitstage/cr-log")
        cr_file = Path(f".gitstage/change_requests/CR-{cr_number}.md")
        cr_file.write_text(content)
        
        repo.index.add([str(cr_file)])
        repo.index.commit(f"Update CR-{cr_number}")
        
        if "origin" in repo.remotes:
            repo.git.push("origin", "gitstage/cr-log")
        
        return True
        
    except Exception as e:
        console.print(f"[red]❌ Failed to save CR changes: {str(e)}[/red]")
        return False
    finally:
        repo.git.checkout(original_branch)

# CLI Commands
@app.command("edit")
def edit_cr(
    cr_id: str,
    editor: Optional[str] = typer.Option(None, "--editor", "-e", help="Override default editor")
):
    """
    Edit a Change Request if its current stage allows editing.
    
    The CR must not be in a terminal stage (e.g., "Complete") as defined in stageflow.json.
    Supports multiple editors and platforms, with proper UTF-8 encoding handling.
    
    Args:
        cr_id: CR identifier (XXXX or CR-XXXX format)
        editor: Optional editor command to override defaults
    """
    try:
        require_git_repo()
        
        try:
            cr_number = get_cr_number(cr_id)
        except ValueError as e:
            console.print(f"[red]❌ {str(e)}[/red]")
            raise typer.Exit(1)
        
        content = load_cr_file(cr_number)
        if not content:
            console.print(f"[red]❌ CR-{cr_number} not found[/red]")
            raise typer.Exit(1)
        
        metadata = parse_cr_metadata(content)
        current_stage = metadata["stage"]
        
        if not is_stage_editable(current_stage):
            console.print(f"[red]❌ Cannot edit CR-{cr_number}: Stage '{current_stage}' is not editable[/red]")
            console.print("[yellow]ℹ Tip: Check gitstage/config/stageflow.json for stage rules[/yellow]")
            raise typer.Exit(1)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', encoding='utf-8', delete=False) as temp:
            temp_path = temp.name
            temp.write(content)
        
        try:
            if open_editor(temp_path, editor):
                with open(temp_path, 'r', encoding='utf-8') as temp:
                    edited_content = temp.read()
                
                if has_content_changed(content, edited_content):
                    if save_cr_changes(cr_number, edited_content):
                        console.print(f"[green]✓ Successfully updated CR-{cr_number}[/green]")
                    else:
                        console.print(f"[red]❌ Failed to save changes to CR-{cr_number}[/red]")
                        raise typer.Exit(1)
                else:
                    console.print("[yellow]ℹ No changes made[/yellow]")
            else:
                console.print("[yellow]ℹ Edit cancelled or editor failed[/yellow]")
                raise typer.Exit(1)
            
        finally:
            try:
                os.unlink(temp_path)
            except:
                pass
        
    except Exception as e:
        console.print(f"[red]❌ Error: {str(e)}[/red]")
        raise typer.Exit(1)

@app.command("show")
def show_cr(cr_id: str):
    """Print out a formatted markdown preview of a single CR."""
    try:
        require_git_repo()
        
        try:
            cr_number = get_cr_number(cr_id)
        except ValueError as e:
            console.print(f"[red]❌ {str(e)}[/red]")
            raise typer.Exit(1)
        
        content = load_cr_file(cr_number)
        if not content:
            raise typer.Exit(1)
        
        console.print("\n")
        console.print(Markdown(content))
        console.print("\n")
        
    except Exception as e:
        console.print(f"[red]❌ Error: {str(e)}[/red]")
        raise typer.Exit(1)

@app.command("list")
def list_crs():
    """Display a table of all CRs with summary, stage, and status."""
    try:
        require_git_repo()
        repo = Repo(".")
        original_branch = repo.active_branch.name
        
        try:
            repo.git.checkout("gitstage/cr-log")
            
            table = Table(title="Change Requests")
            table.add_column("CR", style="cyan")
            table.add_column("Summary")
            table.add_column("Stage", style="blue")
            table.add_column("Status", style="green")
            table.add_column("Created", style="yellow")
            table.add_column("Author", style="magenta")
            
            cr_dir = Path(".gitstage/change_requests")
            if not cr_dir.exists():
                console.print("[yellow]No CRs found[/yellow]")
                return
            
            cr_files = sorted(cr_dir.glob("CR-*.md"))
            
            for cr_file in cr_files:
                content = cr_file.read_text()
                metadata = parse_cr_metadata(content)
                
                table.add_row(
                    f"CR-{metadata['number']}",
                    metadata['summary'],
                    metadata['stage'],
                    metadata['status'],
                    metadata['created'],
                    metadata['author']
                )
            
            console.print(table)
            
        finally:
            repo.git.checkout(original_branch)
            
    except Exception as e:
        console.print(f"[red]❌ Error: {str(e)}[/red]")
        raise typer.Exit(1)

@app.command("add")
def add(
    summary: Optional[str] = typer.Option(None, help="Summary of the change request"),
    motivation: Optional[str] = typer.Option(None, help="Motivation for the change"),
    dependencies: Optional[str] = typer.Option(None, help="Dependencies required"),
    acceptance: Optional[str] = typer.Option(None, help="Acceptance criteria"),
    notes: Optional[str] = typer.Option(None, help="Additional notes"),
):
    """Create a new Change Request (CR) file."""
    try:
        # Verify Git repository
        require_git_repo()
        
        # Set up CR branch if needed
        repo = Repo(".")
        setup_cr_branch(repo)
        
        # Get CR number
        cr_number = get_next_cr_number()
        
        # Interactive mode if no arguments provided
        if not summary:
            console.print("\n[bold cyan]📝 Creating new Change Request[/bold cyan]")
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
        
        # Show preview
        console.print("\n[bold]Preview:[/bold]")
        console.print(Panel(cr_file.read_text(), title=f"CR-{cr_number}"))
        
        # Confirm
        if Confirm.ask("\nSave this Change Request?"):
            save_cr_to_branch(cr_file, summary, cr_number)
            console.print(f"[green]✓ Created CR-{cr_number}[/green]")
        else:
            console.print("[yellow]⚠ CR creation cancelled[/yellow]")
            raise typer.Exit(0)
            
    except Exception as e:
        console.print(f"[red]❌ Error: {str(e)}[/red]")
        raise typer.Exit(1)

def setup_cr_branch(repo: Repo) -> None:
    """Set up the gitstage/cr-log branch if it doesn't exist."""
    try:
        # Check if branch exists
        if "gitstage/cr-log" not in repo.heads:
            # Create orphan branch
            repo.git.checkout("--orphan", "gitstage/cr-log")
            
            # Create initial structure
            Path(".gitstage/change_requests").mkdir(parents=True, exist_ok=True)
            Path(".gitstage/next_cr.txt").write_text("0001")
            
            # Initial commit
            repo.index.add([".gitstage"])
            repo.index.commit("Initialize GitStage CR log branch")
            
            # Push to remote if it exists
            if "origin" in repo.remotes:
                repo.git.push("--set-upstream", "origin", "gitstage/cr-log")
            
            console.print("[green]✓ Created gitstage/cr-log branch[/green]")
    except Exception as e:
        console.print(f"[red]❌ Failed to set up CR branch: {str(e)}[/red]")
        raise

def save_cr_to_branch(cr_file: Path, summary: str, cr_number: str) -> None:
    """Save the CR file to the gitstage/cr-log branch."""
    repo = Repo(".")
    original_branch = repo.active_branch.name
    
    try:
        # Switch to CR branch
        repo.git.checkout("gitstage/cr-log")
        
        # Ensure directory exists
        cr_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Write CR file
        cr_file.write_text(cr_file.read_text())
        
        # Update next_cr.txt with incremented number
        next_cr_file = Path(".gitstage/next_cr.txt")
        next_cr_file.write_text(f"{int(cr_number) + 1:04d}")
        
        # Stage both files
        repo.index.add([str(cr_file), ".gitstage/next_cr.txt"])
        
        # Commit both files together
        repo.index.commit(f"Add CR-{cr_number}: {summary}")
        
        # Push if remote exists
        if "origin" in repo.remotes:
            repo.git.push("origin", "gitstage/cr-log")
        
        console.print(f"[green]✓ Saved CR to gitstage/cr-log branch[/green]")
        
    except Exception as e:
        console.print(f"[red]❌ Failed to save CR to branch: {str(e)}[/red]")
        raise
    finally:
        # Always return to original branch
        try:
            repo.git.checkout(original_branch)
            console.print(f"[green]✓ Returned to branch:[/] [bold]{original_branch}[/]")
        except Exception as e:
            console.print(f"[red]❌ Failed to return to original branch: {str(e)}[/red]")
            raise 