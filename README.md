# GitStage

**GitStage** is a developer-first CLI tool that manages Git changes through a clean, staged review workflow. It simplifies how features move from `dev` → `testing` → `main`, with built-in tooling for promotion, change tracking, and structured reviews.

---

## 🚀 Features

- 🧱 **Stage-based Workflow** – Promote code through defined branches like `dev`, `testing`, `main`
- 📝 **Change Tracking** – Track summaries and test plans for every promoted commit
- 🔍 **Review System** – Approve or reject changes with optional comments
- 🌿 **Branch Management** – List and switch between branches easily
- 💡 **Rich CLI** – Beautiful command-line interface using `typer` and `rich`
- 📋 **Change Requests** – Create and manage structured change requests

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

You can customize the branch names and order to match your workflow.

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

### `cr`

Manage Change Requests (CRs) for tracking structured changes.

```bash
# Interactive mode
gitstage cr add

# Non-interactive mode
gitstage cr add \
  --summary "Implement Backend Payment API" \
  --motivation "CRUD functionality for payment entries" \
  --dependencies "Prisma schema completed; Express routes structured" \
  --acceptance "GET/POST/PUT/DELETE /payments; Valid structure; Manual tests" \
  --notes "Authentication not implemented"
```

* Creates structured markdown files in `.gitstage/change_requests/`
* Stores CRs in a separate `gitstage/cr-log` branch
* Auto-generates CR numbers and metadata
* Supports both interactive and non-interactive usage

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
    ├── cr.py
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
