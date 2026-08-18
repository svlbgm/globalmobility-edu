import json
import sqlite3
from pathlib import Path


DATABASE_PATH = Path("data/knowledge_base.db")


def get_connection():
    """Create and return a connection to the SQLite database."""

    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row

    return connection


def initialize_database():
    """Create the document chunks table if it does not exist."""

    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS document_chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                embedding TEXT NOT NULL,
                UNIQUE(source, chunk_index)
            )
            """
        )


def clear_database():
    """Remove all existing document chunks."""

    with get_connection() as connection:
        connection.execute("DELETE FROM document_chunks")


def insert_chunks(chunks, embeddings):
    """Insert document chunks and embeddings into SQLite."""

    if len(chunks) != len(embeddings):
        raise ValueError(
            "The number of chunks and embeddings must match."
        )

    records = []

    for chunk, embedding in zip(chunks, embeddings):
        records.append(
            (
                chunk["source"],
                chunk["chunk_index"],
                chunk["content"],
                json.dumps(embedding)
            )
        )

    with get_connection() as connection:
        connection.executemany(
            """
            INSERT OR REPLACE INTO document_chunks (
                source,
                chunk_index,
                content,
                embedding
            )
            VALUES (?, ?, ?, ?)
            """,
            records
        )


def get_all_chunks():
    """Retrieve all chunks and deserialize their embeddings."""

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, source, chunk_index, content, embedding
            FROM document_chunks
            ORDER BY source, chunk_index
            """
        ).fetchall()

    return [
        {
            "id": row["id"],
            "source": row["source"],
            "chunk_index": row["chunk_index"],
            "content": row["content"],
            "embedding": json.loads(row["embedding"])
        }
        for row in rows
    ]


def get_chunk_count():
    """Return the number of chunks stored in the database."""

    with get_connection() as connection:
        result = connection.execute(
            "SELECT COUNT(*) FROM document_chunks"
        ).fetchone()

    return result[0]