import re
from dataclasses import dataclass
from typing import Dict, Tuple, Optional

TYPES = ("biography", "institution", "law", "event")

# --- heuristic patterns (Wikipedia titles) ---
BIO_HINTS = [
    # bio pages are usually just a name, so we detect *non*-bio via strong non-bio signals
]

INSTITUTION_PATTERNS = [
    r"\bDepartment\b",
    r"\bMinistry\b",
    r"\bAgency\b",
    r"\bBureau\b",
    r"\bCommission\b",
    r"\bCommittee\b",
    r"\bCouncil\b",
    r"\bCourt\b",
    r"\bCongress\b",
    r"\bParliament\b",
    r"\bSenate\b",
    r"\bHouse of Representatives\b",
    r"\bSupreme Court\b",
    r"\bWhite House\b",
    r"\bCabinet\b",
    r"\bFBI\b",
    r"\bCIA\b",
    r"\bNSA\b",
    r"\bPentagon\b",
    r"\bDemocratic Party\b",
    r"\bRepublican Party\b",
    r"\bLabour Party\b",
    r"\bConservative Party\b",
    r"\bGovernment\b",
    r"\bAdministration\b",
]

LAW_POLICY_PATTERNS = [
    r"\bAct\b",
    r"\bBill\b",
    r"\bLaw\b",
    r"\bAmendment\b",
    r"\bTreaty\b",
    r"\bExecutive Order\b",
    r"\bRegulation\b",
    r"\bPolicy\b",
    r"\bAffordable Care Act\b",
    r"\bCivil Rights Act\b",
    r"\bPatriot Act\b",
    r"\bVoting Rights Act\b",
]

EVENT_PATTERNS = [
    r"\bElection\b",
    r"\bPresidential election\b",
    r"\bMidterm elections\b",
    r"\bInauguration\b",
    r"\bImpeachment\b",
    r"\bTrial\b",
    r"\bProtest\b",
    r"\bRiot\b",
    r"\bAttack\b",
    r"\bCoup\b",
    r"\bWar\b",
    r"\bConflict\b",
    r"\bCrisis\b",
    r"\bSummit\b",
    r"\bDebate\b",
    r"\bConvention\b",
    r"\bscandal\b",
    r"\binvestigation\b",
    r"\b\d{4}\b",  # year in title is a strong event hint
]


@dataclass
class TypeResult:
    type: str
    confidence: float
    evidence: str


def _match_any(title: str, patterns) -> Optional[str]:
    for p in patterns:
        if re.search(p, title, flags=re.IGNORECASE):
            return p
    return None


def classify_title(title: str) -> TypeResult:
    """
    Rule-based classifier to label titles into:
    biography / institution / law / event
    Returns confidence + evidence for auditability.
    """
    t = title.strip()

    # Strong signals first
    m = _match_any(t, LAW_POLICY_PATTERNS)
    if m:
        return TypeResult(type="law", confidence=0.90, evidence=f"title_match:{m}")

    m = _match_any(t, EVENT_PATTERNS)
    if m:
        return TypeResult(type="event", confidence=0.85, evidence=f"title_match:{m}")

    m = _match_any(t, INSTITUTION_PATTERNS)
    if m:
        return TypeResult(
            type="institution", confidence=0.85, evidence=f"title_match:{m}"
        )

    # Biography is the default bucket for person-name titles
    # Heuristic: if it looks like a name (2-4 tokens, mostly capitalized, no commas/parentheses)
    tokens = [x for x in re.split(r"\s+", t) if x]
    if 1 < len(tokens) <= 4 and not any(ch in t for ch in [",", "(", ")", ":"]):
        # many biographies fit this; still not perfect, so confidence moderate
        return TypeResult(
            type="biography", confidence=0.70, evidence="default_name_like_title"
        )

    # fallback: institution-ish (generic political topic)
    return TypeResult(type="institution", confidence=0.55, evidence="fallback_generic")
