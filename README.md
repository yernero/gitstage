# GitStage

**GitStage** is a developer-first CLI tool that manages Git changes through a clean, staged review workflow. It simplifies how features move from `dev` → `testing` → `main`, with built-in tooling for promotion, change tracking, and structured reviews.

---

## 🚀 Features

- 🧱 **Stage-based Workflow** – Promote code through defined branches like `dev`, `testing`, `main`
- 📝 **Change Tracking** – Track summaries and test plans for every promoted commit
- 🔍 **Review System** – Approve or reject changes with optional comments
- 🌿 **Branch Management** – List and switch between branches easily
- 💡 **Rich CLI** – Beautiful command-line interface using `typer` and `rich`
- 📋 **Change Requests** – Create and manage structured change requests with stage-based permissions

---

## 📦 Installation

```bash
pip install gitstage
```

---

## ⚙️ Configuration

Create a `.gitstage_config.json` at the root of your Git repository:

```json
{
  "stages": ["dev", "testing", "main"]
}
```

For Change Request stage permissions, create or modify `gitstage/config/stageflow.json`:

```json
{
  "In Progress": { "editable": true },
  "Testing": { "editable": true },
  "Main Review": { "editable": true },
  "Complete": { "editable": false }
}
```

You can customize the branch names, order, and CR permissions to match your workflow.

---

## 🛠️ Commands

### `push`

Promote selected file changes from one stage to the next.

```bash
gitstage push
gitstage push --from dev --to testing --files a.py b.py --summary "Fix auth bug" --test-plan "Passed unit tests"
```

Options:

* `--all` – Commit and push all changes without prompts
* `--force-promote` – Override checks that prevent duplicate promotions

---

### `flatten`

Reset downstream branches to match an upstream branch (e.g., resetting `dev` to `main`).

```bash
gitstage flatten --branch-from main --branch-to dev
gitstage flatten --cascade --force
```

Options:

* `--cascade` – Flatten all downstream stages
* `--dry-run` – Preview changes
* `--force` – Skip confirmation prompts

---

### `review`

Review promoted commits and approve or reject them.

```bash
gitstage review <commit-hash> --approve
gitstage review --all --approve
```

* Shows summaries and test plans
* Batch approve/reject with `--all`

---

### `cr` (Change Request Management)

Create, edit, and manage Change Requests (CRs) with stage-based permissions.

- **Modular subcommand structure:** CR commands are now organized in a package with subcommands (e.g., `cr edit`).
- **Enhanced `cr edit` command:** Now a Typer subcommand, supports future extensions, and provides diff preview before saving.
- **Stage-based permissions:** Editing is only allowed in stages marked editable in `stageflow.json`.
- **Improved editor integration:** Supports `$EDITOR`, `$VISUAL`, `--editor` flag, and Notepad++ auto-detection on Windows.
- **Rich diff preview:** See changes before saving edits.
- **Version history:** All edits are versioned in the `gitstage/cr-log` branch.

Example usage:
```bash
gitstage cr edit 0001
# or
gitstage cr edit CR-0001 --editor "notepad++"
```

Features:
* Creates structured markdown files in `.gitstage/change_requests/`
* Stores CRs in a separate `gitstage/cr-log` branch
* Auto-generates CR numbers and metadata
* Stage-based edit permissions
* Cross-platform editor support
* Environment variable support (`EDITOR`/`VISUAL`)
* UTF-8 encoding handling
* Rich table output for listing
* Markdown preview for viewing

Editor Configuration:
* Uses `$EDITOR` or `$VISUAL` environment variables
* Falls back to platform defaults (Notepad++/notepad on Windows, nano/vim/vi on Unix)
* Override with `--editor` flag
* Special support for Notepad++ on Windows

Example Notepad++ Configuration:
```bash
# Windows PowerShell
$env:EDITOR="'C:\Program Files\Notepad++\notepad++.exe' -multiInst -notabbar -nosession -noPlugin -notepadStyleCmdline"

# Windows CMD
set EDITOR="C:\Program Files\Notepad++\notepad++.exe" -multiInst -notabbar -nosession -noPlugin -notepadStyleCmdline

# Unix
export EDITOR=nano
```

---

### `init`

Initialize GitStage in your current repo.

```bash
gitstage init
```

---

### `branch`

List available branches or switch between them.

```bash
gitstage branch         # List
gitstage branch dev     # Switch
```

---

## 🧱 Project Structure

```
gitstage/
├── cli.py                # Entry point
├── __init__.py
└── commands/
    ├── push.py
    ├── promote.py
    ├── review.py
    ├── init.py
    ├── branch.py
    ├── cr.py            # Change Request management
    ├── utils.py
    └── __init__.py
```

---

## 🧪 Development

### Install & Test

```bash
# Install with editable mode
pip install -e .

# Run tests
pytest
```

### Dependencies

* [`typer`](https://typer.tiangolo.com/)
* [`rich`](https://rich.readthedocs.io/)
* [`gitpython`](https://gitpython.readthedocs.io/)
* [`sqlalchemy`](https://www.sqlalchemy.org/)

---

## 🤝 Contributing

Pull requests welcome! Please fork the repo and open a PR. Feature ideas, bug reports, and docs improvements are appreciated.

---

## 📄 License

MIT License. See `LICENSE` for details.

```

---

Let me know if you'd like a shorter version for PyPI or to split this into multiple docs (e.g., `docs/USAGE.md`).
```
