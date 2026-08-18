from foundry_local_sdk import Configuration, FoundryLocalManager

from src.retrieval import search_chunks


class RAGPipeline:
    """Manage local embedding, retrieval, and answer generation."""

    def __init__(self):
        config = Configuration(
            app_name="crisislens_local",
            log_level="info"
        )

        FoundryLocalManager.initialize(config)
        self.manager = FoundryLocalManager.instance

        self.embedding_model = self.manager.catalog.get_model(
            "qwen3-embedding-0.6b"
        )

        self.chat_model = self.manager.catalog.get_model(
            "phi-4-mini"
        )

        self.embedding_client = None
        self.chat_client = None

    def start(self):
        """Download and load the required local models."""

        print("Preparing the embedding model...")
        self.embedding_model.download()
        self.embedding_model.load()

        self.embedding_client = (
            self.embedding_model.get_embedding_client()
        )

        print("Preparing Phi-4 Mini...")
        self.chat_model.download()
        self.chat_model.load()

        self.chat_client = self.chat_model.get_chat_client()

        print("RAG pipeline is ready.")

    def answer(self, question, top_k=3):
        """Retrieve context and generate a grounded answer."""

        if self.embedding_client is None:
            raise RuntimeError(
                "The pipeline has not been started."
            )

        retrieved_chunks = search_chunks(
            question,
            self.embedding_client,
            top_k=top_k
        )

        context_parts = []

        for result in retrieved_chunks:
            context_parts.append(
                f"Source: {result['source']}\n"
                f"Content: {result['content']}"
            )

        context = "\n\n".join(context_parts)

        system_prompt = """
You are a grounded document assistant.

Follow these rules:
1. Answer only with information found in the provided context.
2. Do not use outside knowledge or make assumptions.
3. If the context is insufficient, clearly state that the
   answer could not be found in the provided documents.
4. Cite source file names in square brackets.
5. Keep the answer clear, concise, and factual.
""".strip()

        user_prompt = f"""
Context:
{context}

Question:
{question}

Provide a grounded answer with source citations.
""".strip()

        messages = [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ]

        response = self.chat_client.complete_chat(messages)
        answer = response.choices[0].message.content

        return {
            "answer": answer,
            "sources": retrieved_chunks
        }

    def stop(self):
        """Unload local models and release resources."""

        if self.chat_model.is_loaded:
            print("Unloading Phi-4 Mini...")
            self.chat_model.unload()

        if self.embedding_model.is_loaded:
            print("Unloading the embedding model...")
            self.embedding_model.unload()