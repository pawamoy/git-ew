# Contributing

Contributions are welcome and appreciated. This project uses email-based workflows itself.

## Setup

Fork and clone the repository:

```bash
git clone https://github.com/pawamoy/git-ew.git
cd git-ew
make setup
```

If it fails, install [uv](https://github.com/astral-sh/uv) manually:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync
```

Run `make help` to see available commands.

## Development Workflow

1. Create a branch: `git switch -c feature-or-bugfix-name`
2. Make your changes
3. Run checks:
   ```bash
   make format  # Auto-format code
   make check   # Run all checks
   make test    # Run tests
   ```
4. If updating documentation: `make docs` and verify at http://localhost:8000
5. Follow the commit message convention below

## Project Structure

```
src/git_ew/_internal/
├── cli.py           # Command-line interface
├── app.py           # FastAPI application
├── models.py        # SQLAlchemy models
├── database.py      # Database operations
├── email_parser.py  # Email parsing
├── email_fetcher.py # Fetch from sources
├── email_sender.py  # SMTP sending
├── thread_utils.py  # Thread organization
├── sync.py          # Email sync
├── templates/       # Jinja2 templates
└── static/          # CSS and JavaScript

tests/
├── test_database.py
├── test_email_parser.py
└── test_thread_utils.py
```

## Testing

Run tests with pytest:

```bash
pytest
pytest --cov  # With coverage
```

Write async tests with pytest-asyncio:

```python
import pytest
from git_ew._internal.database import Database

@pytest.mark.asyncio
async def test_database():
    db = Database("sqlite+aiosqlite:///:memory:")
    await db.init_db()
    thread = await db.create_thread("Test", "msg1", is_patch=False)
    assert thread.id is not None
```

## Code Style

- Follow PEP 8
- Use type hints
- Write docstrings for public APIs
- Prefer async/await for I/O operations
- Keep functions focused and small

Example:

```python
async def get_thread_messages(
    db: Database,
    thread_id: int,
) -> list[Message]:
    """Get all messages in a thread.

    Args:
        db: Database instance.
        thread_id: Thread ID.

    Returns:
        List of messages in chronological order.
    """
    thread = await db.get_thread(thread_id)
    if not thread:
        return []
    return sorted(thread.messages, key=lambda m: m.date)
```

## Adding Features

When adding a new email source type:

1. Create fetcher class in `_internal/email_fetcher.py`
2. Update factory function
3. Add tests
4. Update documentation

## Debugging

Database inspection:

```bash
sqlite3 git_ew.db
.tables
SELECT * FROM threads;
```

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Commit Message Convention

Follow the [Angular convention](https://gist.github.com/stephenparish/9941e89d80e2bc58a153):

```
<type>[(scope)]: Subject

[Body]
```

Types: `build`, `chore`, `ci`, `deps`, `docs`, `feat`, `fix`, `perf`, `refactor`, `style`, `tests`

Subject and body must be valid Markdown. Capitalize subject but no trailing dot.

Add trailers at the end for references:

```
Issue #10: https://github.com/namespace/project/issues/10
```

## Pull Requests

Link related issues in the PR message.

Use fixups during review:

```bash
git commit --fixup=SHA
git rebase -i --autosquash main
git push -f
```

Or push each commit and we'll squash before merging.

## Email Patches

Send patches via email:

```bash
git format-patch origin/main
git send-email *.patch
```

## Questions

- Check documentation
- Open a GitHub issue
- Join Matrix/Gitter discussion
- Email maintainers
