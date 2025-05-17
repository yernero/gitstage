import typer
from git import Repo, InvalidGitRepositoryError
from rich.console import Console
from rich.panel import Panel
from pathlib import Path
import json

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

def main(
    stages: list[str] = typer.Option(
        ["dev", "testing", "main"],
        "--stages",
        help="List of stages in order (e.g., dev testing main)",
    ),
):
    """Initialize GitStage in the current repository."""
    try:
        # Try to get existing repo or initialize new one
        try:
            repo = Repo('.', search_parent_directories=True)
            console.print("[green]✓ Found existing Git repository[/green]")
        except InvalidGitRepositoryError:
            repo = Repo.init('.')
            console.print("[green]✓ Initialized new Git repository[/green]")
        
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
        
        # Save stageflow configuration
        save_stageflow(stages)
        console.print("[green]✓ Saved stageflow configuration[/green]")
        
        # Commit and push config to all branches
        current_branch = repo.active_branch.name
        for stage in stages:
            commit_and_push_config(repo, stage, stages)
        
        # Return to original branch
        repo.git.checkout(current_branch)
        
        # Show summary
        summary = Panel(
            f"GitStage initialized successfully!\n\n"
            f"Stages: {' → '.join(stages)}\n"
            f"Config: .gitstage_config.json\n\n"
            f"Config file has been committed and pushed to all branches.",
            title="🎉 Success",
            border_style="green"
        )
        console.print(summary)
        
    except Exception as e:
        console.print(f"[red]❌ Error: {str(e)}[/red]")
        raise typer.Exit(1) 