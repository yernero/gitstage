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
- Audit Logging: Track all CR edits with user and timestamp
- Version History: Keep historical snapshots of CRs
- Diff Preview: Show changes before saving

Editor Support:
- Cross-platform editor integration (Windows/Unix)
- Environment variable support (EDITOR/VISUAL)
- Notepad++ auto-detection on Windows
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
from rich.syntax import Syntax
from pathlib import Path
import os
import re
import json
import platform
import shlex
import subprocess
import tempfile
import difflib
from typing import Optional, Dict, Tuple, List, Set
from functools import lru_cache
from datetime import datetime, timezone

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
    created = datetime.now().strftime("%Y-%m-%d")
    
    # Ensure multiline fields are properly formatted
    def format_multiline(text: str) -> str:
        """Format multiline text with proper line breaks."""
        if text is None or text.strip() == "":
            return "\nNone"  # Add newline before "None"
        return "\n" + "\n".join(line for line in text.splitlines())
    
    content = f"""### CR-{cr_number}: {summary}

**Status**: In Progress  
**Stage**: {stage}  
**Created**: {created}  
**Author**: {author}

**Summary**:  
{format_multiline(summary)}

**Motivation**:  
{format_multiline(motivation)}

**Dependencies**:  
{format_multiline(dependencies)}

**Acceptance Criteria**:  
{format_multiline(acceptance)}

**Notes**:  
{format_multiline(notes or "")}
"""
    
    cr_dir = Path(".gitstage/change_requests")
    cr_dir.mkdir(parents=True, exist_ok=True)
    cr_file = cr_dir / f"CR-{cr_number}.md"
    cr_file.write_text(content, encoding='utf-8')
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
def detect_notepad_plus_plus() -> Optional[str]:
    """
    Auto-detect Notepad++ installation on Windows.
    Returns the full editor command with arguments if found.
    """
    if platform.system() != "Windows":
        return None
        
    known_paths = [
        r"C:\Program Files\Notepad++\notepad++.exe",
        r"C:\Program Files (x86)\Notepad++\notepad++.exe"
    ]
    
    for path in known_paths:
        if os.path.exists(path):
            return f'"{path}" -multiInst -notabbar -nosession -noPlugin -notepadStyleCmdline'
    
    return None

def get_history_dir() -> Path:
    """Get the directory for storing CR history and logs."""
    history_dir = Path(".gitstage/history")
    history_dir.mkdir(parents=True, exist_ok=True)
    return history_dir

def save_cr_version(cr_number: str, content: str) -> str:
    """
    Save a historical version of a CR.
    
    Args:
        cr_number: The CR number
        content: CR content to save
        
    Returns:
        str: The timestamp used for the version
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    version_dir = get_history_dir() / f"CR-{cr_number}"
    version_dir.mkdir(exist_ok=True)
    
    version_file = version_dir / f"{timestamp}.md"
    version_file.write_text(content, encoding='utf-8')
    
    return timestamp

def log_cr_edit(cr_number: str, original: str, edited: str) -> None:
    """
    Log a CR edit to the history file.
    
    Args:
        cr_number: The CR number
        original: Original content
        edited: New content
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    log_file = get_history_dir() / f"CR-{cr_number}.log.json"
    
    # Parse which sections changed
    def get_sections(content: str) -> Set[str]:
        sections = set()
        for line in content.splitlines():
            if line.startswith("**") and "**:" in line:
                section = line[2:line.find("**:")]
                sections.add(section)
        return sections
    
    original_sections = get_sections(original)
    edited_sections = get_sections(edited)
    changed_sections = list(edited_sections - original_sections)
    
    # Create log entry
    log_entry = {
        "timestamp": timestamp,
        "user": get_git_user_name(),
        "cr_id": f"CR-{cr_number}",
        "summary": "Edited CR via gitstage",
        "changes_detected": changed_sections
    }
    
    # Append to log file
    if log_file.exists():
        logs = json.loads(log_file.read_text(encoding='utf-8'))
    else:
        logs = []
    
    logs.append(log_entry)
    log_file.write_text(json.dumps(logs, indent=2), encoding='utf-8')

def show_diff_preview(original: str, edited: str) -> None:
    """
    Show a diff preview of changes using rich formatting.
    
    Args:
        original: Original content
        edited: New content
    """
    diff = list(difflib.unified_diff(
        original.splitlines(),
        edited.splitlines(),
        fromfile="Before Edit",
        tofile="After Edit",
        lineterm=""
    ))
    
    if not diff:
        console.print("[yellow]No changes detected.[/yellow]")
        return
    
    console.print("\n[bold]Changes Preview:[/bold]")
    
    # Format diff with syntax highlighting
    diff_text = "\n".join(diff)
    syntax = Syntax(diff_text, "diff", theme="monokai")
    console.print(syntax)
    console.print()

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
            # Try to detect Notepad++ first on Windows
            editor = detect_notepad_plus_plus()
            
            if not editor:
                if platform.system() == "Windows":
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
    Shows diff preview and maintains edit history.
    
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
                    # Show diff preview
                    show_diff_preview(content, edited_content)
                    
                    # Confirm changes
                    if not Confirm.ask("Do you want to save these changes?"):
                        console.print("[yellow]Changes discarded.[/yellow]")
                        return
                    
                    # Save historical version
                    save_cr_version(cr_number, content)
                    
                    # Save changes
                    if save_cr_changes(cr_number, edited_content):
                        # Log the edit
                        log_cr_edit(cr_number, content, edited_content)
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

@app.command("history")
def show_history(cr_id: str):
    """Show edit history and previous versions of a CR."""
    try:
        require_git_repo()
        cr_number = get_cr_number(cr_id)
        
        # Check history directory
        history_dir = get_history_dir()
        version_dir = history_dir / f"CR-{cr_number}"
        log_file = history_dir / f"CR-{cr_number}.log.json"
        
        if not version_dir.exists() or not log_file.exists():
            console.print(f"[yellow]No history found for CR-{cr_number}[/yellow]")
            return
        
        # Show edit log
        logs = json.loads(log_file.read_text(encoding='utf-8'))
        
        table = Table(title=f"Edit History for CR-{cr_number}")
        table.add_column("Timestamp", style="cyan")
        table.add_column("User", style="green")
        table.add_column("Changes", style="yellow")
        
        for entry in logs:
            table.add_row(
                entry["timestamp"],
                entry["user"],
                ", ".join(entry["changes_detected"]) or "No sections changed"
            )
        
        console.print(table)
        console.print()
        
        # List versions
        versions = sorted(version_dir.glob("*.md"))
        if not versions:
            return
        
        console.print("[bold]Available Versions:[/bold]")
        for i, version in enumerate(versions, 1):
            timestamp = version.stem
            console.print(f"{i}. {timestamp}")
        
        # Allow version selection
        choice = Prompt.ask(
            "\nSelect version to view",
            choices=[str(i) for i in range(1, len(versions) + 1)],
            default="1"
        )
        
        selected = versions[int(choice) - 1]
        content = selected.read_text(encoding='utf-8')
        
        # Show version content
        console.print("\n[bold]Version Content:[/bold]")
        console.print(Markdown(content))
        
        # Offer diff with current
        if Confirm.ask("Show diff with current version?"):
            current = load_cr_file(cr_number)
            if current:
                show_diff_preview(content, current)
        
    except Exception as e:
        console.print(f"[red]❌ Error: {str(e)}[/red]")
        raise typer.Exit(1) 