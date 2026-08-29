from src.rag_pipeline import RAGPipeline


def main():
    pipeline = RAGPipeline()

    try:
        pipeline.start()
        role = "Student"
        question = (
            "The older exchange guide says I can request "
            "course approval after returning, but the current "
            "policy requires pre-approval. Which procedure applies?"
        )

        print(f"\nRole: {role}")
        print(f"Question: {question}")
        result = pipeline.answer(
            question=question,
            role=role,
            top_k=4,
        )

        print("\nGlobalMobility EDU response:")
        print(result["answer"])
        print("\nRetrieved evidence:")

        for source in result["sources"]:
            print(
                f"- {source['source']} | "
                f"status={source['status']} | "
                f"final={source['score']:.4f} | "
                f"semantic={source['semantic_score']:.4f}"
            )

        issues = result["validation_issues"]

        if issues:
            print("\nSemantic validation failures:")

            for issue in issues:
                print(f"- {issue}")

            raise AssertionError(
                "The generated answer did not satisfy the "
                "GlobalMobility EDU response contract."
            )

        forbidden_content = (
            "personal equivalency proposal",
            "international programs office",
            "double-major course counting",
        )
        lowered_answer = result["answer"].lower()

        for phrase in forbidden_content:
            if phrase in lowered_answer:
                raise AssertionError(
                    "The answer reused irrelevant or historical content: "
                    + phrase
                )

        expected_sources = [
            "exchange_course_recognition_v2_2026.txt",
            "exchange_course_recognition_v1_2022.txt",
        ]
        actual_sources = [
            source["source"]
            for source in result["sources"][:2]
        ]

        if actual_sources != expected_sources:
            raise AssertionError(
                "The current policy and its linked legacy version "
                f"were not retrieved first: {actual_sources}"
            )

        print("\nSemantic validation: PASS")
    finally:
        pipeline.stop()


if __name__ == "__main__":
    main()
