# Improvement and handoff contract

## Mapper to Tracker

Propose, but do not silently apply:

- Project current-node or next-action changes;
- Workstream or Batch creation/resizing;
- new dependency, Decision, Exception, Artifact, or Node rows;
- status transitions;
- capacity assumptions and calibration fields.

Every material proposal must identify the register, stable row ID, field, current value, proposed value, rationale, evidence, and Decision requirement.

The Tracker remains authoritative for live state and prioritization.

## Mapper to worker skills

Handoff one bounded node execution at a time. Include:

- Project, Workstream, Batch, and Node IDs;
- exact source and assignment scope;
- required input fields and stable keys;
- expected output artifact and schema;
- source/evidence policy;
- acceptance check and stopping rule;
- checkpoint cadence and capacity ceiling;
- candidate-email policy;
- output path and return counts.

Use these default handoffs when available:

- organization-universe discovery -> `organizational-roster-building`;
- conference/event roster -> `research-conference-presenter-roster`;
- role-specific school-system research -> `school-system-assessment-contact-research`;
- public contact discovery -> `coordinated-efficient-contact-research`;
- freshness-sensitive source lookup -> `current-info-search`;
- material branch rationale -> `agent-decision-receipts`;
- Tracker state or priority update -> `contact-research-work-tracker`.

If no formal skill owns a node, name the repeatable process and mark `PROCESS_NOT_FORMALIZED`.

## Skill or worker-prompt revision proposals

Create a proposal only when supported by one of:

- a blocking structural defect;
- repeated exceptions or rework;
- validated Batch performance showing a consistent weakness or opportunity;
- a stable successful pattern across more than one Project;
- a policy change recorded in the Project contract.

Do not treat one anecdotal result or an unvalidated worker return as general evidence.

Use this proposal schema:

`proposal_id`, `target_skill_or_process`, `mapped_node_ids`, `evidence_class`, `evidence_ids`, `observed_pattern`, `proposed_change`, `expected_effect`, `risk`, `test_case`, `rollback`, `status`.

Evidence classes:

- `DESIGN_EVIDENCE`
- `PILOT_EVIDENCE`
- `LIVE_VALIDATED_EVIDENCE`
- `POLICY_DECISION`

Statuses:

- `PROPOSED`
- `NEEDS_REVIEW`
- `ACCEPTED`
- `IMPLEMENTED`
- `REJECTED`
- `SUPERSEDED`

Hand substantial creation or revision to `skill-creator`; hand release-readiness review to `project-skill-audit-enhanced`. Do not edit another skill merely because the Mapper detected an opportunity unless the user explicitly requests implementation.

## Learning loop

After each validated cohort:

1. compare estimated and actual time, tokens, tools, rows, usable emails, candidates, exceptions, and QA effort;
2. separate worker throughput from coordinator merge/QA time;
3. compare candidate-to-verified conversion and direct-email yield;
4. identify whether the issue is pathway, node, handoff, Batch-size, evidence-policy, or skill behavior;
5. propose the smallest reversible change and a test case;
6. record the outcome in the Decision log and update the map only after review.

## Safety and evidence boundaries

- Never authorize paid enrichment, subscriptions, outreach, login, scraping, publication, or external messages through a workflow recommendation alone.
- Never weaken a source or evidence policy to increase reported yield.
- Never merge candidate and verified direct-email counts.
- Never fabricate missing performance observations.
- Keep raw artifacts and superseded maps for auditability; use stable status fields instead of destructive replacement.
