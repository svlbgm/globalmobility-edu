import math

from src.database import get_all_chunks


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


def search_chunks(query, embedding_client, top_k=3):
    """Return the document chunks most relevant to a query."""

    if not query.strip():
        raise ValueError("The query cannot be empty.")

    if top_k <= 0:
        raise ValueError("top_k must be greater than zero.")

    stored_chunks = get_all_chunks()

    if not stored_chunks:
        raise ValueError(
            "The knowledge base is empty. Run ingest.py first."
        )

    response = embedding_client.generate_embedding(query)
    query_embedding = response.data[0].embedding

    results = []

    for chunk in stored_chunks:
        score = cosine_similarity(
            query_embedding,
            chunk["embedding"]
        )

        results.append(
            {
                "id": chunk["id"],
                "source": chunk["source"],
                "chunk_index": chunk["chunk_index"],
                "content": chunk["content"],
                "score": score
            }
        )

    results.sort(
        key=lambda result: result["score"],
        reverse=True
    )

    return results[:top_k]