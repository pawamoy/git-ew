#!/usr/bin/env python3
"""Ingest all zsh-workers archives into the database."""

from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from git_ew._internal.models import Base
from git_ew._internal.mailing_lists.zsh_workers.ingest import ingest_archive


def main():
    """Ingest all archives."""
    # Initialize sync database
    engine = create_engine("sqlite:///./git_ew.db")
    Base.metadata.create_all(engine)
    session_maker = sessionmaker(bind=engine)

    # Create a mock db object with session_maker for the ingest function
    class MockDB:
        def __init__(self, session_maker):
            self.session_maker = session_maker

    db = MockDB(session_maker)

    archive_dir = Path(".archives")
    archives = sorted(archive_dir.glob("*.tgz"))

    print(f"Found {len(archives)} archives to ingest\n")

    total_inserted = 0
    total_skipped = 0

    for archive_path in archives:
        print(f"Ingesting {archive_path.name}...", end=" ", flush=True)
        try:
            inserted, skipped = ingest_archive(archive_path, db)
            total_inserted += inserted
            total_skipped += skipped

            print(f"✓ ({inserted} new, {skipped} skipped)")
        except Exception as e:
            print(f"✗ Error: {e}")

    print(f"\n{'='*60}")
    print(f"Total emails ingested: {total_inserted}")
    print(f"Total emails skipped (duplicates): {total_skipped}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
