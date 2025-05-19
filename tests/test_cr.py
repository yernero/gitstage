import pytest
from pathlib import Path
from datetime import datetime
from git import Repo
from typer.testing import CliRunner

from gitstage.cli import app
from gitstage.commands.cr import create_cr_file, get_next_cr_number, normalize_cr_id

runner = CliRunner()

@pytest.fixture
def temp_git_repo(tmp_path):
    """Create a temporary Git repository for testing."""
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()
    repo = Repo.init(repo_path)
    
    # Create initial commit
    (repo_path / "README.md").write_text("# Test Repo")
    repo.index.add(["README.md"])
    repo.index.commit("Initial commit")
    
    # Set up CR infrastructure
    cr_dir = repo_path / ".gitstage" / "change_requests"
    cr_dir.mkdir(parents=True)
    (repo_path / ".gitstage" / "next_cr.txt").write_text("0001")
    
    return repo_path

def test_cr_creation_with_multiline_content(temp_git_repo):
    """Test creating a CR with multiline content in all fields."""
    # Test data with multiline content
    cr_data = {
        "cr_number": "0001",
        "summary": "Test Summary\nWith multiple lines\nAnd more lines",
        "motivation": "Line 1\nLine 2\nLine 3",
        "dependencies": "Dep 1\nDep 2\nDep 3",
        "acceptance": "- Criteria 1\n  - Sub 1\n  - Sub 2\n- Criteria 2",
        "notes": "Note 1\nNote 2\nWith tabs\tand special chars"
    }
    
    # Create CR file
    cr_file = create_cr_file(**cr_data)
    
    # Read the created file
    content = cr_file.read_text(encoding='utf-8')
    
    # Verify all content is preserved
    assert cr_data["summary"] in content
    assert cr_data["motivation"] in content
    assert cr_data["dependencies"] in content
    assert cr_data["acceptance"] in content
    assert cr_data["notes"] in content
    
    # Verify datetime format
    today = datetime.now().strftime("%Y-%m-%d")
    assert f"**Created**: {today}" in content

def test_cr_creation_with_empty_notes(temp_git_repo):
    """Test creating a CR with empty notes field."""
    cr_data = {
        "cr_number": "0002",
        "summary": "Test Summary",
        "motivation": "Test Motivation",
        "dependencies": "Test Dependencies",
        "acceptance": "Test Acceptance",
        "notes": None
    }
    
    cr_file = create_cr_file(**cr_data)
    content = cr_file.read_text(encoding='utf-8')
    
    assert "**Notes**:\nNone" in content

def test_cr_number_incrementation(temp_git_repo):
    """Test that CR numbers are properly incremented."""
    # Initial number should be 0001
    assert get_next_cr_number() == "0001"
    
    # Create a CR
    cr_data = {
        "cr_number": "0001",
        "summary": "Test",
        "motivation": "Test",
        "dependencies": "Test",
        "acceptance": "Test"
    }
    create_cr_file(**cr_data)
    
    # Next number should be incremented
    next_cr = Path(temp_git_repo) / ".gitstage" / "next_cr.txt"
    assert next_cr.read_text().strip() == "0002"

def test_cr_id_normalization():
    """Test CR ID normalization with various formats."""
    test_cases = [
        ("0001", "CR-0001"),
        ("CR-0001", "CR-0001"),
        ("9999", "CR-9999"),
        ("CR-9999", "CR-9999")
    ]
    
    for input_id, expected in test_cases:
        assert normalize_cr_id(input_id) == expected
    
    # Test invalid formats
    invalid_ids = ["CR1", "CR-1", "00001", "CR-00001", "abcd", "CR-abcd"]
    for invalid_id in invalid_ids:
        with pytest.raises(ValueError):
            normalize_cr_id(invalid_id)

def test_cr_cli_commands(temp_git_repo):
    """Test CR CLI commands with multiline content."""
    # Change to the test repo directory
    import os
    os.chdir(temp_git_repo)
    
    # Initialize Git repo with CR infrastructure
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0
    
    # Create a CR with multiline content
    result = runner.invoke(app, ["cr", "add"], input=(
        "Test Summary Line 1\nTest Summary Line 2\n"  # Summary
        "Test Motivation Line 1\nTest Motivation Line 2\n"  # Motivation
        "Test Dependencies Line 1\nTest Dependencies Line 2\n"  # Dependencies
        "Test Acceptance Line 1\nTest Acceptance Line 2\n"  # Acceptance
        "Test Notes Line 1\nTest Notes Line 2\n"  # Notes
        "y\n"  # Confirm save
    ))
    assert result.exit_code == 0
    
    # List CRs
    result = runner.invoke(app, ["cr", "list"])
    assert result.exit_code == 0
    assert "Test Summary Line 1" in result.stdout
    
    # Show CR
    result = runner.invoke(app, ["cr", "show", "0001"])
    assert result.exit_code == 0
    assert "Test Summary Line 1" in result.stdout
    assert "Test Summary Line 2" in result.stdout
    assert "Test Motivation Line 1" in result.stdout
    assert "Test Notes Line 1" in result.stdout 