from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from .answering import build_answer_contract, package_answers
from .corpus import CorpusStore
from .markdown_formatter import render_rfp_markdown, slugify
from .models import AnswerContract, BidRequest
from .response_indexer import render_response_index_markdown
from .rfp_parser import extract_text_from_path, parse_rfp_file
from .sharepoint_graph import SharePointSyncService, SyncConfig
from .taxonomy import build_evidence_hints, detect_domains


SUPPORTED_BID_CONTEXT_SUFFIXES = {".md", ".txt", ".json", ".csv", ".tsv", ".docx", ".pdf"}


@dataclass
class RfpResponseRunResult:
    run_id: str
    run_dir: str
    artifacts: dict[str, str]
    question_count: int
    high_touch_count: int
    answer_count: int
    sync_before_run: bool = False
    sync_result: dict[str, Any] | None = None
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "run_dir": self.run_dir,
            "artifacts": self.artifacts,
            "question_count": self.question_count,
            "high_touch_count": self.high_touch_count,
            "answer_count": self.answer_count,
            "sync_before_run": self.sync_before_run,
            "sync_result": self.sync_result,
            "warnings": self.warnings,
        }


def generate_rfp_response_run(
    bid_brief_path: str | Path | None = None,
    *,
    bid_brief: dict[str, Any] | None = None,
) -> RfpResponseRunResult:
    payload, brief_base_dir = _load_bid_brief(bid_brief_path, bid_brief)
    normalized = _normalize_bid_brief(payload, brief_base_dir)

    sync_result: dict[str, Any] | None = None
    if normalized["sync_before_run"]:
        if not normalized["config_path"]:
            raise ValueError("`config_path` is required when `sync_before_run` is true.")
        config = SyncConfig.from_file(normalized["config_path"])
        sync_result = SharePointSyncService(config, folder_key="truth_source").sync(
            full_resync=normalized["full_resync"]
        ).to_dict()
        normalized["truth_source_corpus_dir"] = str(config.truth_source_corpus_dir)

    run_dir = _prepare_run_dir(normalized)
    normalized["run_id"] = run_dir.name
    normalized["run_dir"] = str(run_dir)

    bid_request = _parse_bid_request(normalized)
    _apply_bid_context_to_request(bid_request, normalized)
    corpus = CorpusStore(normalized["truth_source_corpus_dir"])
    answers = _draft_answers_with_bid_context(bid_request, corpus, normalized)

    artifacts = _write_run_artifacts(
        run_dir=run_dir,
        normalized=normalized,
        bid_request=bid_request,
        answers=answers,
        sync_result=sync_result,
    )

    return RfpResponseRunResult(
        run_id=run_dir.name,
        run_dir=str(run_dir),
        artifacts=artifacts,
        question_count=len(bid_request.questions),
        high_touch_count=sum(1 for question in bid_request.questions if question.human_guidance_required),
        answer_count=len(answers),
        sync_before_run=normalized["sync_before_run"],
        sync_result=sync_result,
        warnings=normalized["warnings"],
    )


def _load_bid_brief(
    bid_brief_path: str | Path | None,
    bid_brief: dict[str, Any] | None,
) -> tuple[dict[str, Any], Path]:
    if bid_brief is not None:
        return dict(bid_brief), Path.cwd()
    if not bid_brief_path:
        raise ValueError("`bid_brief_path` or inline `bid_brief` is required.")
    path = Path(bid_brief_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload, path.parent


def _normalize_bid_brief(payload: dict[str, Any], brief_base_dir: Path) -> dict[str, Any]:
    company_name = payload.get("company_name") or payload.get("customer_name")
    if not company_name:
        raise ValueError("Bid brief requires `company_name` or `customer_name`.")
    rfp_input = payload.get("rfp_input_path")
    if not rfp_input:
        raise ValueError("Bid brief requires `rfp_input_path`.")

    run_date = payload.get("run_date") or date.today().isoformat()
    opportunity_name = payload.get("opportunity_name") or payload.get("rfp_name") or ""
    base_run_id = payload.get("run_id") or _build_run_id(run_date, company_name, opportunity_name)
    output_root = _resolve_path(
        payload.get("output_root", "data/outputs/rfp-response-runs"),
        brief_base_dir,
    )
    rfp_input_path = _resolve_path(rfp_input, brief_base_dir)
    primary_rfp_path, bid_pack_context_files, warnings = _resolve_primary_rfp(
        rfp_input_path,
        payload.get("primary_rfp_path"),
        brief_base_dir,
    )

    config_path = payload.get("config_path")
    resolved_config_path = str(_resolve_path(config_path, brief_base_dir)) if config_path else ""
    truth_source_corpus_dir = payload.get("truth_source_corpus_dir")
    if truth_source_corpus_dir:
        corpus_dir = _resolve_path(truth_source_corpus_dir, brief_base_dir)
    elif resolved_config_path:
        config = SyncConfig.from_file(resolved_config_path, allow_missing_secret=True)
        corpus_dir = config.truth_source_corpus_dir
    else:
        corpus_dir = Path("data/truth-source")

    answer_profile_path = payload.get("answer_profile_path")
    answer_profile: dict[str, Any] = {}
    if answer_profile_path:
        profile_path = _resolve_path(answer_profile_path, brief_base_dir)
        answer_profile = json.loads(profile_path.read_text(encoding="utf-8"))

    context_files = [
        str(_resolve_path(path, brief_base_dir))
        for path in _normalize_string_list(payload.get("bid_context_paths", []))
    ]
    context_files.extend(str(path) for path in bid_pack_context_files)
    context_files = list(dict.fromkeys(context_files))

    context_text, context_warnings = _collect_bid_context_text(context_files)
    warnings.extend(context_warnings)

    requested_package_formats = [
        item.lower() for item in _normalize_string_list(payload.get("requested_package_formats", []))
    ]
    unsupported_formats = [
        item for item in requested_package_formats if item not in {"markdown", "json", "csv"}
    ]
    if unsupported_formats:
        raise ValueError(f"Unsupported package formats: {', '.join(unsupported_formats)}")

    normalized_segments = _normalize_string_list(
        payload.get("target_client_segments")
        or payload.get("client_segments")
        or payload.get("client_segment")
        or []
    )
    mandatory_attachments = _normalize_string_list(payload.get("mandatory_attachments", []))
    human_reviewers = _normalize_string_list(
        payload.get("human_reviewers") or payload.get("review_owners") or []
    )
    win_themes = _normalize_string_list(payload.get("win_themes", []))

    customer_context = payload.get("customer_context", "")
    customer_context_text = (
        json.dumps(customer_context, indent=2, sort_keys=True)
        if isinstance(customer_context, dict)
        else str(customer_context)
    )
    supplied_retrieval_context = payload.get("retrieval_context") or ""
    supplied_retrieval_context_text = (
        json.dumps(supplied_retrieval_context, indent=2, sort_keys=True)
        if isinstance(supplied_retrieval_context, dict)
        else str(supplied_retrieval_context)
    )
    retrieval_context = "\n\n".join(
        part
        for part in [
            customer_context_text,
            "\n".join(win_themes),
            supplied_retrieval_context_text,
            context_text,
        ]
        if part
    )

    return {
        "company_name": str(company_name),
        "opportunity_name": str(opportunity_name),
        "run_date": run_date,
        "base_run_id": base_run_id,
        "run_id": base_run_id,
        "output_root": str(output_root),
        "overwrite_existing_run": bool(payload.get("overwrite_existing_run", False)),
        "rfp_input_path": str(rfp_input_path),
        "primary_rfp_path": str(primary_rfp_path),
        "bid_pack_context_files": context_files,
        "customer_context": customer_context,
        "customer_context_status": "bid-context-input-not-approved-evidence",
        "retrieval_context": retrieval_context,
        "target_client_segments": normalized_segments,
        "submission_deadline": payload.get("submission_deadline", ""),
        "response_tone": payload.get("response_tone", ""),
        "answer_profile_path": str(_resolve_path(answer_profile_path, brief_base_dir))
        if answer_profile_path
        else "",
        "answer_profile": answer_profile,
        "win_themes": win_themes,
        "mandatory_attachments": mandatory_attachments,
        "human_reviewers": human_reviewers,
        "config_path": resolved_config_path,
        "truth_source_corpus_dir": str(corpus_dir),
        "sync_before_run": bool(payload.get("sync_before_run", False)),
        "full_resync": bool(payload.get("full_resync", False)),
        "requested_package_formats": requested_package_formats,
        "warnings": warnings,
    }


def _resolve_path(value: str | Path | None, brief_base_dir: Path) -> Path:
    if value is None:
        return Path()
    path = Path(value)
    if path.is_absolute():
        return path
    base_candidate = brief_base_dir / path
    if base_candidate.exists():
        return base_candidate
    return path


def _resolve_primary_rfp(
    rfp_input_path: Path,
    primary_rfp_path: str | None,
    brief_base_dir: Path,
) -> tuple[Path, list[Path], list[str]]:
    warnings: list[str] = []
    if rfp_input_path.is_file():
        return rfp_input_path, [], warnings
    if not rfp_input_path.is_dir():
        raise ValueError(f"RFP input path does not exist: {rfp_input_path}")
    candidates = [
        path
        for path in sorted(rfp_input_path.iterdir())
        if path.is_file() and path.suffix.lower() in SUPPORTED_BID_CONTEXT_SUFFIXES
    ]
    if primary_rfp_path:
        primary = _resolve_path(primary_rfp_path, brief_base_dir)
        if not primary.is_absolute() and not primary.exists():
            primary = rfp_input_path / primary
        if not primary.exists():
            raise ValueError(f"Primary RFP path does not exist: {primary}")
    else:
        named = [
            path
            for path in candidates
            if any(
                token in path.stem.lower()
                for token in ("rfp", "rft", "tender", "questionnaire", "requirements")
            )
        ]
        if len(named) == 1:
            primary = named[0]
        elif len(candidates) == 1:
            primary = candidates[0]
        else:
            raise ValueError(
                "`primary_rfp_path` is required when `rfp_input_path` is a folder "
                "without exactly one clear primary RFP document."
            )
    context_files = [path for path in candidates if path != primary]
    if context_files:
        warnings.append(
            "Non-primary bid pack files were treated as customer-supplied bid context, "
            "not approved evidence."
        )
    return primary, context_files, warnings


def _collect_bid_context_text(paths: list[str]) -> tuple[str, list[str]]:
    snippets: list[str] = []
    warnings: list[str] = []
    for raw_path in paths:
        path = Path(raw_path)
        if not path.exists():
            warnings.append(f"Bid context file does not exist and was skipped: {path}")
            continue
        if path.suffix.lower() not in SUPPORTED_BID_CONTEXT_SUFFIXES:
            warnings.append(f"Bid context file has unsupported format and was skipped: {path}")
            continue
        try:
            text = extract_text_from_path(path)
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"Bid context file could not be read and was skipped: {path} ({exc})")
            continue
        snippets.append(f"Source: {path}\n{text[:3000]}")
    return "\n\n".join(snippets), warnings


def _parse_bid_request(normalized: dict[str, Any]) -> BidRequest:
    bid = parse_rfp_file(normalized["primary_rfp_path"])
    if normalized["submission_deadline"] and normalized["submission_deadline"] not in bid.deadlines:
        bid.deadlines.append(normalized["submission_deadline"])
    return bid


def _apply_bid_context_to_request(bid: BidRequest, normalized: dict[str, Any]) -> None:
    target_segments = normalized["target_client_segments"]
    if target_segments:
        bid.target_client_segments = list(dict.fromkeys(target_segments + bid.target_client_segments))

    context_domains = detect_domains(normalized["retrieval_context"])
    for question in bid.questions:
        if target_segments:
            question.related_client_segments = list(
                dict.fromkeys(question.related_client_segments + target_segments)
            )
        if context_domains:
            question.related_domains = list(dict.fromkeys(question.related_domains + context_domains))
        question.evidence_hints = build_evidence_hints(
            question.related_domains,
            question.related_client_segments,
        )


def _draft_answers_with_bid_context(
    bid: BidRequest,
    corpus: CorpusStore,
    normalized: dict[str, Any],
) -> list[AnswerContract]:
    answers: list[AnswerContract] = []
    context = normalized["retrieval_context"]
    for question in bid.questions:
        query = "\n".join(part for part in [question.question_text, context] if part)
        hits = corpus.search(
            query,
            limit=3,
            approved_only=True,
            client_segments=question.related_client_segments,
            domains=question.related_domains,
        )
        answer = build_answer_contract(question, hits)
        _apply_bid_level_review_items(answer, normalized)
        answers.append(answer)
    return answers


def _apply_bid_level_review_items(answer: AnswerContract, normalized: dict[str, Any]) -> None:
    for attachment in normalized["mandatory_attachments"]:
        if attachment not in answer.required_attachments:
            answer.required_attachments.append(attachment)
    if normalized["human_reviewers"]:
        reviewer_text = "Review owners: " + ", ".join(normalized["human_reviewers"])
        if reviewer_text not in answer.followups:
            answer.followups.append(reviewer_text)
    if normalized["customer_context"]:
        context_note = (
            "Customer-specific bid context influenced retrieval and drafting posture; "
            "do not treat it as approved capability evidence."
        )
        if context_note not in answer.followups:
            answer.followups.append(context_note)


def _write_run_artifacts(
    *,
    run_dir: Path,
    normalized: dict[str, Any],
    bid_request: BidRequest,
    answers: list[AnswerContract],
    sync_result: dict[str, Any] | None,
) -> dict[str, str]:
    artifacts: dict[str, str] = {}
    artifact_payloads = {
        "bid-brief.normalized.json": json.dumps(normalized, indent=2, sort_keys=True),
        "structured-rfp.md": render_rfp_markdown(bid_request),
        "response-index.md": render_response_index_markdown(bid_request),
        "answer-contracts.json": package_answers(answers, output_format="json"),
        "draft-answers.md": package_answers(answers, output_format="markdown"),
        "human-review-actions.md": _render_human_review_actions(
            normalized["run_id"], bid_request, answers
        ),
        "run-record.md": _render_run_record(normalized, bid_request, answers, sync_result),
    }
    for filename, content in artifact_payloads.items():
        path = run_dir / filename
        path.write_text(content, encoding="utf-8")
        artifacts[filename] = str(path)

    for output_format in normalized["requested_package_formats"]:
        if output_format == "markdown":
            continue
        filename = f"draft-answers.{output_format}"
        path = run_dir / filename
        path.write_text(package_answers(answers, output_format=output_format), encoding="utf-8")
        artifacts[filename] = str(path)
    return artifacts


def _render_human_review_actions(
    run_id: str,
    bid_request: BidRequest,
    answers: list[AnswerContract],
) -> str:
    lines = [
        "# Human Review Actions",
        "",
        f"- Run ID: `{run_id}`",
        f"- Question count: {len(bid_request.questions)}",
        f"- High-touch questions: {sum(1 for question in bid_request.questions if question.human_guidance_required)}",
        "",
        "## Required Actions",
        "",
    ]
    action_count = 0
    for answer in answers:
        actions = list(dict.fromkeys(answer.gaps + answer.followups + answer.required_attachments))
        if not actions:
            continue
        action_count += 1
        lines.extend([f"### {answer.question_id}", answer.question_text, ""])
        for action in actions:
            lines.append(f"- {action}")
        lines.append("")
    if action_count == 0:
        lines.append("No explicit human-review actions were generated.")
        lines.append("")
    lines.extend(
        [
            "## Evidence Boundary",
            "",
            "- Generation used approved `true source` corpus records only.",
            "- `update_inbox` was not synced, read, promoted, or consolidated by this run.",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def _render_run_record(
    normalized: dict[str, Any],
    bid_request: BidRequest,
    answers: list[AnswerContract],
    sync_result: dict[str, Any] | None,
) -> str:
    cited_documents = _summarize_citations(answers)
    artifacts = [
        "bid-brief.normalized.json",
        "structured-rfp.md",
        "response-index.md",
        "answer-contracts.json",
        "draft-answers.md",
        "human-review-actions.md",
        "run-record.md",
    ]
    lines = [
        "# RFP Response Run Record",
        "",
        "## Run Context",
        f"- Run ID: `{normalized['run_id']}`",
        f"- Run folder: `{normalized['run_dir']}`",
        f"- Company: {normalized['company_name']}",
        f"- Opportunity: {normalized['opportunity_name'] or 'not supplied'}",
        f"- Run date: {normalized['run_date']}",
        f"- RFP input: `{normalized['rfp_input_path']}`",
        f"- Primary RFP: `{normalized['primary_rfp_path']}`",
        f"- Question count: {len(bid_request.questions)}",
        f"- High-touch questions: {sum(1 for question in bid_request.questions if question.human_guidance_required)}",
        "",
        "## Evidence Boundary",
        f"- True-source corpus: `{normalized['truth_source_corpus_dir']}`",
        f"- SharePoint config: `{normalized['config_path'] or 'not supplied'}`",
        f"- Sync before run: {'Yes' if normalized['sync_before_run'] else 'No'}",
        "- Approved evidence only: Yes",
        "- Update inbox touched: No",
        "- Source consolidation or promotion performed: No",
        "",
    ]
    if sync_result:
        lines.extend(
            [
                "## Sync Result",
                f"- Synced: {sync_result.get('synced', 0)}",
                f"- Deleted: {sync_result.get('deleted', 0)}",
                f"- Skipped: {sync_result.get('skipped', 0)}",
                f"- Errors: {len(sync_result.get('errors', []))}",
                "",
            ]
        )
    lines.extend(
        [
            "## Bid Context Inputs",
            f"- Customer context status: {normalized['customer_context_status']}",
            (
                f"- Target client segments: {', '.join(normalized['target_client_segments'])}"
                if normalized["target_client_segments"]
                else "- Target client segments: not supplied"
            ),
            (
                f"- Win themes: {', '.join(normalized['win_themes'])}"
                if normalized["win_themes"]
                else "- Win themes: not supplied"
            ),
            (
                f"- Human reviewers: {', '.join(normalized['human_reviewers'])}"
                if normalized["human_reviewers"]
                else "- Human reviewers: not supplied"
            ),
            "",
            "### Bid Pack Context Files",
        ]
    )
    if normalized["bid_pack_context_files"]:
        for path in normalized["bid_pack_context_files"]:
            lines.append(f"- `{path}`")
    else:
        lines.append("- none")
    lines.extend(["", "## Cited Approved Evidence"])
    if cited_documents:
        for document in cited_documents:
            lines.append(
                f"- `{document['document_id']}` {document['title']} "
                f"({document['source_library']}) - {document['citation_count']} citation(s)"
            )
    else:
        lines.append("- none")
    lines.extend(["", "## Generated Artifacts"])
    for artifact in artifacts:
        lines.append(f"- `{artifact}`")
    requested_extra = [
        f"draft-answers.{item}"
        for item in normalized["requested_package_formats"]
        if item != "markdown"
    ]
    for artifact in requested_extra:
        lines.append(f"- `{artifact}`")
    lines.extend(
        [
            "",
            "## Review Summary",
            f"- Low-confidence answers: {sum(1 for answer in answers if answer.confidence == 'low')}",
            f"- Answers with gaps: {sum(1 for answer in answers if answer.gaps)}",
            f"- Answers requiring attachments: {sum(1 for answer in answers if answer.required_attachments)}",
        ]
    )
    if normalized["warnings"]:
        lines.extend(["", "## Warnings"])
        for warning in normalized["warnings"]:
            lines.append(f"- {warning}")
    return "\n".join(lines).strip() + "\n"


def _summarize_citations(answers: list[AnswerContract]) -> list[dict[str, Any]]:
    by_document: dict[str, dict[str, Any]] = {}
    for answer in answers:
        for citation in answer.citations:
            entry = by_document.setdefault(
                citation.document_id,
                {
                    "document_id": citation.document_id,
                    "title": citation.title,
                    "source_library": citation.source_library,
                    "citation_count": 0,
                },
            )
            entry["citation_count"] += 1
    return sorted(by_document.values(), key=lambda item: item["document_id"])


def _prepare_run_dir(normalized: dict[str, Any]) -> Path:
    output_root = Path(normalized["output_root"])
    output_root.mkdir(parents=True, exist_ok=True)
    candidate = output_root / normalized["base_run_id"]
    if normalized["overwrite_existing_run"]:
        candidate.mkdir(parents=True, exist_ok=True)
        return candidate
    if not candidate.exists():
        candidate.mkdir(parents=True)
        return candidate
    index = 2
    while True:
        suffixed = output_root / f"{normalized['base_run_id']}-{index}"
        if not suffixed.exists():
            suffixed.mkdir(parents=True)
            return suffixed
        index += 1


def _build_run_id(run_date: str, company_name: str, opportunity_name: str = "") -> str:
    parts = [run_date, company_name, opportunity_name]
    return slugify("-".join(part for part in parts if part))


def _normalize_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value else []
    return [str(item) for item in value if str(item)]
