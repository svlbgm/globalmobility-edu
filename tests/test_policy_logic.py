import tempfile
import unittest
from pathlib import Path

from src.document_processor import process_document
from src.retrieval import (
    _include_strongest_linked_versions,
    _recency_score,
    _role_score,
    _status_score,
)


class PolicyMetadataTests(unittest.TestCase):
    def test_exchange_application_calendar_is_current_and_answerable(self):
        path = (
            Path(__file__).resolve().parents[1]
            / "documents"
            / "exchange_application_calendar_v1_2026.txt"
        )

        chunks = process_document(path)

        self.assertEqual(chunks[0]["status"], "current_approved")
        self.assertEqual(
            chunks[0]["title"],
            "Exchange Program Application Calendar",
        )
        self.assertIn("1–15 March", chunks[0]["content"])
        self.assertIn("1–15 October", chunks[0]["content"])

    def test_metadata_is_extracted_from_plain_text(self):
        policy = """SYNTHETIC TEST
[POLICY_METADATA]
title: Example Policy
version: 2.0
status: current_approved
effective_date: 2026-01-01
reviewed_date: 2025-12-01
owner: Academic Affairs
audience: Student, Academic Advisor
supersedes: old_policy.txt
[/POLICY_METADATA]

Students submit the required evidence through the portal.
"""

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.txt"
            path.write_text(policy, encoding="utf-8")
            chunks = process_document(path)

        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0]["version"], "2.0")
        self.assertEqual(
            chunks[0]["status"],
            "current_approved",
        )
        self.assertNotIn(
            "[POLICY_METADATA]",
            chunks[0]["content"],
        )
        self.assertIn(
            "Status: current_approved",
            chunks[0]["embedding_text"],
        )

    def test_governance_scores_prefer_current_policy(self):
        self.assertGreater(
            _status_score("current_approved"),
            _status_score("legacy"),
        )
        self.assertGreater(
            _status_score("superseded"),
            _status_score("legacy_unverified"),
        )

    def test_role_alignment_is_explicit(self):
        self.assertEqual(
            _role_score("Student, Academic Advisor", "Student"),
            1.0,
        )
        self.assertLess(
            _role_score("Student", "Department Administrator"),
            1.0,
        )

    def test_valid_date_scores_above_missing_date(self):
        self.assertGreater(
            _recency_score("2026-01-01"),
            _recency_score(""),
        )

    def test_sibling_chunks_of_the_top_document_are_kept_together(self):
        ranked_results = [
            {
                "source": "calendar.txt",
                "chunk_index": 1,
                "score": 0.70,
                "content": (
                    "This calendar does not create a "
                    "late-application process."
                ),
            },
            {
                "source": "appeals.txt",
                "chunk_index": 0,
                "score": 0.67,
                "content": "Appeals procedure text.",
            },
            {
                "source": "calendar.txt",
                "chunk_index": 0,
                "score": 0.55,
                "content": (
                    "Students may apply during either standard "
                    "window: 1-15 March and 1-15 October."
                ),
            },
        ]

        selected = _include_strongest_linked_versions(
            ranked_results,
            limit=3,
        )

        selected_keys = {
            (item["source"], item["chunk_index"])
            for item in selected
        }
        self.assertIn(("calendar.txt", 1), selected_keys)
        self.assertIn(
            ("calendar.txt", 0),
            selected_keys,
            "The lower-ranked sibling chunk of the top document should "
            "still be included so the generated answer is not missing "
            "facts that live in another chunk of the same document.",
        )


if __name__ == "__main__":
    unittest.main()
