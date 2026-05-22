from __future__ import annotations

import json
import sys
from typing import Any

from .answering import build_answer_contract, package_answers
from .corpus import CorpusStore
from .markdown_formatter import build_markdown_knowledge_base, render_rfp_markdown
from .models import AnswerContract, Question
from .rfp_parser import parse_rfp_file, parse_rfp_text
from .response_indexer import render_response_index_json, render_response_index_markdown
from .sharepoint_graph import SharePointSyncService, SyncConfig
from .source_refresh import SourceRefreshService


SERVER_INFO = {"name": "sharepoint-knowledge", "version": "0.1.0"}


TOOLS: list[dict[str, Any]] = [
    {
        "name": "sync_sharepoint_library",
        "description": "Synchronize the true-source or update-inbox SharePoint folder into the local mirror.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "config_path": {"type": "string"},
                "full_resync": {"type": "boolean", "default": False},
                "folder_key": {"type": "string", "default": "truth_source"},
            },
            "required": ["config_path"],
        },
    },
    {
        "name": "search_evidence_corpus",
        "description": "Search the mirrored evidence corpus for approved bid material.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "corpus_dir": {"type": "string", "default": "data/truth-source"},
                "limit": {"type": "integer", "default": 5},
                "approved_only": {"type": "boolean", "default": True},
                "client_segments": {"type": "array"},
                "domains": {"type": "array"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_evidence_record",
        "description": "Return one normalized evidence record by document id.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "document_id": {"type": "string"},
                "corpus_dir": {"type": "string", "default": "data/truth-source"},
            },
            "required": ["document_id"],
        },
    },
    {
        "name": "search_sharepoint_live",
        "description": "Query live SharePoint search as fallback for fresh or missing content.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "config_path": {"type": "string"},
                "limit": {"type": "integer", "default": 5},
            },
            "required": ["query", "config_path"],
        },
    },
    {
        "name": "extract_rfp_questions",
        "description": "Parse an RFP document or raw text into discrete question records.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "text": {"type": "string"},
                "title": {"type": "string", "default": ""},
            },
        },
    },
    {
        "name": "render_rfp_markdown",
        "description": "Convert an RFP into structured markdown with related domains and question links.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "text": {"type": "string"},
                "title": {"type": "string", "default": ""},
            },
        },
    },
    {
        "name": "build_markdown_knowledge_base",
        "description": "Convert mirrored source documents into structured markdown files and domain knowledge packs.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "corpus_dir": {"type": "string", "default": "data/truth-source"},
                "output_dir": {"type": "string"},
                "config_path": {"type": "string"},
                "folder_key": {"type": "string", "default": "truth_source"},
            },
        },
    },
    {
        "name": "prepare_source_refresh",
        "description": "Compare update-inbox content against the true-source corpus and build a human-review refresh plan.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "config_path": {"type": "string"},
                "output_dir": {"type": "string", "default": "data/outputs"},
            },
            "required": ["config_path"],
        },
    },
    {
        "name": "promote_source_refresh",
        "description": "Promote approved refresh candidates into the local true-source corpus after human review.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "config_path": {"type": "string"},
                "candidate_ids": {"type": "array"},
                "output_dir": {"type": "string", "default": "data/outputs"},
            },
            "required": ["config_path", "candidate_ids"],
        },
    },
    {
        "name": "create_answer_contract",
        "description": "Build the answer contract for one question from mirrored evidence.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "question_text": {"type": "string"},
                "question_id": {"type": "string", "default": "Q001"},
                "corpus_dir": {"type": "string", "default": "data/truth-source"},
                "limit": {"type": "integer", "default": 3},
                "client_segments": {"type": "array"},
                "domains": {"type": "array"},
            },
            "required": ["question_text"],
        },
    },
    {
        "name": "build_response_index",
        "description": "Create a structured response index from the RFP with response format and human-guidance flags.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "text": {"type": "string"},
                "title": {"type": "string", "default": ""},
                "format": {"type": "string", "default": "markdown"},
            },
        },
    },
    {
        "name": "package_answers",
        "description": "Render answer contracts as markdown, JSON, or CSV.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "answers": {"type": "array"},
                "format": {"type": "string", "default": "markdown"},
            },
            "required": ["answers"],
        },
    },
]


def main() -> None:
    while True:
        message = _read_message()
        if message is None:
            return
        if "id" not in message:
            _handle_notification(message)
            continue
        response = _handle_request(message)
        _write_message(response)


def _handle_request(message: dict[str, Any]) -> dict[str, Any]:
    method = message.get("method")
    request_id = message.get("id")
    try:
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "serverInfo": SERVER_INFO,
                    "capabilities": {"tools": {"listChanged": False}},
                },
            }
        if method == "ping":
            return {"jsonrpc": "2.0", "id": request_id, "result": {}}
        if method == "tools/list":
            return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": TOOLS}}
        if method == "tools/call":
            params = message.get("params", {})
            result = _call_tool(params.get("name", ""), params.get("arguments", {}))
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(result, indent=2)}],
                    "structuredContent": result,
                },
            }
        raise ValueError(f"Unsupported method: {method}")
    except Exception as exc:  # noqa: BLE001
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32000, "message": str(exc)},
        }


def _handle_notification(message: dict[str, Any]) -> None:
    # This server does not currently act on notifications such as `initialized`.
    _ = message


def _call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name == "sync_sharepoint_library":
        config = SyncConfig.from_file(arguments["config_path"])
        result = SharePointSyncService(
            config,
            folder_key=arguments.get("folder_key", "truth_source"),
        ).sync(full_resync=arguments.get("full_resync", False))
        return result.to_dict()
    if name == "search_evidence_corpus":
        corpus = CorpusStore(arguments.get("corpus_dir", "data/truth-source"))
        hits = corpus.search(
            arguments["query"],
            limit=int(arguments.get("limit", 5)),
            approved_only=arguments.get("approved_only", True),
            client_segments=arguments.get("client_segments", []),
            domains=arguments.get("domains", []),
        )
        return {"hits": [hit.to_dict() for hit in hits]}
    if name == "get_evidence_record":
        corpus = CorpusStore(arguments.get("corpus_dir", "data/truth-source"))
        record = corpus.get(arguments["document_id"])
        return {"record": record.to_dict() if record else None}
    if name == "search_sharepoint_live":
        config = SyncConfig.from_file(arguments["config_path"])
        hits = SharePointSyncService(config).search_live(
            arguments["query"],
            limit=int(arguments.get("limit", 5)),
        )
        return {"hits": hits}
    if name == "extract_rfp_questions":
        if arguments.get("path"):
            bid = parse_rfp_file(arguments["path"])
        elif arguments.get("text"):
            bid = parse_rfp_text(arguments["text"], title=arguments.get("title", ""))
        else:
            raise ValueError("Either `path` or `text` is required.")
        return bid.to_dict()
    if name == "render_rfp_markdown":
        if arguments.get("path"):
            bid = parse_rfp_file(arguments["path"])
        elif arguments.get("text"):
            bid = parse_rfp_text(arguments["text"], title=arguments.get("title", ""))
        else:
            raise ValueError("Either `path` or `text` is required.")
        return {"markdown": render_rfp_markdown(bid)}
    if name == "build_markdown_knowledge_base":
        if arguments.get("config_path"):
            config = SyncConfig.from_file(arguments["config_path"], allow_missing_secret=True)
            corpus = CorpusStore(config.corpus_dir_for(arguments.get("folder_key", "truth_source")))
        else:
            corpus = CorpusStore(arguments.get("corpus_dir", "data/truth-source"))
        result = build_markdown_knowledge_base(corpus, output_dir=arguments.get("output_dir"))
        return result.to_dict()
    if name == "prepare_source_refresh":
        config = SyncConfig.from_file(arguments["config_path"], allow_missing_secret=True)
        result = SourceRefreshService(config).build_refresh_plan(
            output_dir=arguments.get("output_dir", "data/outputs")
        )
        return result.to_dict()
    if name == "promote_source_refresh":
        config = SyncConfig.from_file(arguments["config_path"], allow_missing_secret=True)
        result = SourceRefreshService(config).promote_candidates(
            arguments["candidate_ids"],
            output_dir=arguments.get("output_dir", "data/outputs"),
        )
        return result.to_dict()
    if name == "create_answer_contract":
        question = Question(
            question_id=arguments.get("question_id", "Q001"),
            question_text=arguments["question_text"],
        )
        corpus = CorpusStore(arguments.get("corpus_dir", "data/truth-source"))
        hits = corpus.search(
            arguments["question_text"],
            limit=int(arguments.get("limit", 3)),
            client_segments=arguments.get("client_segments", []),
            domains=arguments.get("domains", []),
        )
        return build_answer_contract(question, hits).to_dict()
    if name == "build_response_index":
        if arguments.get("path"):
            bid = parse_rfp_file(arguments["path"])
        elif arguments.get("text"):
            bid = parse_rfp_text(arguments["text"], title=arguments.get("title", ""))
        else:
            raise ValueError("Either `path` or `text` is required.")
        if arguments.get("format", "markdown") == "json":
            return {"rendered": render_response_index_json(bid)}
        return {"rendered": render_response_index_markdown(bid)}
    if name == "package_answers":
        answers = [AnswerContract.from_dict(item) for item in arguments["answers"]]
        return {"rendered": package_answers(answers, output_format=arguments.get("format", "markdown"))}
    raise ValueError(f"Unknown tool: {name}")


def _read_message() -> dict[str, Any] | None:
    headers: dict[str, str] = {}
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            return None
        decoded = line.decode("utf-8").strip()
        if decoded == "":
            break
        key, value = decoded.split(":", 1)
        headers[key.strip().lower()] = value.strip()
    content_length = int(headers.get("content-length", "0"))
    if content_length == 0:
        return None
    payload = sys.stdin.buffer.read(content_length)
    return json.loads(payload.decode("utf-8"))


def _write_message(payload: dict[str, Any]) -> None:
    encoded = json.dumps(payload).encode("utf-8")
    header = f"Content-Length: {len(encoded)}\r\n\r\n".encode("utf-8")
    sys.stdout.buffer.write(header + encoded)
    sys.stdout.buffer.flush()


if __name__ == "__main__":
    main()
