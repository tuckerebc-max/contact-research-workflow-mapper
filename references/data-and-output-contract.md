# Mapper data and output contract

## Contents

1. Canonical inputs
2. Workflow map schema
3. Recommendation schema
4. Gap schema
5. Proposed Tracker updates

## Canonical inputs

Require:

- `project_register.csv`
- `node_inventory.csv`

Use when present:

- `workstream_register.csv`
- `batch_register.csv`
- `decision_log.csv`
- `exceptions.csv`
- `next_actions.csv`
- `pilot_workflow_maps.csv`
- `skill_catalog.csv`
- Project contracts, rosters, QA reports, checkpoints, and canonical outputs

The Mapper reads these files. It does not modify them unless the user explicitly requests an update after reviewing the proposed changes.

## Workflow map schema

Use one row per node or decision.

| Field | Required | Meaning |
|---|---:|---|
| `map_id` | Yes | Stable map-step ID. |
| `project_id` | Yes | Parent Project ID. |
| `sequence` | Yes | Unique positive integer. |
| `step_type` | Yes | `NODE` or `DECISION`. |
| `node_id` | Yes | Registered node ID or stable decision ID. |
| `node_name` | Yes | Human-readable transformation or question. |
| `required_or_optional` | Yes | `REQUIRED`, `OPTIONAL`, or `SKIPPED`. |
| `entry_condition` | Yes | What must be true before the step. |
| `exit_criteria` | Yes | Testable completion or disposition rule. |
| `decision_gate` | For decisions | Stable decision ID or question key. |
| `possible_next_nodes` | Yes | Semicolon-separated registered node IDs; use `END` only for an intentional terminal. |
| `batch_unit` | Yes | Project, organization, person, candidate, district, district-role, Batch, or other explicit unit. |
| `coordinator_note` | No | Concise operating guidance. |
| `recommended_skill_or_process` | Yes | Formal skill, repeatable process, or `PROCESS_NOT_FORMALIZED`. |
| `basis` | Yes | `PROJECT_CONTRACT`, `TRACKER_STATE`, `LIVE_OBSERVATION`, `PILOT_PATTERN`, or `MAPPER_INFERENCE`. |
| `confidence` | Yes | `HIGH`, `MEDIUM`, or `LOW`. |
| `mapper_status` | Yes | `PROPOSED`, `REVIEWED`, `ACCEPTED`, `SUPERSEDED`, or `REJECTED`. |

Decision IDs do not need to appear in the node inventory. Node-step IDs must resolve exactly.

## Recommendation schema

Write `mapper_recommendation.json` with:

- `project_id`, `project_name`, `archetype`, and `baseline`;
- `classification` dimensions;
- `current_node_id`, `recommended_next_node_id`, and `recommended_skill_or_process`;
- `batch_recommendation`: unit, records, checkpoint records, available slots, capacity status, basis, confidence, and observed Batch count;
- `creative_lane_status` and `decisions_required`;
- `map_counts`: required, optional, skipped, decisions, and nodes;
- `gaps`: blocking, material, and learning counts;
- `proposed_tracker_updates`;
- `generated_at`.

Use ISO 8601 UTC for timestamps. A timestamp does not make a recommendation current if the underlying Tracker checkpoint is stale.

## Gap schema

Write one row per issue to `workflow_gaps.csv`:

`gap_id`, `project_id`, `node_id`, `gap_type`, `severity`, `evidence`, `recommended_action`, `status`.

Controlled values:

- severity: `BLOCKING`, `MATERIAL`, `LEARNING`;
- status: `OPEN`, `ACCEPTED`, `FIXED`, `DEFERRED`, `NOT_APPLICABLE`.

Common gap types:

- `NODE_NOT_REGISTERED`
- `PROCESS_NOT_FORMALIZED`
- `HANDOFF_AMBIGUOUS`
- `DECISION_REQUIRED`
- `CANDIDATE_ATTRIBUTION_GAP`
- `CAPACITY_UNCALIBRATED`
- `CURRENT_NODE_OUTSIDE_MAP`
- `MAP_REGISTER_MISMATCH`
- `ACCEPTANCE_CHECK_WEAK`
- `NODE_SCHEMA_MISALIGNED`

## Proposed Tracker updates

Return proposed updates as a list; do not apply them by default. Each proposal must name:

- target register and stable row ID;
- field and current value when known;
- proposed value;
- reason and evidence IDs;
- whether the update is required before execution;
- Decision record required, if any.

Keep Project strategy in the Project register and bounded execution in the Batch register. Do not move person-, organization-, or email-level rows into the portfolio Tracker.
