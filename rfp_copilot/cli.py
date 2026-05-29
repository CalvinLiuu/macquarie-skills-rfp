from __future__ import annotations

import argparse
import json
from pathlib import Path

from .answering import draft_answers_for_bid, package_answers
from .corpus import CorpusStore
from .document_analysis import build_document_analysis_plan
from .markdown_formatter import build_markdown_knowledge_base, render_rfp_markdown
from .models import AnswerContract
from .rfp_parser import parse_rfp_file
from .response_indexer import render_response_index_json, render_response_index_markdown
from .sharepoint_graph import SharePointSyncService, SyncConfig
from .sharepoint_structure import build_sharepoint_structure_plan
from .source_refresh import SourceRefreshService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="RFP Copilot workflow CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    sync = subparsers.add_parser("sync", help="Synchronize the SharePoint knowledge mirror")
    sync.add_argument("--config", required=True)
    sync.add_argument("--full-resync", action="store_true")
    sync.add_argument("--folder-key", default="truth_source", choices=["truth_source", "update_inbox"])

    search = subparsers.add_parser("search-corpus", help="Search mirrored evidence")
    search.add_argument("--query", required=True)
    search.add_argument("--corpus-dir", default="data/truth-source")
    search.add_argument("--limit", type=int, default=5)
    search.add_argument("--include-unapproved", action="store_true")

    parse = subparsers.add_parser("parse-rfp", help="Parse an RFP input into question JSON")
    parse.add_argument("--input", required=True)
    parse.add_argument("--output")

    render_rfp = subparsers.add_parser(
        "render-rfp-markdown",
        help="Convert an RFP into structured markdown with related question mapping",
    )
    render_rfp.add_argument("--input", required=True)
    render_rfp.add_argument("--output")

    build_docs = subparsers.add_parser(
        "build-knowledge-markdown",
        help="Build structured markdown documents and domain packs from the mirrored corpus",
    )
    build_docs.add_argument("--corpus-dir")
    build_docs.add_argument("--output-dir")
    build_docs.add_argument("--config")
    build_docs.add_argument("--folder-key", default="truth_source", choices=["truth_source", "update_inbox"])

    structure = subparsers.add_parser(
        "describe-sharepoint-structure",
        help="Render the expected SharePoint folder structure and business-action mapping",
    )
    structure.add_argument("--config", required=True)
    structure.add_argument("--output-dir", default="data/outputs")

    analysis_plan = subparsers.add_parser(
        "plan-document-analysis",
        help="Group mirrored documents by type and assign specialist analysis agents",
    )
    analysis_plan.add_argument("--corpus-dir", default="data/truth-source")
    analysis_plan.add_argument("--output-dir", default="data/outputs")

    refresh = subparsers.add_parser(
        "prepare-source-refresh",
        help="Compare update-inbox content with true-source content and build a refresh report",
    )
    refresh.add_argument("--config", required=True)
    refresh.add_argument("--output-dir", default="data/outputs")

    promote = subparsers.add_parser(
        "promote-source-refresh",
        help="Promote reviewed refresh candidates into the local true-source corpus",
    )
    promote.add_argument("--config", required=True)
    promote.add_argument("--candidate-id", action="append", required=True)
    promote.add_argument("--output-dir", default="data/outputs")

    response_index = subparsers.add_parser(
        "render-response-index",
        help="Build a structured response index from an RFP",
    )
    response_index.add_argument("--input", required=True)
    response_index.add_argument("--output")
    response_index.add_argument("--format", default="markdown", choices=["markdown", "json"])

    draft = subparsers.add_parser("draft-answers", help="Generate answer contracts from an RFP")
    draft.add_argument("--input", required=True)
    draft.add_argument("--corpus-dir", default="data/truth-source")
    draft.add_argument("--output")
    draft.add_argument("--format", default="json", choices=["json", "markdown", "csv"])

    package = subparsers.add_parser("package-answers", help="Render stored answers to another format")
    package.add_argument("--input", required=True)
    package.add_argument("--output")
    package.add_argument("--format", default="markdown", choices=["json", "markdown", "csv"])

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "sync":
        config = SyncConfig.from_file(args.config)
        result = SharePointSyncService(config, folder_key=args.folder_key).sync(full_resync=args.full_resync)
        print(json.dumps(result.to_dict(), indent=2))
        return
    if args.command == "search-corpus":
        corpus = CorpusStore(args.corpus_dir)
        hits = corpus.search(
            args.query,
            limit=args.limit,
            approved_only=not args.include_unapproved,
        )
        print(json.dumps([hit.to_dict() for hit in hits], indent=2))
        return
    if args.command == "parse-rfp":
        bid = parse_rfp_file(args.input)
        payload = json.dumps(bid.to_dict(), indent=2)
        if args.output:
            Path(args.output).write_text(payload, encoding="utf-8")
        print(payload)
        return
    if args.command == "render-rfp-markdown":
        bid = parse_rfp_file(args.input)
        rendered = render_rfp_markdown(bid)
        if args.output:
            Path(args.output).parent.mkdir(parents=True, exist_ok=True)
            Path(args.output).write_text(rendered, encoding="utf-8")
        print(rendered)
        return
    if args.command == "build-knowledge-markdown":
        if args.corpus_dir:
            corpus = CorpusStore(args.corpus_dir)
        elif args.config:
            config = SyncConfig.from_file(args.config, allow_missing_secret=True)
            corpus = CorpusStore(config.corpus_dir_for(args.folder_key))
        else:
            parser.error("build-knowledge-markdown requires either --corpus-dir or --config")
        result = build_markdown_knowledge_base(corpus, output_dir=args.output_dir)
        print(json.dumps(result.to_dict(), indent=2))
        return
    if args.command == "describe-sharepoint-structure":
        config = SyncConfig.from_file(args.config, allow_missing_secret=True)
        result = build_sharepoint_structure_plan(
            config.sharepoint_structure,
            output_dir=args.output_dir,
        )
        print(json.dumps(result.to_dict(), indent=2))
        return
    if args.command == "plan-document-analysis":
        corpus = CorpusStore(args.corpus_dir)
        result = build_document_analysis_plan(corpus, output_dir=args.output_dir)
        print(json.dumps(result.to_dict(), indent=2))
        return
    if args.command == "prepare-source-refresh":
        config = SyncConfig.from_file(args.config, allow_missing_secret=True)
        result = SourceRefreshService(config).build_refresh_plan(output_dir=args.output_dir)
        print(json.dumps(result.to_dict(), indent=2))
        return
    if args.command == "promote-source-refresh":
        config = SyncConfig.from_file(args.config, allow_missing_secret=True)
        result = SourceRefreshService(config).promote_candidates(
            args.candidate_id,
            output_dir=args.output_dir,
        )
        print(json.dumps(result.to_dict(), indent=2))
        return
    if args.command == "render-response-index":
        bid = parse_rfp_file(args.input)
        rendered = (
            render_response_index_json(bid)
            if args.format == "json"
            else render_response_index_markdown(bid)
        )
        if args.output:
            Path(args.output).parent.mkdir(parents=True, exist_ok=True)
            Path(args.output).write_text(rendered, encoding="utf-8")
        print(rendered)
        return
    if args.command == "draft-answers":
        bid = parse_rfp_file(args.input)
        corpus = CorpusStore(args.corpus_dir)
        answers = draft_answers_for_bid(bid, corpus)
        rendered = package_answers(answers, output_format=args.format)
        if args.output:
            Path(args.output).write_text(rendered, encoding="utf-8")
        print(rendered)
        return
    if args.command == "package-answers":
        answers = _load_answers(args.input)
        rendered = package_answers(answers, output_format=args.format)
        if args.output:
            Path(args.output).write_text(rendered, encoding="utf-8")
        print(rendered)
        return
    parser.error("Unknown command")


def _load_answers(path: str | Path) -> list[AnswerContract]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return [AnswerContract.from_dict(item) for item in payload]


if __name__ == "__main__":
    main()
