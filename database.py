from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

from solution import audit_email


SCHEMA = """
CREATE TABLE IF NOT EXISTS emails (
    email_id TEXT PRIMARY KEY,
    sender TEXT NOT NULL DEFAULT '',
    subject TEXT NOT NULL DEFAULT '',
    body TEXT NOT NULL DEFAULT '',
    source_path TEXT NOT NULL,
    category TEXT,
    status TEXT,
    review_reason TEXT,
    defect_fields_json TEXT NOT NULL DEFAULT '[]',
    has_defect INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS attachments (
    attachment_id INTEGER PRIMARY KEY,
    email_id TEXT NOT NULL REFERENCES emails(email_id) ON DELETE CASCADE,
    relative_path TEXT NOT NULL,
    filename TEXT NOT NULL,
    extension TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    sha256 TEXT NOT NULL,
    content BLOB NOT NULL,
    UNIQUE(email_id, relative_path)
);

CREATE INDEX IF NOT EXISTS idx_emails_category ON emails(category);
CREATE INDEX IF NOT EXISTS idx_emails_status ON emails(status);
CREATE INDEX IF NOT EXISTS idx_attachments_email_id ON attachments(email_id);
"""


def connect(database_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(database_path)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(SCHEMA)
    return connection


def import_dataset(root: Path, database_path: Path) -> dict[str, Any]:
    inbox_dir = root / "inbox"
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = connect(database_path)
    email_count = 0
    attachment_count = 0
    with connection:
        for email_path in sorted(inbox_dir.glob("email_*.json")):
            record = json.loads(email_path.read_text(encoding="utf-8"))
            email_id = record.get("email_id", email_path.stem)
            result = audit_email(record, root)
            connection.execute(
                """
                INSERT INTO emails
                    (email_id, sender, subject, body, source_path, category, status,
                     review_reason, defect_fields_json, has_defect)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(email_id) DO UPDATE SET
                    sender=excluded.sender, subject=excluded.subject, body=excluded.body,
                    source_path=excluded.source_path, category=excluded.category,
                    status=excluded.status, review_reason=excluded.review_reason,
                    defect_fields_json=excluded.defect_fields_json, has_defect=excluded.has_defect
                """,
                (
                    email_id,
                    record.get("from", ""),
                    record.get("subject", ""),
                    record.get("body", ""),
                    email_path.relative_to(root).as_posix(),
                    result["category"],
                    result["status"],
                    result["review_reason"],
                    json.dumps(result["defect_fields"]),
                    int(result["has_defect"]),
                ),
            )
            connection.execute("DELETE FROM attachments WHERE email_id = ?", (email_id,))
            for relative_name in record.get("attachments", []):
                attachment_path = root / relative_name
                if not attachment_path.is_file():
                    continue
                content = attachment_path.read_bytes()
                connection.execute(
                    """
                    INSERT INTO attachments
                        (email_id, relative_path, filename, extension, size_bytes, sha256, content)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        email_id,
                        Path(relative_name).as_posix(),
                        attachment_path.name,
                        attachment_path.suffix.lower(),
                        len(content),
                        hashlib.sha256(content).hexdigest(),
                        content,
                    ),
                )
                attachment_count += 1
            email_count += 1
    connection.close()
    return {
        "database": str(database_path),
        "emails": email_count,
        "attachments": attachment_count,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Import the inbox and attachments into SQLite.")
    parser.add_argument("--root", type=Path, default=Path(__file__).parent)
    parser.add_argument("--database", type=Path, default=Path("docuanchor.db"))
    args = parser.parse_args()
    summary = import_dataset(args.root.resolve(), args.database)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()