import typer
from git import Repo
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from typing import Optional

from gitstage.commands.utils import require_git_repo

console = Console()

def list_branches(repo: Repo) -> None:
    """List all local and remote branches in a formatted table."""
    # Get local branches
    local_branches = [branch.name for branch in repo.heads]
    current_branch = repo.active_branch.name
    
    # Get remote branches
    remote_branches = []
    for ref in repo.remote().refs:
        branch_name = ref.name.split('/')[-1]
        if branch_name not in local_branches:
            remote_branches.append(branch_name)
    
    # Create table
    table = Table(title="Git Branches")
    table.add_column("Type", style="cyan")
    table.add_column("Branch", style="green")
    table.add_column("Status", style="yellow")
    
    # Add local branches
    for branch in sorted(local_branches):
        status = "✓ Current" if branch == current_branch else ""
        table.add_row("Local", branch, status)
    
    # Add remote branches
    for branch in sorted(remote_branches):
        table.add_row("Remote", branch, "")
    
    console.print(table)

def switch_branch(repo: Repo, branch_name: str) -> None:
    """Switch to the specified branch."""
    try:
        # Check if branch exists locally
        if branch_name in repo.heads:
            repo.heads[branch_name].checkout()
            console.print(f"[green]✓ Switched to branch '{branch_name}'[/green]")
            return
        
        # Check if branch exists remotely
        remote = repo.remote()
        for ref in remote.refs:
            if ref.name.split('/')[-1] == branch_name:
                # Create local branch tracking remote
                repo.create_head(branch_name, ref)
                repo.heads[branch_name].checkout()
                console.print(f"[green]✓ Created and switched to branch '{branch_name}'[/green]")
                return
        
        console.print(f"[red]❌ Branch '{branch_name}' not found locally or remotely[/red]")
        raise typer.Exit(1)
        
    except Exception as e:
        console.print(f"[red]❌ Error switching to branch: {str(e)}[/red]")
        raise typer.Exit(1)

def main(
    branch_name: Optional[str] = typer.Argument(None, help="Branch to switch to")
):
    """List all branches or switch to a specific branch."""
    try:
        # Verify Git repository
        require_git_repo()
        
        # Get the current repository
        repo = Repo(".")
        
        if branch_name:
            # Switch to specified branch
            switch_branch(repo, branch_name)
        else:
            # List all branches
            list_branches(repo)
            
    except Exception as e:
        console.print(f"[red]❌ Error: {str(e)}[/red]")
        raise typer.Exit(1) 