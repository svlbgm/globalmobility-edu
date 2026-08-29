"""Run the delivery-level GlobalMobility EDU demo scenarios."""

import re
import sys

import requests


BACKEND_URL = "http://127.0.0.1:8000"

SCENARIOS = (
    {
        "name": "exchange application period",
        "role": "Student",
        "question": "When can I apply?",
        "required": (
            "1–15 March",
            "1–15 October",
            "exchange_application_calendar_v1_2026.txt",
        ),
        "forbidden": (
            "course-mapping table",
            "final transcript",
        ),
    },
    {
        "name": "current versus legacy conflict",
        "role": "Student",
        "question": (
            "The older exchange guide says I can request course approval "
            "after returning, but the current policy requires pre-approval. "
            "Which procedure applies?"
        ),
        "required": (
            "documented procedural conflict/difference",
            "governing source",
            "must not be used",
        ),
        "forbidden": ("personal equivalency proposal",),
    },
    {
        "name": "selected-role boundary",
        "role": "Academic Advisor",
        "question": (
            "A student changed a host course during mobility. What should "
            "the Academic Advisor do, and what remains the student's "
            "responsibility?"
        ),
        "required": (
            "### Actions for the selected role",
            "### Responsibilities of other roles",
            "Student:",
        ),
        "forbidden": (),
    },
    {
        "name": "missing information",
        "role": "Student",
        "question": (
            "Exactly how many working days will a course-recognition "
            "request take?"
        ),
        "required": ("### Information gaps",),
        "forbidden": (),
    },
    {
        "name": "authority over semantic similarity",
        "role": "Department Administrator",
        "question": (
            "Is an unsigned Learning Agreement sent by email a completed "
            "submission under the current procedure?"
        ),
        "required": (
            "learning_agreement_v2_2026.txt",
            "governing source",
        ),
        "forbidden": (),
    },
)


def run_scenario(scenario):
    response = requests.post(
        f"{BACKEND_URL}/analyze",
        json={
            "question": scenario["question"],
            "role": scenario["role"],
            "top_k": 4,
        },
        timeout=900,
    )
    response.raise_for_status()
    result = response.json()
    answer = result["answer"]

    if result.get("validation_issues"):
        raise AssertionError(result["validation_issues"])

    for phrase in scenario["required"]:
        if phrase.lower() not in answer.lower():
            raise AssertionError(f"Missing required phrase: {phrase}")

    for phrase in scenario["forbidden"]:
        if phrase.lower() in answer.lower():
            raise AssertionError(f"Forbidden phrase present: {phrase}")

    if scenario["name"] == "missing information":
        if re.search(r"\b\d+\s+working days?\b", answer.lower()):
            raise AssertionError("A processing duration was invented.")

        gap_language = (
            "not specify",
            "not specified",
            "no guaranteed",
        )

        if not any(phrase in answer.lower() for phrase in gap_language):
            raise AssertionError(
                "The missing processing duration was not stated clearly."
            )

    if scenario["name"] == "selected-role boundary":
        selected_actions = answer.split(
            "### Actions for the selected role",
            1,
        )[1].split("### Responsibilities of other roles", 1)[0].lower()

        for phrase in (
            "record the approved mapping",
            "send the verified package",
            "review the revised mapping",
            "review the revised documents",
        ):
            if phrase in selected_actions:
                raise AssertionError(
                    "Another or unspecified role's task leaked into the "
                    f"selected-role section: {phrase}"
                )

    return result


def main():
    selected = SCENARIOS

    if len(sys.argv) > 1:
        selected = tuple(
            SCENARIOS[int(value) - 1]
            for value in sys.argv[1:]
        )

    for index, scenario in enumerate(selected, start=1):
        print(
            f"\n[{index}/{len(selected)}] "
            f"{scenario['name']} ({scenario['role']})"
        )
        result = run_scenario(scenario)
        print(result["answer"])
        print(
            f"PASS in {result.get('response_time_seconds', '?')} seconds"
        )


if __name__ == "__main__":
    main()
