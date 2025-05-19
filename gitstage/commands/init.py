import typer
from git import Repo, InvalidGitRepositoryError
from rich.console import Console
from rich.panel import Panel
from pathlib import Path
import json
import re

from gitstage.commands.utils import save_stageflow

app = typer.Typer()
console = Console()

def ensure_branch_published(repo: Repo, branch: str):
    """Ensure a branch exists and is published to the remote."""
    try:
        # Check if branch exists on remote
        remote_ref = f"origin/{branch}"
        if remote_ref in repo.references:
            console.print(f"[yellow]ℹ Branch '{branch}' is already published[/yellow]")
            return
        
        # Push branch to remote
        repo.git.push("--set-upstream", "origin", branch)
        console.print(f"[green]✔ Published branch '{branch}' to remote origin[/green]")
    except Exception as e:
        console.print(f"[red]❌ Failed to publish branch '{branch}': {str(e)}[/red]")
        raise

def commit_and_push_config(repo: Repo, branch: str, stages: list[str]):
    """Commit and push the config file to a specific branch."""
    try:
        # Switch to the branch
        repo.git.checkout(branch)
        
        # Ensure config file exists in working directory
        config_path = Path(".gitstage_config.json")
        if not config_path.exists():
            # Save the config file again
            save_stageflow(stages)
            console.print(f"[yellow]ℹ Recreated config file on {branch}[/yellow]")
        
        # Add the config file
        repo.index.add([".gitstage_config.json"])
        
        # Check if there are changes to commit
        if repo.is_dirty():
            # Commit the changes
            repo.index.commit("chore: update .gitstage_config.json")
            console.print(f"[green]✓ Committed config file to {branch}[/green]")
            
            # Push to remote
            repo.git.push("origin", branch)
            console.print(f"[green]✓ Pushed config file to {branch}[/green]")
        else:
            console.print(f"[yellow]ℹ No config changes to commit on {branch}[/yellow]")
            
    except Exception as e:
        console.print(f"[red]❌ Failed to commit/push config to {branch}: {str(e)}[/red]")
        raise

def setup_gitignore(repo: Repo, branch: str):
    """Set up .gitignore to ignore .gitstage/* except config file."""
    try:
        # Switch to the branch
        repo.git.checkout(branch)
        
        # Create or update .gitignore
        gitignore_path = Path(".gitignore")
        gitignore_content = """# GitStage
.gitstage/*
!.gitstage_config.json
"""
        
        # Read existing content if file exists
        existing_content = ""
        if gitignore_path.exists():
            existing_content = gitignore_path.read_text()
        
        # Add GitStage rules if not present
        if "# GitStage" not in existing_content:
            if existing_content and not existing_content.endswith("\n"):
                existing_content += "\n"
            existing_content += gitignore_content
            gitignore_path.write_text(existing_content)
            
            # Stage and commit .gitignore
            repo.index.add([".gitignore"])
            repo.index.commit("chore: add GitStage rules to .gitignore")
            
            # Push if remote exists
            if "origin" in repo.remotes:
                repo.git.push("origin", branch)
            
            console.print(f"[green]✓ Added GitStage rules to .gitignore on {branch}[/green]")
        else:
            console.print(f"[yellow]ℹ GitStage rules already in .gitignore on {branch}[/yellow]")
            
    except Exception as e:
        console.print(f"[red]❌ Failed to set up .gitignore on {branch}: {str(e)}[/red]")
        raise

def setup_cr_infrastructure(repo: Repo):
    """Set up the CR infrastructure in the gitstage/cr-log branch."""
    try:
        # Save current branch
        original_branch = repo.active_branch.name
        
        # Check if CR branch exists
        if "gitstage/cr-log" not in repo.heads:
            # Create orphan branch
            repo.git.checkout("--orphan", "gitstage/cr-log")
            
            # Create CR infrastructure
            cr_dir = Path(".gitstage/change_requests")
            cr_dir.mkdir(parents=True, exist_ok=True)
            
            # Create next_cr.txt with initial value 0001
            next_cr_file = Path(".gitstage/next_cr.txt")
            next_cr_file.write_text("0001")
            
            # Stage and commit CR infrastructure
            repo.index.add([".gitstage/change_requests", ".gitstage/next_cr.txt"])
            repo.index.commit("Initialize GitStage CR log branch")
            
            # Push to remote if it exists
            if "origin" in repo.remotes:
                repo.git.push("--set-upstream", "origin", "gitstage/cr-log")
            
            console.print("[green]✓ Created gitstage/cr-log branch with CR infrastructure[/green]")
        else:
            # Switch to CR branch to ensure files are tracked
            repo.git.checkout("gitstage/cr-log")
            
            # Force add any untracked files
            if Path(".gitstage/next_cr.txt").exists():
                repo.index.add([".gitstage/next_cr.txt"], force=True)
            if Path(".gitstage/change_requests").exists():
                repo.index.add([".gitstage/change_requests"], force=True)
            
            # Commit if there are changes
            if repo.is_dirty():
                repo.index.commit("chore: ensure CR infrastructure is tracked")
                if "origin" in repo.remotes:
                    repo.git.push("origin", "gitstage/cr-log")
                console.print("[green]✓ Ensured CR infrastructure is tracked[/green]")
        
        # Return to original branch
        repo.git.checkout(original_branch)
        console.print(f"[green]✓ Returned to branch:[/] [bold]{original_branch}[/]")
        
    except Exception as e:
        # Try to return to original branch
        try:
            repo.git.checkout(original_branch)
            console.print(f"[green]✓ Returned to branch:[/] [bold]{original_branch}[/]")
        except:
            pass
        console.print(f"[red]❌ Failed to set up CR infrastructure: {str(e)}[/red]")
        raise

def main(
    stages: list[str] = typer.Option(
        ["dev", "testing", "main"],
        "--stages",
        help="List of stages in order (e.g., dev testing main)",
    ),
):
    """Initialize GitStage in the current repository."""
    try:
        # Validate stage names
        for stage in stages:
            if not stage or stage.strip() == "":
                raise typer.BadParameter(f"Invalid stage name '{stage}': must not be empty or whitespace.")
            if stage.startswith("-"):
                raise typer.BadParameter(f"Invalid stage name '{stage}': must not start with a dash.")
            if not re.fullmatch(r"^[A-Za-z0-9._/-]+$", stage):
                raise typer.BadParameter(f"Invalid stage name '{stage}': must only contain letters, numbers, dots, underscores, dashes, or slashes.")
        # Try to get existing repo or initialize new one
        try:
            repo = Repo('.', search_parent_directories=True)
            console.print("[green]✓ Found existing Git repository[/green]")
        except InvalidGitRepositoryError:
            repo = Repo.init('.')
            console.print("[green]✓ Initialized new Git repository[/green]")
        
        # Save original branch
        original_branch = repo.active_branch.name
        
        # Ensure remote exists
        if not repo.remotes:
            console.print("[yellow]⚠ No remote found. Creating 'origin'...[/yellow]")
            repo.create_remote('origin', repo.working_dir)
        
        # Create and publish branches
        for stage in stages:
            # Create branch if it doesn't exist
            if stage not in repo.heads:
                repo.create_head(stage)
                console.print(f"[green]✓ Created branch: {stage}[/green]")
            else:
                console.print(f"[yellow]ℹ Branch already exists: {stage}[/yellow]")
            
            # Ensure branch is published
            ensure_branch_published(repo, stage)
            
            # Set up .gitignore for mainline branches
            setup_gitignore(repo, stage)
        
        # Save stageflow configuration
        save_stageflow(stages)
        console.print("[green]✓ Saved stageflow configuration[/green]")
        
        # Commit and push config to all branches
        for stage in stages:
            commit_and_push_config(repo, stage, stages)
        
        # Set up CR infrastructure
        setup_cr_infrastructure(repo)
        
        # Return to original branch
        repo.git.checkout(original_branch)
        console.print(f"[green]✓ Returned to branch:[/] [bold]{original_branch}[/]")
        
        # Show summary
        summary = Panel(
            f"GitStage initialized successfully!\n\n"
            f"Stages: {' → '.join(stages)}\n"
            f"Config: .gitstage_config.json\n"
            f"CR Log: gitstage/cr-log branch\n"
            f".gitignore: Updated on all branches\n\n"
            f"Config file has been committed and pushed to all branches.",
            title="🎉 Success",
            border_style="green"
        )
        console.print(summary)
        
    except Exception as e:
        # Try to return to original branch
        try:
            repo.git.checkout(original_branch)
            console.print(f"[green]✓ Returned to branch:[/] [bold]{original_branch}[/]")
        except:
            pass
        console.print(f"[red]❌ Error: {str(e)}[/red]")
        raise typer.Exit(1) 