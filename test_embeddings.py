import math

from foundry_local_sdk import Configuration, FoundryLocalManager
from src.document_processor import process_document


def cosine_similarity(vector_a, vector_b):
    """Calculate cosine similarity between two vectors."""

    dot_product = sum(
        a * b for a, b in zip(vector_a, vector_b)
    )

    magnitude_a = math.sqrt(
        sum(value * value for value in vector_a)
    )

    magnitude_b = math.sqrt(
        sum(value * value for value in vector_b)
    )

    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0

    return dot_product / (magnitude_a * magnitude_b)


def main():
    print("Processing the sample document...")

    chunks = process_document(
        "documents/rag_notes.txt",
        chunk_size=60,
        overlap=10
    )

    chunk_contents = [
        chunk["content"] for chunk in chunks
    ]

    print(f"Created {len(chunks)} chunks.")

    config = Configuration(
        app_name="microsoft_local_rag",
        log_level="info"
    )

    FoundryLocalManager.initialize(config)
    manager = FoundryLocalManager.instance

    print("Selecting the embedding model...")

    embedding_model = manager.catalog.get_model(
        "qwen3-embedding-0.6b"
    )

    try:
        print("Downloading the embedding model...")

        embedding_model.download(
            lambda progress: print(
                f"\rDownload progress: {progress:.2f}%",
                end="",
                flush=True
            )
        )

        print("\nLoading the embedding model...")
        embedding_model.load()

        embedding_client = (
            embedding_model.get_embedding_client()
        )

        print("Generating document embeddings...")

        document_response = (
            embedding_client.generate_embeddings(
                chunk_contents
            )
        )

        document_embeddings = [
            item.embedding
            for item in document_response.data
        ]

        question = (
            "Why does a local RAG application "
            "improve privacy?"
        )

        print(f"\nQuestion: {question}")

        question_response = (
            embedding_client.generate_embedding(question)
        )

        question_embedding = (
            question_response.data[0].embedding
        )

        results = []

        for chunk, embedding in zip(
            chunks,
            document_embeddings
        ):
            score = cosine_similarity(
                question_embedding,
                embedding
            )

            results.append((score, chunk))

        results.sort(
            key=lambda result: result[0],
            reverse=True
        )

        print(
            f"Embedding dimensions: "
            f"{len(question_embedding)}"
        )

        print("\nSearch results:")

        for score, chunk in results:
            print("\n" + "=" * 60)
            print(f"Similarity: {score:.4f}")
            print(
                f"Chunk index: "
                f"{chunk['chunk_index']}"
            )
            print(f"Content: {chunk['content']}")

    finally:
        if embedding_model.is_loaded:
            print("\nUnloading the embedding model...")
            embedding_model.unload()

    print("\nEmbedding test completed successfully.")


if __name__ == "__main__":
    main()