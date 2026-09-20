from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pyodbc

from solution import audit_email


ROOT = Path(__file__).parent
SERVER = os.getenv("MSSQL_SERVER", r"localhost\MSSQLSERVER01")
DATABASE = os.getenv("MSSQL_DATABASE", "DocuAnchorDB")
DRIVER = os.getenv("MSSQL_DRIVER", "ODBC Driver 18 for SQL Server")

SCHEMA = """
IF OBJECT_ID(N'dbo.attachments', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.attachments (
        attachment_id BIGINT IDENTITY(1,1) PRIMARY KEY,
        email_id NVARCHAR(64) NOT NULL,
        relative_path NVARCHAR(512) NOT NULL,
        filename NVARCHAR(255) NOT NULL,
        extension NVARCHAR(32) NOT NULL,
        size_bytes BIGINT NOT NULL,
        sha256 CHAR(64) NOT NULL,
        content VARBINARY(MAX) NOT NULL,
        CONSTRAINT UQ_attachments_email_path UNIQUE (email_id, relative_path)
    );
END;
IF OBJECT_ID(N'dbo.emails', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.emails (
        email_id NVARCHAR(64) PRIMARY KEY,
        sender NVARCHAR(512) NOT NULL DEFAULT N'',
        subject NVARCHAR(2000) NOT NULL DEFAULT N'',
        body NVARCHAR(MAX) NOT NULL DEFAULT N'',
        source_path NVARCHAR(512) NOT NULL,
        category NVARCHAR(32) NULL,
        status NVARCHAR(32) NULL,
        review_reason NVARCHAR(64) NULL,
        defect_fields_json NVARCHAR(MAX) NOT NULL DEFAULT N'[]',
        has_defect BIT NOT NULL DEFAULT 0
    );
END;
"""


def connection_string() -> str:
    return (
        f"DRIVER={{{DRIVER}}};SERVER={SERVER};DATABASE={DATABASE};"
        "Trusted_Connection=yes;Encrypt=yes;TrustServerCertificate=yes;"
    )


def import_dataset(root: Path = ROOT) -> dict[str, int | str]:
    connection = pyodbc.connect(connection_string(), autocommit=False)
    cursor = connection.cursor()
    cursor.execute(SCHEMA)
    email_count = 0
    attachment_count = 0
    try:
        for email_path in sorted((root / "inbox").glob("email_*.json")):
            record = json.loads(email_path.read_text(encoding="utf-8"))
            email_id = record.get("email_id", email_path.stem)
            result = audit_email(record, root)
            cursor.execute("DELETE FROM attachments WHERE email_id = ?", email_id)
            cursor.execute("DELETE FROM emails WHERE email_id = ?", email_id)
            cursor.execute(
                """
                INSERT INTO dbo.emails
                    (email_id, sender, subject, body, source_path, category, status,
                     review_reason, defect_fields_json, has_defect)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                email_id, record.get("from", ""), record.get("subject", ""), record.get("body", ""),
                email_path.relative_to(root).as_posix(), result["category"], result["status"],
                result["review_reason"], json.dumps(result["defect_fields"]), result["has_defect"],
            )
            for relative_name in record.get("attachments", []):
                attachment_path = root / relative_name
                if not attachment_path.is_file():
                    continue
                content = attachment_path.read_bytes()
                cursor.execute(
                    """
                    INSERT INTO dbo.attachments
                        (email_id, relative_path, filename, extension, size_bytes, sha256, content)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    email_id, Path(relative_name).as_posix(), attachment_path.name,
                    attachment_path.suffix.lower(), len(content), hashlib.sha256(content).hexdigest(), content,
                )
                attachment_count += 1
            email_count += 1
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
    return {"server": SERVER, "database": DATABASE, "emails": email_count, "attachments": attachment_count}


if __name__ == "__main__":
    print(json.dumps(import_dataset(), indent=2))