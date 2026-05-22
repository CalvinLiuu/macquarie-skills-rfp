from __future__ import annotations

import csv
import io
import json
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from .models import BidRequest, Question
from .taxonomy import enrich_question_relationships, infer_bid_client_segments


QUESTION_LINE = re.compile(r"^(?:q(?:uestion)?\s*)?(\d{1,3})[\].): -]+(.+)$", re.IGNORECASE)
DEADLINE_LINE = re.compile(
    r"(?:(?:submission|response|proposal)\s+)?(?:deadline|due date|submit by)[: ]+(.+)$",
    re.IGNORECASE,
)
DELIVERABLE_LINE = re.compile(r"^(?:-|[*])\s+(.+)$")


class UnsupportedFormatError(RuntimeError):
    pass


def parse_rfp_file(path: str | Path) -> BidRequest:
    file_path = Path(path)
    return parse_rfp_text(
        extract_text_from_path(file_path),
        source_path=str(file_path),
        title=file_path.stem.replace("-", " ").title(),
    )


def parse_rfp_text(text: str, source_path: str = "", title: str = "") -> BidRequest:
    target_client_segments = infer_bid_client_segments(title, text)
    questions = extract_questions(text)
    enrich_question_relationships(questions, bid_client_segments=target_client_segments)
    deadlines = extract_deadlines(text)
    deliverables = extract_deliverables(text)
    return BidRequest(
        source_path=source_path,
        questions=questions,
        deadlines=deadlines,
        deliverables=deliverables,
        title=title,
        target_client_segments=target_client_segments,
    )


def extract_text_from_path(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md"}:
        return path.read_text(encoding="utf-8")
    if suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        return json.dumps(payload, indent=2)
    if suffix in {".csv", ".tsv"}:
        delimiter = "\t" if suffix == ".tsv" else ","
        return _table_to_text(path.read_text(encoding="utf-8"), delimiter)
    if suffix == ".docx":
        return _extract_docx_text(path.read_bytes())
    if suffix == ".pdf":
        return _extract_pdf_text(path.read_bytes())
    raise UnsupportedFormatError(f"Unsupported RFP format: {path.suffix}")


def extract_text_from_binary(filename: str, content: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix in {".txt", ".md"}:
        return content.decode("utf-8", errors="ignore")
    if suffix == ".json":
        return json.dumps(json.loads(content.decode("utf-8", errors="ignore")), indent=2)
    if suffix in {".csv", ".tsv"}:
        delimiter = "\t" if suffix == ".tsv" else ","
        return _table_to_text(content.decode("utf-8", errors="ignore"), delimiter)
    if suffix == ".docx":
        return _extract_docx_text(content)
    if suffix == ".pdf":
        return _extract_pdf_text(content)
    raise UnsupportedFormatError(f"Unsupported evidence format: {suffix}")


def extract_questions(text: str) -> list[Question]:
    candidates: list[str] = []
    current: list[str] = []
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines:
        if QUESTION_LINE.match(line):
            if current:
                candidates.append(" ".join(current).strip())
            current = [line]
            continue
        if current:
            if line.lower().startswith(("attachments", "deliverables", "submission deadline")):
                candidates.append(" ".join(current).strip())
                current = []
                continue
            if QUESTION_LINE.match(line):
                candidates.append(" ".join(current).strip())
                current = [line]
                continue
            current.append(line)
            continue
        if line.endswith("?"):
            candidates.append(line)
    if current:
        candidates.append(" ".join(current).strip())
    if not candidates:
        blocks = [block.strip() for block in re.split(r"\n\s*\n", text) if block.strip()]
        for block in blocks:
            if block.endswith("?"):
                candidates.append(block)
    questions: list[Question] = []
    for index, candidate in enumerate(candidates, start=1):
        normalized = " ".join(candidate.split())
        match = QUESTION_LINE.match(normalized)
        question_id = f"Q{index:03d}"
        question_text = normalized
        if match:
            question_id = f"Q{int(match.group(1)):03d}"
            question_text = match.group(2).strip()
        question_type = infer_question_type(question_text)
        questions.append(
            Question(
                question_id=question_id,
                question_text=question_text,
                question_type=question_type,
            )
        )
    return questions


def infer_question_type(text: str) -> str:
    lower = text.lower()
    if any(token in lower for token in ("security", "iso", "soc", "control", "certification")):
        return "security"
    if any(token in lower for token in ("commercial", "price", "pricing", "fee")):
        return "commercial"
    if any(token in lower for token in ("transition", "delivery", "approach", "architecture", "hosting")):
        return "technical"
    if any(token in lower for token in ("team", "staff", "personnel", "cv", "resume")):
        return "staffing"
    return "general"


def extract_deadlines(text: str) -> list[str]:
    results: list[str] = []
    for line in text.splitlines():
        match = DEADLINE_LINE.search(line.strip())
        if match:
            results.append(match.group(1).strip())
    return results


def extract_deliverables(text: str) -> list[str]:
    deliverables: list[str] = []
    attachment_mode = False
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if "attachment" in stripped.lower() or "deliverable" in stripped.lower():
            attachment_mode = True
            continue
        if attachment_mode:
            match = DELIVERABLE_LINE.match(stripped)
            if match:
                deliverables.append(match.group(1).strip())
            elif ":" in stripped:
                attachment_mode = False
    return deliverables


def _table_to_text(content: str, delimiter: str) -> str:
    reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)
    lines: list[str] = []
    for index, row in enumerate(reader, start=1):
        joined = "; ".join(f"{key}: {value}" for key, value in row.items() if value)
        lines.append(f"Row {index}: {joined}")
    if lines:
        return "\n".join(lines)
    return content


def _extract_docx_text(content: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        document_xml = archive.read("word/document.xml")
    root = ElementTree.fromstring(document_xml)
    parts: list[str] = []
    for node in root.iter():
        if node.tag.endswith("}t") and node.text:
            parts.append(node.text)
        if node.tag.endswith("}p"):
            parts.append("\n")
    return " ".join("".join(parts).split())


def _extract_pdf_text(content: bytes) -> str:
    if not shutil.which("pdftotext"):
        raise UnsupportedFormatError(
            "PDF extraction requires the `pdftotext` command or a pre-converted text export."
        )
    with tempfile.NamedTemporaryFile(suffix=".pdf") as source, tempfile.NamedTemporaryFile(
        suffix=".txt"
    ) as target:
        source.write(content)
        source.flush()
        subprocess.run(
            ["pdftotext", source.name, target.name],
            check=True,
            capture_output=True,
            text=True,
        )
        return Path(target.name).read_text(encoding="utf-8", errors="ignore")
