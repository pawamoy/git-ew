# SPDX-License-Identifier: ISC

# Copyright (c) 2021, Timothée Mazzucotelli and contributors

# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.

# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""Zsh-workers mailing list utilities."""

import argparse
import logging
import sys
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from time import strptime
from urllib.error import URLError
from urllib.request import urlopen, urlretrieve

BASE_URL = "https://www.zsh.org/mla/zsh-workers/"
_logger = logging.getLogger(__name__)


class LinkExtractor(HTMLParser):
    """Extract .tgz archive links and dates from HTML."""

    def __init__(self):
        super().__init__()
        self.archives: dict[str, date | None] = {}
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
        if len(self._current_line) > 50:  # Approximate line length  # noqa: PLR2004
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

                        parsed_time = strptime(date_str, "%d-%b-%Y")
                        parsed = date(parsed_time.tm_year, parsed_time.tm_mon, parsed_time.tm_mday)
                        # Associate this date with the last archived filename found
                        if self.archives:
                            last_filename = list(self.archives.keys())[-1]
                            if self.archives[last_filename] is None:
                                self.archives[last_filename] = parsed
                    except (ValueError, IndexError):
                        _logger.debug("Could not parse archive date from %r", part, exc_info=True)

            self._current_line = ""


def fetch_archive_list() -> dict[str, date | None]:
    """Fetch the list of available archives from zsh.org with dates.

    Returns:
        Dict mapping archive filenames to their dates (or None if date couldn't be parsed)

    Raises:
        URLError: If the page cannot be fetched.
    """
    try:
        with urlopen(BASE_URL) as response:
            html = response.read().decode("utf-8")
    except URLError as e:
        raise URLError(f"Failed to fetch {BASE_URL}: {e}") from e

    parser = LinkExtractor()
    parser.feed(html)
    # Return sorted by filename
    return dict(sorted(parser.archives.items()))


def _get_matching_archives(
    available_archives: dict[str, date | None],
    since: date | None = None,
    until: date | None = None,
) -> list[str]:
    """Return archive filenames within the requested date range.

    Args:
        available_archives: Dict of available archive filenames to dates.
        since: Only include archives from this date onwards.
        until: Only include archives up to this date.

    Returns:
        Archive filenames within the requested date range.
    """
    matching = []

    for filename, file_date in available_archives.items():
        if since is not None and file_date is not None and file_date < since:
            continue
        if until is not None and file_date is not None and file_date > until:
            continue

        matching.append(filename)

    return matching


def get_missing_archives(
    archive_dir: Path,
    available_archives: dict[str, date | None],
    since: date | None = None,
    until: date | None = None,
) -> list[str]:
    """Determine which matching archives need to be downloaded.

    Args:
        archive_dir: Directory where archives are stored.
        available_archives: Dict of available archive filenames to dates.
        since: Only include archives from this date onwards.
        until: Only include archives up to this date.

    Returns:
        Matching archive filenames that do not exist locally.
    """
    existing = {file.name for file in archive_dir.glob("*.tgz")}

    return [
        filename for filename in _get_matching_archives(available_archives, since, until) if filename not in existing
    ]


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
        _logger.info("Downloading %s", filename)
        urlretrieve(url, output_path)  # noqa: S310
        _logger.info("Downloaded %s", filename)
    except URLError as error:
        _logger.error("Failed to download %s: %s", filename, error)  # noqa: TRY400
        # Clean up partially downloaded file
        if output_path.exists():
            output_path.unlink()
        return False
    else:
        return True


def main() -> int:
    """Main entry point."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(
        description="Sync zsh-workers mailing list archives from zsh.org",
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
    since_date: date | None = None
    if args.since:
        try:
            since_date = (
                date(int(args.since), 1, 1)
                if len(args.since) == 4  # noqa: PLR2004
                else date.fromisoformat(args.since)
            )
        except ValueError:
            _logger.error("Invalid date format %r. Use YYYY or YYYY-MM-DD", args.since)  # noqa: TRY400
            return 1

    # Create directory if it doesn't exist
    archive_dir.mkdir(parents=True, exist_ok=True)

    # Fetch available archives
    _logger.info("Fetching archive list from zsh.org")
    try:
        available = fetch_archive_list()
    except URLError as error:
        _logger.error("Failed to fetch archive list: %s", error)  # noqa: TRY400
        return 1

    _logger.info("Found %d archives available", len(available))

    # Determine missing archives
    missing = get_missing_archives(archive_dir, available, since_date)

    if not missing:
        _logger.info("All requested archives are already downloaded")
        return 0

    _logger.info("Found %d new archives to download", len(missing))

    if args.verbose:
        _logger.info("Missing archives:")
        for name in missing:
            _logger.info("  - %s", name)

    if args.dry_run:
        _logger.info("Dry-run: no archives downloaded")
        return 0

    success_count = 0
    for filename in missing:
        if download_archive(filename, archive_dir):
            success_count += 1

    _logger.info("Downloaded %d/%d archives", success_count, len(missing))

    if success_count < len(missing):
        _logger.warning("%d archive downloads failed", len(missing) - success_count)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
