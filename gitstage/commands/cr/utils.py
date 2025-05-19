"""
Shared utilities for CR management.
"""

import os
import re
import json
import platform
import shlex
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict
from functools import lru_cache
from git import Repo
from rich.console import Console
import difflib
from rich.syntax import Syntax

console = Console()

@lru_cache(maxsize=1)
def load_stageflow_config() -> Dict[str, Dict[str, bool]]:
    """Load and cache the stageflow configuration from JSON."""
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
    """Check if a given CR stage is editable according to stageflow config."""
    config = load_stageflow_config()
    stage_config = config.get(stage, {"editable": True})
    return stage_config["editable"]

def get_next_cr_number() -> str:
    """Get the next CR number from .gitstage/next_cr.txt."""
    cr_file = Path(".gitstage/next_cr.txt")
    if not cr_file.exists():
        cr_file.parent.mkdir(parents=True, exist_ok=True)
        cr_file.write_text("0001")
        return "0001"
    
    return cr_file.read_text().strip()

def normalize_cr_id(input_id: str) -> str:
    """Normalize CR ID to standard format (CR-XXXX)."""
    if re.fullmatch(r"\d{4}", input_id):
        return f"CR-{input_id}"
    elif re.fullmatch(r"CR-\d{4}", input_id):
        return input_id
    else:
        raise ValueError("Invalid CR ID format. Use CR-0001 or 0001")

def get_cr_number(cr_id: str) -> str:
    """Extract the 4-digit number from a CR ID."""
    try:
        normalized = normalize_cr_id(cr_id)
        return normalized.split("-")[1]
    except Exception:
        raise ValueError("Invalid CR ID format. Use CR-0001 or 0001")

def get_git_user_name() -> str:
    """Get the Git user name from config."""
    repo = Repo(".")
    try:
        return repo.config_reader().get_value("user", "name")
    except:
        return os.getenv("USER", "Unknown")

def load_cr_file(cr_number: str) -> Optional[str]:
    """Load a CR file from the gitstage/cr-log branch."""
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

def save_cr_changes(cr_number: str, content: str) -> bool:
    """Save changes to a CR file and commit them to the cr-log branch."""
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

def parse_cr_metadata(content: str) -> dict:
    """Parse CR metadata from markdown content."""
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

def detect_notepad_plus_plus() -> Optional[str]:
    """Auto-detect Notepad++ installation on Windows."""
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

def open_editor(file_path: str, editor_override: Optional[str] = None) -> bool:
    """Open a file in the user's preferred editor and wait for it to close."""
    try:
        editor = editor_override or os.environ.get("EDITOR") or os.environ.get("VISUAL")
        
        if not editor:
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
    """Compare original and edited content, ignoring line ending differences."""
    def normalize(text: str) -> str:
        return "\n".join(line.rstrip() for line in text.splitlines()).strip()
    
    return normalize(original) != normalize(edited)

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

def create_cr_file(
    cr_number: str,
    summary: str,
    motivation: str,
    dependencies: str,
    acceptance: str,
    notes: Optional[str] = None
) -> Path:
    """Create a CR markdown file with structured content."""
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

def show_diff_preview(original: str, edited: str) -> None:
    """Show a diff preview of changes using rich formatting."""
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