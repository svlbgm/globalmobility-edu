import json
import sqlite3
from pathlib import Path


DATABASE_PATH = Path("data") / "knowledge_base.db"

METADATA_COLUMNS = {
    "title": "TEXT NOT NULL DEFAULT ''",
    "version": "TEXT NOT NULL DEFAULT ''",
    "status": "TEXT NOT NULL DEFAULT 'unclassified'",
    "effective_date": "TEXT NOT NULL DEFAULT ''",
    "reviewed_date": "TEXT NOT NULL DEFAULT ''",
    "owner": "TEXT NOT NULL DEFAULT ''",
    "audience": "TEXT NOT NULL DEFAULT ''",
    "supersedes": "TEXT NOT NULL DEFAULT ''",
    "superseded_by": "TEXT NOT NULL DEFAULT ''",
}


def _connect():
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    """Create the chunk table and migrate older databases."""

    with _connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                embedding TEXT NOT NULL
            )
            """
        )

        existing_columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(chunks)"
            ).fetchall()
        }

        for name, definition in METADATA_COLUMNS.items():
            if name not in existing_columns:
                connection.execute(
                    f"ALTER TABLE chunks "
                    f"ADD COLUMN {name} {definition}"
                )


def clear_database():
    """Remove previously indexed chunks."""

    initialize_database()

    with _connect() as connection:
        connection.execute("DELETE FROM chunks")


def insert_chunks(chunks, embeddings):
    """Persist policy chunks and embedding vectors."""

    if len(chunks) != len(embeddings):
        raise ValueError(
            "Each chunk must have exactly one embedding."
        )

    initialize_database()

    rows = []

    for chunk, embedding in zip(chunks, embeddings):
        rows.append(
            (
                chunk["source"],
                chunk["chunk_index"],
                chunk["content"],
                json.dumps(embedding),
                chunk.get("title", ""),
                chunk.get("version", ""),
                chunk.get("status", "unclassified"),
                chunk.get("effective_date", ""),
                chunk.get("reviewed_date", ""),
                chunk.get("owner", ""),
                chunk.get("audience", ""),
                chunk.get("supersedes", ""),
                chunk.get("superseded_by", ""),
            )
        )

    with _connect() as connection:
        connection.executemany(
            """
            INSERT INTO chunks (
                source,
                chunk_index,
                content,
                embedding,
                title,
                version,
                status,
                effective_date,
                reviewed_date,
                owner,
                audience,
                supersedes,
                superseded_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )


def get_all_chunks():
    """Load all indexed chunks and deserialize embeddings."""

    initialize_database()

    with _connect() as connection:
        records = connection.execute(
            """
            SELECT
                source,
                chunk_index,
                content,
                embedding,
                title,
                version,
                status,
                effective_date,
                reviewed_date,
                owner,
                audience,
                supersedes,
                superseded_by
            FROM chunks
            """
        ).fetchall()

    chunks = []

    for record in records:
        chunk = dict(record)
        chunk["embedding"] = json.loads(chunk["embedding"])
        chunks.append(chunk)

    return chunks


def get_chunk_count():
    """Return the number of indexed policy sections."""

    initialize_database()

    with _connect() as connection:
        row = connection.execute(
            "SELECT COUNT(*) AS count FROM chunks"
        ).fetchone()

    return row["count"]
