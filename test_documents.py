from src.document_processor import process_document


def main():
    document_path = "documents/rag_notes.txt"

    chunks = process_document(
        document_path,
        chunk_size=60,
        overlap=10
    )

    print(f"Number of chunks: {len(chunks)}")

    for chunk in chunks:
        print("\n" + "=" * 60)
        print(f"Source: {chunk['source']}")
        print(f"Chunk index: {chunk['chunk_index']}")
        print(f"Content: {chunk['content']}")


if __name__ == "__main__":
    main()