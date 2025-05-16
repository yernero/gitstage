import typer
from git import Repo, InvalidGitRepositoryError
from rich.console import Console
from rich.panel import Panel

from gitstage.commands.utils import save_stageflow

app = typer.Typer()
console = Console()

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
        
        # Create branches if they don't exist
        for stage in stages:
            if stage not in repo.heads:
                repo.create_head(stage)
                console.print(f"[green]✓ Created branch: {stage}[/green]")
            else:
                console.print(f"[yellow]! Branch already exists: {stage}[/yellow]")
        
        # Save stageflow configuration
        save_stageflow(stages)
        console.print("[green]✓ Saved stageflow configuration[/green]")
        
        # Show summary
        summary = Panel(
            f"GitStage initialized successfully!\n\n"
            f"Stages: {' → '.join(stages)}\n"
            f"Config: .gitstage_config.json",
            title="🎉 Success",
            border_style="green"
        )
        console.print(summary)
        
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        raise typer.Exit(1) 