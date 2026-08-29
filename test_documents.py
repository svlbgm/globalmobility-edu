from src.document_processor import process_document


def main():
    chunks = process_document(
        "documents/exchange_course_recognition_v2_2026.txt",
        chunk_size=180,
        overlap=30,
    )

    print(f"Number of policy sections: {len(chunks)}")

    for chunk in chunks:
        print("\n" + "=" * 60)
        print(f"Source: {chunk['source']}")
        print(f"Version: {chunk['version']}")
        print(f"Status: {chunk['status']}")
        print(f"Audience: {chunk['audience']}")
        print(f"Chunk index: {chunk['chunk_index']}")
        print(f"Content: {chunk['content']}")


if __name__ == "__main__":
    main()
