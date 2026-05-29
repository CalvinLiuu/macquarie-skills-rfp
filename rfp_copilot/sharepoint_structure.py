from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import SharePointFolderRole, SharePointStructurePlan


SEGMENT_LABELS: dict[str, str] = {
    "enterprise": "Enterprise",
    "hyperscaler": "Hyperscalers",
    "small_business": "Small Business",
    "government": "Government",
}

SEGMENT_ROLE_DEFAULTS: dict[str, dict[str, str]] = {
    "previous_rfps": {
        "folder": "Previous RFP",
        "purpose": "Historical RFP inputs used to understand question patterns and customer context.",
        "document_type": "rfp",
        "business_action": "mark_successful_rfp_document_information",
    },
    "successful_rfps": {
        "folder": "Successful RFPs",
        "purpose": "Approved winning RFP responses that can inform future answer strategy.",
        "document_type": "rfp",
        "business_action": "mark_successful_rfp_document_information",
    },
    "successful_current_info": {
        "folder": "Successful Up To Date Information",
        "purpose": "Current approved segment-specific facts refreshed from successful RFPs and source updates.",
        "document_type": "general_knowledge",
        "business_action": "refresh_successful_document_information",
    },
}

GENERAL_DOCUMENT_DEFAULTS: dict[str, dict[str, str]] = {
    "important_information": {
        "folder": "Important Information",
        "purpose": "General source material that may affect future RFP evidence.",
        "document_type": "general_knowledge",
        "business_action": "refresh_successful_document_information",
    },
    "infrastructure_changes": {
        "folder": "New Infrastructure",
        "purpose": "New site, centre, or infrastructure changes that should refresh approved RFP facts.",
        "document_type": "macquarie_implementation",
        "business_action": "refresh_successful_document_information",
    },
    "equipment_changes": {
        "folder": "Equipment Changes",
        "purpose": "Equipment changes such as power, cooling, or capacity improvements.",
        "document_type": "macquarie_implementation",
        "business_action": "refresh_successful_document_information",
    },
}


def build_sharepoint_folder_roles(structure: dict[str, Any]) -> list[SharePointFolderRole]:
    client_segment_root = structure.get("client_segment_root", "RFP Knowledge/Client Segments")
    segment_config = structure.get("client_segments", {})
    general_root = structure.get("general_documents_root", "RFP Knowledge/Documents")
    general_config = structure.get("general_documents", {})
    roles: list[SharePointFolderRole] = []

    for segment, label in SEGMENT_LABELS.items():
        configured = segment_config.get(segment, {})
        segment_root = configured.get("root", f"{client_segment_root}/{label}")
        for role, defaults in SEGMENT_ROLE_DEFAULTS.items():
            roles.append(
                SharePointFolderRole(
                    role=role,
                    folder_path=configured.get(role, f"{segment_root}/{defaults['folder']}"),
                    purpose=defaults["purpose"],
                    client_segment=segment,
                    document_type=defaults["document_type"],
                    business_action=defaults["business_action"],
                )
            )

    for role, defaults in GENERAL_DOCUMENT_DEFAULTS.items():
        roles.append(
            SharePointFolderRole(
                role=role,
                folder_path=general_config.get(role, f"{general_root}/{defaults['folder']}"),
                purpose=defaults["purpose"],
                document_type=defaults["document_type"],
                business_action=defaults["business_action"],
            )
        )
    return roles


def match_sharepoint_folder_role(
    structure: dict[str, Any],
    source_path: str,
) -> SharePointFolderRole | None:
    normalized_path = _normalize_path(source_path)
    matches = [
        role
        for role in build_sharepoint_folder_roles(structure)
        if normalized_path.startswith(_normalize_path(role.folder_path))
    ]
    if not matches:
        return None
    return max(matches, key=lambda role: len(_normalize_path(role.folder_path)))


def build_sharepoint_structure_plan(
    structure: dict[str, Any],
    output_dir: str | Path = "data/outputs",
) -> SharePointStructurePlan:
    folder_roles = build_sharepoint_folder_roles(structure)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    manifest_path = output_path / "sharepoint-structure-plan.json"
    report_path = output_path / "sharepoint-structure-plan.md"
    manifest_path.write_text(
        json.dumps([role.to_dict() for role in folder_roles], indent=2),
        encoding="utf-8",
    )
    report_path.write_text(render_sharepoint_structure_markdown(folder_roles), encoding="utf-8")
    return SharePointStructurePlan(
        folder_roles=folder_roles,
        report_path=str(report_path),
        manifest_path=str(manifest_path),
    )


def render_sharepoint_structure_markdown(folder_roles: list[SharePointFolderRole]) -> str:
    lines = [
        "# SharePoint Structure Plan",
        "",
        "## Client Segment Folders",
        "",
    ]
    for segment, label in SEGMENT_LABELS.items():
        roles = [role for role in folder_roles if role.client_segment == segment]
        lines.extend([f"### {label}", ""])
        for role in roles:
            lines.append(f"- `{role.role}`: {role.folder_path}")
        lines.append("")

    lines.extend(["## General Document Folders", ""])
    for role in [item for item in folder_roles if not item.client_segment]:
        lines.append(f"- `{role.role}`: {role.folder_path}")

    lines.extend(["", "## Business Actions", ""])
    actions = sorted({role.business_action for role in folder_roles if role.business_action})
    for action in actions:
        action_roles = [role for role in folder_roles if role.business_action == action]
        role_names = ", ".join(role.role for role in action_roles)
        lines.append(f"- `{action}` uses: {role_names}")
    return "\n".join(lines).strip() + "\n"


def _normalize_path(path: str) -> str:
    return path.strip("/").lower()
