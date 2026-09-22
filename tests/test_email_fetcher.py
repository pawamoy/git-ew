"""Tests for email source fetchers."""

from git_ew._internal.email_fetcher import IMAPFetcher


def test_imap_fetcher_filters_by_mailing_list_headers() -> None:
    """Accept list headers and reject unrelated messages."""
    fetcher = IMAPFetcher(
        "imap.example.com",
        "user@example.com",
        "password",
        mailing_list={
            "addresses": ["zsh-workers@zsh.org"],
            "list_ids": ["zsh-workers.zsh.org"],
        },
    )

    list_headers = b"""\
Message-ID: <list@example.com>
To: zsh-workers@zsh.org
List-Id: <zsh-workers.zsh.org>

"""
    unrelated_headers = b"""\
Message-ID: <other@example.com>
To: someone@example.com

"""

    assert fetcher._matches_mailing_list(list_headers)
    assert not fetcher._matches_mailing_list(unrelated_headers)
