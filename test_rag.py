from src.rag_pipeline import RAGPipeline


def main():
    pipeline = RAGPipeline()

    try:
        pipeline.start()

        question = (
            "How does this application store and use "
            "document embeddings?"
        )

        print(f"\nQuestion: {question}")

        result = pipeline.answer(
            question,
            top_k=3
        )

        print("\nGrounded answer:")
        print(result["answer"])

        print("\nRetrieved sources:")

        for source in result["sources"]:
            print(
                f"- {source['source']} "
                f"(similarity: {source['score']:.4f})"
            )

    finally:
        pipeline.stop()


if __name__ == "__main__":
    main()