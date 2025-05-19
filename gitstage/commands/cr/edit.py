"""
CR Edit Subcommand Module

This module provides the core functionality for editing Change Requests.
It handles:
- Loading CR content
- Opening in editor
- Change detection
- Diff preview
- Saving changes
- Version history
"""

import os
import tempfile
import typer
from rich.console import Console
from rich.prompt import Confirm
from git import Repo

from ..utils import require_git_repo
from .utils import (
    get_cr_number,
    load_cr_file,
    save_cr_changes,
    parse_cr_metadata,
    open_editor,
    has_content_changed,
    show_diff_preview,
    is_stage_editable
)

app = typer.Typer()
console = Console()

@app.callback(invoke_without_command=True)
def edit_cr(
    cr_id: str,
    editor: str = typer.Option(None, "--editor", "-e", help="Override default editor")
):
    """Edit a Change Request if its current stage allows editing."""
    try:
        require_git_repo()
        
        try:
            cr_number = get_cr_number(cr_id)
        except ValueError as e:
            console.print(f"[red]❌ {str(e)}[/red]")
            raise typer.Exit(1)
        
        content = load_cr_file(cr_number)
        if not content:
            console.print(f"[red]❌ CR-{cr_number} not found[/red]")
            raise typer.Exit(1)
        
        metadata = parse_cr_metadata(content)
        current_stage = metadata["stage"]
        
        if not is_stage_editable(current_stage):
            console.print(f"[red]❌ Cannot edit CR-{cr_number}: Stage '{current_stage}' is not editable[/red]")
            console.print("[yellow]ℹ Tip: Check gitstage/config/stageflow.json for stage rules[/yellow]")
            raise typer.Exit(1)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', encoding='utf-8', delete=False) as temp:
            temp_path = temp.name
            temp.write(content)
        
        try:
            if open_editor(temp_path, editor):
                with open(temp_path, 'r', encoding='utf-8') as temp:
                    edited_content = temp.read()
                
                if has_content_changed(content, edited_content):
                    # Show diff preview
                    show_diff_preview(content, edited_content)
                    
                    # Confirm changes
                    if not Confirm.ask("Do you want to save these changes?"):
                        console.print("[yellow]Changes discarded.[/yellow]")
                        return
                    
                    # Save changes
                    if save_cr_changes(cr_number, edited_content):
                        console.print(f"[green]✓ Successfully updated CR-{cr_number}[/green]")
                    else:
                        console.print(f"[red]❌ Failed to save changes to CR-{cr_number}[/red]")
                        raise typer.Exit(1)
                else:
                    console.print("[yellow]ℹ No changes made[/yellow]")
            else:
                console.print("[yellow]ℹ Edit cancelled or editor failed[/yellow]")
                raise typer.Exit(1)
            
        finally:
            try:
                os.unlink(temp_path)
            except:
                pass
        
    except Exception as e:
        console.print(f"[red]❌ Error: {str(e)}[/red]")
        raise typer.Exit(1)

if __name__ == "__main__":
    app() 