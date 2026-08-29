# GlobalMobility EDU Acceptance Tests

## 1. Exchange application period

- Role: Student
- Question: `When can I apply?`
- Expected: answer the recurring March and October exchange-application windows from `exchange_application_calendar_v1_2026.txt`; do not return course-recognition or transcript steps.

## 2. Current policy overrides legacy advice

- Role: Student
- Expected: prefer `exchange_course_recognition_v2_2026.txt`, identify version 1 as legacy and explain the conflict with citations.

## 3. Role-aware responsibility

- Role: Academic Advisor
- Expected: the advisor reviews academic compatibility; the student submits revised documents; the committee retains final recognition authority.

## 4. Missing-information refusal

- Role: Student
- Expected: report that the retrieved evidence does not guarantee a number of processing days. Never invent a duration.

## 5. Learning Agreement conflict

- Role: Department Administrator
- Expected: an unsigned email attachment is not a completed current submission; distinguish the current portal procedure from the superseded email guide.
