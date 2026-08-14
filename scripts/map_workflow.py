#!/usr/bin/env python3
"""Create a proposed contact-research workflow map from Tracker artifacts.

The script is read-only with respect to Tracker inputs. It writes a proposed map,
recommendation, and gap report into a separate output directory.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MAP_FIELDS = [
    "map_id",
    "project_id",
    "sequence",
    "step_type",
    "node_id",
    "node_name",
    "required_or_optional",
    "entry_condition",
    "exit_criteria",
    "decision_gate",
    "possible_next_nodes",
    "batch_unit",
    "coordinator_note",
    "recommended_skill_or_process",
    "basis",
    "confidence",
    "mapper_status",
]

GAP_FIELDS = [
    "gap_id",
    "project_id",
    "node_id",
    "gap_type",
    "severity",
    "evidence",
    "recommended_action",
    "status",
]

ARCHETYPES = {
    "existing-person-roster",
    "event-participant-roster",
    "role-specific-organizations",
    "organization-universe",
    "custom",
}

MAPPER_NODES = {
    "N02_SCOPE_CONTRACT",
    "N04_COORDINATOR_CAPACITY_PLAN",
    "N42_THROUGHPUT_RETROSPECTIVE",
    "N43_SKILL_SPEC_REVISION",
    "N44_NEW_UNIVERSE_DISCOVERY",
}

FORMALIZATION_STATUSES = {"INVENTORY", "FORMALIZED", "PROVISIONAL", "PLANNED"}


def read_csv(path: Path, required: bool = False) -> list[dict[str, str]]:
    if not path.exists():
        if required:
            raise FileNotFoundError(f"Missing required file: {path}")
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def integer(row: dict[str, str], key: str, default: int = 0) -> int:
    try:
        return int(float((row.get(key) or "").strip()))
    except (TypeError, ValueError):
        return default


def slug(value: str, maximum: int = 24) -> str:
    cleaned = re.sub(r"[^A-Z0-9]+", "-", value.upper()).strip("-")
    if cleaned.startswith("PRJ-"):
        cleaned = cleaned[4:]
    return (cleaned or "PROJECT")[:maximum].rstrip("-")


def split_ids(value: str) -> list[str]:
    return [item.strip() for item in re.split(r"[;,]", value or "") if item.strip()]


def normalize_node_rows(rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], int]:
    """Normalize the legacy one-column-left node row shape without mutating input."""
    normalized: list[dict[str, str]] = []
    shifted_count = 0
    for original in rows:
        row = dict(original)
        if (
            (row.get("formalization_status") or "") not in FORMALIZATION_STATUSES
            and (row.get("optional_flag") or "") in FORMALIZATION_STATUSES
        ):
            shifted_count += 1
            row["notes"] = row.get("pilot_relevance") or ""
            row["pilot_relevance"] = row.get("owner") or ""
            row["owner"] = row.get("formalization_status") or ""
            row["formalization_status"] = row.get("optional_flag") or ""
            row["optional_flag"] = row.get("common_next_nodes") or ""
            row["common_next_nodes"] = row.get("acceptance_check") or ""
            row["acceptance_check"] = row.get("evidence_bar") or ""
            row["evidence_bar"] = row.get("token_tool_profile") or ""
            row["token_tool_profile"] = row.get("timebox_hint") or ""
            row["timebox_hint"] = row.get("default_parallelism") or ""
            row["default_parallelism"] = row.get("default_batch_unit") or ""
            row["default_batch_unit"] = row.get("preconditions") or ""
            row["preconditions"] = row.get("primary_output") or ""
            row["primary_output"] = row.get("required_inputs") or ""
            row["required_inputs"] = ""
        normalized.append(row)
    return normalized, shifted_count


def classify_project(project: dict[str, str], explicit: str | None) -> str:
    if explicit and explicit != "auto":
        return explicit
    text = " ".join(str(value) for value in project.values()).lower()
    stage = (project.get("current_stage") or "").lower()
    roster_count = integer(project, "roster_count")
    if "linkedin" in text or "connection" in text:
        return "existing-person-roster"
    if any(term in text for term in ("school system", "school-system", "district", "nces")):
        return "role-specific-organizations"
    if any(term in text for term in ("conference", "presenter", "participant", "event", "summit", "aime")):
        return "event-participant-roster"
    if any(term in text for term in ("organization universe", "organization roster", "staff roster", "organizations")):
        return "organization-universe"
    if roster_count > 0 and "contact" in stage:
        return "existing-person-roster"
    return "custom"


def project_classification(project: dict[str, str], archetype: str) -> dict[str, str]:
    starting = {
        "existing-person-roster": "person roster",
        "event-participant-roster": "person-event roster or event sources",
        "role-specific-organizations": "organization roster with functional roles",
        "organization-universe": "organization universe or roster",
        "custom": "requires source inspection",
    }[archetype]
    relationship = {
        "existing-person-roster": "person and current organization",
        "event-participant-roster": "person-event-organization",
        "role-specific-organizations": "organization-functional role-person",
        "organization-universe": "organization-parent/affiliate-person",
        "custom": "requires review",
    }[archetype]
    unit = {
        "existing-person-roster": "person",
        "event-participant-roster": "organization group or person",
        "role-specific-organizations": "organization-role",
        "organization-universe": "organization",
        "custom": "calibration unit",
    }[archetype]
    return {
        "starting_artifact": starting,
        "relationship_complexity": relationship,
        "optimization_target": "volume of accurate usable emails with roster and identity quality",
        "operational_unit": unit,
        "current_maturity": project.get("current_stage") or "UNKNOWN",
    }


def creative_lane_status(
    project: dict[str, str],
    archetype: str,
    decisions: list[dict[str, str]],
    override: str,
) -> tuple[str, str]:
    if override != "auto":
        return override, "explicit command option"

    project_id = project.get("project_id", "")
    relevant = []
    for row in decisions:
        row_project = (row.get("project_id") or "").strip()
        searchable = " ".join(
            [
                row.get("decision_type") or "",
                row.get("question") or "",
                row.get("selected_option") or "",
                row.get("notes") or "",
            ]
        ).lower()
        if row_project == project_id and any(term in searchable for term in ("candidate", "creative", "inferred", "pattern")):
            relevant.append((row, searchable))

    for row, searchable in reversed(relevant):
        if any(term in searchable for term in ("prohibit", "disabled", "not permitted", "do not infer", "no candidate")):
            return "disabled", f"decision {row.get('decision_id', '')}"
        if any(term in searchable for term in ("enabled", "permitted", "allow candidate", "creative lane enabled")):
            return "enabled", f"decision {row.get('decision_id', '')}"

    project_text = " ".join(str(value) for value in project.values()).lower()
    if archetype == "role-specific-organizations" and any(term in project_text for term in ("school", "district")):
        return "disabled", "current school-system workflow policy"
    return "requires-decision", "no project-specific candidate-policy decision found"


def node_row(
    node_id: str,
    treatment: str,
    entry: str,
    exit_criteria: str,
    next_nodes: list[str],
    batch_unit: str,
    note: str,
    basis: str = "PILOT_PATTERN",
    confidence: str = "MEDIUM",
) -> dict[str, str]:
    return {
        "step_type": "NODE",
        "node_id": node_id,
        "node_name": "",
        "required_or_optional": treatment,
        "entry_condition": entry,
        "exit_criteria": exit_criteria,
        "decision_gate": "",
        "possible_next_nodes": ";".join(next_nodes),
        "batch_unit": batch_unit,
        "coordinator_note": note,
        "basis": basis,
        "confidence": confidence,
        "mapper_status": "PROPOSED",
    }


def decision_row(
    decision_id: str,
    question: str,
    entry: str,
    exit_criteria: str,
    next_nodes: list[str],
    batch_unit: str,
    note: str,
) -> dict[str, str]:
    return {
        "step_type": "DECISION",
        "node_id": decision_id,
        "node_name": question,
        "required_or_optional": "REQUIRED",
        "entry_condition": entry,
        "exit_criteria": exit_criteria,
        "decision_gate": decision_id,
        "possible_next_nodes": ";".join(next_nodes),
        "batch_unit": batch_unit,
        "coordinator_note": note,
        "basis": "PROJECT_CONTRACT",
        "confidence": "HIGH" if "policy" not in question.lower() else "LOW",
        "mapper_status": "PROPOSED",
    }


def common_opening() -> list[dict[str, str]]:
    return [
        node_row("N00_PROJECT_INTAKE", "REQUIRED", "Project source and objective identified", "Project ID, objective, owner, policy, and definition of done recorded", ["N01_SOURCE_INVENTORY"], "Project", "Preserve or propose one stable Project ID."),
        node_row("N01_SOURCE_INVENTORY", "REQUIRED", "Project intake exists", "Material sources, prior outputs, and checkpoints registered", ["N02_SCOPE_CONTRACT"], "Project", "Do not infer stage from filenames alone."),
        node_row("N02_SCOPE_CONTRACT", "REQUIRED", "Source inventory is available", "Inclusion, evidence, candidate, stopping, and release rules are testable", ["N03_NORMALIZE_IDS", "N10_ROSTER_EXTRACT"], "Project", "Record unresolved policy as a Decision requirement."),
    ]


def contact_spine(project_id: str, unit: str, include_conflict_review: bool) -> list[dict[str, str]]:
    short = slug(project_id, 14)
    rows = [
        node_row("N20_CONTACT_RESEARCH", "REQUIRED", "Identity, scope, and calibrated Batch are ready", "Each assigned unit has a direct route, office route, candidate, unresolved, or blocked disposition", ["N24_PUBLIC_EMAIL_ATTRIBUTION", "N21_OFFICE_ROUTE_RESEARCH", "N22_EMAIL_PATTERN_CANDIDATE"], unit, "Use the shortest reliable public-source path."),
        decision_row(f"D-MAP-{short}-DIRECT", "Is exact attributable public email evidence available?", "A contact-search result exists", "Direct-evidence, office-route, candidate-policy, or unresolved branch selected", ["N24_PUBLIC_EMAIL_ATTRIBUTION", "N21_OFFICE_ROUTE_RESEARCH", "N22_EMAIL_PATTERN_CANDIDATE"], unit, "Pattern or syntax alone is not evidence."),
        node_row("N21_OFFICE_ROUTE_RESEARCH", "OPTIONAL", "Direct public email is unavailable and an office route is allowed", "Role-appropriate office route or unresolved disposition recorded", ["N25_CONTACT_HYGIENE_DEDUPE", "N26_CONTACT_CONFIDENCE_CLASSIFY", "N41_RINSE_REPEAT_QUEUE"], unit, "Keep office routes separate from direct emails."),
        decision_row(f"D-MAP-{short}-CREATIVE", "Does the Project contract permit the creative candidate lane?", "Direct public email is unavailable", "Candidate lane enabled, disabled, or sent to review", ["N22_EMAIL_PATTERN_CANDIDATE", "N41_RINSE_REPEAT_QUEUE"], unit, "A project-specific policy decision is required."),
        node_row("N22_EMAIL_PATTERN_CANDIDATE", "OPTIONAL", "Direct email is unavailable and the contract permits candidates", "Candidate stored separately with basis and unconfirmed status", ["N23_CANDIDATE_TARGETED_SEARCH", "N41_RINSE_REPEAT_QUEUE"], unit, "Never populate the verified direct-email field."),
        node_row("N23_CANDIDATE_TARGETED_SEARCH", "OPTIONAL", "A candidate exists and targeted public search is permitted", "Candidate confirmed, rejected, or retained as unconfirmed", ["N24_PUBLIC_EMAIL_ATTRIBUTION", "N26_CONTACT_CONFIDENCE_CLASSIFY", "N41_RINSE_REPEAT_QUEUE"], "Candidate subset", "Open and record the underlying public source."),
        node_row("N24_PUBLIC_EMAIL_ATTRIBUTION", "REQUIRED", "Exact email evidence is available", "Verified direct email promoted only with current attributable public evidence", ["N25_CONTACT_HYGIENE_DEDUPE", "N26_CONTACT_CONFIDENCE_CLASSIFY"], "Contact row", "Retain candidate basis and confirmation source."),
        node_row("N25_CONTACT_HYGIENE_DEDUPE", "REQUIRED", "Raw contact returns exist", "Direct, office, candidate, invalid, duplicate, and unresolved routes are normalized and separated", ["N26_CONTACT_CONFIDENCE_CLASSIFY", "N31_BATCH_SCHEMA_QA"], "Contact group", "Preserve conflicting evidence in the ledger."),
        node_row("N26_CONTACT_CONFIDENCE_CLASSIFY", "REQUIRED", "Clean contact rows exist", "Identity status, email status, confidence, and release tier assigned", ["N31_BATCH_SCHEMA_QA", "N41_RINSE_REPEAT_QUEUE"], "Contact row", "Use separate primary, expanded, candidate, and exception views."),
        node_row("N31_BATCH_SCHEMA_QA", "REQUIRED", "Raw return and Batch manifest exist", "Schema, assignment coverage, statuses, and counts reconcile", ["N32_IDENTITY_CONFLICT_REVIEW", "N33_FINAL_RELEASE_QA", "N40_EXCEPTION_TRIAGE"], "Batch", "A required node cannot pass on partial silent omissions."),
    ]
    if include_conflict_review:
        rows.append(node_row("N32_IDENTITY_CONFLICT_REVIEW", "OPTIONAL", "QA identifies a material identity or evidence conflict", "Conflict resolved, deferred, or blocked with rationale", ["N33_FINAL_RELEASE_QA", "N40_EXCEPTION_TRIAGE"], "Exception group", "Do not resolve evidence by majority vote."))
    rows.extend(
        [
            node_row("N33_FINAL_RELEASE_QA", "REQUIRED", "Validated Batch outputs are merged", "Counts, evidence, duplicates, exceptions, and limitations pass or are documented", ["N34_EXPORT_XLS_GOOGLE", "N41_RINSE_REPEAT_QUEUE"], "Project or Workstream", "Report verified direct, office, candidate, invalid, and unresolved counts separately."),
            node_row("N34_EXPORT_XLS_GOOGLE", "REQUIRED", "Release QA passes", "Readable workbook/export and Artifact record created", ["N41_RINSE_REPEAT_QUEUE", "N42_THROUGHPUT_RETROSPECTIVE"], "Project", "Structured files remain canonical."),
            node_row("N41_RINSE_REPEAT_QUEUE", "OPTIONAL", "Valid lower-confidence or unresolved opportunities remain", "Each queued item has a reason, next best action, and stopping rule", ["N20_CONTACT_RESEARCH", "N22_EMAIL_PATTERN_CANDIDATE", "N23_CANDIDATE_TARGETED_SEARCH", "N42_THROUGHPUT_RETROSPECTIVE"], "Project queue", "Do not repeat unchanged searches."),
            node_row("N42_THROUGHPUT_RETROSPECTIVE", "REQUIRED", "At least one validated Batch cohort exists", "Observed time, tokens, tools, QA, yield, conversion, and concurrency update the next recommendation", ["N04_COORDINATOR_CAPACITY_PLAN", "N43_SKILL_SPEC_REVISION", "END"], "Batch cohort", "Separate worker throughput from coordinator merge and QA time."),
            node_row("N43_SKILL_SPEC_REVISION", "OPTIONAL", "Repeated evidence supports a process or skill change", "Revision proposal has evidence, test case, risk, and rollback", ["N42_THROUGHPUT_RETROSPECTIVE", "END"], "Node or skill", "Do not edit another skill without explicit authorization."),
        ]
    )
    return rows


def template_for(archetype: str, project_id: str) -> list[dict[str, str]]:
    rows = common_opening()
    if archetype == "existing-person-roster":
        rows.extend(
            [
                node_row("N03_NORMALIZE_IDS", "REQUIRED", "Usable person roster exists", "Stable record IDs and source coverage reconcile", ["N04_COORDINATOR_CAPACITY_PLAN"], "Person row", "Preserve source values and prior email provenance."),
                node_row("N04_COORDINATOR_CAPACITY_PLAN", "REQUIRED", "Stable person IDs exist", "Disjoint Workstreams and bounded calibration Batches have owners and ceilings", ["N20_CONTACT_RESEARCH"], "25-person calibration", "Treat 25 as an uncalibrated starting point."),
            ]
        )
        rows.extend(contact_spine(project_id, "Person Batch", include_conflict_review=False))
    elif archetype == "event-participant-roster":
        rows.extend(
            [
                node_row("N10_ROSTER_EXTRACT", "REQUIRED", "Official event sources are defined", "Person-event rows and source ledger exist", ["N11_ORG_RESOLUTION", "N12_PERSON_RESOLUTION"], "Person-event source row", "Preserve participation type and source row."),
                node_row("N11_ORG_RESOLUTION", "REQUIRED", "Event rows contain organization context", "Organizations have canonical keys and merge decisions", ["N12_PERSON_RESOLUTION", "N14_ROSTER_DEDUPE"], "Organization group", "Keep parent and affiliate arms distinct when evidence requires."),
                node_row("N12_PERSON_RESOLUTION", "REQUIRED", "Organization context and event rows exist", "Person identity and event/current context are recorded", ["N13_ROLE_PARTICIPATION_CLASSIFY"], "Person group", "Do not collapse similar names without evidence."),
                node_row("N13_ROLE_PARTICIPATION_CLASSIFY", "REQUIRED", "Person identity is sufficiently resolved", "Participation and title fields are standardized while exact source values remain", ["N14_ROSTER_DEDUPE", "N15_ROSTER_COVERAGE_QA"], "Person-event group", "Keep event-time and current titles separate."),
                node_row("N14_ROSTER_DEDUPE", "REQUIRED", "Identity and participation fields exist", "Canonical person roster and relationship ledger preserve all source rows", ["N15_ROSTER_COVERAGE_QA"], "Person group", "Retain distinct sessions and roles."),
                node_row("N15_ROSTER_COVERAGE_QA", "REQUIRED", "Canonical roster and source ledger exist", "Every source participant has a disposition and counts reconcile", ["N04_COORDINATOR_CAPACITY_PLAN", "N40_EXCEPTION_TRIAGE"], "Project", "Do not let contact research outrun identity QA."),
                node_row("N04_COORDINATOR_CAPACITY_PLAN", "REQUIRED", "Roster QA passes", "Organization-aware Workstreams and bounded Batches are registered", ["N20_CONTACT_RESEARCH"], "10-15 organizations or 25 people", "Use a low-confidence calibration until actuals exist."),
            ]
        )
        rows.extend(contact_spine(project_id, "Person Batch", include_conflict_review=True))
    elif archetype == "role-specific-organizations":
        rows.extend(
            [
                node_row("N03_NORMALIZE_IDS", "REQUIRED", "Exact source sheet or roster is selected", "Stable organization keys and source order reconcile", ["N10_ROSTER_EXTRACT"], "Organization row", "Use the strongest supplied identifier."),
                node_row("N10_ROSTER_EXTRACT", "REQUIRED", "Stable organization rows exist", "Bounded organization Batch input and checkpoints exist", ["N11_ORG_RESOLUTION", "N13_ROLE_PARTICIPATION_CLASSIFY"], "25-organization Batch", "Use a smaller Batch if role depth or source friction is unknown."),
                node_row("N11_ORG_RESOLUTION", "REQUIRED", "Organization identifiers exist", "Official identity, type, parent, and affiliate context are resolved", ["N13_ROLE_PARTICIPATION_CLASSIFY", "N15_ROSTER_COVERAGE_QA"], "Organization group", "Preserve network and parent relationships."),
                node_row("N13_ROLE_PARTICIPATION_CLASSIFY", "REQUIRED", "Organization identity is confirmed", "Required functional roles have exact-title mappings or allowed outcomes", ["N15_ROSTER_COVERAGE_QA"], "Organization-role row", "Use functional responsibility rather than title keyword alone."),
                node_row("N15_ROSTER_COVERAGE_QA", "REQUIRED", "Role rows and manifest exist", "Every required organization-role unit has a disposition", ["N04_COORDINATOR_CAPACITY_PLAN", "N40_EXCEPTION_TRIAGE"], "Checkpoint cohort", "Vacant or distributed functions may be valid outcomes."),
                node_row("N04_COORDINATOR_CAPACITY_PLAN", "REQUIRED", "Roster/role checkpoint passes", "Batch ceiling, checkpoint cadence, owner, and concurrency are recorded", ["N20_CONTACT_RESEARCH"], "Five-unit checkpoint inside bounded Batch", "Measure organization-role units, not organizations alone."),
            ]
        )
        rows.extend(contact_spine(project_id, "Organization-role Batch", include_conflict_review=True))
    else:
        rows.extend(
            [
                node_row("N03_NORMALIZE_IDS", "REQUIRED", "Source universe is selected", "Stable organization and source IDs reconcile", ["N10_ROSTER_EXTRACT"], "Source row", "Preserve original source values."),
                node_row("N10_ROSTER_EXTRACT", "REQUIRED", "Organization universe or sources exist", "Raw organization/person rows and source ledger exist", ["N11_ORG_RESOLUTION"], "5-10 organizations", "Start small when staff depth is unknown."),
                node_row("N11_ORG_RESOLUTION", "REQUIRED", "Organization rows exist", "Canonical organizations and relationship decisions exist", ["N12_PERSON_RESOLUTION", "N13_ROLE_PARTICIPATION_CLASSIFY"], "Organization group", "Resolve parent and affiliate relationships."),
                node_row("N12_PERSON_RESOLUTION", "OPTIONAL", "Named people are present", "Person identities have evidence and statuses", ["N13_ROLE_PARTICIPATION_CLASSIFY", "N14_ROSTER_DEDUPE"], "Person group", "Keep unresolved identities separate."),
                node_row("N13_ROLE_PARTICIPATION_CLASSIFY", "REQUIRED", "Organization/person context exists", "Target roles or participation types are standardized", ["N14_ROSTER_DEDUPE", "N15_ROSTER_COVERAGE_QA"], "Person or role row", "Retain exact source title."),
                node_row("N14_ROSTER_DEDUPE", "REQUIRED", "Identity and role fields exist", "Canonical roster and merge ledger preserve source traceability", ["N15_ROSTER_COVERAGE_QA"], "Organization/person group", "Do not merge on display name alone."),
                node_row("N15_ROSTER_COVERAGE_QA", "REQUIRED", "Canonical roster exists", "Source coverage and dispositions reconcile", ["N04_COORDINATOR_CAPACITY_PLAN", "N40_EXCEPTION_TRIAGE"], "Project", "Gate high-volume contact fan-out on roster quality."),
                node_row("N04_COORDINATOR_CAPACITY_PLAN", "REQUIRED", "Roster QA passes", "A bounded calibration assignment has an owner and ceiling", ["N20_CONTACT_RESEARCH"], "5-10 organizations", "Calibrate from source friction and staff depth."),
            ]
        )
        rows.extend(contact_spine(project_id, "Person or organization Batch", include_conflict_review=True))
    return rows


def skill_candidates(node_id: str, catalog: list[dict[str, str]]) -> list[str]:
    candidates: list[tuple[int, int, str]] = []
    state_rank = {"EXISTING": 0, "NEW": 1, "PROCESS_TO_FORMALIZE": 2, "PLANNED": 3}
    priority_rank = {"T1": 0, "T2": 1, "T3": 2}
    for row in catalog:
        if node_id not in split_ids(row.get("mapped_node_ids", "")):
            continue
        name = (row.get("name") or "").strip()
        if name:
            candidates.append(
                (
                    state_rank.get((row.get("current_state") or "").strip(), 9),
                    priority_rank.get((row.get("priority") or "").strip(), 9),
                    name,
                )
            )
    if node_id in MAPPER_NODES and not any(item[2] == "contact-research-workflow-mapper" for item in candidates):
        candidates.append((1, 0, "contact-research-workflow-mapper"))
    return [name for _, _, name in sorted(candidates)]


def prioritize_skill_names(names: list[str], archetype: str) -> list[str]:
    preferred = {
        "existing-person-roster": ["coordinated-efficient-contact-research"],
        "event-participant-roster": ["research-conference-presenter-roster", "coordinated-efficient-contact-research"],
        "role-specific-organizations": ["school-system-assessment-contact-research", "coordinated-efficient-contact-research"],
        "organization-universe": ["organizational-roster-building", "coordinated-efficient-contact-research"],
        "custom": [],
    }[archetype]
    rank = {name: index for index, name in enumerate(preferred)}
    return sorted(names, key=lambda name: (rank.get(name, len(preferred)), names.index(name)))


def observed_batches(project_id: str, batches: list[dict[str, str]]) -> list[dict[str, str]]:
    observed = []
    for row in batches:
        if row.get("project_id") != project_id:
            continue
        if row.get("qa_status") not in {"PASS", "PASS_WITH_WARNINGS"}:
            continue
        if integer(row, "rows_completed") <= 0:
            continue
        if integer(row, "actual_tokens") <= 0 and integer(row, "actual_minutes") <= 0:
            continue
        observed.append(row)
    return observed


def batch_recommendation(project: dict[str, str], archetype: str, batches: list[dict[str, str]]) -> dict[str, Any]:
    project_id = project.get("project_id", "")
    observed = observed_batches(project_id, batches)
    defaults = {
        "existing-person-roster": ("people", 25, 10),
        "event-participant-roster": ("people or organization groups", 25, 10),
        "role-specific-organizations": ("organizations with role rows", 25, 5),
        "organization-universe": ("organizations", 10, 5),
        "custom": ("calibration units", 10, 5),
    }
    unit, default_records, checkpoint = defaults[archetype]
    target = integer(project, "target_batch_records", default_records) or default_records
    maximum = integer(project, "max_batch_records", target) or target
    recommended = min(target, maximum)
    basis = "TRACKER_STATE" if project.get("target_batch_records") else "PILOT_PATTERN"
    confidence = "LOW"

    if observed:
        recommended = int(statistics.median(integer(row, "rows_completed") for row in observed))
        recommended = min(max(1, recommended), maximum)
        basis = "LIVE_OBSERVATION"
        confidence = "HIGH" if len(observed) >= 3 else "MEDIUM"

    active = integer(project, "active_batch_count")
    ceiling = max(1, integer(project, "max_concurrent_batches", 1))
    slots = max(0, ceiling - active)
    capacity_status = "WAIT_FOR_CAPACITY" if slots == 0 else ("CALIBRATED" if observed else "CALIBRATION_REQUIRED")

    token_budget = integer(project, "token_budget_remaining")
    tokens_per_batch = integer(project, "estimated_tokens_per_batch")
    if token_budget and tokens_per_batch and token_budget < tokens_per_batch:
        capacity_status = "RESIZE_BATCH"
        recommended = max(1, recommended // 2)
        confidence = "LOW"

    return {
        "unit": unit,
        "recommended_records": recommended,
        "checkpoint_records": min(checkpoint, recommended),
        "available_slots": slots,
        "max_concurrent_batches": ceiling,
        "capacity_status": capacity_status,
        "basis": basis,
        "confidence": confidence,
        "observed_batch_count": len(observed),
    }


def write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def escape_md(value: Any) -> str:
    return str(value if value is not None else "").replace("|", "\\|").replace("\n", " ")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tracker-root", required=True, type=Path)
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--archetype", choices=["auto", *sorted(ARCHETYPES)], default="auto")
    parser.add_argument("--creative-lane", choices=["auto", "enabled", "disabled", "requires-decision"], default="auto")
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()

    projects = read_csv(args.tracker_root / "project_register.csv", required=True)
    raw_nodes = read_csv(args.tracker_root / "node_inventory.csv", required=True)
    nodes, shifted_node_rows = normalize_node_rows(raw_nodes)
    batches = read_csv(args.tracker_root / "batch_register.csv")
    decisions = read_csv(args.tracker_root / "decision_log.csv")
    pilot_maps = read_csv(args.tracker_root / "pilot_workflow_maps.csv")
    catalog = read_csv(args.tracker_root / "skill_catalog.csv")

    matches = [row for row in projects if row.get("project_id") == args.project_id]
    if len(matches) != 1:
        raise SystemExit(f"Expected exactly one project row for {args.project_id}; found {len(matches)}")
    project = matches[0]
    archetype = classify_project(project, args.archetype)
    creative_status, creative_basis = creative_lane_status(project, archetype, decisions, args.creative_lane)
    node_lookup = {row.get("node_id", ""): row for row in nodes}

    rows = template_for(archetype, args.project_id)
    project_short = slug(args.project_id)
    for index, row in enumerate(rows, start=1):
        row["map_id"] = f"MAP-{project_short}-{index:02d}"
        row["project_id"] = args.project_id
        row["sequence"] = str(index)
        if row["step_type"] == "NODE":
            inventory = node_lookup.get(row["node_id"], {})
            row["node_name"] = inventory.get("node_name") or row["node_id"]
            skills = prioritize_skill_names(skill_candidates(row["node_id"], catalog), archetype)
            row["recommended_skill_or_process"] = ";".join(skills) if skills else "PROCESS_NOT_FORMALIZED"
        else:
            row["recommended_skill_or_process"] = "contact-research-workflow-mapper;agent-decision-receipts"

        if row["node_id"] == "N22_EMAIL_PATTERN_CANDIDATE":
            if creative_status == "disabled":
                row["required_or_optional"] = "SKIPPED"
                row["entry_condition"] = "Project policy prohibits the creative candidate lane"
                row["exit_criteria"] = "Skip recorded with policy basis"
                row["confidence"] = "HIGH"
            elif creative_status == "enabled":
                row["confidence"] = "HIGH"
            else:
                row["confidence"] = "LOW"

    gaps: list[dict[str, str]] = []

    def add_gap(node_id: str, gap_type: str, severity: str, evidence: str, action: str) -> None:
        gaps.append(
            {
                "gap_id": "",
                "project_id": args.project_id,
                "node_id": node_id,
                "gap_type": gap_type,
                "severity": severity,
                "evidence": evidence,
                "recommended_action": action,
                "status": "OPEN",
            }
        )

    if creative_status == "requires-decision":
        add_gap(
            "N22_EMAIL_PATTERN_CANDIDATE",
            "DECISION_REQUIRED",
            "BLOCKING",
            creative_basis,
            "Record a Project-specific decision enabling or disabling the creative candidate lane before execution.",
        )

    if shifted_node_rows:
        add_gap(
            "",
            "NODE_SCHEMA_MISALIGNED",
            "MATERIAL",
            f"Detected {shifted_node_rows} node rows using the legacy one-column-left shape after purpose",
            "Repair node_inventory.csv by populating required_inputs and shifting the downstream fields into their declared columns; preserve this run's compatibility normalization as diagnostic evidence.",
        )

    formalized_by_skill = set()
    for row in catalog:
        if row.get("kind") == "FORMAL_SKILL" and row.get("current_state") in {"EXISTING", "NEW"}:
            formalized_by_skill.update(split_ids(row.get("mapped_node_ids", "")))
    for row in rows:
        if row["step_type"] != "NODE" or row["required_or_optional"] == "SKIPPED":
            continue
        inventory = node_lookup.get(row["node_id"], {})
        if not inventory:
            add_gap(row["node_id"], "NODE_NOT_REGISTERED", "BLOCKING", "Generated node is absent from node_inventory.csv", "Register or replace the node before Tracker execution.")
        elif inventory.get("formalization_status") != "FORMALIZED" and row["node_id"] not in formalized_by_skill and row["node_id"] not in MAPPER_NODES:
            add_gap(row["node_id"], "PROCESS_NOT_FORMALIZED", "LEARNING", f"Node status is {inventory.get('formalization_status') or 'UNKNOWN'} and no existing formal skill is mapped", "Assign a repeatable process owner or create a skill-revision proposal after pilot evidence.")

    batch_rec = batch_recommendation(project, archetype, batches)
    if batch_rec["observed_batch_count"] == 0:
        add_gap(
            "N04_COORDINATOR_CAPACITY_PLAN",
            "CAPACITY_UNCALIBRATED",
            "MATERIAL",
            "No validated Batch has nonzero actual time or token observations",
            "Run one bounded calibration Batch and record time, tokens, tools, output, yield, exceptions, and QA burden.",
        )

    map_nodes = [row["node_id"] for row in rows if row["step_type"] == "NODE"]
    current_node = project.get("current_node_id", "")
    if current_node and current_node not in map_nodes:
        add_gap(
            current_node,
            "CURRENT_NODE_OUTSIDE_MAP",
            "BLOCKING",
            f"Project register current_node_id={current_node}",
            "Reconcile the Project register or revise the proposed path through a Decision record.",
        )

    pilot_rows = [row for row in pilot_maps if row.get("project_id") == args.project_id and row.get("step_type") == "NODE"]
    if pilot_rows:
        pilot_nodes = {row.get("node_id", "") for row in pilot_rows}
        generated_nodes = set(map_nodes)
        missing = sorted(generated_nodes - pilot_nodes)
        extra = sorted(pilot_nodes - generated_nodes)
        if missing:
            add_gap(
                "",
                "MAP_REGISTER_MISMATCH",
                "MATERIAL",
                "Pilot map omits generated canonical nodes: " + ";".join(missing),
                "Review the omitted nodes and update or supersede the pilot map after acceptance.",
            )
        if extra:
            add_gap(
                "",
                "MAP_REGISTER_MISMATCH",
                "MATERIAL",
                "Pilot map contains nodes outside the generated canonical path: " + ";".join(extra),
                "Record whether the extra nodes are Project-specific extensions or remove them from the accepted path.",
            )

    for index, gap in enumerate(gaps, start=1):
        gap["gap_id"] = f"GAP-{project_short}-{index:03d}"

    map_by_node = {row["node_id"]: row for row in rows if row["step_type"] == "NODE"}
    recommended_next = current_node if current_node in map_by_node else next(
        (row["node_id"] for row in rows if row["step_type"] == "NODE" and row["required_or_optional"] == "REQUIRED"),
        "",
    )
    recommended_skill = map_by_node.get(recommended_next, {}).get("recommended_skill_or_process", "")

    decisions_required = []
    if creative_status == "requires-decision":
        decisions_required.append("Enable or disable the creative candidate lane for this Project.")
    if batch_rec["capacity_status"] == "CALIBRATION_REQUIRED":
        decisions_required.append("Accept or resize the first bounded calibration Batch.")

    proposed_updates = []
    if shifted_node_rows:
        proposed_updates.append(
            {
                "register": "node_inventory.csv",
                "row_id": "ALL_LEGACY_SHIFTED_ROWS",
                "field": "required_inputs through notes",
                "current_value": "legacy one-column-left row shape",
                "proposed_value": "fields aligned to the declared header with required_inputs populated",
                "reason": "The Mapper detected a schema/register mismatch and normalized it only in memory.",
                "required_before_execution": False,
            }
        )
    if creative_status == "requires-decision":
        proposed_updates.append(
            {
                "register": "decision_log.csv",
                "row_id": "PROPOSED",
                "field": "selected_option",
                "current_value": "",
                "proposed_value": "ENABLE_CANDIDATES or DISABLE_CANDIDATES",
                "reason": "The candidate branch cannot execute without a Project-specific policy decision.",
                "required_before_execution": True,
            }
        )
    if batch_rec["observed_batch_count"] == 0:
        proposed_updates.append(
            {
                "register": "batch_register.csv",
                "row_id": "PROPOSED_CALIBRATION_BATCH",
                "field": "record_count",
                "current_value": "",
                "proposed_value": str(batch_rec["recommended_records"]),
                "reason": "Capacity and throughput are uncalibrated.",
                "required_before_execution": True,
            }
        )

    recommendation = {
        "project_id": args.project_id,
        "project_name": project.get("project_name", ""),
        "archetype": archetype,
        "baseline": {
            "existing-person-roster": "LinkedIn connections",
            "event-participant-roster": "AIME/event participant",
            "role-specific-organizations": "school-system functional roles",
            "organization-universe": "organization universe to staff roster",
            "custom": "custom organization/person path",
        }[archetype],
        "classification": project_classification(project, archetype),
        "current_node_id": current_node,
        "recommended_next_node_id": recommended_next,
        "recommended_skill_or_process": recommended_skill,
        "batch_recommendation": batch_rec,
        "creative_lane_status": creative_status,
        "creative_lane_basis": creative_basis,
        "decisions_required": decisions_required,
        "map_counts": {
            "nodes": sum(row["step_type"] == "NODE" for row in rows),
            "decisions": sum(row["step_type"] == "DECISION" for row in rows),
            "required": sum(row["required_or_optional"] == "REQUIRED" for row in rows),
            "optional": sum(row["required_or_optional"] == "OPTIONAL" for row in rows),
            "skipped": sum(row["required_or_optional"] == "SKIPPED" for row in rows),
        },
        "gaps": {
            "blocking": sum(gap["severity"] == "BLOCKING" for gap in gaps),
            "material": sum(gap["severity"] == "MATERIAL" for gap in gaps),
            "learning": sum(gap["severity"] == "LEARNING" for gap in gaps),
        },
        "proposed_tracker_updates": proposed_updates,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }

    output_files = ["workflow_map.csv", "workflow_map.md", "workflow_gaps.csv", "mapper_recommendation.json"]
    if args.output_dir.exists() and not args.replace:
        collisions = [name for name in output_files if (args.output_dir / name).exists()]
        if collisions:
            raise SystemExit("Output files already exist; use a new directory or explicit --replace: " + ", ".join(collisions))
    args.output_dir.mkdir(parents=True, exist_ok=True)

    write_csv(args.output_dir / "workflow_map.csv", MAP_FIELDS, rows)
    write_csv(args.output_dir / "workflow_gaps.csv", GAP_FIELDS, gaps)
    with (args.output_dir / "mapper_recommendation.json").open("w", encoding="utf-8") as handle:
        json.dump(recommendation, handle, indent=2, ensure_ascii=False)
        handle.write("\n")

    lines = [
        f"# Proposed workflow map: {project.get('project_name') or args.project_id}",
        "",
        f"- Project: `{args.project_id}`",
        f"- Archetype: `{archetype}`",
        f"- Baseline: {recommendation['baseline']}",
        f"- Current / recommended node: `{current_node or 'UNKNOWN'}` / `{recommended_next or 'UNKNOWN'}`",
        f"- Creative lane: `{creative_status}` ({creative_basis})",
        f"- Batch: {batch_rec['recommended_records']} {batch_rec['unit']}; checkpoint {batch_rec['checkpoint_records']}; `{batch_rec['capacity_status']}`; confidence `{batch_rec['confidence']}`",
        "",
        "## Pathway",
        "",
        "| Seq | Type | Node / decision | Treatment | Recommended skill/process | Entry | Exit |",
        "|---:|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            "| {sequence} | {step_type} | `{node_id}` {node_name} | {required_or_optional} | {recommended_skill_or_process} | {entry_condition} | {exit_criteria} |".format(
                **{key: escape_md(value) for key, value in row.items()}
            )
        )
    lines.extend(["", "## Decisions required", ""])
    if decisions_required:
        lines.extend(f"- {item}" for item in decisions_required)
    else:
        lines.append("- None identified from current records.")
    lines.extend(["", "## Gaps", ""])
    if gaps:
        lines.extend(
            f"- **{gap['severity']} / {gap['gap_type']}** `{gap['node_id'] or 'path'}`: {gap['evidence']} Recommended: {gap['recommended_action']}"
            for gap in gaps
        )
    else:
        lines.append("- No structural gaps identified.")
    (args.output_dir / "workflow_map.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(
        f"CREATED: {args.project_id} | archetype={archetype} | "
        f"steps={len(rows)} | gaps={len(gaps)} | output={args.output_dir}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
