import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest


class StreamlitContractTests(unittest.TestCase):
    @staticmethod
    def element_with_label(elements, label):
        return next(
            element for element in elements if element.label == label
        )

    def test_main_form_exposes_demo_controls(self):
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        app = AppTest.from_file(str(app_path)).run(timeout=30)

        self.assertEqual(len(app.exception), 0)
        role = self.element_with_label(app.selectbox, "Your role")
        scenario = self.element_with_label(
            app.selectbox,
            "Try an example",
        )
        question = self.element_with_label(
            app.text_area,
            "Your question",
        )

        self.assertEqual(
            list(role.options),
            [
                "Student",
                "Academic Advisor",
                "Department Administrator",
            ],
        )
        self.assertFalse(
            any(
                selectbox.label == "Sources to compare"
                for selectbox in app.selectbox
            )
        )
        self.assertFalse(
            any(
                expander.label == "Advanced settings"
                for expander in app.expander
            )
        )
        self.assertEqual(scenario.value, "Application period")
        self.assertEqual(question.value, "When can I apply?")
        self.assertEqual(
            app.button[0].label,
            "Check applicable policies",
        )

    def test_scenario_selection_updates_the_question(self):
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        app = AppTest.from_file(str(app_path)).run(timeout=30)
        scenario = self.element_with_label(
            app.selectbox,
            "Try an example",
        )

        scenario.select("Role-aware guidance").run(timeout=30)

        question = self.element_with_label(
            app.text_area,
            "Your question",
        )
        self.assertEqual(
            question.value,
            "A student changed a host course during mobility. "
            "What should the Academic Advisor do, and what remains "
            "the student's responsibility?",
        )

    def test_result_uses_human_readable_evidence_labels(self):
        class FakeResponse:
            def __init__(self, payload):
                self.payload = payload
                self.ok = True

            def json(self):
                return self.payload

        health_payload = {
            "status": "ready",
            "chat_model": "Phi-4 Mini",
            "embedding_model": "Qwen3 Embedding",
            "indexed_chunks": 8,
        }
        result_payload = {
            "answer": (
                "## Applicable guidance\nUse the current_approved policy "
                "[current_policy.txt]."
            ),
            "response_time_seconds": 157.85,
            "sources": [
                {
                    "source": "current_policy.txt",
                    "title": "Current Policy",
                    "version": "2.0",
                    "effective_date": "2026-02-01",
                    "status": "current_approved",
                    "owner": "Academic Affairs",
                    "audience": "Student",
                    "score": 0.8102,
                    "semantic_score": 0.693,
                    "status_score": 1.0,
                    "recency_score": 0.944,
                    "role_score": 1.0,
                    "content": (
                        "SYNTHETIC DEMONSTRATION DOCUMENT — NOT AN "
                        "OFFICIAL UNIVERSITY POLICY Purpose This is "
                        "the current procedure."
                    ),
                }
            ],
        }
        app_path = Path(__file__).resolve().parents[1] / "app.py"

        with (
            patch(
                "requests.get",
                return_value=FakeResponse(health_payload),
            ),
            patch(
                "requests.post",
                return_value=FakeResponse(result_payload),
            ) as post_request,
        ):
            app = AppTest.from_file(str(app_path)).run(timeout=30)
            submit = next(
                button
                for button in app.button
                if button.label == "Check applicable policies"
            )
            submit.click().run(timeout=30)

        self.assertEqual(len(app.exception), 0)
        self.assertEqual(
            post_request.call_args.kwargs["json"]["top_k"],
            3,
        )
        source_expander = next(
            expander
            for expander in app.expander
            if expander.label.startswith(":blue[Source 1]")
        )
        self.assertEqual(
            source_expander.label,
            ":blue[Source 1] · :orange[Current Policy v2.0] · "
            "Current approved",
        )
        self.assertTrue(
            any(
                caption.value == "Completed locally in 2 min 38 sec."
                for caption in app.caption
            )
        )
        self.assertTrue(
            any("**Purpose**" in item.value for item in app.markdown)
        )
        self.assertTrue(
            any(
                "[**Source 1**](#source-1)" in item.value
                and "current approved" in item.value
                for item in app.markdown
            )
        )

    def test_blank_applicable_guidance_uses_conflict_as_bottom_line(self):
        class FakeResponse:
            def __init__(self, payload):
                self.payload = payload
                self.ok = True

            def json(self):
                return self.payload

        health_payload = {"status": "ready", "indexed_chunks": 1}
        result_payload = {
            "answer": (
                "### Applicable guidance\n\n"
                "### Actions for the selected role\n"
                "1. Review the mapping [current_policy.txt].\n"
                "### Responsibilities of other roles\n\n"
                "### Version and conflict check\n"
                "Use the current procedure [current_policy.txt].\n"
                "### Information gaps\n"
            ),
            "sources": [
                {
                    "source": "current_policy.txt",
                    "title": "Current Policy",
                    "version": "2.0",
                    "effective_date": "2026-02-01",
                    "status": "current_approved",
                    "owner": "Academic Affairs",
                    "audience": "Academic Advisor",
                    "score": 0.81,
                    "content": "The Academic Advisor reviews the mapping.",
                }
            ],
        }
        app_path = Path(__file__).resolve().parents[1] / "app.py"

        with (
            patch("requests.get", return_value=FakeResponse(health_payload)),
            patch("requests.post", return_value=FakeResponse(result_payload)),
        ):
            app = AppTest.from_file(str(app_path)).run(timeout=30)
            role = self.element_with_label(app.selectbox, "Your role")
            role.select("Academic Advisor").run(timeout=30)
            submit = next(
                button
                for button in app.button
                if button.label == "Check applicable policies"
            )
            submit.click().run(timeout=30)

        markdown_values = [item.value for item in app.markdown]
        self.assertTrue(
            any(
                "Use the current procedure" in value
                for value in markdown_values
            )
        )
        self.assertTrue(
            any(
                "[**Source 1 — Current Policy v2.0**](#source-1)"
                in item.value
                for item in app.markdown
            )
        )
        self.assertFalse(
            any("current_policy.txt" in item.value for item in app.markdown)
        )
        self.assertNotIn(
            "answer-box",
            app_path.read_text(encoding="utf-8"),
        )

    def test_timing_question_leads_with_a_plain_answer(self):
        class FakeResponse:
            def __init__(self, payload):
                self.payload = payload
                self.ok = True

            def json(self):
                return self.payload

        health_payload = {"status": "ready", "indexed_chunks": 8}
        result_payload = {
            "answer": (
                "### Applicable guidance\nThe current policy applies "
                "[current_policy.txt].\n"
                "### Actions for the selected role\nNo selected-role "
                "action is specified for the requested processing time "
                "[current_policy.txt].\n"
                "### Responsibilities of other roles\nNo other-role "
                "responsibility specifies the requested processing time "
                "[current_policy.txt].\n"
                "### Version and conflict check\nThe current policy is "
                "the governing source [current_policy.txt].\n"
                "### Information gaps\nThe policy does not state a "
                "guaranteed completion time [current_policy.txt]."
            ),
            "sources": [
                {
                    "source": "current_policy.txt",
                    "title": "Current Policy",
                    "version": "2.0",
                    "effective_date": "2026-02-01",
                    "status": "current_approved",
                    "owner": "Academic Affairs",
                    "audience": "Student",
                    "score": 0.81,
                    "content": (
                        "This policy does not specify a guaranteed number "
                        "of working days."
                    ),
                }
            ],
        }
        app_path = Path(__file__).resolve().parents[1] / "app.py"

        with (
            patch(
                "requests.get",
                return_value=FakeResponse(health_payload),
            ),
            patch(
                "requests.post",
                return_value=FakeResponse(result_payload),
            ),
        ):
            app = AppTest.from_file(str(app_path)).run(timeout=30)
            scenario = self.element_with_label(
                app.selectbox,
                "Try an example",
            )
            scenario.select("Missing information").run(timeout=30)
            submit = next(
                button
                for button in app.button
                if button.label == "Check applicable policies"
            )
            submit.click().run(timeout=30)

        markdown_values = [item.value for item in app.markdown]
        self.assertEqual(len(app.exception), 0)
        self.assertTrue(
            any(
                "do not give a guaranteed number of working days"
                in value
                for value in markdown_values
            )
        )
        self.assertIn("### What to do next", markdown_values)
        self.assertTrue(
            any(
                "Ask Academic Affairs for the current expected timeline"
                in value
                for value in markdown_values
            )
        )
        self.assertNotIn(
            "### What you should do as Student",
            markdown_values,
        )
        self.assertNotIn(
            "### What the policy does not specify",
            markdown_values,
        )
        self.assertTrue(
            any(
                expander.label.startswith("Technical explanation")
                or expander.label == "Audit details (optional)"
                for expander in app.expander
            )
        )

    def test_uncovered_question_labels_documents_as_checked(self):
        class FakeResponse:
            def __init__(self, payload):
                self.payload = payload
                self.ok = True

            def json(self):
                return self.payload

        health_payload = {"status": "ready", "indexed_chunks": 8}
        result_payload = {
            "answerability": "not_covered",
            "next_step": "Check the current exchange application portal.",
            "answer": (
                "### Applicable guidance\n"
                "The documents do not state when applications open "
                "[current_policy.txt].\n"
                "### Actions for the selected role\n"
                "No selected-role action is specified for an exchange-"
                "program application date [current_policy.txt].\n"
                "### Responsibilities of other roles\n"
                "No other-role responsibility specifies an exchange-"
                "program application date [current_policy.txt].\n"
                "### Version and conflict check\n"
                "No relevant conflict was found [current_policy.txt].\n"
                "### Information gaps\n"
                "The application deadline is not specified "
                "[current_policy.txt]."
            ),
            "sources": [
                {
                    "source": "current_policy.txt",
                    "title": "Current Policy",
                    "version": "2.0",
                    "effective_date": "2026-02-01",
                    "status": "current_approved",
                    "owner": "Academic Affairs",
                    "audience": "Student",
                    "score": 0.81,
                    "content": "A course-recognition procedure.",
                }
            ],
        }
        app_path = Path(__file__).resolve().parents[1] / "app.py"

        with (
            patch("requests.get", return_value=FakeResponse(health_payload)),
            patch("requests.post", return_value=FakeResponse(result_payload)),
        ):
            app = AppTest.from_file(str(app_path)).run(timeout=30)
            question = self.element_with_label(app.text_area, "Your question")
            question.input("When can I apply for the exchange?")
            submit = next(
                button
                for button in app.button
                if button.label == "Check applicable policies"
            )
            submit.click().run(timeout=30)

        markdown_values = [item.value for item in app.markdown]
        self.assertIn("### What to do next", markdown_values)
        self.assertIn("### Documents checked", markdown_values)
        self.assertNotIn(
            "### What you should do as Student",
            markdown_values,
        )
        self.assertNotIn("### Who else is involved", markdown_values)
        self.assertNotIn("### Sources used", markdown_values)


if __name__ == "__main__":
    unittest.main()
