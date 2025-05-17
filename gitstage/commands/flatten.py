import typer
from git import Repo
from rich.console import Console
from rich.prompt import Confirm
from rich.panel import Panel
from typing import List, Optional

from gitstage.commands.utils import require_git_repo, get_stageflow

console = Console()

def get_stages_before(current_stage: str) -> List[str]:
    """Get all stages before the current stage in the stageflow."""
    stages = get_stageflow()
    try:
        current_index = stages.index(current_stage)
        return stages[:current_index]
    except ValueError:
        return []

def get_stages_after(current_stage: str) -> List[str]:
    """Get all stages after the current stage in the stageflow."""
    stages = get_stageflow()
    try:
        current_index = stages.index(current_stage)
        return stages[current_index + 1:]
    except ValueError:
        return []

def show_branch_diff(repo: Repo, branch_from: str, branch_to: str) -> None:
    """Show the difference between branches."""
    try:
        # Get commits that are in branch_to but not in branch_from
        commits = list(repo.iter_commits(f"{branch_from}..{branch_to}"))
        
        if commits:
            console.print(f"\n[bold yellow]⚠️ The following commits will be removed from {branch_to}:[/bold yellow]")
            for commit in commits:
                console.print(f"  [yellow]- {commit.hexsha[:7]} {commit.message.splitlines()[0]}[/yellow]")
        else:
            console.print(f"\n[green]✓ No commits to remove - {branch_to} is already in sync with {branch_from}[/green]")
            
    except Exception as e:
        console.print(f"[red]❌ Error showing branch diff: {str(e)}[/red]")

def flatten_branch(repo: Repo, branch_from: str, branch_to: str, force: bool = False, dry_run: bool = False) -> bool:
    """Flatten a branch to match its source branch."""
    try:
        # Show what will be removed
        show_branch_diff(repo, branch_from, branch_to)
        
        # Get confirmation
        warning_panel = Panel(
            f"[bold red]⚠️ Warning:[/bold red]\n\n"
            f"This will destroy all local and remote history for {branch_to} and overwrite it with {branch_from}.\n"
            f"Any commits in {branch_to} that are not in {branch_from} will be permanently removed.\n\n"
            f"This operation cannot be undone!",
            title="⚠️ Flatten Warning",
            border_style="red"
        )
        console.print(warning_panel)
        
        if not force and not Confirm.ask(f"Are you sure you want to flatten {branch_to} to match {branch_from}?", default=False):
            console.print("[yellow]Flatten cancelled.[/yellow]")
            return False
        
        if dry_run:
            console.print(f"[yellow]Dry run: Would flatten {branch_to} to match {branch_from}[/yellow]")
            return True
        
        # Perform the flatten
        console.print(f"[yellow]Switching to {branch_to} branch...[/yellow]")
        repo.heads[branch_to].checkout()
        
        console.print(f"[yellow]Resetting {branch_to} to match {branch_from}...[/yellow]")
        repo.git.reset("--hard", f"origin/{branch_from}")
        
        console.print(f"[yellow]Force pushing to origin/{branch_to}...[/yellow]")
        repo.git.push("--force", "origin", branch_to)
        
        # Show success message
        success_panel = Panel(
            f"Successfully flattened {branch_to} to match {branch_from}!\n"
            f"All extra commits have been removed.",
            title="🎉 Success",
            border_style="green"
        )
        console.print(success_panel)
        return True
        
    except Exception as e:
        console.print(f"[red]❌ Error flattening {branch_to}: {str(e)}[/red]")
        return False

def main(
    branch_from: str = typer.Option(None, help="Source branch to match (default: highest stage in stageflow)"),
    branch_to: str = typer.Option(None, help="Destination branch to flatten (default: next stage in stageflow)"),
    cascade: bool = typer.Option(False, "--cascade", "-c", help="Cascade flattening through all downstream branches"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompts"),
    dry_run: bool = typer.Option(False, "--dry-run", "-d", help="Show what would be done without making changes"),
):
    """Reset a branch to match its source branch, removing any extra commits."""
    try:
        # Verify Git repository
        require_git_repo()
        
        # Get the current repository
        repo = Repo(".")
        
        # Get stageflow
        stages = get_stageflow()
        if not stages:
            console.print("[red]❌ No stages defined in stageflow![/red]")
            raise typer.Exit(1)
        
        # Handle cascade mode
        if cascade:
            # Reverse the stages list for top-down cascading
            stages_reversed = list(reversed(stages))
            
            # Determine starting point
            if branch_from:
                if branch_from not in stages_reversed:
                    console.print(f"[red]❌ Source branch '{branch_from}' is not in the stageflow![/red]")
                    raise typer.Exit(1)
                start_index = stages_reversed.index(branch_from)
            else:
                start_index = 0  # Start from the highest stage (last in original list)
                branch_from = stages_reversed[0]
            
            # Get target branches for cascading
            target_branches = []
            for i in range(start_index + 1, len(stages_reversed)):
                target_branches.append(stages_reversed[i])
            
            if not target_branches:
                console.print(f"[yellow]⚠️ No downstream branches found after {branch_from}[/yellow]")
                if branch_from != stages_reversed[0]:
                    console.print(f"[yellow]Note: {branch_from} is not the highest stage. Consider using --branch-from {stages_reversed[0]} to start from the top.[/yellow]")
                raise typer.Exit(0)
            
            console.print(f"\n[bold cyan]Cascade flattening from {branch_from} to:[/bold cyan]")
            for branch in target_branches:
                console.print(f"  [cyan]→ {branch}[/cyan]")
            
            if not force and not Confirm.ask("Proceed with cascade flattening?", default=False):
                console.print("[yellow]Cascade flattening cancelled.[/yellow]")
                raise typer.Exit(0)
            
            # Perform cascade flattening
            current_from = branch_from
            for branch in target_branches:
                if not flatten_branch(repo, current_from, branch, force, dry_run):
                    console.print(f"[red]❌ Failed to flatten {branch}. Stopping cascade.[/red]")
                    raise typer.Exit(1)
                current_from = branch  # Use the flattened branch as the source for the next step
            
            if dry_run:
                console.print("\n[green]✓ Dry run completed successfully[/green]")
            else:
                console.print("\n[green]✓ Cascade flattening completed successfully[/green]")
            
        else:
            # Single branch flattening
            if not branch_from:
                branch_from = stages[-1]  # Use highest stage as default
                console.print(f"[green]✓ Using highest stage as source: {branch_from}[/green]")
            
            if not branch_to:
                # Find the next stage after branch_from in the reversed list
                stages_reversed = list(reversed(stages))
                try:
                    from_index = stages_reversed.index(branch_from)
                    if from_index < len(stages_reversed) - 1:
                        branch_to = stages_reversed[from_index + 1]
                        console.print(f"[green]✓ Using next stage as destination: {branch_to}[/green]")
                    else:
                        console.print(f"[red]❌ No downstream branches found after {branch_from}[/red]")
                        raise typer.Exit(1)
                except ValueError:
                    console.print(f"[red]❌ Source branch '{branch_from}' is not in the stageflow![/red]")
                    raise typer.Exit(1)
            
            if branch_to not in repo.heads:
                console.print(f"[red]❌ Destination branch '{branch_to}' does not exist![/red]")
                raise typer.Exit(1)
            
            if not flatten_branch(repo, branch_from, branch_to, force, dry_run):
                raise typer.Exit(1)
        
    except Exception as e:
        console.print(f"[red]❌ Error: {str(e)}[/red]")
        raise typer.Exit(1) 