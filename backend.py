import time
from threading import Lock

from flask import Flask, jsonify, request

from src.database import get_chunk_count
from src.rag_pipeline import RAGPipeline


app = Flask(__name__)
pipeline = None
analysis_lock = Lock()

ALLOWED_ROLES = {
    "Student",
    "Academic Advisor",
    "Department Administrator",
}


@app.get("/health")
def health():
    return jsonify(
        {
            "status": "ready" if pipeline else "starting",
            "indexed_chunks": get_chunk_count(),
            "chat_model": "Phi-4 Mini",
            "embedding_model": "Qwen3 Embedding",
            "ranking": "Semantic + policy governance",
        }
    )


@app.post("/analyze")
def analyze():
    if pipeline is None:
        return jsonify(
            {"error": "The local policy engine is not ready."}
        ), 503

    payload = request.get_json(silent=True) or {}
    question = str(payload.get("question", "")).strip()
    role = str(payload.get("role", "Student")).strip()

    try:
        top_k = max(
            2,
            min(int(payload.get("top_k", 3)), 6),
        )
    except (TypeError, ValueError):
        return jsonify(
            {"error": "top_k must be an integer."}
        ), 400

    if not question:
        return jsonify(
            {"error": "The question cannot be empty."}
        ), 400

    if role not in ALLOWED_ROLES:
        return jsonify(
            {"error": "Unsupported academic role."}
        ), 400

    if not analysis_lock.acquire(blocking=False):
        return jsonify(
            {
                "error": (
                    "The local policy engine is already reviewing another "
                    "question. Please wait for it to finish."
                )
            }
        ), 409

    started_at = time.perf_counter()

    try:
        result = pipeline.answer(
            question=question,
            role=role,
            top_k=top_k,
        )

        if result.get("validation_issues"):
            return jsonify(
                {
                    "error": (
                        "The local model response did not pass the "
                        "grounding and governance checks. Please retry."
                    ),
                    "validation_issues": result["validation_issues"],
                }
            ), 422

        result["response_time_seconds"] = round(
            time.perf_counter() - started_at,
            2,
        )
        return jsonify(result)
    except Exception as error:
        print(f"Analysis error: {error}")
        return jsonify({"error": str(error)}), 500
    finally:
        analysis_lock.release()


if __name__ == "__main__":
    pipeline = RAGPipeline()

    try:
        pipeline.start()
        app.run(
            host="127.0.0.1",
            port=8000,
            debug=False,
            use_reloader=False,
            threaded=False,
        )
    finally:
        pipeline.stop()
