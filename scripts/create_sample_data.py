#!/usr/bin/env python3
"""Create sample data for testing git-ew.

This script creates some sample email threads to demonstrate the interface.
"""

import asyncio
from datetime import UTC, datetime, timedelta

from git_ew._internal.database import Database


async def create_sample_data() -> None:
    """Create sample threads and messages."""
    print("Creating sample data...")

    db = Database()
    await db.init_db()

    # Sample thread 1: Bug report
    print("Creating bug report thread...")
    thread1 = await db.create_thread(
        subject="Bug: Segfault in parser.c",
        first_message_id="bug-001@example.com",
        is_patch=False,
    )

    now = datetime.now(UTC)

    # Initial bug report
    await db.create_message(
        message_id="bug-001@example.com",
        thread_id=thread1.id,
        from_email="alice@example.com",
        from_name="Alice Developer",
        subject="Bug: Segfault in parser.c",
        date=now - timedelta(days=3),
        body="""Hi,

I'm experiencing a segfault in parser.c when parsing large files.

Steps to reproduce:
1. Compile with gcc 12.0
2. Run: ./parser large_file.txt
3. Segfault occurs at line 234

Environment:
- OS: Linux 6.5
- Architecture: x86_64

Thanks!
Alice""",
    )

    # First reply
    await db.create_message(
        message_id="bug-001-reply-1@example.com",
        thread_id=thread1.id,
        from_email="bob@example.com",
        from_name="Bob Maintainer",
        subject="Re: Bug: Segfault in parser.c",
        date=now - timedelta(days=2, hours=12),
        body="""Hi Alice,

Thanks for the report. I can reproduce this issue.

Looking at line 234, it seems we're not checking for NULL before dereferencing.

I'll prepare a patch.

Bob""",
        in_reply_to="bug-001@example.com",
    )

    # Sample thread 2: Patch submission
    print("Creating patch thread...")
    thread2 = await db.create_thread(
        subject="[PATCH] Fix buffer overflow in parser",
        first_message_id="patch-001@example.com",
        is_patch=True,
    )

    # Patch email
    await db.create_message(
        message_id="patch-001@example.com",
        thread_id=thread2.id,
        from_email="bob@example.com",
        from_name="Bob Maintainer",
        subject="[PATCH] Fix buffer overflow in parser",
        date=now - timedelta(days=2),
        body="""This patch fixes the buffer overflow issue reported in bug-001.

The problem was a missing NULL check before dereferencing the pointer.

Tested on Linux x86_64 with various large files.

Signed-off-by: Bob Maintainer <bob@example.com>
---""",
        is_patch=True,
        patch_content="""diff --git a/parser.c b/parser.c
index 1234567..89abcdef 100644
--- a/parser.c
+++ b/parser.c
@@ -231,6 +231,10 @@ int parse_line(char *line) {
     char *token;

     token = get_next_token(line);
+    if (token == NULL) {
+        fprintf(stderr, "Error: NULL token\\n");
+        return -1;
+    }

     process_token(token);
     return 0;
""",
    )

    # Review comment 1
    await db.create_message(
        message_id="patch-001-review-1@example.com",
        thread_id=thread2.id,
        from_email="charlie@example.com",
        from_name="Charlie Reviewer",
        subject="Re: [PATCH] Fix buffer overflow in parser",
        date=now - timedelta(days=1, hours=18),
        body="""Looks good to me!

Tested this patch with the reproducer from bug-001 and it works correctly.

Reviewed-by: Charlie Reviewer <charlie@example.com>""",
        in_reply_to="patch-001@example.com",
    )

    # Review comment 2
    await db.create_message(
        message_id="patch-001-review-2@example.com",
        thread_id=thread2.id,
        from_email="dana@example.com",
        from_name="Dana Expert",
        subject="Re: [PATCH] Fix buffer overflow in parser",
        date=now - timedelta(days=1, hours=15),
        body="""Nice catch! One minor suggestion:

Instead of fprintf to stderr, should we use the existing error logging
function error_log()? That way it's consistent with the rest of the codebase.

Otherwise LGTM.

Dana""",
        in_reply_to="patch-001@example.com",
    )

    # Reply to review
    await db.create_message(
        message_id="patch-001-review-2-reply@example.com",
        thread_id=thread2.id,
        from_email="bob@example.com",
        from_name="Bob Maintainer",
        subject="Re: [PATCH] Fix buffer overflow in parser",
        date=now - timedelta(days=1, hours=10),
        body="""Good point Dana!

I'll update the patch to use error_log() and send a v2.

Thanks for the review!

Bob""",
        in_reply_to="patch-001-review-2@example.com",
    )

    # Sample thread 3: Feature discussion
    print("Creating feature discussion thread...")
    thread3 = await db.create_thread(
        subject="RFC: Add support for UTF-8 in parser",
        first_message_id="rfc-001@example.com",
        is_patch=False,
    )

    await db.create_message(
        message_id="rfc-001@example.com",
        thread_id=thread3.id,
        from_email="eve@example.com",
        from_name="Eve Contributor",
        subject="RFC: Add support for UTF-8 in parser",
        date=now - timedelta(days=5),
        body="""Hi all,

I'd like to propose adding UTF-8 support to the parser. Currently it only
handles ASCII, which limits its usefulness for international users.

My proposed approach:
1. Add a new utf8_mode flag
2. Update tokenizer to handle multibyte characters
3. Maintain backward compatibility with ASCII mode

What do you think?

Best,
Eve""",
    )

    # Multiple replies to show branching
    await db.create_message(
        message_id="rfc-001-reply-1@example.com",
        thread_id=thread3.id,
        from_email="frank@example.com",
        from_name="Frank User",
        subject="Re: RFC: Add support for UTF-8 in parser",
        date=now - timedelta(days=4, hours=20),
        body="""Great idea! I've been wanting this for a while.

One concern: will this affect performance for ASCII-only files?

Frank""",
        in_reply_to="rfc-001@example.com",
    )

    await db.create_message(
        message_id="rfc-001-reply-2@example.com",
        thread_id=thread3.id,
        from_email="grace@example.com",
        from_name="Grace Architect",
        subject="Re: RFC: Add support for UTF-8 in parser",
        date=now - timedelta(days=4, hours=18),
        body="""+1 from me.

We should probably also consider:
- What encoding to default to
- How to handle invalid UTF-8 sequences
- Documentation updates

Grace""",
        in_reply_to="rfc-001@example.com",
    )

    print("\n✓ Sample data created successfully!")
    print("\nCreated:")
    print(f"  - Thread 1: {thread1.subject}")
    print(f"  - Thread 2: {thread2.subject}")
    print(f"  - Thread 3: {thread3.subject}")
    print("\nStart the server with: git-ew serve")


if __name__ == "__main__":
    asyncio.run(create_sample_data())
