import unittest

import backend


class StubPipeline:
    def answer(self, question, role, top_k):
        return {
            "answer": f"{role}: {question}",
            "role": role,
            "sources": [],
            "validation_issues": [],
        }


class InvalidAnswerPipeline:
    def answer(self, question, role, top_k):
        return {
            "answer": "Unsafe draft",
            "role": role,
            "sources": [],
            "validation_issues": ["Missing citation"],
        }


class BackendContractTests(unittest.TestCase):
    def setUp(self):
        self.previous_pipeline = backend.pipeline
        self.client = backend.app.test_client()

    def tearDown(self):
        backend.pipeline = self.previous_pipeline

    def test_health_reports_starting_without_pipeline(self):
        backend.pipeline = None

        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "starting")

    def test_analyze_rejects_empty_question_and_unknown_role(self):
        backend.pipeline = StubPipeline()

        empty = self.client.post("/analyze", json={"question": ""})
        unknown = self.client.post(
            "/analyze",
            json={"question": "Test", "role": "Dean"},
        )

        self.assertEqual(empty.status_code, 400)
        self.assertEqual(unknown.status_code, 400)

    def test_analyze_returns_pipeline_contract(self):
        backend.pipeline = StubPipeline()

        response = self.client.post(
            "/analyze",
            json={
                "question": "Which policy applies?",
                "role": "Student",
                "top_k": 3,
            },
        )
        payload = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["role"], "Student")
        self.assertEqual(payload["validation_issues"], [])
        self.assertIn("response_time_seconds", payload)

    def test_analyze_rejects_a_second_concurrent_request(self):
        backend.pipeline = StubPipeline()
        backend.analysis_lock.acquire()

        try:
            response = self.client.post(
                "/analyze",
                json={"question": "Test", "role": "Student"},
            )
        finally:
            backend.analysis_lock.release()

        self.assertEqual(response.status_code, 409)
        self.assertIn("already reviewing", response.get_json()["error"])

    def test_analyze_fails_closed_on_quality_violation(self):
        backend.pipeline = InvalidAnswerPipeline()

        response = self.client.post(
            "/analyze",
            json={"question": "Which policy?", "role": "Student"},
        )

        self.assertEqual(response.status_code, 422)
        self.assertIn("grounding", response.get_json()["error"])


if __name__ == "__main__":
    unittest.main()
