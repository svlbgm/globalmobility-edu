import time

from flask import Flask, jsonify, request

from src.database import get_chunk_count
from src.rag_pipeline import RAGPipeline


app = Flask(__name__)
pipeline = None


@app.get("/health")
def health():
    return jsonify(
        {
            "status": "ready" if pipeline else "starting",
            "indexed_chunks": get_chunk_count(),
            "chat_model": "Phi-4 Mini",
            "embedding_model": "Qwen3 Embedding"
        }
    )


@app.post("/analyze")
def analyze():
    if pipeline is None:
        return jsonify(
            {"error": "The local AI pipeline is not ready."}
        ), 503

    payload = request.get_json(silent=True) or {}

    question = payload.get("question", "").strip()
    role = payload.get("role", "Student")
    top_k = int(payload.get("top_k", 3))

    if not question:
        return jsonify(
            {"error": "The question cannot be empty."}
        ), 400

    started_at = time.perf_counter()

    try:
        result = pipeline.answer(
            question=question,
            role=role,
            top_k=top_k
        )

        result["response_time_seconds"] = round(
            time.perf_counter() - started_at,
            2
        )

        return jsonify(result)

    except Exception as error:
        print(f"Analysis error: {error}")

        return jsonify(
            {"error": str(error)}
        ), 500


if __name__ == "__main__":
    pipeline = RAGPipeline()

    try:
        pipeline.start()

        app.run(
            host="127.0.0.1",
            port=8000,
            debug=False,
            use_reloader=False,
            threaded=False
        )

    finally:
        pipeline.stop()