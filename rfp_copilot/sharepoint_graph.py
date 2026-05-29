from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .corpus import CorpusStore, chunk_text
from .markdown_formatter import build_markdown_knowledge_base
from .models import EvidenceRecord, SyncResult
from .rfp_parser import UnsupportedFormatError, extract_text_from_binary
from .sharepoint_structure import match_sharepoint_folder_role
from .taxonomy import (
    analysis_focus_for_document_type,
    detect_client_segments,
    detect_document_type,
    detect_domains,
    specialist_agent_for_document_type,
)


GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"


class GraphRequestError(RuntimeError):
    pass


class GraphClient:
    def __init__(self, tenant_id: str, client_id: str, client_secret: str) -> None:
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self._token: str | None = None

    def get_token(self) -> str:
        if self._token:
            return self._token
        url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        body = urllib.parse.urlencode(
            {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": "https://graph.microsoft.com/.default",
                "grant_type": "client_credentials",
            }
        ).encode("utf-8")
        request = urllib.request.Request(url, data=body, method="POST")
        request.add_header("Content-Type", "application/x-www-form-urlencoded")
        response = self._read_json(request)
        self._token = response["access_token"]
        return self._token

    def request_json(
        self,
        method: str,
        path_or_url: str,
        *,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = path_or_url if path_or_url.startswith("http") else f"{GRAPH_BASE_URL}{path_or_url}"
        payload = json.dumps(body).encode("utf-8") if body is not None else None
        request = urllib.request.Request(url, data=payload, method=method)
        request.add_header("Authorization", f"Bearer {self.get_token()}")
        request.add_header("Accept", "application/json")
        if payload is not None:
            request.add_header("Content-Type", "application/json")
        return self._read_json(request)

    def download_drive_item(self, drive_id: str, item_id: str) -> bytes:
        url = f"{GRAPH_BASE_URL}/drives/{drive_id}/items/{item_id}/content"
        request = urllib.request.Request(url, method="GET")
        request.add_header("Authorization", f"Bearer {self.get_token()}")
        try:
            with urllib.request.urlopen(request) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            raise GraphRequestError(f"Failed to download drive item {item_id}: {exc}") from exc

    def get_delta_page(
        self,
        site_id: str,
        drive_id: str,
        delta_link: str = "",
    ) -> dict[str, Any]:
        if delta_link:
            return self.request_json("GET", delta_link)
        return self.request_json("GET", f"/sites/{site_id}/drives/{drive_id}/root/delta")

    def get_item_fields(self, drive_id: str, item_id: str) -> dict[str, Any]:
        try:
            payload = self.request_json("GET", f"/drives/{drive_id}/items/{item_id}/listItem/fields")
        except GraphRequestError:
            return {}
        return payload

    def search_drive_items(
        self,
        query: str,
        *,
        limit: int = 5,
        region: str = "",
    ) -> list[dict[str, Any]]:
        body: dict[str, Any] = {
            "requests": [
                {
                    "entityTypes": ["driveItem"],
                    "query": {"queryString": query},
                    "size": limit,
                }
            ]
        }
        if region:
            body["requests"][0]["region"] = region
        payload = self.request_json("POST", "/search/query", body=body)
        results: list[dict[str, Any]] = []
        for response in payload.get("value", []):
            for container in response.get("hitsContainers", []):
                for hit in container.get("hits", []):
                    resource = hit.get("resource", {})
                    summary = hit.get("summary", "")
                    results.append(
                        {
                            "id": resource.get("id", hit.get("hitId", "")),
                            "name": resource.get("name", ""),
                            "webUrl": resource.get("webUrl", ""),
                            "summary": summary,
                        }
                    )
        return results[:limit]

    def _read_json(self, request: urllib.request.Request) -> dict[str, Any]:
        try:
            with urllib.request.urlopen(request) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise GraphRequestError(f"Graph request failed: {exc.code} {detail}") from exc


@dataclass
class SyncConfig:
    tenant_id: str
    client_id: str
    client_secret: str
    site_id: str
    drive_id: str
    source_library: str
    state_dir: Path
    truth_source_corpus_dir: Path
    update_inbox_corpus_dir: Path
    truth_source_folder: str = ""
    update_inbox_folder: str = ""
    allowed_extensions: list[str] = field(default_factory=lambda: [".md", ".txt", ".docx", ".pdf"])
    metadata_fields: dict[str, str] = field(default_factory=dict)
    sharepoint_structure: dict[str, Any] = field(default_factory=dict)
    region: str = ""
    approved_default: bool = False
    live_unapproved_allowed: bool = False

    @classmethod
    def from_file(
        cls,
        path: str | Path,
        *,
        allow_missing_secret: bool = False,
    ) -> "SyncConfig":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        paths = payload.get("paths", {})
        secret = payload.get("client_secret", "")
        secret_env = payload.get("client_secret_env", "")
        if not secret and secret_env:
            secret = os.environ.get(secret_env, "")
        if not secret and not allow_missing_secret:
            raise ValueError("SharePoint client secret is missing.")
        return cls(
            tenant_id=payload["tenant_id"],
            client_id=payload["client_id"],
            client_secret=secret,
            site_id=payload["site_id"],
            drive_id=payload["drive_id"],
            source_library=payload["source_library"],
            state_dir=Path(paths.get("state_dir", "data/state")),
            truth_source_corpus_dir=Path(
                paths.get("truth_source_corpus_dir", paths.get("corpus_dir", "data/truth-source"))
            ),
            update_inbox_corpus_dir=Path(
                paths.get("update_inbox_corpus_dir", "data/update-inbox")
            ),
            truth_source_folder=payload.get(
                "truth_source_folder",
                payload.get("source_folder", ""),
            ),
            update_inbox_folder=payload.get("update_inbox_folder", ""),
            allowed_extensions=payload.get("allowed_extensions", [".md", ".txt", ".docx", ".pdf"]),
            metadata_fields=payload.get("metadata_fields", {}),
            sharepoint_structure=payload.get("sharepoint_structure", {}),
            region=payload.get("region", ""),
            approved_default=payload.get("approved_default", False),
            live_unapproved_allowed=payload.get("live_unapproved_allowed", False),
        )

    def state_file(self, folder_key: str) -> Path:
        return self.state_dir / f"sharepoint-sync-{folder_key}.json"

    def corpus_dir_for(self, folder_key: str) -> Path:
        if folder_key == "update_inbox":
            return self.update_inbox_corpus_dir
        return self.truth_source_corpus_dir

    def folder_path_for(self, folder_key: str) -> str:
        if folder_key == "update_inbox":
            return self.update_inbox_folder
        return self.truth_source_folder


class SharePointSyncService:
    def __init__(
        self,
        config: SyncConfig,
        client: GraphClient | None = None,
        *,
        folder_key: str = "truth_source",
    ) -> None:
        self.config = config
        self.folder_key = folder_key
        self.client = client or GraphClient(
            config.tenant_id,
            config.client_id,
            config.client_secret,
        )
        self.config.state_dir.mkdir(parents=True, exist_ok=True)
        self.corpus = CorpusStore(config.corpus_dir_for(folder_key))

    def sync(self, full_resync: bool = False) -> SyncResult:
        state = {} if full_resync else self._load_state()
        if full_resync:
            self.corpus.clear()
        delta_link = state.get("delta_link", "")
        result = SyncResult()
        while True:
            payload = self.client.get_delta_page(
                self.config.site_id,
                self.config.drive_id,
                delta_link=delta_link,
            )
            for item in payload.get("value", []):
                self._process_item(item, result)
            next_link = payload.get("@odata.nextLink", "")
            delta_link = next_link or payload.get("@odata.deltaLink", "")
            if not next_link:
                break
        markdown_result = self.rebuild_markdown_views()
        result.markdown_documents = markdown_result.documents_written
        result.markdown_packs = markdown_result.domain_packs_written
        result.client_segment_packs = markdown_result.client_segment_packs_written
        result.document_type_packs = markdown_result.document_type_packs_written
        result.delta_link = delta_link
        self._save_state({"delta_link": delta_link})
        return result

    def search_live(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        hits = self.client.search_drive_items(query, limit=limit, region=self.config.region)
        for hit in hits:
            hit["approved_for_use"] = self.config.live_unapproved_allowed
            if not self.config.live_unapproved_allowed:
                hit["warning"] = (
                    "Live SharePoint result is discovery-only until it is mirrored or manually approved."
                )
        return hits

    def rebuild_markdown_views(self) -> Any:
        return build_markdown_knowledge_base(self.corpus)

    def _process_item(self, item: dict[str, Any], result: SyncResult) -> None:
        if "deleted" in item:
            if self.corpus.remove(item["id"]):
                result.deleted += 1
            return
        if "folder" in item:
            result.skipped += 1
            return
        if not self._item_in_scope(item):
            result.skipped += 1
            return
        filename = item.get("name", "")
        suffix = Path(filename).suffix.lower()
        if suffix not in self.config.allowed_extensions:
            result.skipped += 1
            return
        try:
            content = self.client.download_drive_item(self.config.drive_id, item["id"])
            text = extract_text_from_binary(filename, content)
        except UnsupportedFormatError as exc:
            result.skipped += 1
            result.errors.append(f"{filename}: {exc}")
            return
        except Exception as exc:  # noqa: BLE001
            result.errors.append(f"{filename}: {exc}")
            return
        fields = self.client.get_item_fields(self.config.drive_id, item["id"])
        raw_path = self.corpus.write_raw_text(item["id"], text)
        source_path = self._item_path(item)
        folder_role = match_sharepoint_folder_role(self.config.sharepoint_structure, source_path)
        folder_document_type = folder_role.document_type if folder_role else ""
        document_type = detect_document_type(
            source_path,
            filename,
            text,
            metadata_value=self._lookup_field(fields, "document_type") or folder_document_type,
        )
        client_segments = detect_client_segments(source_path, filename, text)
        if folder_role and folder_role.client_segment and folder_role.client_segment not in client_segments:
            client_segments.append(folder_role.client_segment)
        metadata = dict(fields)
        if folder_role:
            metadata["sharepoint_folder_role"] = folder_role.to_dict()
        record = EvidenceRecord(
            document_id=item["id"],
            source_url=item.get("webUrl", ""),
            source_library=self.config.source_library,
            title=filename,
            owner=self._lookup_field(fields, "owner") or self._fallback_owner(item),
            effective_date=self._lookup_field(fields, "effective_date") or item.get("createdDateTime", ""),
            review_date=self._lookup_field(fields, "review_date"),
            classification=self._lookup_field(fields, "classification") or "internal",
            approved_for_bids=self._read_approved_flag(fields),
            version=item.get("eTag", item.get("cTag", "")),
            text_chunks=chunk_text(text),
            domains=detect_domains(filename, text),
            client_segments=client_segments,
            source_collection=self.folder_key,
            source_path=source_path,
            raw_path=str(raw_path),
            document_type=document_type,
            specialist_agent=specialist_agent_for_document_type(document_type),
            analysis_focus=analysis_focus_for_document_type(document_type),
            metadata=metadata,
        )
        self.corpus.upsert(record)
        result.synced += 1

    def _lookup_field(self, fields: dict[str, Any], logical_name: str) -> str:
        column = self.config.metadata_fields.get(logical_name, "")
        value = fields.get(column, "") if column else ""
        return str(value) if value is not None else ""

    def _read_approved_flag(self, fields: dict[str, Any]) -> bool:
        raw_value = self._lookup_field(fields, "approved_for_bids")
        if raw_value == "":
            return self.config.approved_default
        return str(raw_value).strip().lower() in {"1", "true", "yes", "approved"}

    def _fallback_owner(self, item: dict[str, Any]) -> str:
        for key in ("lastModifiedBy", "createdBy"):
            actor = item.get(key, {})
            user = actor.get("user", {})
            if user.get("displayName"):
                return user["displayName"]
        return ""

    def _item_in_scope(self, item: dict[str, Any]) -> bool:
        scope_folder = self.config.folder_path_for(self.folder_key)
        if not scope_folder:
            return True
        folder = scope_folder.strip("/").lower()
        item_path = self._item_path(item).lower()
        return item_path.startswith(folder)

    def _item_path(self, item: dict[str, Any]) -> str:
        parent_path = item.get("parentReference", {}).get("path", "")
        if ":/" in parent_path:
            parent_path = parent_path.split(":/", 1)[1]
        parent_path = parent_path.strip("/")
        name = item.get("name", "").strip("/")
        return "/".join(part for part in (parent_path, name) if part)

    def _load_state(self) -> dict[str, Any]:
        path = self.config.state_file(self.folder_key)
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def _save_state(self, payload: dict[str, Any]) -> None:
        path = self.config.state_file(self.folder_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
