import typer
from rich.console import Console

from gitstage.commands import push, promote, review

app = typer.Typer(help="GitStage - A CLI tool for managing Git changes with review workflow")
console = Console()

# Add commands from modules
app.add_typer(push.app, name="push", help="Record and push changes to dev branch")
app.add_typer(promote.app, name="promote", help="Promote changes from dev to testing or main")
app.add_typer(review.app, name="review", help="Review and approve/reject changes")

if __name__ == "__main__":
    app()
