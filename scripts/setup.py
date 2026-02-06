#!/usr/bin/env python3
"""Quick setup script for git-ew.

This script helps you quickly configure git-ew for first use.
"""
# ruff: noqa: ASYNC250, PLC0415

import asyncio
import sys


async def main() -> None:
    """Run the setup wizard."""
    print("=== git-ew Setup Wizard ===\n")

    # Import after the banner so user sees it immediately
    from git_ew._internal.database import Database

    # Initialize database
    print("Initializing database...")
    db = Database()
    await db.init_db()
    print("✓ Database initialized\n")

    # Email configuration
    print("Email Configuration (for sending replies)")
    print("-" * 50)

    smtp_host = input("SMTP Host (e.g., smtp.gmail.com): ").strip()
    smtp_port = input("SMTP Port (default 587): ").strip() or "587"
    from_email = input("Your Email Address: ").strip()
    from_name = input("Your Name: ").strip()
    username = input("SMTP Username (default: same as email): ").strip() or from_email
    password = input("SMTP Password/App Password: ").strip()
    use_tls = input("Use TLS? (Y/n): ").strip().lower() != "n"

    email_config = {
        "smtp_host": smtp_host,
        "smtp_port": int(smtp_port),
        "from_email": from_email,
        "from_name": from_name,
        "username": username,
        "password": password,
        "use_tls": use_tls,
    }

    await db.set_config("email_config", email_config)
    print("✓ Email configuration saved\n")

    # Email source configuration
    print("Email Source Configuration")
    print("-" * 50)
    print("Where should git-ew fetch emails from?")
    print("1. Maildir (local maildir folder)")
    print("2. Mbox (mbox archive file)")
    print("3. Skip for now")

    choice = input("\nChoice (1-3): ").strip()

    if choice == "1":
        import json

        from git_ew._internal.models import EmailSource

        name = input("Source name (e.g., 'my-maildir'): ").strip()
        path = input("Path to maildir folder: ").strip()

        async with db.session() as session:
            source = EmailSource(
                name=name,
                source_type="maildir",
                config=json.dumps({"path": path}),
                enabled=True,
            )
            session.add(source)

        print("✓ Maildir source added\n")

    elif choice == "2":
        import json

        from git_ew._internal.models import EmailSource

        name = input("Source name (e.g., 'mailing-list'): ").strip()
        path = input("Path to mbox file: ").strip()

        async with db.session() as session:
            source = EmailSource(
                name=name,
                source_type="mbox",
                config=json.dumps({"path": path}),
                enabled=True,
            )
            session.add(source)

        print("✓ Mbox source added\n")

    else:
        print("⊘ Skipped email source configuration\n")

    print("=" * 50)
    print("Setup complete! 🎉\n")
    print("To start the server, run:")
    print("  git-ew serve")
    print("\nThen open http://127.0.0.1:8000 in your browser")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nSetup cancelled.")
        sys.exit(1)
    except Exception as e:  # noqa: BLE001
        print(f"\n\nError: {e}")
        sys.exit(1)
