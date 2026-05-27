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

DOCUMENT_TYPE_ORDER = [
    "rfp",
    "macquarie_current_state",
    "macquarie_implementation",
    "macquarie_guideline",
    "competitor_brochure",
    "general_knowledge",
]

DOCUMENT_TYPE_LABELS: dict[str, str] = {
    "rfp": "RFP",
    "macquarie_current_state": "Macquarie Current State",
    "macquarie_implementation": "Macquarie Implementation",
    "macquarie_guideline": "Macquarie Guideline",
    "competitor_brochure": "Competitor Brochure",
    "general_knowledge": "General Knowledge",
}

SPECIALIST_AGENT_BY_DOCUMENT_TYPE: dict[str, str] = {
    "rfp": "rfp-requirements-analyst",
    "macquarie_current_state": "macquarie-current-state-analyst",
    "macquarie_implementation": "macquarie-implementation-analyst",
    "macquarie_guideline": "macquarie-guideline-analyst",
    "competitor_brochure": "competitor-brochure-analyst",
    "general_knowledge": "general-knowledge-analyst",
}

DOCUMENT_TYPE_PURPOSE: dict[str, str] = {
    "rfp": "Interpret the tender itself, identify requirement intent, and capture what good and bad answers look like.",
    "macquarie_current_state": "Summarize Macquarie's current estate, incumbent arrangements, and existing constraints.",
    "macquarie_implementation": "Review Macquarie implementation history, recent delivery changes, and lessons learned.",
    "macquarie_guideline": "Extract Macquarie guardrails, standards, policies, and approval boundaries.",
    "competitor_brochure": "Assess competitor positioning, brochure claims, and differentiators to sharpen bid strategy.",
    "general_knowledge": "Capture reusable product, service, and capability evidence that does not fit a specialist lane.",
}

DOCUMENT_ANALYSIS_FOCUS: dict[str, list[str]] = {
    "rfp": [
        "Mandatory requirements and evaluation criteria.",
        "What prior responses did well or poorly against similar asks.",
        "Attachments, deadlines, and answer-format constraints.",
    ],
    "macquarie_current_state": [
        "Current platforms, operating model, and incumbent services.",
        "Known pain points, dependencies, and transition constraints.",
        "Signals that explain why the RFP exists now.",
    ],
    "macquarie_implementation": [
        "Recent implementation choices, rollout outcomes, and delivery lessons.",
        "Technology changes that should shape the proposed solution.",
        "Operational implications of new platforms or migrations.",
    ],
    "macquarie_guideline": [
        "Non-negotiable standards, policies, and governance controls.",
        "Approval points, compliance obligations, and mandatory wording boundaries.",
        "Artifacts or evidence that Macquarie expects suppliers to provide.",
    ],
    "competitor_brochure": [
        "Competitor claims, capability themes, and marketing emphasis.",
        "Strengths to counter, gaps to exploit, and differentiators to emphasize.",
        "Reusable market language that should not be copied as fact without validation.",
    ],
    "general_knowledge": [
        "Reusable service evidence and factual capability statements.",
        "Source freshness, ownership, and bid approval status.",
    ],
}

DOCUMENT_TYPE_ALIASES: dict[str, str] = {
    "request_for_proposal": "rfp",
    "request_for_tender": "rfp",
    "tender": "rfp",
    "rfq": "rfp",
    "macquarie_current": "macquarie_current_state",
    "current_state": "macquarie_current_state",
    "existing_state": "macquarie_current_state",
    "macquarie_existing_state": "macquarie_current_state",
    "macquarie_current_state": "macquarie_current_state",
    "macquarie_implementation": "macquarie_implementation",
    "implementation": "macquarie_implementation",
    "macquarie_guideline": "macquarie_guideline",
    "guideline": "macquarie_guideline",
    "policy": "macquarie_guideline",
    "competitor": "competitor_brochure",
    "competitor_brochure": "competitor_brochure",
    "brochure": "competitor_brochure",
    "general": "general_knowledge",
    "general_knowledge": "general_knowledge",
}


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


def normalize_document_type(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return DOCUMENT_TYPE_ALIASES.get(slug, slug if slug in DOCUMENT_TYPE_LABELS else "general_knowledge")


def detect_document_type(*parts: str, metadata_value: str = "") -> str:
    if metadata_value:
        normalized = normalize_document_type(metadata_value)
        if normalized in DOCUMENT_TYPE_LABELS:
            return normalized

    text = " ".join(part for part in parts if part).lower()
    mentions_macquarie = "macquarie" in text
    mentions_competitor = any(token in text for token in ("competitor", "comparison", "benchmark", "alternative"))

    if _contains_any(
        text,
        (
            "request for proposal",
            "request for tender",
            "rfp",
            "rfq",
            "tender response",
            "supplier questionnaire",
            "bid questionnaire",
            "pricing schedule",
        ),
    ):
        return "rfp"
    if _contains_any(text, ("current state", "current environment", "existing environment", "as is", "baseline", "incumbent", "existing estate")):
        return "macquarie_current_state" if mentions_macquarie or "/current-state/" in text else "general_knowledge"
    if _contains_any(text, ("implementation", "migration", "rollout", "deployment", "cutover", "transition", "uplift", "modernisation", "modernization")):
        return "macquarie_implementation" if mentions_macquarie else "general_knowledge"
    if _contains_any(text, ("guideline", "policy", "standard", "playbook", "guardrail", "governance", "framework", "principle")):
        return "macquarie_guideline" if mentions_macquarie else "general_knowledge"
    if mentions_competitor and _contains_any(
        text,
        (
            "brochure",
            "datasheet",
            "data sheet",
            "capability statement",
            "capability deck",
            "sales deck",
            "product sheet",
            "service overview",
            "solution overview",
            "flyer",
        ),
    ):
        return "competitor_brochure"
    if mentions_macquarie:
        if "guideline" in text or "policy" in text or "standard" in text:
            return "macquarie_guideline"
        if "implementation" in text or "migration" in text or "rollout" in text:
            return "macquarie_implementation"
        if "current" in text or "existing" in text:
            return "macquarie_current_state"
    return "general_knowledge"


def document_type_label(document_type: str) -> str:
    return DOCUMENT_TYPE_LABELS.get(document_type, document_type.replace("_", " ").title())


def specialist_agent_for_document_type(document_type: str) -> str:
    normalized = normalize_document_type(document_type)
    return SPECIALIST_AGENT_BY_DOCUMENT_TYPE.get(normalized, "general-knowledge-analyst")


def document_type_purpose(document_type: str) -> str:
    normalized = normalize_document_type(document_type)
    return DOCUMENT_TYPE_PURPOSE.get(
        normalized,
        DOCUMENT_TYPE_PURPOSE["general_knowledge"],
    )


def analysis_focus_for_document_type(document_type: str) -> list[str]:
    normalized = normalize_document_type(document_type)
    return list(DOCUMENT_ANALYSIS_FOCUS.get(normalized, DOCUMENT_ANALYSIS_FOCUS["general_knowledge"]))


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


def _contains_any(text: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in text for phrase in phrases)


def _question_type_to_domain(question_type: str) -> str:
    mapping = {
        "security": "security",
        "commercial": "commercial",
        "staffing": "staffing",
        "technical": "delivery",
    }
    return mapping.get(question_type, "")
