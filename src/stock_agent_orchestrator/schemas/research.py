from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Candidate:
    name: str
    code: str
    price: float
    rsi: float
    day_change: str
    reason: str


@dataclass(slots=True)
class CandidatePoolSnapshot:
    source_path: str
    as_of: str
    candidates: list[Candidate] = field(default_factory=list)


@dataclass(slots=True)
class SevenLayerCard:
    name: str
    code: str
    layer_1_market: str
    layer_2_rsi: str
    layer_3_financials: str
    layer_4_fund_flow: str
    layer_5_catalysts: str
    layer_6_theme: str
    layer_7_risks: str


@dataclass(slots=True)
class RuleUpdateSuggestion:
    title: str
    description: str
    requires_user_review: bool
    evidence: list[str] = field(default_factory=list)

