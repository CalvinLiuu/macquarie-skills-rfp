from __future__ import annotations

import re

from .models import Question


DOMAIN_KEYWORDS: dict[str, tuple[str, ...]] = {
    "security": (
        "security",
        "iso 27001",
        "soc 2",
        "cyber",
        "control",
        "certification",
        "iam",
        "encryption",
        "vulnerability",
    ),
    "compliance": (
        "compliance",
        "audit",
        "regulatory",
        "policy",
        "governance",
        "standard",
        "assurance",
        "attestation",
    ),
    "sovereignty": (
        "sovereign",
        "residency",
        "jurisdiction",
        "australia",
        "australian",
        "onshore",
        "data location",
        "data centre location",
    ),
    "power": (
        "power",
        "ups",
        "generator",
        "electrical",
        "utility feed",
        "redundancy",
        "load bank",
    ),
    "cooling": (
        "cooling",
        "hvac",
        "thermal",
        "temperature",
        "chiller",
        "crac",
        "airflow",
    ),
    "network": (
        "network",
        "latency",
        "carrier",
        "bandwidth",
        "connectivity",
        "routing",
        "cross connect",
    ),
    "delivery": (
        "delivery",
        "transition",
        "implementation",
        "migration",
        "cutover",
        "continuity",
        "service continuity",
        "approach",
    ),
    "operations": (
        "operations",
        "support",
        "incident",
        "monitoring",
        "runbook",
        "availability",
        "service desk",
    ),
    "staffing": (
        "team",
        "staff",
        "personnel",
        "cv",
        "resume",
        "resource",
        "architect",
    ),
    "commercial": (
        "commercial",
        "price",
        "pricing",
        "fee",
        "term",
        "contract",
    ),
}

DOMAIN_ORDER = list(DOMAIN_KEYWORDS.keys())
DOMAIN_PACK_PATH_TEMPLATE = "domains/{domain}.md"
CLIENT_SEGMENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "hyperscaler": (
        "hyperscaler",
        "aws",
        "amazon web services",
        "azure",
        "microsoft azure",
        "google cloud",
        "gcp",
        "cloud provider",
    ),
    "startup": (
        "startup",
        "scaleup",
        "early stage",
        "series a",
        "series b",
        "high growth",
        "small business",
        "smb",
    ),
    "enterprise": (
        "enterprise",
        "large enterprise",
        "corporate",
        "multinational",
        "listed company",
        "private enterprise",
    ),
    "government": (
        "government",
        "public sector",
        "department",
        "ministry",
        "agency",
        "federal",
        "state government",
        "local government",
        "council",
    ),
}
CLIENT_SEGMENT_ORDER = list(CLIENT_SEGMENT_KEYWORDS.keys())
CLIENT_SEGMENT_PACK_TEMPLATE = "client-segments/{segment}/{domain}.md"


def detect_domains(*parts: str) -> list[str]:
    text = " ".join(part for part in parts if part).lower()
    matches: list[str] = []
    for domain in DOMAIN_ORDER:
        keywords = DOMAIN_KEYWORDS[domain]
        if any(keyword in text for keyword in keywords):
            matches.append(domain)
    return matches


def detect_client_segments(*parts: str) -> list[str]:
    text = " ".join(part for part in parts if part).lower()
    matches: list[str] = []
    for segment in CLIENT_SEGMENT_ORDER:
        keywords = CLIENT_SEGMENT_KEYWORDS[segment]
        if any(keyword in text for keyword in keywords):
            matches.append(segment)
    return matches


def infer_bid_client_segments(*parts: str) -> list[str]:
    return detect_client_segments(*parts)


def enrich_question_relationships(
    questions: list[Question],
    bid_client_segments: list[str] | None = None,
) -> list[Question]:
    fallback_segments = bid_client_segments or []
    for question in questions:
        domains = detect_domains(question.question_text)
        if not domains:
            fallback = _question_type_to_domain(question.question_type)
            if fallback:
                domains = [fallback]
        segments = detect_client_segments(question.question_text) or fallback_segments
        response_format = infer_response_format(question.question_text)
        guidance_reasons = infer_human_guidance(question, segments, response_format=response_format)
        question.related_domains = domains
        question.related_client_segments = segments
        question.response_format = response_format
        question.human_guidance_required = bool(guidance_reasons)
        question.human_guidance_reasons = guidance_reasons
        question.evidence_hints = build_evidence_hints(domains, segments)

    for question in questions:
        related_ids: list[str] = []
        for other in questions:
            if other.question_id == question.question_id:
                continue
            shared_domains = set(question.related_domains) & set(other.related_domains)
            shared_segments = set(question.related_client_segments) & set(other.related_client_segments)
            if shared_domains or (
                question.question_type == other.question_type and question.question_type != "general"
            ) or shared_segments:
                related_ids.append(other.question_id)
        question.related_question_ids = sorted(set(related_ids))
    return questions


def build_evidence_hints(domains: list[str], client_segments: list[str]) -> list[str]:
    hints: list[str] = []
    if client_segments:
        for segment in client_segments:
            for domain in domains or ["general"]:
                hints.append(CLIENT_SEGMENT_PACK_TEMPLATE.format(segment=segment, domain=domain))
    for domain in domains:
        hints.append(DOMAIN_PACK_PATH_TEMPLATE.format(domain=domain))
    return list(dict.fromkeys(hints))


def infer_response_format(text: str) -> str:
    lower = text.lower()
    if any(token in lower for token in ("attachment", "attach", "case stud", "cv", "resume")):
        return "attachment"
    if any(token in lower for token in ("table", "matrix", "schedule", "spreadsheet", "list all")):
        return "table"
    if any(token in lower for token in ("yes/no", "yes or no", "confirm whether")):
        return "yes-no"
    if any(token in lower for token in ("outline", "describe", "explain", "approach", "provide details")):
        return "narrative"
    return "narrative"


def infer_human_guidance(
    question: Question,
    client_segments: list[str],
    *,
    response_format: str,
) -> list[str]:
    lower = question.question_text.lower()
    reasons: list[str] = []
    if question.question_type == "commercial" or any(
        token in lower for token in ("pricing", "commercial", "fee", "contract", "legal")
    ):
        reasons.append("Commercial or legal review required before final submission.")
    if "government" in client_segments or any(
        token in lower for token in ("government", "public sector", "sovereign", "compliance")
    ):
        reasons.append("Policy and compliance owner should confirm the response.")
    if response_format == "attachment":
        reasons.append("A human should verify the named attachment list and latest document versions.")
    if any(token in lower for token in ("guarantee", "warrant", "commit", "must comply")):
        reasons.append("Commitment language should be reviewed by an accountable owner.")
    return list(dict.fromkeys(reasons))


def summarize_chunk(text: str, max_sentences: int = 2) -> str:
    stripped = " ".join(text.split())
    if not stripped:
        return ""
    sentences = re.split(r"(?<=[.!?])\s+", stripped)
    return " ".join(sentences[:max_sentences]).strip()


def normalize_title_key(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def rank_segment_overlap(left: list[str], right: list[str]) -> int:
    return len(set(left) & set(right))


def rank_domain_overlap(left: list[str], right: list[str]) -> int:
    return len(set(left) & set(right))


def guess_client_segment_from_path(path: str) -> list[str]:
    return detect_client_segments(path)


def _question_type_to_domain(question_type: str) -> str:
    mapping = {
        "security": "security",
        "commercial": "commercial",
        "staffing": "staffing",
        "technical": "delivery",
    }
    return mapping.get(question_type, "")
