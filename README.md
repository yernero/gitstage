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

## Usage

### Initialize Repository

Initialize your repository with the stageflow configuration:

```bash
gitstage init
```

This will:
- Create a `.gitstage` directory
- Set up the stageflow configuration
- Initialize the SQLite database for change tracking

### Branch Management

List all branches or switch to a specific branch:

```bash
# List all branches
gitstage branch

# Switch to a branch
gitstage branch dev
```

The branch command will:
- Show a formatted table of local and remote branches
- Mark the current branch
- Create tracking branches when switching to remote branches

### Push Changes

Push changes to the next stage in the workflow:

```bash
gitstage push [--branch-from BRANCH] [--branch-to BRANCH] [--files FILES...] [--summary SUMMARY] [--test-plan TEST_PLAN]
```

The push command will:
- Handle uncommitted changes
- Ensure the source branch is synced with origin
- Show a diff of changes
- Allow selective file inclusion
- Create a commit with summary and test plan
- Push to the destination branch
- Record the change in the database

### Promote Changes

Promote changes from one stage to another:

```bash
gitstage promote [--from FROM] [--to TO]
```

### Review Changes

Review and approve/reject changes:

```bash
gitstage review [--approve/--reject] [--comment COMMENT]
```

## Configuration

The tool uses a stageflow configuration to define the stages and their relationships. The default configuration is:

```yaml
stages:
  - dev
  - testing
  - main
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

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.