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

![screenshot](https://github.com/user-attachments/assets/d94cdee4-898f-4f1f-be0e-c513714508e6)

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

<div id="premium-sponsors" style="text-align: center;">

<div id="silver-sponsors"><b>Silver sponsors</b><p>
<a href="https://fastapi.tiangolo.com/"><img alt="FastAPI" src="https://raw.githubusercontent.com/tiangolo/fastapi/master/docs/en/docs/img/logo-margin/logo-teal.png" style="height: 200px; "></a><br>
</p></div>

<div id="bronze-sponsors"><b>Bronze sponsors</b><p>
<a href="https://www.nixtla.io/"><picture><source media="(prefers-color-scheme: light)" srcset="https://www.nixtla.io/img/logo/full-black.svg"><source media="(prefers-color-scheme: dark)" srcset="https://www.nixtla.io/img/logo/full-white.svg"><img alt="Nixtla" src="https://www.nixtla.io/img/logo/full-black.svg" style="height: 60px; "></picture></a><br>
</p></div>
</div>

---

<div id="sponsors"><p>
<a href="https://github.com/ofek"><img alt="ofek" src="https://avatars.githubusercontent.com/u/9677399?u=386c330f212ce467ce7119d9615c75d0e9b9f1ce&v=4" style="height: 32px; border-radius: 100%;"></a>
<a href="https://github.com/samuelcolvin"><img alt="samuelcolvin" src="https://avatars.githubusercontent.com/u/4039449?u=42eb3b833047c8c4b4f647a031eaef148c16d93f&v=4" style="height: 32px; border-radius: 100%;"></a>
<a href="https://github.com/tlambert03"><img alt="tlambert03" src="https://avatars.githubusercontent.com/u/1609449?u=922abf0524b47739b37095e553c99488814b05db&v=4" style="height: 32px; border-radius: 100%;"></a>
<a href="https://github.com/ssbarnea"><img alt="ssbarnea" src="https://avatars.githubusercontent.com/u/102495?u=c7bd9ddf127785286fc939dd18cb02db0a453bce&v=4" style="height: 32px; border-radius: 100%;"></a>
<a href="https://github.com/femtomc"><img alt="femtomc" src="https://avatars.githubusercontent.com/u/34410036?u=f13a71daf2a9f0d2da189beaa94250daa629e2d8&v=4" style="height: 32px; border-radius: 100%;"></a>
<a href="https://github.com/cmarqu"><img alt="cmarqu" src="https://avatars.githubusercontent.com/u/360986?v=4" style="height: 32px; border-radius: 100%;"></a>
<a href="https://github.com/kolenaIO"><img alt="kolenaIO" src="https://avatars.githubusercontent.com/u/77010818?v=4" style="height: 32px; border-radius: 100%;"></a>
<a href="https://github.com/ramnes"><img alt="ramnes" src="https://avatars.githubusercontent.com/u/835072?u=3fca03c3ba0051e2eb652b1def2188a94d1e1dc2&v=4" style="height: 32px; border-radius: 100%;"></a>
<a href="https://github.com/machow"><img alt="machow" src="https://avatars.githubusercontent.com/u/2574498?u=c41e3d2f758a05102d8075e38d67b9c17d4189d7&v=4" style="height: 32px; border-radius: 100%;"></a>
<a href="https://github.com/BenHammersley"><img alt="BenHammersley" src="https://avatars.githubusercontent.com/u/99436?u=4499a7b507541045222ee28ae122dbe3c8d08ab5&v=4" style="height: 32px; border-radius: 100%;"></a>
<a href="https://github.com/trevorWieland"><img alt="trevorWieland" src="https://avatars.githubusercontent.com/u/28811461?u=74cc0e3756c1d4e3d66b5c396e1d131ea8a10472&v=4" style="height: 32px; border-radius: 100%;"></a>
<a href="https://github.com/MarcoGorelli"><img alt="MarcoGorelli" src="https://avatars.githubusercontent.com/u/33491632?u=7de3a749cac76a60baca9777baf71d043a4f884d&v=4" style="height: 32px; border-radius: 100%;"></a>
<a href="https://github.com/analog-cbarber"><img alt="analog-cbarber" src="https://avatars.githubusercontent.com/u/7408243?u=642fc2bdcc9904089c62fe5aec4e03ace32da67d&v=4" style="height: 32px; border-radius: 100%;"></a>
<a href="https://github.com/OdinManiac"><img alt="OdinManiac" src="https://avatars.githubusercontent.com/u/22727172?u=36ab20970f7f52ae8e7eb67b7fcf491fee01ac22&v=4" style="height: 32px; border-radius: 100%;"></a>
<a href="https://github.com/rstudio-sponsorship"><img alt="rstudio-sponsorship" src="https://avatars.githubusercontent.com/u/58949051?u=0c471515dd18111be30dfb7669ed5e778970959b&v=4" style="height: 32px; border-radius: 100%;"></a>
<a href="https://github.com/schlich"><img alt="schlich" src="https://avatars.githubusercontent.com/u/21191435?u=6f1240adb68f21614d809ae52d66509f46b1e877&v=4" style="height: 32px; border-radius: 100%;"></a>
<a href="https://github.com/butterlyn"><img alt="butterlyn" src="https://avatars.githubusercontent.com/u/53323535?v=4" style="height: 32px; border-radius: 100%;"></a>
<a href="https://github.com/livingbio"><img alt="livingbio" src="https://avatars.githubusercontent.com/u/10329983?v=4" style="height: 32px; border-radius: 100%;"></a>
<a href="https://github.com/NemetschekAllplan"><img alt="NemetschekAllplan" src="https://avatars.githubusercontent.com/u/912034?v=4" style="height: 32px; border-radius: 100%;"></a>
<a href="https://github.com/EricJayHartman"><img alt="EricJayHartman" src="https://avatars.githubusercontent.com/u/9259499?u=7e58cc7ec0cd3e85b27aec33656aa0f6612706dd&v=4" style="height: 32px; border-radius: 100%;"></a>
<a href="https://github.com/15r10nk"><img alt="15r10nk" src="https://avatars.githubusercontent.com/u/44680962?u=f04826446ff165742efa81e314bd03bf1724d50e&v=4" style="height: 32px; border-radius: 100%;"></a>
<a href="https://github.com/activeloopai"><img alt="activeloopai" src="https://avatars.githubusercontent.com/u/34816118?v=4" style="height: 32px; border-radius: 100%;"></a>
<a href="https://github.com/roboflow"><img alt="roboflow" src="https://avatars.githubusercontent.com/u/53104118?v=4" style="height: 32px; border-radius: 100%;"></a>
<a href="https://github.com/cmclaughlin"><img alt="cmclaughlin" src="https://avatars.githubusercontent.com/u/1061109?u=ddf6eec0edd2d11c980f8c3aa96e3d044d4e0468&v=4" style="height: 32px; border-radius: 100%;"></a>
<a href="https://github.com/blaisep"><img alt="blaisep" src="https://avatars.githubusercontent.com/u/254456?u=97d584b7c0a6faf583aa59975df4f993f671d121&v=4" style="height: 32px; border-radius: 100%;"></a>
<a href="https://github.com/RapidataAI"><img alt="RapidataAI" src="https://avatars.githubusercontent.com/u/104209891?v=4" style="height: 32px; border-radius: 100%;"></a>
<a href="https://github.com/rodolphebarbanneau"><img alt="rodolphebarbanneau" src="https://avatars.githubusercontent.com/u/46493454?u=6c405452a40c231cdf0b68e97544e07ee956a733&v=4" style="height: 32px; border-radius: 100%;"></a>
<a href="https://github.com/theSymbolSyndicate"><img alt="theSymbolSyndicate" src="https://avatars.githubusercontent.com/u/111542255?v=4" style="height: 32px; border-radius: 100%;"></a>
<a href="https://github.com/blakeNaccarato"><img alt="blakeNaccarato" src="https://avatars.githubusercontent.com/u/20692450?u=bb919218be30cfa994514f4cf39bb2f7cf952df4&v=4" style="height: 32px; border-radius: 100%;"></a>
<a href="https://github.com/ChargeStorm"><img alt="ChargeStorm" src="https://avatars.githubusercontent.com/u/26000165?v=4" style="height: 32px; border-radius: 100%;"></a>
<a href="https://github.com/Alphadelta14"><img alt="Alphadelta14" src="https://avatars.githubusercontent.com/u/480845?v=4" style="height: 32px; border-radius: 100%;"></a>
<a href="https://github.com/Cusp-AI"><img alt="Cusp-AI" src="https://avatars.githubusercontent.com/u/178170649?v=4" style="height: 32px; border-radius: 100%;"></a>
</p></div>


*And 7 more private sponsor(s).*

<!-- sponsors-end -->
