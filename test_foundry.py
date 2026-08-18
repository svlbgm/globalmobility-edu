from foundry_local_sdk import Configuration, FoundryLocalManager


def main():
    print("Initializing Foundry Local...")

    config = Configuration(
        app_name="microsoft_local_rag",
        log_level="info"
    )

    FoundryLocalManager.initialize(config)
    manager = FoundryLocalManager.instance

    print("Checking the model catalog...")

    models = manager.catalog.list_models()

    print(f"\nNumber of models available for this device: {len(models)}")

    for model in models:
        print(model)


if __name__ == "__main__":
    main()