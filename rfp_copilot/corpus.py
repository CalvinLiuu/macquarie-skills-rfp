from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from .models import EvidenceRecord, SearchHit


TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> set[str]:
    return set(TOKEN_PATTERN.findall(text.lower()))


def chunk_text(text: str, max_chars: int = 1200) -> list[str]:
    cleaned = " ".join(text.split())
    if not cleaned:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(cleaned):
        end = min(len(cleaned), start + max_chars)
        if end < len(cleaned):
            split_at = cleaned.rfind(" ", start, end)
            if split_at > start + 200:
                end = split_at
        chunks.append(cleaned[start:end].strip())
        start = end
    return [chunk for chunk in chunks if chunk]


class CorpusStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.records_dir = self.root / "evidence"
        self.raw_dir = self.root / "raw"
        self.records_dir.mkdir(parents=True, exist_ok=True)
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    def clear(self) -> None:
        if self.records_dir.exists():
            shutil.rmtree(self.records_dir)
        if self.raw_dir.exists():
            shutil.rmtree(self.raw_dir)
        self.records_dir.mkdir(parents=True, exist_ok=True)
        self.raw_dir.mkdir(parents=True, exist_ok=True)

    def record_path(self, document_id: str) -> Path:
        return self.records_dir / f"{document_id}.json"

    def raw_path(self, document_id: str) -> Path:
        return self.raw_dir / f"{document_id}.txt"

    def upsert(self, record: EvidenceRecord) -> Path:
        payload = record.to_dict()
        path = self.record_path(record.document_id)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return path

    def write_raw_text(self, document_id: str, text: str) -> Path:
        path = self.raw_path(document_id)
        path.write_text(text, encoding="utf-8")
        return path

    def remove(self, document_id: str) -> bool:
        removed = False
        for path in (self.record_path(document_id), self.raw_path(document_id)):
            if path.exists():
                path.unlink()
                removed = True
        return removed

    def get(self, document_id: str) -> EvidenceRecord | None:
        path = self.record_path(document_id)
        if not path.exists():
            return None
        return EvidenceRecord.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def list_records(self) -> list[EvidenceRecord]:
        records: list[EvidenceRecord] = []
        for path in sorted(self.records_dir.glob("*.json")):
            records.append(EvidenceRecord.from_dict(json.loads(path.read_text(encoding="utf-8"))))
        return records

    def search(
        self,
        query: str,
        limit: int = 5,
        approved_only: bool = True,
        client_segments: list[str] | None = None,
        domains: list[str] | None = None,
    ) -> list[SearchHit]:
        query_tokens = tokenize(query)
        if not query_tokens:
            return []
        hits: list[SearchHit] = []
        for record in self.list_records():
            if approved_only and not record.approved_for_bids:
                continue
            best_score = 0.0
            best_excerpt = ""
            best_chunk_index = 0
            for index, chunk in enumerate(record.text_chunks):
                score = self._score(
                    query,
                    query_tokens,
                    chunk,
                    record,
                    client_segments=client_segments or [],
                    domains=domains or [],
                )
                if score > best_score:
                    best_score = score
                    best_excerpt = chunk
                    best_chunk_index = index
            if best_score > 0:
                hits.append(
                    SearchHit(
                        record=record,
                        score=best_score,
                        excerpt=best_excerpt,
                        chunk_index=best_chunk_index,
                    )
                )
        hits.sort(key=lambda item: item.score, reverse=True)
        return hits[:limit]

    def _score(
        self,
        query: str,
        query_tokens: set[str],
        chunk: str,
        record: EvidenceRecord,
        *,
        client_segments: list[str],
        domains: list[str],
    ) -> float:
        text = " ".join(
            [
                record.title,
                chunk,
                record.owner,
                record.classification,
                " ".join(record.domains),
                " ".join(record.client_segments),
            ]
        ).lower()
        chunk_tokens = tokenize(text)
        overlap = len(query_tokens & chunk_tokens)
        if overlap == 0:
            return 0.0
        score = overlap / max(len(query_tokens), 1)
        if query.lower() in text:
            score += 0.5
        if record.approved_for_bids:
            score += 0.15
        if record.review_date:
            score += 0.05
        if client_segments and set(client_segments) & set(record.client_segments):
            score += 0.25
        if domains and set(domains) & set(record.domains):
            score += 0.2
        return score
