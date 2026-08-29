from foundry_local_sdk import Configuration, FoundryLocalManager

from src.retrieval import search_chunks


def main():
    configuration = Configuration(
        app_name="globalmobility_retrieval_test",
        log_level="info",
    )
    FoundryLocalManager.initialize(configuration)
    manager = FoundryLocalManager.instance
    model = manager.catalog.get_model("qwen3-embedding-0.6b")

    try:
        model.download()
        model.load()
        client = model.get_embedding_client()
        question = (
            "Which exchange course-recognition version applies, "
            "and can approval wait until after return?"
        )
        results = search_chunks(
            question=question,
            embedding_client=client,
            top_k=4,
            role="Student",
        )

        print(f"Question: {question}")
        print("\nGovernance-aware retrieval results:")

        for position, result in enumerate(results, start=1):
            print("\n" + "=" * 60)
            print(f"Rank: {position}")
            print(f"Source: {result['source']}")
            print(f"Status: {result['status']}")
            print(f"Final score: {result['score']:.4f}")
            print(
                f"Semantic={result['semantic_score']:.4f}, "
                f"Status={result['status_score']:.4f}, "
                f"Recency={result['recency_score']:.4f}, "
                f"Role={result['role_score']:.4f}"
            )
            print(f"Content: {result['content']}")
    finally:
        if model.is_loaded:
            model.unload()


if __name__ == "__main__":
    main()
