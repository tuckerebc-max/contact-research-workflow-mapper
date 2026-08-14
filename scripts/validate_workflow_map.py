#!/usr/bin/env python3
"""Validate a Contact Research Workflow Mapper CSV against the node inventory."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


REQUIRED_FIELDS = {
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
    "recommended_skill_or_process",
    "basis",
    "confidence",
    "mapper_status",
}

TREATMENTS = {"REQUIRED", "OPTIONAL", "SKIPPED"}
STEP_TYPES = {"NODE", "DECISION"}
BASES = {"PROJECT_CONTRACT", "TRACKER_STATE", "LIVE_OBSERVATION", "PILOT_PATTERN", "MAPPER_INFERENCE"}
CONFIDENCE = {"HIGH", "MEDIUM", "LOW"}
MAPPER_STATUSES = {"PROPOSED", "REVIEWED", "ACCEPTED", "SUPERSEDED", "REJECTED"}
FULL_MAP_REQUIRED = {"N00_PROJECT_INTAKE", "N01_SOURCE_INVENTORY", "N02_SCOPE_CONTRACT"}
RELEASE_NODES = {"N33_FINAL_RELEASE_QA", "N34_EXPORT_XLS_GOOGLE"}


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def split_ids(value: str) -> list[str]:
    return [item.strip() for item in re.split(r"[;,]", value or "") if item.strip()]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--map", required=True, type=Path)
    parser.add_argument("--nodes", required=True, type=Path)
    parser.add_argument("--project-id")
    args = parser.parse_args()

    errors: list[str] = []
    if not args.map.exists():
        errors.append(f"Missing workflow map: {args.map}")
    if not args.nodes.exists():
        errors.append(f"Missing node inventory: {args.nodes}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    rows = read_rows(args.map)
    nodes = read_rows(args.nodes)
    if not rows:
        print("ERROR: Workflow map has no rows")
        return 1
    headers = set(rows[0].keys())
    for field in sorted(REQUIRED_FIELDS - headers):
        errors.append(f"Missing required field: {field}")

    node_ids = {row.get("node_id", "") for row in nodes if row.get("node_id")}
    map_ids = [row.get("map_id", "") for row in rows]
    if len(set(map_ids)) != len(map_ids) or any(not value for value in map_ids):
        errors.append("map_id values must be nonblank and unique")

    sequences: list[int] = []
    project_ids = {row.get("project_id", "") for row in rows}
    if len(project_ids) != 1 or "" in project_ids:
        errors.append("A workflow map must contain exactly one nonblank project_id")
    if args.project_id and project_ids != {args.project_id}:
        errors.append(f"Map project_id does not match --project-id {args.project_id}")

    mapped_nodes: list[str] = []
    for row in rows:
        row_id = row.get("map_id", "<unknown>")
        try:
            sequence = int(row.get("sequence", ""))
            if sequence <= 0:
                raise ValueError
            sequences.append(sequence)
        except ValueError:
            errors.append(f"{row_id}: sequence must be a positive integer")
        step_type = row.get("step_type", "")
        if step_type not in STEP_TYPES:
            errors.append(f"{row_id}: invalid step_type {step_type}")
        treatment = row.get("required_or_optional", "")
        if treatment not in TREATMENTS:
            errors.append(f"{row_id}: invalid treatment {treatment}")
        if row.get("basis", "") not in BASES:
            errors.append(f"{row_id}: invalid basis {row.get('basis', '')}")
        if row.get("confidence", "") not in CONFIDENCE:
            errors.append(f"{row_id}: invalid confidence {row.get('confidence', '')}")
        if row.get("mapper_status", "") not in MAPPER_STATUSES:
            errors.append(f"{row_id}: invalid mapper_status {row.get('mapper_status', '')}")
        if not row.get("batch_unit"):
            errors.append(f"{row_id}: batch_unit is required")
        if not row.get("recommended_skill_or_process"):
            errors.append(f"{row_id}: recommended_skill_or_process is required")
        if treatment != "SKIPPED" and (not row.get("entry_condition") or not row.get("exit_criteria")):
            errors.append(f"{row_id}: active steps require entry_condition and exit_criteria")

        node_id = row.get("node_id", "")
        if step_type == "NODE":
            mapped_nodes.append(node_id)
            if node_id not in node_ids:
                errors.append(f"{row_id}: unknown node_id {node_id}")
        elif step_type == "DECISION":
            if not row.get("decision_gate"):
                errors.append(f"{row_id}: decision step requires decision_gate")
            if not node_id.startswith("D-"):
                errors.append(f"{row_id}: decision node_id should start with D-")

        for next_id in split_ids(row.get("possible_next_nodes", "")):
            if next_id == "END" or next_id.startswith("D-"):
                continue
            if next_id.startswith("N") and next_id not in node_ids:
                errors.append(f"{row_id}: possible_next_nodes references unknown node {next_id}")
            elif not next_id.startswith("N"):
                errors.append(f"{row_id}: invalid next-step reference {next_id}")

    if len(sequences) != len(set(sequences)):
        errors.append("sequence values must be unique")
    if sequences and sorted(sequences) != list(range(1, len(rows) + 1)):
        errors.append("sequence values must be contiguous from 1 through the row count")

    missing_opening = sorted(FULL_MAP_REQUIRED - set(mapped_nodes))
    if missing_opening:
        errors.append("Full map missing shared opening nodes: " + ", ".join(missing_opening))
    if not RELEASE_NODES.issubset(set(mapped_nodes)):
        errors.append("Full map must contain final release QA and export nodes")
    if "N20_CONTACT_RESEARCH" in mapped_nodes and "N24_PUBLIC_EMAIL_ATTRIBUTION" not in mapped_nodes:
        errors.append("Contact-research path lacks the public email attribution gate")
    for candidate_node in ("N22_EMAIL_PATTERN_CANDIDATE", "N23_CANDIDATE_TARGETED_SEARCH"):
        if candidate_node in mapped_nodes:
            candidate_rows = [row for row in rows if row.get("node_id") == candidate_node]
            if any(row.get("required_or_optional") == "REQUIRED" for row in candidate_rows):
                errors.append(f"{candidate_node} must remain OPTIONAL or SKIPPED")
    if "N42_THROUGHPUT_RETROSPECTIVE" not in mapped_nodes:
        errors.append("Full map must contain a throughput/quality retrospective")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"PASS: {len(rows)} steps, {len(mapped_nodes)} node steps, {len(rows) - len(mapped_nodes)} decisions validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
