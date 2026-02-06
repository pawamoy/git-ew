"""Zsh-workers mailing list utilities."""

import argparse
import sys
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import urlopen, urlretrieve
from urllib.error import URLError


BASE_URL = "https://www.zsh.org/mla/zsh-workers/"


class LinkExtractor(HTMLParser):
    """Extract .tgz archive links and dates from HTML."""

    def __init__(self):
        super().__init__()
        self.archives: dict[str, datetime | None] = {}
        self._in_pre = False
        self._current_line = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Track pre tags and extract href attributes."""
        if tag == "pre":
            self._in_pre = True
        elif tag == "a" and self._in_pre:
            for attr, value in attrs:
                if attr == "href" and value and value.endswith(".tgz"):
                    filename = value.split("/")[-1]
                    # Date will be extracted from text content after the link
                    self.archives[filename] = None

    def handle_endtag(self, tag: str) -> None:
        """Track end of pre tag."""
        if tag == "pre":
            self._in_pre = False

    def handle_data(self, data: str) -> None:
        """Extract date information from pre-formatted text."""
        if not self._in_pre:
            return

        self._current_line += data

        # Look for date patterns in the line (DD-MMM-YYYY format)
        # Example: "12-Jun-1995"
        if len(self._current_line) > 50:  # Approximate line length
            parts = self._current_line.split()
            for i, part in enumerate(parts):
                # Try to parse date from parts
                if "-" in part and len(parts) > i + 1:
                    try:
                        # Try common date formats
                        date_str = part
                        # Convert French month names to English
                        date_str = date_str.replace("janv.", "Jan")
                        date_str = date_str.replace("févr.", "Feb")
                        date_str = date_str.replace("mars", "Mar")
                        date_str = date_str.replace("avril", "Apr")
                        date_str = date_str.replace("mai", "May")
                        date_str = date_str.replace("juin", "Jun")
                        date_str = date_str.replace("juil.", "Jul")
                        date_str = date_str.replace("août", "Aug")
                        date_str = date_str.replace("sept.", "Sep")
                        date_str = date_str.replace("oct.", "Oct")
                        date_str = date_str.replace("nov.", "Nov")
                        date_str = date_str.replace("déc.", "Dec")

                        parsed = datetime.strptime(date_str, "%d-%b-%Y")
                        # Associate this date with the last archived filename found
                        if self.archives:
                            last_filename = list(self.archives.keys())[-1]
                            if self.archives[last_filename] is None:
                                self.archives[last_filename] = parsed
                    except (ValueError, IndexError):
                        pass

            self._current_line = ""


def fetch_archive_list() -> dict[str, datetime | None]:
    """Fetch the list of available archives from zsh.org with dates.

    Returns:
        Dict mapping archive filenames to their dates (or None if date couldn't be parsed)

    Raises:
        URLError: If the page cannot be fetched.
    """
    try:
        with urlopen(BASE_URL) as response:
            html = response.read().decode('utf-8')
    except URLError as e:
        raise URLError(f"Failed to fetch {BASE_URL}: {e}") from e

    parser = LinkExtractor()
    parser.feed(html)
    # Return sorted by filename
    return dict(sorted(parser.archives.items()))


def get_missing_archives(
    archive_dir: Path,
    available_archives: dict[str, datetime | None],
    since: datetime | None = None,
) -> list[str]:
    """Determine which archives need to be downloaded.

    Args:
        archive_dir: Directory where archives are stored.
        available_archives: Dict of available archive filenames to dates.
        since: Only include archives from this date onwards.

    Returns:
        List of archive filenames that need to be downloaded.
    """
    existing = {f.name for f in archive_dir.glob("*.tgz")}
    missing = []

    for filename, file_date in available_archives.items():
        if filename in existing:
            continue

        # Filter by date if specified
        if since is not None and file_date is not None and file_date < since:
            continue

        missing.append(filename)

    return missing


def download_archive(filename: str, archive_dir: Path) -> bool:
    """Download a single archive.

    Args:
        filename: Archive filename to download.
        archive_dir: Directory to save the archive to.

    Returns:
        True if download succeeded, False otherwise.
    """
    url = BASE_URL + filename
    output_path = archive_dir / filename

    try:
        print(f"Downloading {filename}...", end=" ", flush=True)
        urlretrieve(url, output_path)
        print("✓")
        return True
    except URLError as e:
        print(f"✗ ({e})")
        # Clean up partially downloaded file
        if output_path.exists():
            output_path.unlink()
        return False


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Sync zsh-workers mailing list archives from zsh.org"
    )
    parser.add_argument(
        "-d",
        "--directory",
        type=Path,
        default=Path(".archives"),
        help="Directory to store archives (default: .archives)",
    )
    parser.add_argument(
        "-s",
        "--since",
        type=str,
        help="Only download archives from this date onwards. "
        "Format: YYYY (year) or YYYY-MM-DD (specific date). "
        "Example: --since 2020 or --since 2020-01-15",
    )
    parser.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        help="Show what would be downloaded without actually downloading",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show more detailed output",
    )

    args = parser.parse_args()
    archive_dir = args.directory

    # Parse --since argument
    since_date: datetime | None = None
    if args.since:
        try:
            if len(args.since) == 4:  # Year only (YYYY)
                since_date = datetime.strptime(args.since, "%Y")
            else:  # Full date (YYYY-MM-DD)
                since_date = datetime.strptime(args.since, "%Y-%m-%d")
        except ValueError:
            print(
                f"Error: Invalid date format '{args.since}'. "
                "Use YYYY or YYYY-MM-DD",
                file=sys.stderr,
            )
            return 1

    # Create directory if it doesn't exist
    archive_dir.mkdir(parents=True, exist_ok=True)

    # Fetch available archives
    print("Fetching archive list from zsh.org...")
    try:
        available = fetch_archive_list()
    except URLError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    print(f"Found {len(available)} archives available")

    # Determine missing archives
    missing = get_missing_archives(archive_dir, available, since_date)

    if not missing:
        print("All requested archives already downloaded!")
        return 0

    print(f"Found {len(missing)} new archive(s) to download")

    if args.verbose:
        print("Missing archives:")
        for name in missing:
            print(f"  - {name}")

    if args.dry_run:
        print("\n(dry-run mode: not downloading)")
        return 0

    # Download missing archives
    print()
    success_count = 0
    for filename in missing:
        if download_archive(filename, archive_dir):
            success_count += 1

    print()
    print(f"Downloaded {success_count}/{len(missing)} archive(s)")

    if success_count < len(missing):
        print(f"Warning: {len(missing) - success_count} download(s) failed", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
