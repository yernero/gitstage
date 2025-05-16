import tempfile
from pathlib import Path
from git import Repo
from typer.testing import CliRunner
from gitstage.cli import app

runner = CliRunner()

def test_push_command():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        repo = Repo.init(repo_path)
        (repo_path / "README.md").write_text("Initial commit")
        repo.index.add(["README.md"])
        repo.index.commit("init")
        
        result = runner.invoke(app, ["push"], input="Test summary\nTest plan\n")
        assert result.exit_code == 0
