from foundry_local_sdk import Configuration, FoundryLocalManager

from src.document_processor import process_document
from src.retrieval import cosine_similarity


def main():
    chunks = process_document(
        "documents/exchange_course_recognition_v2_2026.txt"
    )
    contents = [
        chunk["embedding_text"]
        for chunk in chunks
    ]

    configuration = Configuration(
        app_name="globalmobility_embedding_test",
        log_level="info",
    )
    FoundryLocalManager.initialize(configuration)
    manager = FoundryLocalManager.instance
    model = manager.catalog.get_model("qwen3-embedding-0.6b")

    try:
        model.download()
        model.load()
        client = model.get_embedding_client()
        document_response = client.generate_embeddings(contents)
        document_embeddings = [
            item.embedding
            for item in document_response.data
        ]

        question = (
            "Must exchange courses be reviewed before mobility?"
        )
        question_response = client.generate_embedding(question)
        question_embedding = question_response.data[0].embedding

        print(f"Question: {question}")
        print(
            f"Embedding dimensions: {len(question_embedding)}"
        )

        for chunk, embedding in zip(
            chunks,
            document_embeddings,
        ):
            score = cosine_similarity(
                question_embedding,
                embedding,
            )
            print("\n" + "=" * 60)
            print(f"Similarity: {score:.4f}")
            print(f"Status: {chunk['status']}")
            print(f"Content: {chunk['content']}")
    finally:
        if model.is_loaded:
            model.unload()


if __name__ == "__main__":
    main()
