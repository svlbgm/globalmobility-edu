from src.rag_pipeline import RAGPipeline


def main():
    pipeline = RAGPipeline()

    try:
        pipeline.start()

        role = "Operations Manager"

        question = (
            "Several employee computers appear to be "
            "locked by ransomware. What should I do "
            "during the first 30 minutes, and should "
            "the affected computers be powered off?"
        )

        print(f"\nRole: {role}")
        print(f"Question: {question}")

        result = pipeline.answer(
            question=question,
            role=role,
            top_k=4
        )

        print("\nCrisisLens response:")
        print(result["answer"])

        print("\nRetrieved evidence:")

        for source in result["sources"]:
            print(
                f"- {source['source']} "
                f"(relevance: {source['score']:.4f})"
            )

    finally:
        pipeline.stop()


if __name__ == "__main__":
    main()