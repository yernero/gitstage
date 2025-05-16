import typer
from git import Repo
from rich.console import Console
from rich.table import Table

from gitstage.commands.utils import get_change

app = typer.Typer()
console = Console()

@app.command()
def promote(
    target: str = typer.Option(
        ...,
        prompt=True,
        help="Target branch to promote to (testing or main)",
        callback=lambda x: x if x in ["testing", "main"] else typer.BadParameter("Target must be 'testing' or 'main'")
    ),
):
    """Promote changes from dev to testing or main branch."""
    try:
        # Get the current repository
        repo = Repo(".")
        
        # Ensure we're on the dev branch
        if repo.active_branch.name != "dev":
            console.print("[yellow]Switching to dev branch...[/yellow]")
            repo.heads.dev.checkout()
        
        # Get the latest commit
        latest_commit = repo.head.commit
        
        # Get the change record
        change = get_change(latest_commit.hexsha)
        if not change:
            console.print("[red]No change record found for the latest commit![/red]")
            raise typer.Exit(1)
        
        # Display change information
        table = Table(title="Change Details")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Commit Hash", latest_commit.hexsha)
        table.add_row("Summary", change.summary)
        table.add_row("Test Plan", change.test_plan)
        
        console.print(table)
        
        # Confirm promotion
        if not typer.confirm(f"Proceed with promotion to {target}?"):
            console.print("[yellow]Promotion cancelled.[/yellow]")
            raise typer.Exit(0)
        
        # Create and checkout target branch
        target_branch = repo.create_head(target, latest_commit)
        target_branch.checkout()
        
        # Push to target branch
        origin = repo.remote("origin")
        origin.push(target)
        
        console.print(f"[green]Successfully promoted changes to {target} branch![/green]")
        
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        raise typer.Exit(1)
