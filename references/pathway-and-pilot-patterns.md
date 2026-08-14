# Pathway taxonomy and pilot patterns

## Contents

1. Classification dimensions
2. Shared spine
3. Existing person roster
4. Event participant roster
5. Role-specific organization roster
6. Organization-universe custom path
7. Branch and Batch rules

## Classification dimensions

Classify the starting artifact, relationship complexity, evidence policy, outcome target, operational unit, and current maturity before selecting a baseline. Project names are weak evidence; inspect the contract and canonical artifacts.

## Shared spine

Every full map starts with:

`N00_PROJECT_INTAKE -> N01_SOURCE_INVENTORY -> N02_SCOPE_CONTRACT`

Most paths then include stable IDs, roster/identity work as needed, `N04_COORDINATOR_CAPACITY_PLAN`, contact research, evidence and confidence gates, `N31_BATCH_SCHEMA_QA`, release, export, and learning.

Do not force every Project through every roster node. Record skipped nodes and why.

## Existing person roster

Nearest pilot: LinkedIn connections.

Use when a stable person roster already exists and the main work is enrichment.

Typical path:

`N00 -> N01 -> N02 -> N03 -> N04 -> N20 -> decision: direct evidence -> N21/N24 -> decision: creative lane -> N22 -> N23 -> N24 -> N25 -> N26 -> N31 -> N33 -> N34 -> N41/N42 -> N43`

Starting recommendation: 25-person calibration Batch; consider 50 only after validated time, token, tool, yield, and QA observations. Partition on a stable ordinal or record ID. Recalculate when concurrent lanes change.

## Event participant roster

Nearest pilot: AIME-Con.

Use when event/program evidence creates person-event and organization relationships before contact research.

Typical path:

`N00 -> N01 -> N02 -> N10 -> N11 -> N12 -> N13 -> N14 -> N15 -> N04 -> N20 -> N21/N24 -> N22 -> N23 -> N24 -> N25 -> N26 -> N31 -> N32 -> N33 -> N34 -> N41/N42 -> N43`

Preserve event-time role, current role, person-event relationships, and source rows. Group by normalized organization when that reduces duplicate source discovery. Starting recommendation: 10-15 organizations or about 25 people per contact Batch.

## Role-specific organization roster

Nearest pilot: school-system officials.

Use when the research target is a functional role within each organization and a stable organization key is available.

Typical path:

`N00 -> N01 -> N02 -> N03 -> N10 -> N11 -> N13 -> N15 -> N04 -> N20 -> N21/N24 -> N22 -> N23 -> N24 -> N25 -> N26 -> N31 -> N32 -> N33 -> N34 -> N41/N42 -> N43`

Preserve organization keys and source order. Measure workload in organization-role units, not organizations alone. Starting recommendation: 25 organizations with five-organization checkpoints only when the role taxonomy and existing skill support that shape.

The current school-system workflow prohibits inferred email addresses. Treat its candidate lane as disabled unless a recorded Project-contract decision changes the policy.

## Organization-universe custom path

Use when the Project begins with organizations but lacks a sufficiently complete staff or person roster.

Typical path:

`N00 -> N01 -> N02 -> N03 -> N10 -> N11 -> N12/N13 -> N14 -> N15 -> N04 -> contact spine -> release and learning`

Use `organizational-roster-building` for universe construction and organization evidence. Hand off to roster or contact skills only after organization identity and coverage checks pass.

Start with 5-10 organizations when staff depth and source friction are unknown.

## Branch and Batch rules

| Question | Yes | No / unresolved |
|---|---|---|
| Usable roster exists? | Skip extraction with rationale. | Run roster extraction and resolution nodes. |
| Identity/role QA passes? | Proceed to capacity planning/contact work. | Enter conflict review or exception triage. |
| Exact direct email evidence exists? | Run `N24_PUBLIC_EMAIL_ATTRIBUTION`. | Keep direct field empty; consider office route. |
| Office route acceptable? | Store through `N21_OFFICE_ROUTE_RESEARCH`. | Mark unresolved or rinse-and-repeat. |
| Creative lane permitted? | Run optional `N22` then `N23`. | Skip candidate nodes and record policy. |
| Candidate publicly attributed? | Promote through `N24`. | Retain/reject as candidate; never promote by pattern alone. |
| Batch QA passes? | Merge and release. | Triage exception; bounded retry only after repair. |
| Performance observed? | Recalibrate from validated actuals. | Use a low-confidence pilot calibration. |

Batch viability depends on unit complexity, tokens, tool calls, time, source friction, active concurrency, and coordinator merge/QA capacity. A production target is not a Batch-size rule.
