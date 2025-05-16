# gitstage

**GitStage** is a CLI tool to manage Git promotion workflows through structured stages: `development` → `testing` → `main`.

## Features

- Push code to the `dev` branch and document changes
- Propose promotions to `testing` or `main`
- Approve or reject changes with documented reviews
- Store change history in a local SQLite database
- Designed for use with GitHub Actions for CI on `testing` and `main`

## Usage

### Run with Python:
```bash
python -m gitstage.cli --help
```
### Or install and run globally:
```bash
pip install -e .
gitstage push
```

### Requirements
- Python 3.9+
- Typer
- SQLAlchemy
- GitPython
- Rich