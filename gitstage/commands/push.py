import typer
from git import Repo
from rich.console import Console
from rich.prompt import Prompt

from .utils import record_change

app = typer.Typer()
console = Console()

@app.command()
def push(
    summary: str = typer.Option(..., prompt=True, help="Summary of the changes"),
    test_plan: str = typer.Option(..., prompt=True, help="Test plan for the changes"),
):
    """Record a change and push it to the dev branch."""
    try:
        # Get the current repository
        repo = Repo(".")
        
        # Ensure we're on the dev branch
        if repo.active_branch.name != "dev":
            console.print("[yellow]Switching to dev branch...[/yellow]")
            repo.heads.dev.checkout()
        
        # Stage all changes
        repo.index.add("*")
        
        # Create commit
        commit = repo.index.commit(f"{summary}\n\nTest Plan:\n{test_plan}")
        
        # Push to dev
        origin = repo.remote("origin")
        origin.push("dev")
        
        # Record the change
        record_change(
            commit_hash=commit.hexsha,
            summary=summary,
            test_plan=test_plan
        )
        
        console.print(f"[green]Successfully pushed changes to dev branch![/green]")
        console.print(f"Commit hash: {commit.hexsha}")
        
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        raise typer.Exit(1)
