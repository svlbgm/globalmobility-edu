from pathlib import Path

from foundry_local_sdk import Configuration, FoundryLocalManager

from src.database import (
    clear_database,
    get_chunk_count,
    initialize_database,
    insert_chunks
)
from src.document_processor import (
    SUPPORTED_EXTENSIONS,
    process_document
)


DOCUMENTS_DIRECTORY = Path("documents")


def load_documents():
    """Process all supported documents in the documents folder."""

    all_chunks = []

    document_paths = [
        path
        for path in DOCUMENTS_DIRECTORY.iterdir()
        if path.is_file()
        and path.suffix.lower() in SUPPORTED_EXTENSIONS
    ]

    if not document_paths:
        raise FileNotFoundError(
            "No supported documents were found."
        )

    for path in document_paths:
        print(f"Processing: {path.name}")

        chunks = process_document(
            path,
            chunk_size=180,
            overlap=30
        )

        all_chunks.extend(chunks)

        print(f"Created {len(chunks)} chunks.")

    return all_chunks


def main():
    print("Starting document ingestion...")

    chunks = load_documents()
    contents = [chunk["content"] for chunk in chunks]

    config = Configuration(
        app_name="microsoft_local_rag",
        log_level="info"
    )

    FoundryLocalManager.initialize(config)
    manager = FoundryLocalManager.instance

    embedding_model = manager.catalog.get_model(
        "qwen3-embedding-0.6b"
    )

    try:
        print("Preparing the embedding model...")

        embedding_model.download(
            lambda progress: print(
                f"\rDownload progress: {progress:.2f}%",
                end="",
                flush=True
            )
        )

        print("\nLoading the embedding model...")
        embedding_model.load()

        client = embedding_model.get_embedding_client()

        print(
            f"Generating embeddings for "
            f"{len(contents)} chunks..."
        )

        response = client.generate_embeddings(contents)

        embeddings = [
            item.embedding
            for item in response.data
        ]

        initialize_database()
        clear_database()
        insert_chunks(chunks, embeddings)

        print(
            f"\nSuccessfully stored "
            f"{get_chunk_count()} chunks in SQLite."
        )

    finally:
        if embedding_model.is_loaded:
            print("Unloading the embedding model...")
            embedding_model.unload()

    print("Document ingestion completed successfully.")


if __name__ == "__main__":
    main()