import typer
from git import Repo
from rich.console import Console
from rich.table import Table

from gitstage.commands.utils import (
    get_change, update_change_status, update_all_pending_changes,
    ChangeStatus, require_git_repo, get_pending_changes
)

app = typer.Typer()
console = Console()

@app.command()
def review(
    commit_hash: str = typer.Argument(None, help="Commit hash to review (omit to review all pending changes)"),
    approve: bool = typer.Option(False, "--approve", help="Approve the change(s)"),
    reject: bool = typer.Option(False, "--reject", help="Reject the change(s)"),
    all: bool = typer.Option(False, "--all", "-a", help="Review all pending changes"),
):
    """Review a change and approve or reject it."""
    try:
        # Verify Git repository
        require_git_repo()
        
        # Handle reviewing all changes
        if all:
            pending_changes = get_pending_changes()
            if not pending_changes:
                console.print("[yellow]No pending changes to review.[/yellow]")
                raise typer.Exit(0)
            
            # Display all pending changes
            table = Table(title="Pending Changes")
            table.add_column("Commit Hash", style="cyan")
            table.add_column("Summary", style="green")
            table.add_column("Test Plan", style="yellow")
            
            for change in pending_changes:
                table.add_row(
                    change.commit_hash,
                    change.summary,
                    change.test_plan
                )
            
            console.print(table)
            
            # Determine the new status
            if approve and reject:
                console.print("[red]Cannot both approve and reject changes![/red]")
                raise typer.Exit(1)
            elif approve:
                new_status = ChangeStatus.APPROVED
            elif reject:
                new_status = ChangeStatus.REJECTED
            else:
                # If no flag is provided, ask for confirmation
                if not typer.confirm("Do you want to approve all these changes?"):
                    new_status = ChangeStatus.REJECTED
                else:
                    new_status = ChangeStatus.APPROVED
            
            # Update all changes
            updated_count = update_all_pending_changes(new_status)
            console.print(f"[green]Successfully {new_status.value} {updated_count} changes![/green]")
            return
        
        # Handle single change review
        if not commit_hash:
            console.print("[red]Please provide a commit hash or use --all to review all pending changes.[/red]")
            raise typer.Exit(1)
        
        # Get the change record
        change = get_change(commit_hash)
        if not change:
            console.print("[red]No change record found for the given commit hash![/red]")
            raise typer.Exit(1)
        
        # Display change information
        table = Table(title="Change Details")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Commit Hash", change.commit_hash)
        table.add_row("Summary", change.summary)
        table.add_row("Test Plan", change.test_plan)
        table.add_row("Current Status", change.status.value)
        
        console.print(table)
        
        # Determine the new status
        if approve and reject:
            console.print("[red]Cannot both approve and reject a change![/red]")
            raise typer.Exit(1)
        elif approve:
            new_status = ChangeStatus.APPROVED
        elif reject:
            new_status = ChangeStatus.REJECTED
        else:
            # If no flag is provided, ask for confirmation
            if not typer.confirm("Do you want to approve this change?"):
                new_status = ChangeStatus.REJECTED
            else:
                new_status = ChangeStatus.APPROVED
        
        # Update the status
        updated_change = update_change_status(commit_hash, new_status)
        if updated_change:
            console.print(f"[green]Successfully {new_status.value} the change![/green]")
        else:
            console.print("[red]Failed to update change status![/red]")
            raise typer.Exit(1)
        
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        raise typer.Exit(1)
