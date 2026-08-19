import re

from foundry_local_sdk import Configuration, FoundryLocalManager

from src.retrieval import search_chunks


def clean_citations(answer):
    """Remove numeric markers added after filename citations."""

    return re.sub(
        r"(\[[^\]]+\.txt\])\[\d+\]",
        r"\1",
        answer
    )


def remove_duplicate_list_items(answer):
    """Remove repeated list items within the same section."""

    cleaned_lines = []
    seen_items = set()

    for line in answer.splitlines():
        stripped = line.strip()

        if stripped.startswith("###"):
            seen_items = set()
            cleaned_lines.append(line)
            continue

        is_list_item = (
            stripped.startswith("- ")
            or re.match(r"^\d+\.\s+", stripped)
        )

        if is_list_item:
            normalized = re.sub(
                r"^(?:-\s+|\d+\.\s+)",
                "",
                stripped
            )

            normalized = re.sub(
                r"\[[^\]]+\]",
                "",
                normalized
            )

            normalized = " ".join(
                normalized.lower().split()
            ).strip(" .")

            if normalized in seen_items:
                continue

            seen_items.add(normalized)

        cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


class RAGPipeline:
    """Manage local retrieval and grounded answer generation."""

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

        self.chat_client = None

    def start(self):
        """Prepare models while minimizing memory usage."""

        print("Preparing the embedding model...")
        self.embedding_model.download()

        print("Preparing Phi-4 Mini...")
        self.chat_model.download()
        self.chat_model.load()

        self.chat_client = self.chat_model.get_chat_client()

        print("CrisisLens Local is ready.")

    def answer(
        self,
        question,
        role="Operations Manager",
        top_k=4
    ):
        """Generate a role-specific, grounded crisis response."""

        if not question.strip():
            raise ValueError("The question cannot be empty.")

        if self.chat_client is None:
            raise RuntimeError(
                "The pipeline has not been started."
            )

        print("Loading the embedding model...")
        self.embedding_model.load()

        try:
            embedding_client = (
                self.embedding_model.get_embedding_client()
            )

            retrieved_chunks = search_chunks(
                question,
                embedding_client,
                top_k=top_k
            )

        finally:
            if self.embedding_model.is_loaded:
                print("Unloading the embedding model...")
                self.embedding_model.unload()

        context_parts = []

        for result in retrieved_chunks:
            context_parts.append(
                f"Source file: {result['source']}\n"
                f"Retrieval relevance: "
                f"{result['score']:.4f}\n"
                f"Document content:\n"
                f"{result['content']}"
            )

        context = "\n\n---\n\n".join(context_parts)

        system_prompt = """
You are CrisisLens Local, an offline operational crisis
response assistant.

You must follow these rules:

1. Use only the supplied document context.
2. Never add instructions from outside knowledge.
3. Tailor actions to the user's organizational role.
4. Cite every important action with a source filename
   in square brackets.
5. Distinguish current approved documents from legacy,
   outdated, or unverified documents.
6. If documents conflict, clearly describe the conflict.
7. Prioritize the most recently reviewed current and
   approved document.
8. Never silently combine conflicting instructions.
9. If required information is missing, state the gap
   instead of guessing.
10. Do not claim to replace authorized emergency,
    cybersecurity, legal, or safety professionals.
11. Cite sources using only the exact filename in square
    brackets, for example [cyber_incident_playbook.txt].
    Never add numeric citation markers such as [1] or [2].
12. Before writing, internally create a list of candidate
    actions and their supporting sources. Merge actions
    that have the same practical meaning.
13. Before writing, internally classify every action by
    its documented owner or responsible role.
14. The Immediate actions section must contain only actions
    that the stated user role personally performs.
15. Put actions owned by other roles under Escalation and
    communication. State which role owns each action.
16. Clearly distinguish actions the user should personally
    perform from actions they should coordinate or request.
17. Do not place the same action in more than one response
    section.
18. Keep the response concise. Do not repeat warnings,
    citations, actions, or explanations.

Use this exact response structure:

### Incident assessment
Briefly classify the documented situation.

### Immediate actions
Include only actions personally owned by the stated role.
Do not include instructions containing "coordinate with",
"ask", "notify", or "work with" in this section.

### Actions to avoid
List each prohibited or unsupported action only once.

### Escalation and communication
Place coordination, notification, requests, and actions
owned by other roles in this section. Name the responsible
role for each action.

### Evidence and document conflicts
Identify supporting sources and clearly explain conflicting,
legacy, outdated, or unverified instructions.

### Information gaps
State only material information that cannot be determined
from the supplied documents.
""".strip()

        user_prompt = f"""
User role:
{role}

Incident or question:
{question}

Retrieved document context:
{context}

Create a concise, grounded operational response for the
stated role. Follow the required section structure and do
not repeat any action across sections.
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

        raw_answer = response.choices[0].message.content

        cleaned_answer = clean_citations(raw_answer)
        cleaned_answer = remove_duplicate_list_items(
            cleaned_answer
        )

        return {
            "answer": cleaned_answer,
            "role": role,
            "sources": retrieved_chunks
        }

    def stop(self):
        """Unload models and release resources."""

        if self.embedding_model.is_loaded:
            print("Unloading the embedding model...")
            self.embedding_model.unload()

        if self.chat_model.is_loaded:
            print("Unloading Phi-4 Mini...")
            self.chat_model.unload()