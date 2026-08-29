from waitress import serve

import backend
from src.rag_pipeline import RAGPipeline


HOST = "127.0.0.1"
PORT = 8000


def main():
    backend.pipeline = RAGPipeline()

    try:
        backend.pipeline.start()
        print(
            f"GlobalMobility EDU backend ready at http://{HOST}:{PORT}",
            flush=True,
        )
        serve(
            backend.app,
            host=HOST,
            port=PORT,
            threads=2,
        )
    finally:
        if backend.pipeline is not None:
            backend.pipeline.stop()
            backend.pipeline = None


if __name__ == "__main__":
    main()
