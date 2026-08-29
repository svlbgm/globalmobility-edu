import re
from pathlib import Path


SUPPORTED_EXTENSIONS = {".txt", ".pdf", ".docx"}

METADATA_FIELDS = (
    "title",
    "version",
    "status",
    "effective_date",
    "reviewed_date",
    "owner",
    "audience",
    "supersedes",
    "superseded_by",
)


def _read_txt(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _read_pdf(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    return "\n".join(
        page.extract_text() or ""
        for page in reader.pages
    )


def _read_docx(path: Path) -> str:
    from docx import Document

    document = Document(str(path))
    return "\n".join(
        paragraph.text
        for paragraph in document.paragraphs
    )


def read_document(path) -> str:
    """Extract text from a supported local document."""

    path = Path(path)
    extension = path.suffix.lower()

    if extension == ".txt":
        text = _read_txt(path)
    elif extension == ".pdf":
        text = _read_pdf(path)
    elif extension == ".docx":
        text = _read_docx(path)
    else:
        raise ValueError(
            f"Unsupported document type: {extension}"
        )

    cleaned = re.sub(r"\r\n?", "\n", text)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def parse_policy_metadata(text: str):
    """Return normalized policy metadata and document body."""

    pattern = re.compile(
        r"\[POLICY_METADATA\](.*?)\[/POLICY_METADATA\]",
        flags=re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(text)

    metadata = {field: "" for field in METADATA_FIELDS}

    if match:
        for line in match.group(1).splitlines():
            if ":" not in line:
                continue

            key, value = line.split(":", 1)
            key = key.strip().lower()

            if key in metadata:
                metadata[key] = value.strip()

        body = pattern.sub("", text).strip()
    else:
        body = text.strip()
        metadata["status"] = "unclassified"

    return metadata, body


def chunk_text(text: str, chunk_size=180, overlap=30):
    """Split text into overlapping word-based sections."""

    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive.")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError(
            "overlap must be between 0 and chunk_size - 1."
        )

    words = text.split()

    if not words:
        return []

    step = chunk_size - overlap
    sections = []

    for start in range(0, len(words), step):
        section_words = words[start:start + chunk_size]

        if not section_words:
            break

        sections.append(" ".join(section_words))

        if start + chunk_size >= len(words):
            break

    return sections


def _mark_line_breaks_as_sentence_boundaries(text: str) -> str:
    """Give every source line its own sentence-ending punctuation.

    Headings and paragraphs in these documents are separated only by a
    newline. Word-based chunking later joins everything with single
    spaces, which would otherwise erase that boundary and let a short
    heading word (for example "Approval") collide with an unrelated word
    inside a real sentence once flattened.
    """

    marked_lines = []

    for line in text.split("\n"):
        stripped = line.strip()

        if not stripped:
            continue

        if stripped[-1] not in ".!?:":
            stripped += "."

        marked_lines.append(stripped)

    return " ".join(marked_lines)


def process_document(path, chunk_size=180, overlap=30):
    """Extract, classify and chunk a policy document."""

    path = Path(path)
    text = read_document(path)
    metadata, body = parse_policy_metadata(text)
    body = _mark_line_breaks_as_sentence_boundaries(body)
    sections = chunk_text(body, chunk_size, overlap)

    chunks = []

    for index, content in enumerate(sections):
        chunk = {
            "source": path.name,
            "chunk_index": index,
            "content": content,
            **metadata,
        }

        metadata_summary = (
            f"Policy title: {metadata['title']}. "
            f"Version: {metadata['version']}. "
            f"Status: {metadata['status']}. "
            f"Effective date: {metadata['effective_date']}. "
            f"Owner: {metadata['owner']}. "
            f"Audience: {metadata['audience']}."
        )

        chunk["embedding_text"] = (
            f"{metadata_summary}\n{content}"
        )
        chunks.append(chunk)

    return chunks
