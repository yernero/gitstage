import typer
from git import Repo
from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.panel import Panel
from typing import List, Optional, Tuple

from gitstage.commands.utils import record_change, require_git_repo, get_stageflow

console = Console()

def get_next_stage(current_stage: str) -> Optional[str]:
    """Get the next stage in the stageflow after the current stage."""
    stages = get_stageflow()
    try:
        current_index = stages.index(current_stage)
        if current_index < len(stages) - 1:
            return stages[current_index + 1]
    except ValueError:
        pass
    return None

def ensure_branch_synced(repo: Repo, branch: str) -> bool:
    """Ensure a branch is synced with origin."""
    try:
        # Check if branch is ahead of origin
        ahead_count = repo.git.rev_list("--left-only", "--count", f"{branch}...origin/{branch}")
        if int(ahead_count) > 0:
            console.print(f"[yellow]⚠️ Branch '{branch}' has {ahead_count} unpushed commits.[/yellow]")
            if Confirm.ask(f"Push {branch} to origin?", default=True):
                repo.git.push("origin", branch)
                console.print(f"[green]✅ Pushed {branch} to origin.[/green]")
                return True
            return False
        return True
    except Exception as e:
        console.print(f"[red]❌ Error checking branch sync: {str(e)}[/red]")
        return False

def get_changes(repo: Repo, branch: str) -> Tuple[List[str], List[str]]:
    """Get committed and uncommitted changes for a branch."""
    # Get committed changes
    committed = []
    try:
        diff_output = repo.git.diff(f"origin/{branch}..{branch}", name_only=True)
        committed = [f.strip() for f in diff_output.split("\n") if f.strip()]
    except Exception:
        pass
    
    # Get uncommitted changes
    uncommitted = []
    if repo.is_dirty(untracked_files=True):
        for item in repo.index.diff(None):
            uncommitted.append(item.a_path)
        for item in repo.untracked_files:
            uncommitted.append(item)
    
    return committed, uncommitted

def handle_changes(repo: Repo, branch: str) -> Optional[str]:
    """Handle changes in the working directory."""
    committed, uncommitted = get_changes(repo, branch)
    
    if not committed and not uncommitted:
        return None
    
    # Show changes
    if committed:
        console.print("\n[bold cyan]💡 Committed changes not yet pushed:[/bold cyan]")
        for file in committed:
            console.print(f"  [green]+ {file}[/green]")
    
    if uncommitted:
        console.print("\n[bold cyan]💡 Uncommitted changes:[/bold cyan]")
        for file in uncommitted:
            console.print(f"  [yellow]+ {file}[/yellow]")
    
    # Ask how to proceed
    if committed and uncommitted:
        console.print("\n[bold]You have both committed and uncommitted changes.[/bold]")
        choice = Prompt.ask(
            "How would you like to proceed?",
            choices=["push-committed", "commit-all", "select-changes"],
            default="push-committed"
        )
    elif committed:
        choice = "push-committed"
    else:
        choice = "commit-all"
    
    if choice == "push-committed":
        return None
    
    # Get commit message and test plan
    console.print("\n[bold]Please describe your changes:[/bold]")
    summary = Prompt.ask(
        "Enter a brief summary of the changes",
        default="",
        show_default=False
    )
    
    test_plan = Prompt.ask(
        "Describe how this change was tested",
        default="",
        show_default=False
    )
    
    # Handle changes based on choice
    if choice == "commit-all":
        repo.index.add("*")
    else:  # select-changes
        console.print("\n[bold]Select which changes to commit:[/bold]")
        for file in uncommitted:
            if Confirm.ask(f"Include {file}?"):
                repo.index.add(file)
    
    # Create commit
    commit = repo.index.commit(f"{summary}\n\nTest Plan:\n{test_plan}")
    console.print(f"[green]✓ Committed changes: {commit.hexsha}[/green]")
    return commit.hexsha

def show_diff(repo: Repo, branch_from: str, branch_to: str) -> List[str]:
    """Show diff between branches and return list of changed files."""
    try:
        diff_output = repo.git.diff(f"{branch_from}..{branch_to}", name_only=True)
        changed_files = [f.strip() for f in diff_output.split("\n") if f.strip()]
        
        if changed_files:
            console.print("\n[bold cyan]💡 Detected file changes between branches:[/bold cyan]")
            for file in changed_files:
                console.print(f"  [green]+ {file}[/green]")
        else:
            console.print(f"[yellow]⚠️ No changes detected between [bold]{branch_from}[/bold] and [bold]{branch_to}[/bold].[/yellow]")
        
        return changed_files
    except Exception as e:
        console.print(f"[red]Error getting diff: {str(e)}[/red]")
        return []

def main(
    branch_from: str = typer.Option(None, help="Source branch (default: current)"),
    branch_to: str = typer.Option(None, help="Destination branch (default: next in stageflow)"),
    files: List[str] = typer.Option(None, help="Files to include in the push"),
    summary: str = typer.Option(None, help="Summary of the changes"),
    test_plan: str = typer.Option(None, help="Test plan for the changes"),
):
    """Record a change and push it to the next stage in the workflow."""
    try:
        # Verify Git repository
        require_git_repo()
        
        # Get the current repository
        repo = Repo(".")
        
        # Determine source and destination branches
        if not branch_from:
            branch_from = repo.active_branch.name
            console.print(f"[green]✓ Using current branch as source: {branch_from}[/green]")
        
        if not branch_to:
            branch_to = get_next_stage(branch_from)
            if not branch_to:
                console.print("[red]❌ No next stage found in stageflow![/red]")
                raise typer.Exit(1)
            console.print(f"[green]✓ Using next stage as destination: {branch_to}[/green]")
        
        # Ensure branches exist
        if branch_from not in repo.heads:
            console.print(f"[red]❌ Source branch '{branch_from}' does not exist![/red]")
            raise typer.Exit(1)
        if branch_to not in repo.heads:
            console.print(f"[red]❌ Destination branch '{branch_to}' does not exist![/red]")
            raise typer.Exit(1)
        
        # Handle changes and ensure branch is synced
        handle_changes(repo, branch_from)
        if not ensure_branch_synced(repo, branch_from):
            console.print("[yellow]⚠️ Skipping promotion due to unsynced source branch.[/yellow]")
            raise typer.Exit(1)
        
        # Show diff and get changed files
        changed_files = show_diff(repo, branch_from, branch_to)
        if not changed_files:
            if not Confirm.ask("Do you want to continue and manually select files?", default=False):
                raise typer.Exit(0)
        
        # Get summary and test plan if not provided
        if not summary:
            summary = Prompt.ask(
                "Enter a brief summary of the changes",
                default="",
                show_default=False
            )
        
        if not test_plan:
            test_plan = Prompt.ask(
                "Describe how this change was tested",
                default="",
                show_default=False
            )
        
        # Determine which files to include
        files_to_add = []
        if files:
            # Use explicitly provided files
            files_to_add = [f for f in files if f in changed_files]
            if len(files_to_add) != len(files):
                console.print("[yellow]⚠️ Some specified files were not found in the diff.[/yellow]")
        else:
            # Interactive file selection
            console.print("\n[bold]Select which files to include in the push:[/bold]")
            for file in changed_files:
                if Confirm.ask(f"Include {file}?"):
                    files_to_add.append(file)
        
        if not files_to_add:
            console.print("[red]❌ No files selected for commit. Aborting push.[/red]")
            raise typer.Exit(1)
        
        # Show summary and get confirmation
        console.print(f"""
[bold cyan]✅ Ready to push:[/bold cyan]
[bold]Source:[/bold] {branch_from}
[bold]Destination:[/bold] {branch_to}
[bold]Files:[/bold] {', '.join(files_to_add)}
[bold]Summary:[/bold] {summary}
[bold]Test Plan:[/bold] {test_plan}
""")
        
        if not Confirm.ask("Proceed with commit and push?"):
            console.print("[yellow]Push cancelled.[/yellow]")
            raise typer.Exit(0)
        
        # Switch to destination branch
        console.print(f"[yellow]Switching to {branch_to} branch...[/yellow]")
        repo.heads[branch_to].checkout()
        
        # Cherry-pick changes from source branch
        console.print(f"[yellow]Applying changes from {branch_from}...[/yellow]")
        for file in files_to_add:
            repo.git.checkout(branch_from, "--", file)
        
        # Stage selected files
        repo.index.add(files_to_add)
        
        # Create commit
        commit = repo.index.commit(f"{summary}\n\nTest Plan:\n{test_plan}")
        
        # Push to destination branch
        origin = repo.remote("origin")
        origin.push(branch_to)
        
        # Record the change
        record_change(
            commit_hash=commit.hexsha,
            summary=summary,
            test_plan=test_plan
        )
        
        # Switch back to source branch
        console.print(f"[yellow]Switching back to {branch_from} branch...[/yellow]")
        repo.heads[branch_from].checkout()
        
        # Show success message
        success_panel = Panel(
            f"Successfully pushed changes to {branch_to}!\n"
            f"Commit hash: {commit.hexsha}",
            title="🎉 Success",
            border_style="green"
        )
        console.print(success_panel)
        
    except Exception as e:
        console.print(f"[red]❌ Error: {str(e)}[/red]")
        raise typer.Exit(1)
