import unittest
from unittest.mock import Mock

from src.rag_pipeline import (
    RAGPipeline,
    clean_answer,
    enforce_answer_contract,
    has_appeal_role_boundary_evidence,
    has_exchange_application_timing_evidence,
    is_appeal_decision_authority_question,
    is_ambiguous_application_question,
    is_degenerate_completion,
    is_exchange_application_question,
    validate_answer,
)


SOURCES = [
    {
        "source": "exchange_course_recognition_v2_2026.txt",
        "status": "current_approved",
        "supersedes": "exchange_course_recognition_v1_2022.txt",
        "superseded_by": "",
    },
    {
        "source": "exchange_course_recognition_v1_2022.txt",
        "status": "legacy",
        "supersedes": "",
        "superseded_by": "exchange_course_recognition_v2_2026.txt",
    },
]


class AnswerCleanupTests(unittest.TestCase):
    def test_cleanup_preserves_exact_supported_filenames(self):
        answer = (
            "Use the current procedure "
            "[exchange_course_recognition_v2_2026.txt][1] and the PDF "
            "[student_policy.pdf][2]."
        )

        cleaned = clean_answer(answer)

        self.assertIn(
            "[exchange_course_recognition_v2_2026.txt]",
            cleaned,
        )
        self.assertIn("[student_policy.pdf]", cleaned)
        self.assertNotIn("][1]", cleaned)
        self.assertNotIn("][2]", cleaned)

    def test_cleanup_collapses_a_repeated_adjacent_citation(self):
        answer = (
            "You cannot apply late "
            "[exchange_application_calendar_v1_2026.txt]. "
            "[exchange_application_calendar_v1_2026.txt]"
        )

        cleaned = clean_answer(answer)

        self.assertEqual(
            cleaned.count("[exchange_application_calendar_v1_2026.txt]"),
            1,
        )
        self.assertIn(
            "You cannot apply late "
            "[exchange_application_calendar_v1_2026.txt].",
            cleaned,
        )


class DegenerateCompletionTests(unittest.TestCase):
    def test_a_long_run_of_a_repeated_character_is_flagged(self):
        garbage = "!" * 200

        self.assertTrue(is_degenerate_completion(garbage))

    def test_a_normal_answer_is_not_flagged(self):
        answer = (
            "### Applicable guidance\n"
            "You may apply during the standard window "
            "[exchange_application_calendar_v1_2026.txt]."
        )

        self.assertFalse(is_degenerate_completion(answer))

    def test_a_short_legitimate_repeat_is_not_flagged(self):
        answer = "No, no, that procedure does not apply here."

        self.assertFalse(is_degenerate_completion(answer))


class AnswerValidationTests(unittest.TestCase):
    def test_appeal_authority_question_bypasses_chat_generation(self):
        source = {
            **SOURCES[0],
            "source": "student_appeals_v2_2025.txt",
            "title": "Student Academic Appeals Procedure",
            "supersedes": "",
            "content": (
                "A Department Administrator checks whether required fields "
                "and attachments are present but does not decide the merits "
                "of the appeal."
            ),
            "score": 0.9,
        }
        question = (
            "Can a Department Administrator decide the outcome of a "
            "student appeal?"
        )
        pipeline = RAGPipeline.__new__(RAGPipeline)
        pipeline.chat_client = object()
        pipeline._retrieve = Mock(return_value=[source])
        pipeline._complete_text = Mock(
            side_effect=AssertionError("chat generation should not run")
        )

        result = pipeline.answer(
            question,
            role="Department Administrator",
            top_k=3,
        )

        self.assertTrue(is_appeal_decision_authority_question(question))
        self.assertTrue(has_appeal_role_boundary_evidence(source))
        self.assertIn("No. A Department Administrator", result["answer"])
        self.assertEqual(result["answerability"], "supported")
        pipeline._complete_text.assert_not_called()

    def test_short_application_question_defaults_to_exchange_calendar(self):
        self.assertTrue(
            is_ambiguous_application_question("When can I apply?")
        )
        self.assertFalse(
            is_ambiguous_application_question(
                "When can I apply for the exchange?"
            )
        )

        source = {
            **SOURCES[0],
            "source": "exchange_application_calendar_v1_2026.txt",
            "title": "Exchange Program Application Calendar",
            "supersedes": "",
            "content": (
                "Students may apply during either standard window each "
                "academic year: 1–15 March for autumn mobility, and 1–15 "
                "October for spring mobility. The student submits the "
                "online application through the mobility portal. The "
                "International Programs Office owns the calendar. This "
                "calendar does not create a late-application process."
            ),
            "score": 0.9,
        }
        pipeline = RAGPipeline.__new__(RAGPipeline)
        pipeline.chat_client = object()
        pipeline._retrieve = Mock(return_value=[source])
        pipeline._complete_text = Mock(
            side_effect=AssertionError("Model should not be called")
        )

        result = pipeline.answer("When can I apply?", role="Student")

        self.assertEqual(result["answerability"], "supported")
        self.assertIn("1–15 March", result["answer"])
        self.assertIn("1–15 October", result["answer"])
        self.assertEqual(result["sources"], [source])
        retrieval_question = pipeline._retrieve.call_args.kwargs["question"]
        self.assertIn("exchange program", retrieval_question)
        self.assertEqual(pipeline._retrieve.call_args.kwargs["top_k"], 6)
        pipeline._complete_text.assert_not_called()

    def test_contract_handles_sources_without_a_governance_pair(self):
        sources = [
            {
                **SOURCES[0],
                "supersedes": "",
                "content": "The student submits a signed document.",
            }
        ]
        draft = """### Applicable guidance
The current policy applies [exchange_course_recognition_v2_2026.txt].
### Actions for the selected role
1. Submit a signed document [exchange_course_recognition_v2_2026.txt].
### Responsibilities of other roles
No other-role responsibility specifies this request [exchange_course_recognition_v2_2026.txt].
### Version and conflict check
No relevant version conflict was found.
### Information gaps
No material information gap was identified in the retrieved evidence."""

        enforced = enforce_answer_contract(
            draft,
            sources,
            role="Student",
            question="When can I submit a signed document?",
        )

        self.assertIn("No relevant version conflict", enforced)

    def test_contract_replaces_fabricated_conflict_between_unrelated_docs(
        self,
    ):
        sources = [
            {
                "source": "exchange_application_calendar_v1_2026.txt",
                "status": "current_approved",
                "supersedes": "",
                "superseded_by": "",
                "content": "The calendar does not create a late-application process.",
            },
            {
                "source": "student_appeals_v2_2025.txt",
                "status": "current_approved",
                "supersedes": "",
                "superseded_by": "",
                "content": "This procedure does not specify a universal deadline.",
            },
        ]
        draft = """### Applicable guidance
The calendar does not create a late-application process [exchange_application_calendar_v1_2026.txt].
### Actions for the selected role
No selected-role action is specified [exchange_application_calendar_v1_2026.txt].
### Responsibilities of other roles
No other-role responsibility is specified [exchange_application_calendar_v1_2026.txt].
### Version and conflict check
There is a documented procedural conflict/difference with the Student Academic Appeals Procedure [student_appeals_v2_2025.txt]. The calendar must not be used for a new request [exchange_application_calendar_v1_2026.txt].
### Information gaps
No material information gap was identified in the retrieved evidence [exchange_application_calendar_v1_2026.txt]."""

        enforced = enforce_answer_contract(draft, sources, role="Student")

        self.assertNotIn("documented procedural conflict", enforced)
        self.assertNotIn("must not be used", enforced)
        self.assertIn(
            "No linked current-versus-historical version conflict",
            enforced,
        )
        self.assertEqual(
            validate_answer(enforced, sources, "Student"),
            [],
        )

    def test_exchange_application_intent_is_narrow(self):
        self.assertTrue(
            is_exchange_application_question(
                "When can I apply for the exchange?"
            )
        )
        self.assertTrue(
            is_exchange_application_question(
                "What is the Erasmus application deadline?"
            )
        )
        self.assertFalse(
            is_exchange_application_question(
                "When should I submit my final transcript after exchange?"
            )
        )
        self.assertFalse(
            is_exchange_application_question(
                "Can I request course recognition after the exchange?"
            )
        )

    def test_only_current_application_timing_counts_as_evidence(self):
        legacy = {
            **SOURCES[1],
            "content": "This must not be used for new applications.",
        }
        current = {
            **SOURCES[0],
            "title": "Exchange Application Calendar",
            "content": "Exchange applications open on 1 March.",
        }

        self.assertFalse(
            has_exchange_application_timing_evidence([legacy])
        )
        self.assertTrue(
            has_exchange_application_timing_evidence([current])
        )

    def test_exchange_application_question_returns_an_information_gap(self):
        sources = [
            {
                **SOURCES[0],
                "title": "Exchange Course Recognition Procedure",
                "content": "Students prepare a course-mapping table.",
                "score": 0.8,
            },
            {
                **SOURCES[1],
                "content": "This must not be used for new applications.",
                "score": 0.7,
            },
        ]
        pipeline = RAGPipeline.__new__(RAGPipeline)
        pipeline.chat_client = object()
        pipeline._retrieve = Mock(return_value=sources)
        pipeline._complete_text = Mock(
            side_effect=AssertionError("Model should not be called")
        )

        result = pipeline.answer(
            "When can I apply the exchange?",
            role="Student",
        )

        self.assertEqual(result["answerability"], "not_covered")
        self.assertIn("do not state when", result["answer"])
        self.assertIn("application portal", result["next_step"])
        self.assertEqual(
            [item["status"] for item in result["sources"]],
            ["current_approved"],
        )
        pipeline._complete_text.assert_not_called()

    def test_compliant_role_and_conflict_answer_passes(self):
        answer = """### Applicable guidance
Version 2.0 is the governing procedure [exchange_course_recognition_v2_2026.txt].

### Actions for the selected role
1. Prepare the proposed mapping before mobility [exchange_course_recognition_v2_2026.txt].
2. Submit the final documents after mobility [exchange_course_recognition_v2_2026.txt].

### Responsibilities of other roles
- Academic Advisor: review academic fit [exchange_course_recognition_v2_2026.txt].
- Department Administrator: record the approved mapping [exchange_course_recognition_v2_2026.txt].

### Version and conflict check
The current_approved pre-approval rule and legacy post-return rule are a documented procedural conflict/difference [exchange_course_recognition_v2_2026.txt] [exchange_course_recognition_v1_2022.txt]. The current_approved version is the governing source; the legacy procedure must not be used for a new request [exchange_course_recognition_v2_2026.txt] [exchange_course_recognition_v1_2022.txt].

### Information gaps
No guaranteed processing time is specified [exchange_course_recognition_v2_2026.txt]."""

        self.assertEqual(
            validate_answer(answer, SOURCES, "Student"),
            [],
        )

    def test_missing_citation_and_role_leakage_are_reported(self):
        answer = """### Applicable guidance
Use version 2.0.

### Actions for the selected role
1. Academic Advisor reviews academic fit.

### Responsibilities of other roles
- Department Administrator records the mapping.

### Version and conflict check
There is no conflict.

### Information gaps
None."""

        issues = validate_answer(answer, SOURCES, "Student")

        self.assertTrue(
            any("lacks a direct" in issue for issue in issues)
        )
        self.assertTrue(
            any("another role" in issue for issue in issues)
        )
        self.assertTrue(
            any("procedural conflict/difference" in issue for issue in issues)
        )

    def test_hallucinated_source_is_reported(self):
        answer = "\n".join(REQUIRED_MINIMAL_ANSWER) + " [made_up.txt]"

        issues = validate_answer(answer, SOURCES, "Student")

        self.assertTrue(
            any("made_up.txt" in issue for issue in issues)
        )

    def test_leaked_governance_score_is_reported(self):
        answer = """### Applicable guidance
Current guidance applies [exchange_course_recognition_v2_2026.txt].
### Actions for the selected role
1. Prepare the mapping [exchange_course_recognition_v2_2026.txt].
### Responsibilities of other roles
- Advisor: review it [exchange_course_recognition_v2_2026.txt].
### Version and conflict check
The evidence is a current_approved policy with a governance-aware score of 0.8204 [exchange_course_recognition_v2_2026.txt].
### Information gaps
No processing time is specified [exchange_course_recognition_v2_2026.txt]."""

        issues = validate_answer(answer, SOURCES, "Student")

        self.assertTrue(
            any("numeric scores" in issue for issue in issues)
        )

    def test_fabricated_conflict_between_unrelated_documents_is_reported(
        self,
    ):
        unrelated_sources = [
            {
                "source": "exchange_application_calendar_v1_2026.txt",
                "status": "current_approved",
                "supersedes": "",
                "superseded_by": "",
            },
            {
                "source": "student_appeals_v2_2025.txt",
                "status": "current_approved",
                "supersedes": "",
                "superseded_by": "",
            },
        ]
        answer = """### Applicable guidance
The calendar does not create a late-application process [exchange_application_calendar_v1_2026.txt].

### Actions for the selected role
No selected-role action is specified [exchange_application_calendar_v1_2026.txt].

### Responsibilities of other roles
No other-role responsibility is specified [exchange_application_calendar_v1_2026.txt].

### Version and conflict check
There is a documented procedural conflict/difference with the Student Academic Appeals Procedure [student_appeals_v2_2025.txt]. The calendar must not be used for a new request [exchange_application_calendar_v1_2026.txt].

### Information gaps
No material information gap was identified in the retrieved evidence [exchange_application_calendar_v1_2026.txt]."""

        issues = validate_answer(answer, unrelated_sources, "Student")

        self.assertTrue(
            any(
                "no linked current/historical version relationship"
                in issue
                for issue in issues
            )
        )

    def test_unrelated_current_documents_without_conflict_claim_pass(self):
        unrelated_sources = [
            {
                "source": "exchange_application_calendar_v1_2026.txt",
                "status": "current_approved",
                "supersedes": "",
                "superseded_by": "",
            },
            {
                "source": "student_appeals_v2_2025.txt",
                "status": "current_approved",
                "supersedes": "",
                "superseded_by": "",
            },
        ]
        answer = """### Applicable guidance
The calendar does not create a late-application process [exchange_application_calendar_v1_2026.txt].

### Actions for the selected role
No selected-role action is specified [exchange_application_calendar_v1_2026.txt].

### Responsibilities of other roles
No other-role responsibility is specified [exchange_application_calendar_v1_2026.txt].

### Version and conflict check
No relevant version conflict was found in the retrieved evidence [exchange_application_calendar_v1_2026.txt].

### Information gaps
No material information gap was identified in the retrieved evidence [exchange_application_calendar_v1_2026.txt]."""

        issues = validate_answer(answer, unrelated_sources, "Student")

        self.assertEqual(issues, [])

    def test_contract_removes_legacy_action_and_adds_governance(self):
        draft = """### Applicable guidance
The current policy applies [exchange_course_recognition_v2_2026.txt].

### Actions for the selected role
1. Prepare the mapping before mobility [exchange_course_recognition_v2_2026.txt].
2. Wait until returning to request recognition [exchange_course_recognition_v1_2022.txt].

### Responsibilities of other roles
- Academic Advisor: review the mapping [exchange_course_recognition_v2_2026.txt].

### Version and conflict check
The current policy replaced the legacy procedure [exchange_course_recognition_v2_2026.txt] [exchange_course_recognition_v1_2022.txt].

### Information gaps
Processing time is not specified [exchange_course_recognition_v2_2026.txt]."""

        enforced = enforce_answer_contract(draft, SOURCES)

        self.assertNotIn("Wait until returning", enforced)
        self.assertIn("documented procedural conflict/difference", enforced)
        self.assertIn("governing source", enforced)
        self.assertEqual(
            validate_answer(enforced, SOURCES, "Student"),
            [],
        )

    def test_contract_removes_historical_instruction_with_current_citation(self):
        sources = [
            {
                **SOURCES[0],
                "content": (
                    "The student prepares a proposed mapping before mobility."
                ),
            },
            {
                **SOURCES[1],
                "content": (
                    "The student submits a personal equivalency proposal "
                    "after returning."
                ),
            },
        ]
        draft = """### Applicable guidance
Current guidance applies [exchange_course_recognition_v2_2026.txt].
### Actions for the selected role
1. Prepare a proposed mapping before mobility [exchange_course_recognition_v2_2026.txt].
2. Submit a personal equivalency proposal after returning [exchange_course_recognition_v2_2026.txt].
### Responsibilities of other roles
- Advisor: review the mapping [exchange_course_recognition_v2_2026.txt].
### Version and conflict check
The current_approved governing source and legacy version have a documented procedural difference; the legacy version must not be used for a new request [exchange_course_recognition_v2_2026.txt] [exchange_course_recognition_v1_2022.txt].
### Information gaps
No material information gap was identified in the retrieved evidence."""

        enforced = enforce_answer_contract(draft, sources)

        self.assertIn("Prepare a proposed mapping", enforced)
        self.assertNotIn("personal equivalency proposal", enforced)

    def test_contract_keeps_only_actions_owned_by_selected_staff_role(self):
        sources = [
            {
                **SOURCES[0],
                "content": (
                    "The Academic Advisor reviews academic fit. "
                    "The Department Administrator records the approved "
                    "mapping in the student information system. "
                    "The Academic Advisor verifies that completed courses "
                    "match the approved mapping. "
                    "The revised documents must be reviewed before reliance. "
                    "The Department Administrator sends the verified package "
                    "to the department committee."
                ),
            },
            {**SOURCES[1], "content": "A historical procedure."},
        ]
        draft = """### Applicable guidance
Current guidance applies [exchange_course_recognition_v2_2026.txt].
### Actions for the selected role
1. Review academic fit [exchange_course_recognition_v2_2026.txt].
2. Record the approved mapping in the student information system [exchange_course_recognition_v2_2026.txt].
3. Verify completed courses match the approved mapping [exchange_course_recognition_v2_2026.txt].
4. Send the verified package to the department committee [exchange_course_recognition_v2_2026.txt].
5. Review the revised documents before reliance [exchange_course_recognition_v2_2026.txt].
### Responsibilities of other roles
- Department Administrator: record and send the package [exchange_course_recognition_v2_2026.txt].
### Version and conflict check
The current_approved governing source and legacy version have a documented procedural difference; the legacy version must not be used for a new request [exchange_course_recognition_v2_2026.txt] [exchange_course_recognition_v1_2022.txt].
### Information gaps
No material information gap was identified in the retrieved evidence."""

        enforced = enforce_answer_contract(
            draft,
            sources,
            role="Academic Advisor",
        )

        selected = enforced.split(
            "### Responsibilities of other roles",
            1,
        )[0]
        self.assertIn("Review academic fit", selected)
        self.assertIn("Verify completed courses", selected)
        self.assertNotIn("Record the approved mapping", selected)
        self.assertNotIn("Send the verified package", selected)
        self.assertNotIn("Review the revised documents", selected)

    def test_contract_adds_missing_other_role_from_current_evidence(self):
        sources = [
            {
                **SOURCES[0],
                "content": (
                    "If a host course changes, the student must submit a "
                    "revised mapping and updated Learning Agreement. "
                    "The Academic Advisor reviews academic fit."
                ),
            },
            {**SOURCES[1], "content": "A historical procedure."},
        ]
        draft = """### Applicable guidance
Current guidance applies [exchange_course_recognition_v2_2026.txt].
### Actions for the selected role
1. Review academic fit [exchange_course_recognition_v2_2026.txt].
### Responsibilities of other roles
- Department Administrator: record the mapping [exchange_course_recognition_v2_2026.txt].
### Version and conflict check
The current_approved governing source and legacy version have a documented procedural difference; the legacy version must not be used for a new request [exchange_course_recognition_v2_2026.txt] [exchange_course_recognition_v1_2022.txt].
### Information gaps
No material information gap was identified in the retrieved evidence."""

        enforced = enforce_answer_contract(
            draft,
            sources,
            role="Academic Advisor",
            question="A student changed a host course during mobility.",
        )

        self.assertIn("- Student:", enforced)
        self.assertIn("submit a revised mapping", enforced)

    def test_contract_does_not_turn_demo_notice_into_a_responsibility(self):
        sources = [
            {
                **SOURCES[0],
                "content": (
                    "SYNTHETIC DEMONSTRATION DOCUMENT — NOT AN OFFICIAL "
                    "UNIVERSITY POLICY Purpose This current procedure "
                    "governs course-recognition requests for students "
                    "participating in an international exchange. Before "
                    "mobility The student must prepare a proposed mapping. "
                    "The Academic Advisor reviews academic fit."
                ),
            },
            {**SOURCES[1], "content": "A historical procedure."},
        ]
        draft = """### Applicable guidance
Current guidance applies [exchange_course_recognition_v2_2026.txt].
### Actions for the selected role
1. Review academic fit [exchange_course_recognition_v2_2026.txt].
### Responsibilities of other roles
- Department Administrator: record the mapping [exchange_course_recognition_v2_2026.txt].
### Version and conflict check
The current policy supersedes the legacy version.
### Information gaps
No material information gap was identified in the retrieved evidence."""

        enforced = enforce_answer_contract(
            draft,
            sources,
            role="Academic Advisor",
            question="Which procedure applies to course approval?",
        )

        self.assertNotIn("SYNTHETIC DEMONSTRATION", enforced)
        self.assertNotIn("Purpose This current procedure", enforced)

    def test_contract_cites_uncited_governance_and_gap_sentences(self):
        sources = [
            {
                **SOURCES[0],
                "content": (
                    "This policy does not specify a guaranteed number of "
                    "working days for completion."
                ),
            },
            {**SOURCES[1], "content": "Students could apply after return."},
        ]
        draft = """### Applicable guidance
The current policy applies.
### Actions for the selected role
1. Follow the current procedure [exchange_course_recognition_v2_2026.txt].
### Responsibilities of other roles
- Advisor: review the request [exchange_course_recognition_v2_2026.txt].
### Version and conflict check
The current policy supersedes the legacy version. The legacy instruction must not be used.
### Information gaps
The policy does not specify a guaranteed number of working days."""

        enforced = enforce_answer_contract(draft, sources, role="Student")

        self.assertEqual(
            validate_answer(enforced, sources, "Student"),
            [],
        )

    def test_contract_cites_a_plain_no_action_sentence(self):
        sources = [
            {
                **SOURCES[0],
                "content": (
                    "This procedure governs course-recognition requests."
                ),
            },
            {**SOURCES[1], "content": "A historical procedure."},
        ]
        draft = """### Applicable guidance
The current policy applies [exchange_course_recognition_v2_2026.txt].
### Actions for the selected role
No actions are required from the Student role as per the retrieved evidence.
### Responsibilities of other roles
No other-role responsibility specifies this request [exchange_course_recognition_v2_2026.txt].
### Version and conflict check
No relevant version conflict was found.
### Information gaps
No material information gap was identified in the retrieved evidence."""

        enforced = enforce_answer_contract(draft, sources, role="Student")

        self.assertEqual(
            validate_answer(enforced, sources, "Student"),
            [],
        )

    def test_contract_keeps_timing_question_concise(self):
        sources = [
            {
                **SOURCES[0],
                "content": (
                    "The student prepares a mapping. This policy does not "
                    "specify a guaranteed number of working days."
                ),
            },
            {**SOURCES[1], "content": "A historical procedure."},
        ]
        draft = """### Applicable guidance
The current policy applies.
### Actions for the selected role
1. Prepare a mapping [exchange_course_recognition_v2_2026.txt].
### Responsibilities of other roles
- Advisor: review the mapping [exchange_course_recognition_v2_2026.txt].
### Version and conflict check
The current policy supersedes the legacy version.
### Information gaps
No duration is specified. No material information gap was identified in the retrieved evidence."""

        enforced = enforce_answer_contract(
            draft,
            sources,
            role="Student",
            question="Exactly how many working days will processing take?",
        )

        self.assertNotIn("Prepare a mapping", enforced)
        self.assertIn("No selected-role action", enforced)
        self.assertIn("No other-role responsibility", enforced)
        self.assertNotIn("No material information gap", enforced)

    def test_contract_fills_empty_staff_actions_from_owned_evidence(self):
        sources = [
            {
                **SOURCES[0],
                "content": (
                    "The Department Administrator verifies signatures and "
                    "document completeness."
                ),
            },
            {**SOURCES[1], "content": "A historical procedure."},
        ]
        draft = """### Applicable guidance
The current policy applies.
### Actions for the selected role

### Responsibilities of other roles
- Student: upload the signed document [exchange_course_recognition_v2_2026.txt].
### Version and conflict check
The current policy supersedes the legacy version.
### Information gaps
No material information gap was identified in the retrieved evidence."""

        enforced = enforce_answer_contract(
            draft,
            sources,
            role="Department Administrator",
            question="Is an unsigned document complete?",
        )

        self.assertIn("verifies signatures", enforced)


REQUIRED_MINIMAL_ANSWER = (
    "### Applicable guidance",
    "Current guidance applies [exchange_course_recognition_v2_2026.txt].",
    "### Actions for the selected role",
    "1. Prepare the mapping [exchange_course_recognition_v2_2026.txt].",
    "### Responsibilities of other roles",
    "- Advisor: review it [exchange_course_recognition_v2_2026.txt].",
    "### Version and conflict check",
    "A documented procedural difference exists between the current_approved governing source and legacy version; the legacy version must not be used for a new request [exchange_course_recognition_v2_2026.txt] [exchange_course_recognition_v1_2022.txt].",
    "### Information gaps",
    "No processing time is specified [exchange_course_recognition_v2_2026.txt].",
)


if __name__ == "__main__":
    unittest.main()
