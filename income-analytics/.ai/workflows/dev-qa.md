# Development and QA workflow

## 1. Intake and classification

Record the task and acceptance criteria. Classify it before implementation:

- BACKEND_ONLY: domain, persistence, migrations, APIs, integrations, jobs or
  calculations only.
- FRONTEND_ONLY: pages, components, forms, styles, navigation or consumption
  of an existing contract only.
- FULL_STACK: a change spans backend and frontend.

For FULL_STACK work, establish API_CONTRACT first when the frontend depends on
a new backend behavior. The contract records endpoint, method, request,
response, validation, errors, authentication, authorization, domain notes and
backward compatibility.

## 2. Development

Run only the agent or agents selected by classification. Backend and Frontend
may work sequentially or in parallel when the contract makes that safe. Each
produces its own report and reports whether it is READY_FOR_QA or waiting for
the other layer.

## 3. Quality gate

QA receives the task, acceptance criteria, reports, diff and test evidence.
QA independently validates backend, frontend and end-to-end behavior when
applicable, then produces QA_REPORT.

- PASS means TASK_STATUS = DONE.
- FAIL means TASK_STATUS = RETURN_TO_DEV.

Every defect names the responsible agent. Return only those defects to
Backend, Frontend or both agents; after correction, run QA again.

## 4. Stop rule

After three consecutive QA failures for the same problem, set
TASK_STATUS = HUMAN_REVIEW_REQUIRED. Describe persistent defects, attempted
fixes, probable cause and whether a technical or domain decision is needed.

## 5. Reports and persistence

Reports normally remain in execution context. Persist them under
.ai/docs/tasks/ only when auditability or historical traceability is explicitly
needed; do not generate report files automatically for every task.
