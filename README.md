# GitStage

A CLI tool for managing Git changes with a review workflow. GitStage helps teams maintain a clean and organized Git workflow by providing commands for pushing changes, promoting them through different stages, and managing reviews.

## Features

- **Stage-based Workflow**: Manage changes through different stages (dev → testing → main)
- **Change Tracking**: Record and track changes with summaries and test plans
- **Review System**: Approve or reject changes with comments
- **Branch Management**: List and switch between branches easily
- **Rich CLI Interface**: Beautiful and informative command-line interface

## Installation

```bash
pip install gitstage
```

## Configuration

Create a `.gitstage_config.json` file in your repository root:

```json
{
  "stages": ["dev", "testing", "main"]
}
```

## Commands

### 🧪 Push

Promote selected file changes from one branch to the next in your stageflow (`dev` → `testing`, etc.).

```bash
gitstage push
gitstage push --from dev --to testing --files a.py b.py --summary "fix" --test-plan "unit tests"
```

* Commits uncommitted changes if needed
* Only promotes when files have changed
* Prevents duplicate promotions by checking commit history
* Use `--all` to commit and push all changes without prompting
* Use `--force-promote` to override no-op checks

### 🧹 Flatten

Reset one or more downstream branches to match a source branch.

```bash
gitstage flatten --branch-from main --branch-to dev
gitstage flatten --cascade --force
```

* Flattens full pipeline (e.g., `main → testing → dev`)
* Useful for production resets or enforcing top-down truth
* Safe with confirmation prompts; use `--force` to skip
* Use `--dry-run` to preview changes without applying them

### ✅ Review

Review and approve/reject tracked commits.

```bash
gitstage review <commit-hash> --approve
gitstage review --all --approve
```

* Automatically tracks promoted changes
* Use `--all` to review and update all pending changes in batch
* Displays changes in a table with summary and test plan

### 🏗️ Init

Initialize a new GitStage repository.

```bash
gitstage init
```

### 🌿 Branch

List and switch between branches.

```bash
gitstage branch
gitstage branch <branch-name>
```

## Development

### Project Structure

```
gitstage/
├── commands/
│   ├── __init__.py
│   ├── push.py
│   ├── promote.py
│   ├── review.py
│   ├── init.py
│   ├── branch.py
│   └── utils.py
├── cli.py
└── __init__.py
```

### Dependencies

- typer: CLI framework
- rich: Terminal formatting
- gitpython: Git operations
- sqlalchemy: Database operations

### Build and Test

```bash
# Install dependencies
pip install -e .

# Run tests
pytest
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.