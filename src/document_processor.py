from pathlib import Path

from docx import Document
from pypdf import PdfReader


SUPPORTED_EXTENSIONS = {".txt", ".pdf", ".docx"}


def extract_text(file_path: str | Path) -> str:
    """Extract text from a TXT, PDF, or DOCX file."""

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Document not found: {path}")

    extension = path.suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type: {extension}. "
            f"Supported types: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    if extension == ".txt":
        text = path.read_text(encoding="utf-8")

    elif extension == ".pdf":
        reader = PdfReader(path)
        text = "\n".join(
            page.extract_text() or ""
            for page in reader.pages
        )

    else:
        document = Document(path)
        text = "\n".join(
            paragraph.text
            for paragraph in document.paragraphs
            if paragraph.text.strip()
        )

    return text.strip()


def chunk_text(
    text: str,
    chunk_size: int = 180,
    overlap: int = 30
) -> list[str]:
    """Split text into overlapping word-based chunks."""

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero.")

    if overlap < 0:
        raise ValueError("overlap cannot be negative.")

    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size.")

    words = text.split()

    if not words:
        return []

    chunks = []
    step_size = chunk_size - overlap

    for start in range(0, len(words), step_size):
        end = start + chunk_size
        chunk = " ".join(words[start:end]).strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(words):
            break

    return chunks


def process_document(
    file_path: str | Path,
    chunk_size: int = 180,
    overlap: int = 30
) -> list[dict]:
    """Extract and chunk a document while preserving its source name."""

    path = Path(file_path)
    text = extract_text(path)
    chunks = chunk_text(text, chunk_size, overlap)

    return [
        {
            "source": path.name,
            "chunk_index": index,
            "content": chunk
        }
        for index, chunk in enumerate(chunks)
    ]