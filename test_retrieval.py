from foundry_local_sdk import Configuration, FoundryLocalManager

from src.retrieval import search_chunks


def main():
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
        print("Loading the embedding model...")

        embedding_model.download()
        embedding_model.load()

        embedding_client = (
            embedding_model.get_embedding_client()
        )

        question = (
            "Where and how are embeddings stored "
            "in this application?"
        )

        print(f"\nQuestion: {question}")

        results = search_chunks(
            question,
            embedding_client,
            top_k=3
        )

        print("\nRetrieved chunks:")

        for position, result in enumerate(results, start=1):
            print("\n" + "=" * 60)
            print(f"Rank: {position}")
            print(f"Source: {result['source']}")
            print(f"Score: {result['score']:.4f}")
            print(f"Content: {result['content']}")

    finally:
        if embedding_model.is_loaded:
            print("\nUnloading the embedding model...")
            embedding_model.unload()


if __name__ == "__main__":
    main()