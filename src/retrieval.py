import math
from datetime import date, datetime

from src.database import get_all_chunks


SEMANTIC_WEIGHT = 0.60
STATUS_WEIGHT = 0.20
RECENCY_WEIGHT = 0.10
ROLE_WEIGHT = 0.10


def cosine_similarity(vector_a, vector_b):
    """Calculate cosine similarity between two vectors."""

    dot_product = sum(
        value_a * value_b
        for value_a, value_b in zip(vector_a, vector_b)
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


def _status_score(status):
    scores = {
        "current_approved": 1.00,
        "current": 0.85,
        "draft": 0.45,
        "unclassified": 0.35,
        "superseded": 0.20,
        "legacy": 0.10,
        "legacy_unverified": 0.00,
    }
    return scores.get(status.strip().lower(), 0.35)


def _recency_score(effective_date):
    try:
        effective = datetime.strptime(
            effective_date,
            "%Y-%m-%d",
        ).date()
    except (TypeError, ValueError):
        return 0.30

    age_days = max(0, (date.today() - effective).days)
    return max(0.0, 1.0 - age_days / 3650)


def _role_score(audience, role):
    if not role:
        return 0.50

    allowed_roles = {
        item.strip().lower()
        for item in (audience or "").split(",")
        if item.strip()
    }

    if role.strip().lower() in allowed_roles:
        return 1.00

    if "all" in allowed_roles:
        return 0.80

    return 0.15


def _linked_sources(result):
    """Return explicit version relationships from metadata."""

    linked = []

    for field in ("supersedes", "superseded_by"):
        linked.extend(
            source.strip()
            for source in result.get(field, "").split(",")
            if source.strip()
        )

    return linked


def _include_strongest_linked_versions(ranked_results, limit):
    """Keep the strongest policy, its sibling chunks and linked version
    together, so a document split across chunks is not answered from a
    single fragment while a sibling chunk with directly relevant facts
    is left out of the generation context."""

    if not ranked_results:
        return []

    strongest = ranked_results[0]
    chunks_by_source = {}

    for result in ranked_results:
        chunks_by_source.setdefault(result["source"], []).append(result)

    selected = [strongest]

    for sibling in chunks_by_source.get(strongest["source"], []):
        if sibling is strongest or sibling in selected:
            continue

        selected.append(sibling)

        if len(selected) >= limit:
            return selected[:limit]

    for source in _linked_sources(strongest):
        candidates = chunks_by_source.get(source, [])

        for related in candidates:
            if related in selected:
                continue

            related = dict(related)
            related["relationship_included"] = True
            selected.append(related)
            break

        if len(selected) >= limit:
            return selected[:limit]

    for result in ranked_results[1:]:
        if any(
            item["source"] == result["source"]
            for item in selected
        ):
            continue

        selected.append(result)

        if len(selected) >= limit:
            break

    return selected


def search_chunks(
    question,
    embedding_client,
    top_k=3,
    role=None,
):
    """Retrieve and governance-rerank policy sections."""

    if not question.strip():
        raise ValueError("The question cannot be empty.")

    chunks = get_all_chunks()

    if not chunks:
        raise RuntimeError(
            "No policy sections are indexed. Run ingest.py first."
        )

    response = embedding_client.generate_embedding(question)
    question_embedding = response.data[0].embedding
    results = []

    for chunk in chunks:
        semantic = cosine_similarity(
            question_embedding,
            chunk["embedding"],
        )
        semantic = max(0.0, min(1.0, semantic))
        status = _status_score(chunk.get("status", ""))
        recency = _recency_score(
            chunk.get("effective_date", "")
        )
        role_alignment = _role_score(
            chunk.get("audience", ""),
            role,
        )

        final_score = (
            SEMANTIC_WEIGHT * semantic
            + STATUS_WEIGHT * status
            + RECENCY_WEIGHT * recency
            + ROLE_WEIGHT * role_alignment
        )

        result = {
            key: value
            for key, value in chunk.items()
            if key != "embedding"
        }
        result.update(
            {
                "score": final_score,
                "semantic_score": semantic,
                "status_score": status,
                "recency_score": recency,
                "role_score": role_alignment,
            }
        )
        results.append(result)

    results.sort(
        key=lambda item: (
            item["score"],
            item["semantic_score"],
        ),
        reverse=True,
    )

    limit = max(1, min(int(top_k), 8))

    return _include_strongest_linked_versions(
        results,
        limit,
    )
