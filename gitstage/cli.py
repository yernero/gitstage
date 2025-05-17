import typer
from rich.console import Console

from gitstage.commands import push, promote, review, init
from gitstage.commands.branch import main as branch

app = typer.Typer(help="GitStage - A CLI tool for managing Git changes with review workflow")
console = Console()

# Add commands from modules
app.command("init")(init.main)
app.command("push")(push.main)
app.add_typer(promote.app, name="promote", help="Promote changes from dev to testing or main")
app.add_typer(review.app, name="review", help="Review and approve/reject changes")
app.command(name="branch")(branch)

if __name__ == "__main__":
    app()
