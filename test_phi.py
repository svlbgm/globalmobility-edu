from foundry_local_sdk import Configuration, FoundryLocalManager


def main():
    print("Initializing Foundry Local...")

    config = Configuration(
        app_name="microsoft_local_rag",
        log_level="info"
    )

    FoundryLocalManager.initialize(config)
    manager = FoundryLocalManager.instance

    print("Selecting Phi-4 Mini...")
    model = manager.catalog.get_model("phi-4-mini")

    try:
        print("Downloading Phi-4 Mini...")
        print("The first download may take several minutes.")
        model.download()

        print("Loading the model...")
        model.load()

        print("Sending the first question...")
        client = model.get_chat_client()

        messages = [
            {
                "role": "system",
                "content": "You are a helpful and concise AI assistant."
            },
            {
                "role": "user",
                "content": "Explain retrieval-augmented generation in three simple sentences."
            }
        ]

        response = client.complete_chat(messages)
        answer = response.choices[0].message.content

        print("\nPhi-4 Mini response:")
        print(answer)

    finally:
        if model.is_loaded:
            print("\nUnloading the model...")
            model.unload()

    print("Test completed successfully.")


if __name__ == "__main__":
    main()