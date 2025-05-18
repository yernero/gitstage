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
from typing import Optional

from gitstage.commands.utils import require_git_repo

app = typer.Typer()
console = Console()

def get_next_cr_number() -> str:
    """Get the next CR number from .gitstage/next_cr.txt."""
    cr_file = Path(".gitstage/next_cr.txt")
    if not cr_file.exists():
        cr_file.parent.mkdir(parents=True, exist_ok=True)
        cr_file.write_text("0001")
        return "0001"
    
    return cr_file.read_text().strip()

def get_git_user_name() -> str:
    """Get the Git user name from config."""
    repo = Repo(".")
    try:
        return repo.config_reader().get_value("user", "name")
    except:
        return os.getenv("USER", "Unknown")

def create_cr_file(
    cr_number: str,
    summary: str,
    motivation: str,
    dependencies: str,
    acceptance: str,
    notes: Optional[str] = None
) -> Path:
    """Create a CR markdown file with the given content."""
    # Get metadata
    author = get_git_user_name()
    stage = Repo(".").active_branch.name
    created = datetime.datetime.now().strftime("%Y-%m-%d")
    
    # Create content
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
    
    # Create file
    cr_dir = Path(".gitstage/change_requests")
    cr_dir.mkdir(parents=True, exist_ok=True)
    cr_file = cr_dir / f"CR-{cr_number}.md"
    cr_file.write_text(content)
    return cr_file

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

def load_cr_file(cr_number: str) -> Optional[str]:
    """Load a CR file from the gitstage/cr-log branch."""
    repo = Repo(".")
    original_branch = repo.active_branch.name
    
    try:
        # Switch to CR branch
        repo.git.checkout("gitstage/cr-log")
        
        # Check if file exists
        cr_file = Path(f".gitstage/change_requests/CR-{cr_number}.md")
        if not cr_file.exists():
            console.print(f"[red]❌ CR-{cr_number} not found[/red]")
            return None
        
        # Read content
        content = cr_file.read_text()
        return content
        
    except Exception as e:
        console.print(f"[red]❌ Failed to load CR: {str(e)}[/red]")
        return None
    finally:
        # Return to original branch
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
    
    # Parse header line for number and summary
    header_match = re.match(r"### CR-(\d+): (.*)", content.split("\n")[0])
    if header_match:
        metadata["number"] = header_match.group(1)
        metadata["summary"] = header_match.group(2)
    
    # Parse metadata section
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

@app.command("list")
def list_crs():
    """Display a table of all CRs with summary, stage, and status."""
    try:
        require_git_repo()
        repo = Repo(".")
        original_branch = repo.active_branch.name
        
        try:
            # Switch to CR branch
            repo.git.checkout("gitstage/cr-log")
            
            # Create table
            table = Table(title="Change Requests")
            table.add_column("CR", style="cyan")
            table.add_column("Summary")
            table.add_column("Stage", style="blue")
            table.add_column("Status", style="green")
            table.add_column("Created", style="yellow")
            table.add_column("Author", style="magenta")
            
            # Get all CR files
            cr_dir = Path(".gitstage/change_requests")
            if not cr_dir.exists():
                console.print("[yellow]No CRs found[/yellow]")
                return
            
            # Sort CR files by number
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
            # Return to original branch
            repo.git.checkout(original_branch)
            
    except Exception as e:
        console.print(f"[red]❌ Error: {str(e)}[/red]")
        raise typer.Exit(1)

@app.command("show")
def show_cr(cr_id: str):
    """Print out a formatted markdown preview of a single CR."""
    try:
        require_git_repo()
        
        # Extract CR number
        match = re.match(r"CR-?(\d+)", cr_id)
        if not match:
            console.print("[red]❌ Invalid CR ID format. Use CR-XXXX or XXXX[/red]")
            raise typer.Exit(1)
        
        cr_number = match.group(1)
        
        # Load CR content
        content = load_cr_file(cr_number)
        if not content:
            raise typer.Exit(1)
        
        # Display formatted markdown
        console.print("\n")
        console.print(Markdown(content))
        console.print("\n")
        
    except Exception as e:
        console.print(f"[red]❌ Error: {str(e)}[/red]")
        raise typer.Exit(1) 