import typer
from git import Repo
from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.panel import Panel
from typing import Optional

from gitstage.commands.utils import require_git_repo, get_stageflow

console = Console()

def get_previous_stage(current_stage: str) -> Optional[str]:
    """Get the previous stage in the stageflow before the current stage."""
    stages = get_stageflow()
    try:
        current_index = stages.index(current_stage)
        if current_index > 0:
            return stages[current_index - 1]
    except ValueError:
        pass
    return None

def show_branch_diff(repo: Repo, branch_from: str, branch_to: str) -> None:
    """Show the difference between branches."""
    try:
        # Get commits that are in branch_to but not in origin/branch_from
        commits = list(repo.iter_commits(f"origin/{branch_from}..{branch_to}"))
        
        if commits:
            console.print(f"\n[bold yellow]⚠️ The following commits will be removed from {branch_to}:[/bold yellow]")
            for commit in commits:
                console.print(f"  [yellow]- {commit.hexsha[:7]} {commit.message.splitlines()[0]}[/yellow]")
        else:
            console.print(f"\n[green]✓ No commits to remove - {branch_to} is already in sync with origin/{branch_from}[/green]")
            
    except Exception as e:
        console.print(f"[red]❌ Error showing branch diff: {str(e)}[/red]")

def main(
    branch_to: str = typer.Option(None, help="Destination branch to clean (default: testing)"),
    branch_from: str = typer.Option(None, help="Source branch to match (default: previous in stageflow)"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompts"),
):
    """Reset a branch to match its source branch, removing any extra commits."""
    try:
        # Verify Git repository
        require_git_repo()
        
        # Get the current repository
        repo = Repo(".")
        
        # Determine destination and source branches
        if not branch_to:
            branch_to = "testing"
            console.print(f"[green]✓ Using default destination branch: {branch_to}[/green]")
        
        if not branch_from:
            branch_from = get_previous_stage(branch_to)
            if not branch_from:
                console.print("[red]❌ No previous stage found in stageflow![/red]")
                raise typer.Exit(1)
            console.print(f"[green]✓ Using previous stage as source: {branch_from}[/green]")
        
        # Ensure branches exist
        if branch_from not in repo.heads:
            console.print(f"[red]❌ Source branch '{branch_from}' does not exist![/red]")
            raise typer.Exit(1)
        if branch_to not in repo.heads:
            console.print(f"[red]❌ Destination branch '{branch_to}' does not exist![/red]")
            raise typer.Exit(1)
        
        # Ensure remote branch exists
        try:
            repo.git.fetch("origin", branch_from)
        except Exception as e:
            console.print(f"[red]❌ Error fetching origin/{branch_from}: {str(e)}[/red]")
            raise typer.Exit(1)
        
        # Show what will be removed
        show_branch_diff(repo, branch_from, branch_to)
        
        # Get confirmation
        warning_panel = Panel(
            f"[bold red]⚠️ Warning:[/bold red]\n\n"
            f"This will force-reset {branch_to} to match origin/{branch_from}.\n"
            f"Any commits in {branch_to} that are not in origin/{branch_from} will be removed.\n\n"
            f"This operation cannot be undone!",
            title="⚠️ Reset Warning",
            border_style="red"
        )
        console.print(warning_panel)
        
        if not force and not Confirm.ask(f"Are you sure you want to reset {branch_to} to match origin/{branch_from}?", default=False):
            console.print("[yellow]Reset cancelled.[/yellow]")
            raise typer.Exit(0)
        
        # Perform the reset
        console.print(f"[yellow]Switching to {branch_to} branch...[/yellow]")
        repo.heads[branch_to].checkout()
        
        console.print(f"[yellow]Resetting {branch_to} to match origin/{branch_from}...[/yellow]")
        repo.git.reset("--hard", f"origin/{branch_from}")
        
        console.print(f"[yellow]Force pushing to origin/{branch_to}...[/yellow]")
        repo.git.push("--force", "origin", branch_to)
        
        # Show success message
        success_panel = Panel(
            f"Successfully reset {branch_to} to match origin/{branch_from}!\n"
            f"All extra commits have been removed.",
            title="🎉 Success",
            border_style="green"
        )
        console.print(success_panel)
        
    except Exception as e:
        console.print(f"[red]❌ Error: {str(e)}[/red]")
        raise typer.Exit(1) 