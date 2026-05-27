from __future__ import annotations

import csv
import dataclasses
import io
import json
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from .models import BidRequest, Question, RequirementItem
from .taxonomy import enrich_question_relationships, infer_bid_client_segments, infer_response_format


QUESTION_LINE = re.compile(r"^(?:q(?:uestion)?\s*)?(\d{1,3})[\].): -]+(.+)$", re.IGNORECASE)
DEADLINE_LINE = re.compile(
    r"(?:(?:submission|response|proposal)\s+)?(?:deadline|due date|submit by)[: ]+(.+)$",
    re.IGNORECASE,
)
DELIVERABLE_LINE = re.compile(r"^(?:-|[*])\s+(.+)$")
ACTION_VERBS = (
    "describe",
    "provide",
    "outline",
    "explain",
    "detail",
    "submit",
    "include",
    "attach",
    "complete",
    "confirm",
    "list",
    "specify",
    "demonstrate",
    "summarize",
)
REQUIREMENT_PHRASES = (
    "must ",
    "shall ",
    "is required to",
    "are required to",
    "please provide",
    "response must",
    "supplier must",
    "bidder must",
)


@dataclasses.dataclass
class _CandidateBlock:
    text: str
    section: str
    line_start: int
    line_end: int


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
    requirement_items = extract_requirement_items(text)
    questions = _build_questions(requirement_items)
    enrich_question_relationships(questions, bid_client_segments=target_client_segments)
    deadlines = [item.prompt_text for item in requirement_items if item.item_type == "deadline"]
    deliverables = [item.prompt_text for item in requirement_items if item.item_type == "deliverable"]
    return BidRequest(
        source_path=source_path,
        questions=questions,
        requirement_items=requirement_items,
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


def extract_requirement_items(text: str) -> list[RequirementItem]:
    items: list[RequirementItem] = []
    for index, block in enumerate(_extract_candidate_blocks(text), start=1):
        item = _classify_block(block, index)
        if item is not None:
            items.append(item)
    return items


def extract_questions(text: str) -> list[Question]:
    return _build_questions(extract_requirement_items(text))


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
    return [item.prompt_text for item in extract_requirement_items(text) if item.item_type == "deadline"]


def extract_deliverables(text: str) -> list[str]:
    return [item.prompt_text for item in extract_requirement_items(text) if item.item_type == "deliverable"]


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
    namespaces = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs: list[str] = []
    for paragraph in root.findall(".//w:p", namespaces):
        texts = [node.text for node in paragraph.findall(".//w:t", namespaces) if node.text]
        joined = "".join(texts).strip()
        if joined:
            paragraphs.append(joined)
    return "\n".join(paragraphs)


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


def _build_questions(requirement_items: list[RequirementItem]) -> list[Question]:
    questions: list[Question] = []
    used_ids: set[str] = set()
    action_items = [
        item for item in requirement_items if item.item_type in {"question", "instruction", "statement"}
    ]
    for index, item in enumerate(action_items, start=1):
        question_id = _next_question_id(item.original_text, index, used_ids)
        used_ids.add(question_id)
        questions.append(
            Question(
                question_id=question_id,
                question_text=item.prompt_text,
                section=item.section,
                question_type=infer_question_type(item.prompt_text),
            )
        )
    return questions


def _extract_candidate_blocks(text: str) -> list[_CandidateBlock]:
    blocks: list[_CandidateBlock] = []
    current_lines: list[str] = []
    current_start = 0
    current_section = ""
    active_section = ""

    def flush_current(line_end: int) -> None:
        nonlocal current_lines, current_start, current_section
        if not current_lines:
            return
        blocks.append(
            _CandidateBlock(
                text=" ".join(current_lines).strip(),
                section=current_section,
                line_start=current_start,
                line_end=line_end,
            )
        )
        current_lines = []
        current_start = 0
        current_section = ""

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped:
            flush_current(line_number - 1)
            continue
        if _looks_like_section_heading(stripped):
            flush_current(line_number - 1)
            active_section = stripped.rstrip(":").strip()
            continue
        if DEADLINE_LINE.search(stripped):
            flush_current(line_number - 1)
            blocks.append(
                _CandidateBlock(
                    text=stripped,
                    section=active_section,
                    line_start=line_number,
                    line_end=line_number,
                )
            )
            continue
        if _starts_new_item(stripped):
            flush_current(line_number - 1)
            current_lines = [stripped]
            current_start = line_number
            current_section = active_section
            continue
        if current_lines and _looks_like_actionable_line(stripped):
            flush_current(line_number - 1)
            current_lines = [stripped]
            current_start = line_number
            current_section = active_section
            continue
        if current_lines:
            current_lines.append(stripped)
            continue
        if _looks_like_actionable_line(stripped):
            current_lines = [stripped]
            current_start = line_number
            current_section = active_section
    flush_current(len(text.splitlines()))
    return blocks


def _classify_block(block: _CandidateBlock, index: int) -> RequirementItem | None:
    normalized = " ".join(block.text.split())
    if not normalized:
        return None
    item_type = _detect_item_type(normalized, block.section)
    if item_type is None:
        return None
    prompt_text = _prompt_text_for_item(normalized, item_type)
    confidence = "medium"
    if item_type in {"deadline", "deliverable"}:
        confidence = "high"
    elif QUESTION_LINE.match(normalized) or normalized.endswith("?"):
        confidence = "high"
    elif _looks_like_actionable_line(normalized):
        confidence = "medium"
    return RequirementItem(
        item_id=f"R{index:03d}",
        item_type=item_type,
        prompt_text=prompt_text,
        original_text=block.text,
        section=block.section,
        line_start=block.line_start,
        line_end=block.line_end,
        mandatory=_is_mandatory(prompt_text),
        response_format=_response_format_for_item(item_type, prompt_text),
        extraction_confidence=confidence,
    )


def _detect_item_type(text: str, section: str) -> str | None:
    content = _strip_bullet_prefix(text)
    numbered_match = QUESTION_LINE.match(content)
    if numbered_match:
        content = numbered_match.group(2).strip()
    if DEADLINE_LINE.search(text):
        return "deadline"
    if _is_deliverable_context(section) and DELIVERABLE_LINE.match(text):
        return "deliverable"
    if _looks_like_instruction(content):
        return "instruction"
    if _looks_like_requirement_statement(content):
        return "statement"
    if _looks_like_question(content):
        return "question"
    return None


def _prompt_text_for_item(text: str, item_type: str) -> str:
    if item_type == "deadline":
        match = DEADLINE_LINE.search(text)
        return match.group(1).strip() if match else text
    if item_type == "deliverable":
        match = DELIVERABLE_LINE.match(text)
        return match.group(1).strip() if match else text
    stripped = _strip_bullet_prefix(text)
    match = QUESTION_LINE.match(stripped)
    if match:
        return match.group(2).strip()
    return stripped.strip()


def _response_format_for_item(item_type: str, prompt_text: str) -> str:
    if item_type == "deadline":
        return "date"
    if item_type == "deliverable":
        return "attachment"
    return infer_response_format(prompt_text)


def _looks_like_question(text: str) -> bool:
    return bool(QUESTION_LINE.match(text) or text.endswith("?"))


def _looks_like_instruction(text: str) -> bool:
    lower = text.lower()
    return any(lower.startswith(f"{verb} ") for verb in ACTION_VERBS)


def _looks_like_requirement_statement(text: str) -> bool:
    lower = text.lower()
    return any(phrase in lower for phrase in REQUIREMENT_PHRASES)


def _looks_like_actionable_line(text: str) -> bool:
    return _looks_like_question(text) or _looks_like_instruction(text) or _looks_like_requirement_statement(text)


def _starts_new_item(text: str) -> bool:
    return bool(QUESTION_LINE.match(text) or DELIVERABLE_LINE.match(text) or text.endswith("?"))


def _looks_like_section_heading(text: str) -> bool:
    lower = text.lower()
    if text.endswith(":"):
        return True
    if lower.startswith(("section ", "appendix ", "part ")):
        return True
    return text.isupper() and len(text.split()) <= 8


def _is_deliverable_context(section: str) -> bool:
    lower = section.lower()
    return "attachment" in lower or "deliverable" in lower


def _is_mandatory(text: str) -> bool:
    lower = text.lower()
    return any(token in lower for token in ("must", "shall", "required", "mandatory"))


def _next_question_id(original_text: str, default_index: int, used_ids: set[str]) -> str:
    source_number = _source_question_number(original_text)
    if source_number is not None:
        candidate = f"Q{source_number:03d}"
        if candidate not in used_ids:
            return candidate
    candidate = f"Q{default_index:03d}"
    while candidate in used_ids:
        default_index += 1
        candidate = f"Q{default_index:03d}"
    return candidate


def _source_question_number(text: str) -> int | None:
    match = QUESTION_LINE.match(_strip_bullet_prefix(text))
    if not match:
        return None
    return int(match.group(1))


def _strip_bullet_prefix(text: str) -> str:
    match = DELIVERABLE_LINE.match(text)
    if match:
        return match.group(1).strip()
    return text.strip()
