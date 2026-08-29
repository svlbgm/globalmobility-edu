from pathlib import Path

from foundry_local_sdk import Configuration, FoundryLocalManager

from src.database import (
    clear_database,
    get_chunk_count,
    initialize_database,
    insert_chunks,
)
from src.document_processor import (
    SUPPORTED_EXTENSIONS,
    process_document,
)


DOCUMENTS_DIRECTORY = Path("documents")


def load_documents():
    """Process supported files directly inside documents/."""

    if not DOCUMENTS_DIRECTORY.exists():
        raise FileNotFoundError(
            "The documents folder does not exist."
        )

    document_paths = sorted(
        path
        for path in DOCUMENTS_DIRECTORY.iterdir()
        if path.is_file()
        and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )

    if not document_paths:
        raise FileNotFoundError(
            "No supported policy documents were found."
        )

    all_chunks = []

    for path in document_paths:
        print(f"Processing: {path.name}")
        chunks = process_document(
            path,
            chunk_size=180,
            overlap=30,
        )

        if not chunks:
            print("Skipped: no readable policy text.")
            continue

        all_chunks.extend(chunks)
        status = chunks[0].get("status", "unclassified")
        version = chunks[0].get("version", "unknown")
        print(
            f"Created {len(chunks)} chunks "
            f"(version={version}, status={status})."
        )

    if not all_chunks:
        raise RuntimeError(
            "The policy documents produced no chunks."
        )

    return all_chunks


def main():
    print("Starting GlobalMobility EDU ingestion...")
    chunks = load_documents()
    embedding_inputs = [
        chunk["embedding_text"]
        for chunk in chunks
    ]

    configuration = Configuration(
        app_name="globalmobility_edu_ingestion",
        log_level="info",
    )
    FoundryLocalManager.initialize(configuration)
    manager = FoundryLocalManager.instance
    embedding_model = manager.catalog.get_model(
        "qwen3-embedding-0.6b"
    )

    try:
        print("Preparing the embedding model...")
        embedding_model.download()
        print("Loading the embedding model...")
        embedding_model.load()
        client = embedding_model.get_embedding_client()

        print(
            f"Generating embeddings for "
            f"{len(embedding_inputs)} policy sections..."
        )
        response = client.generate_embeddings(
            embedding_inputs
        )
        embeddings = [
            item.embedding
            for item in response.data
        ]

        initialize_database()
        clear_database()
        insert_chunks(chunks, embeddings)

        print(
            f"Successfully stored "
            f"{get_chunk_count()} policy sections in SQLite."
        )
    finally:
        if embedding_model.is_loaded:
            print("Unloading the embedding model...")
            embedding_model.unload()

    print("GlobalMobility EDU ingestion completed successfully.")


if __name__ == "__main__":
    main()
