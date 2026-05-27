from __future__ import annotations

import json
from pathlib import Path

from .corpus import CorpusStore
from .markdown_formatter import build_markdown_knowledge_base
from .models import EvidenceRecord, RefreshCandidate, RefreshPlanResult
from .sharepoint_graph import SharePointSyncService, SyncConfig
from .taxonomy import (
    analysis_focus_for_document_type,
    normalize_title_key,
    rank_domain_overlap,
    rank_segment_overlap,
    specialist_agent_for_document_type,
)


class SourceRefreshService:
    def __init__(self, config: SyncConfig, client=None) -> None:
        self.config = config
        self.truth_source = SharePointSyncService(config, client=client, folder_key="truth_source")
        self.update_inbox = SharePointSyncService(config, client=client, folder_key="update_inbox")

    def sync_all(self, *, full_resync: bool = False) -> dict:
        truth_result = self.truth_source.sync(full_resync=full_resync)
        update_result = self.update_inbox.sync(full_resync=full_resync)
        return {
            "truth_source": truth_result.to_dict(),
            "update_inbox": update_result.to_dict(),
        }

    def build_refresh_plan(self, output_dir: str | Path = "data/outputs") -> RefreshPlanResult:
        truth_records = self.truth_source.corpus.list_records()
        staged_records = self.update_inbox.corpus.list_records()
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        candidates: list[RefreshCandidate] = []

        for staged in staged_records:
            match = self._best_match(staged, truth_records)
            candidate = self._build_candidate(staged, match)
            candidates.append(candidate)

        manifest_path = output_path / "source-refresh-plan.json"
        report_path = output_path / "source-refresh-report.md"
        manifest_path.write_text(
            json.dumps([candidate.to_dict() for candidate in candidates], indent=2),
            encoding="utf-8",
        )
        report_path.write_text(self._render_refresh_report(candidates), encoding="utf-8")
        return RefreshPlanResult(
            candidates=candidates,
            report_path=str(report_path),
            manifest_path=str(manifest_path),
        )

    def promote_candidates(
        self,
        candidate_ids: list[str],
        output_dir: str | Path = "data/outputs",
    ) -> RefreshPlanResult:
        plan = self.build_refresh_plan(output_dir=output_dir)
        selected = [candidate for candidate in plan.candidates if candidate.candidate_id in set(candidate_ids)]
        staged_by_id = {record.document_id: record for record in self.update_inbox.corpus.list_records()}
        promoted = 0
        for candidate in selected:
            if candidate.human_guidance_required:
                continue
            staged = staged_by_id.get(candidate.source_document_id)
            if staged is None:
                continue
            promoted_record = self._promote_record(staged, candidate)
            self.truth_source.corpus.upsert(promoted_record)
            if staged.raw_path:
                raw_path = Path(staged.raw_path)
                if raw_path.exists():
                    self.truth_source.corpus.write_raw_text(
                        promoted_record.document_id,
                        raw_path.read_text(encoding="utf-8"),
                    )
            promoted += 1
        build_markdown_knowledge_base(self.truth_source.corpus)
        return RefreshPlanResult(
            candidates=selected,
            report_path=plan.report_path,
            manifest_path=plan.manifest_path,
            promoted=promoted,
        )

    def _best_match(
        self,
        staged: EvidenceRecord,
        truth_records: list[EvidenceRecord],
    ) -> EvidenceRecord | None:
        staged_key = normalize_title_key(staged.title)
        best_record: EvidenceRecord | None = None
        best_score = -1
        for record in truth_records:
            score = 0
            if normalize_title_key(record.title) == staged_key:
                score += 3
            score += rank_segment_overlap(record.client_segments, staged.client_segments)
            score += rank_domain_overlap(record.domains, staged.domains)
            if score > best_score:
                best_score = score
                best_record = record
        return best_record if best_score > 0 else None

    def _build_candidate(
        self,
        staged: EvidenceRecord,
        match: EvidenceRecord | None,
    ) -> RefreshCandidate:
        reasons: list[str] = []
        if "government" in staged.client_segments:
            reasons.append("Government-oriented content should be reviewed by the compliance owner.")
        if not staged.approved_for_bids:
            reasons.append("The staged document is not marked approved for bids.")
        if match is None:
            action = "add"
            rationale = "No matching truth-source document was found."
        else:
            action = "update"
            rationale = "A likely truth-source match exists and should be reviewed for promotion."
            if match.version == staged.version:
                action = "review"
                reasons.append("The staged and truth-source versions match, so the change needs manual review.")
            if normalize_title_key(match.title) != normalize_title_key(staged.title):
                reasons.append("The title differs from the likely truth-source match.")
        return RefreshCandidate(
            candidate_id=f"refresh-{staged.document_id}",
            title=staged.title,
            proposed_action=action,
            source_document_id=staged.document_id,
            target_document_id=match.document_id if match else "",
            document_type=staged.document_type,
            specialist_agent=staged.specialist_agent or specialist_agent_for_document_type(staged.document_type),
            client_segments=staged.client_segments,
            domains=staged.domains,
            rationale=rationale,
            human_guidance_required=bool(reasons) or action != "add",
            human_guidance_reasons=reasons,
        )

    def _render_refresh_report(self, candidates: list[RefreshCandidate]) -> str:
        lines = [
            "# Source Refresh Report",
            "",
            "## Summary",
            f"- Candidate count: {len(candidates)}",
            f"- Human review required: {sum(1 for candidate in candidates if candidate.human_guidance_required)}",
            "",
            "## Candidates",
            "",
        ]
        for candidate in candidates:
            lines.extend(
                [
                    f"### {candidate.title}",
                    f"- Candidate ID: `{candidate.candidate_id}`",
                    f"- Proposed action: {candidate.proposed_action}",
                    f"- Client segments: {', '.join(candidate.client_segments) if candidate.client_segments else 'general'}",
                    f"- Domains: {', '.join(candidate.domains) if candidate.domains else 'general'}",
                    f"- Rationale: {candidate.rationale}",
                    (
                        f"- Human guidance: {'Yes - ' + '; '.join(candidate.human_guidance_reasons)}"
                        if candidate.human_guidance_required
                        else "- Human guidance: No"
                    ),
                    "",
                ]
            )
        return "\n".join(lines).strip() + "\n"

    def _promote_record(self, staged: EvidenceRecord, candidate: RefreshCandidate) -> EvidenceRecord:
        promoted_id = candidate.target_document_id or f"truth-{staged.document_id}"
        return EvidenceRecord(
            document_id=promoted_id,
            source_url=staged.source_url,
            source_library=staged.source_library,
            title=staged.title,
            owner=staged.owner,
            effective_date=staged.effective_date,
            review_date=staged.review_date,
            classification=staged.classification,
            approved_for_bids=staged.approved_for_bids,
            version=staged.version,
            text_chunks=staged.text_chunks,
            domains=staged.domains,
            client_segments=staged.client_segments,
            source_collection="truth_source",
            source_path=staged.source_path,
            raw_path=staged.raw_path,
            markdown_path="",
            document_type=staged.document_type,
            specialist_agent=staged.specialist_agent,
            analysis_focus=staged.analysis_focus or analysis_focus_for_document_type(staged.document_type),
            metadata=staged.metadata,
        )
