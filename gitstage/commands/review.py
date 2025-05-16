import typer
from git import Repo
from rich.console import Console
from rich.table import Table

from gitstage.commands.utils import get_change, update_change_status, ChangeStatus

app = typer.Typer()
console = Console()

@app.command()
def review(
    commit_hash: str = typer.Argument(..., help="Commit hash to review"),
    approve: bool = typer.Option(False, "--approve", help="Approve the change"),
    reject: bool = typer.Option(False, "--reject", help="Reject the change"),
):
    """Review a change and approve or reject it."""
    try:
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
