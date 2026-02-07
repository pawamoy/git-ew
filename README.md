# git-ew

[![ci](https://github.com/pawamoy/git-ew/workflows/ci/badge.svg)](https://github.com/pawamoy/git-ew/actions?query=workflow%3Aci)
[![documentation](https://img.shields.io/badge/docs-mkdocs-708FCC.svg?style=flat)](https://pawamoy.github.io/git-ew/)
[![pypi version](https://img.shields.io/pypi/v/git-ew.svg)](https://pypi.org/project/git-ew/)
[![gitter](https://img.shields.io/badge/matrix-chat-4DB798.svg?style=flat)](https://app.gitter.im/#/room/#git-ew:gitter.im)

Git Email Workflow - A GitHub-like web interface for email-based git workflows

> [!NOTE]
> This project is developed with the assistance of LLMs / coding agents. It's not fully functional yet. My main use of it will be to continue my contribution of a ZSH_XTRACEFD feature to Zsh, through their zsh-workers mailing list.

## Overview

**git-ew** provides a GitHub-style web interface for email-based git workflows. It organizes emails into threads, handles infinite nesting, and allows posting comments via plain-text emails.

### Features

- GitHub-like interface for viewing threads and patches
- Email integration (maildir, mbox, public archives)
- Threaded discussions with infinite nesting support
- Automatic patch detection and display
- Plain-text email replies with proper headers
- Thread flattening for long linear chains
- SQLite backend with async FastAPI

## Installation

```bash
pip install git-ew
```

With [`uv`](https://docs.astral.sh/uv/):

```bash
uv tool install git-ew
```

## Getting Started

### Quick Demo

Try git-ew with sample data:

```bash
git-ew init
python scripts/create_sample_data.py
git-ew serve
```

Open http://127.0.0.1:8000 to view sample threads.

### Setup

Initialize the database:

```bash
git-ew init
```

Use the interactive setup wizard:

```bash
python scripts/setup.py
```

Or configure manually:

```python
import asyncio
from git_ew._internal.database import Database
from git_ew._internal.models import EmailSource
import json

async def setup():
    db = Database()
    await db.init_db()

    # Configure SMTP for sending emails
    await db.set_config("email_config", {
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "from_email": "you@example.com",
        "from_name": "Your Name",
        "username": "you@example.com",
        "password": "your-app-password",  # Use app password for Gmail
        "use_tls": True
    })

    # Add email source - Maildir
    async with db.session() as session:
        source = EmailSource(
            name="my-inbox",
            source_type="maildir",
            config=json.dumps({"path": "/path/to/maildir"}),
            enabled=True
        )
        session.add(source)

    # Or add email source - Mbox
    async with db.session() as session:
        source = EmailSource(
            name="mailing-list",
            source_type="mbox",
            config=json.dumps({"path": "/path/to/archive.mbox"}),
            enabled=True
        )
        session.add(source)

asyncio.run(setup())
```

### Usage

Start the server:

```bash
git-ew serve                          # Default: http://127.0.0.1:8000
git-ew serve --host 0.0.0.0           # Listen on all interfaces
git-ew serve --port 3000              # Custom port
git-ew serve --reload                 # Auto-reload (development)
```

Access the web interface and click "Sync Emails" to fetch messages from configured sources.

### Configuration Details

#### Email Sources

**Maildir** (local mail folders):

```json
{"path": "/home/user/.mail/INBOX"}
```

**Mbox** (archive files):

```json
{"path": "/path/to/mailing-list.mbox"}
```

**Public Inbox** (coming soon):

```json
{"url": "https://example.org/archive/"}
```

#### SMTP Providers

**Gmail**: Enable 2FA and generate an [app password](https://myaccount.google.com/apppasswords)

**Outlook/Office365**: Use regular or app-specific password

**Custom SMTP**: Any server supporting STARTTLS

#### Command Line

```bash
git-ew init          # Initialize database
git-ew serve         # Start web server
git-ew sync          # Sync emails from sources
```

## How It Works

### Email Fetching

git-ew can fetch emails from various sources:

- **Maildir**: Local maildir folders
- **Mbox**: Mbox archive files
- **Public Archives**: Public-inbox archives (coming soon)

### Thread Organization

Emails are organized into threads based on their `Message-ID`, `In-Reply-To`, and `References` headers. The system:

1. Groups related emails into threads
2. Builds a tree structure with infinite nesting support
3. Detects linear chains (single replies) and marks them for flattening
4. Renders threads with proper indentation and visual hierarchy

### Sending Emails

When you post a comment through the web interface:

1. The comment is sent as a **plain-text email** (no HTML)
2. Proper email headers are set (`In-Reply-To`, `References`)
3. The email is stored in the local database
4. Email threading is maintained correctly

### Patch Detection

git-ew automatically detects patches in emails by looking for:

- Git diff format (`diff --git`)
- Unified diff format (`---` and `+++`)
- `[PATCH]` in the subject line

Patches are displayed with syntax highlighting and can be viewed/hidden.

## Architecture

```
git-ew/
├── models.py           # SQLAlchemy database models
├── database.py         # Database operations
├── email_parser.py     # Email parsing utilities
├── email_fetcher.py    # Fetch emails from various sources
├── email_sender.py     # Send emails via SMTP
├── thread_utils.py     # Thread organization and flattening
├── app.py             # FastAPI application
├── cli.py             # Command-line interface
├── templates/         # Jinja2 HTML templates
│   ├── base.html
│   ├── index.html
│   └── thread.html
└── static/            # CSS and JavaScript
    ├── css/style.css
    └── js/main.js
```

## API Endpoints

- `GET /` - List threads
- `GET /thread/{id}` - View thread details
- `POST /api/thread/{id}/comment` - Post a comment (sends email)
- `POST /api/thread/{id}` - Update thread (e.g., close/reopen)
- `POST /api/sync` - Sync emails from sources
- `GET /api/threads` - Get threads as JSON
- `GET /api/thread/{id}` - Get thread details as JSON

## Sponsors

<!-- sponsors-start -->
<!-- sponsors-end -->
