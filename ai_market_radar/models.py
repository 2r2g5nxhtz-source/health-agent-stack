from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Optional


@dataclass(frozen=True)
class RawDocument:
    id: str
    source_id: str
    source_url: str
    title: str
    raw_text: str
    published_at: Optional[str] = None


@dataclass(frozen=True)
class StructuredEventRecord:
    id: str
    raw_document_id: str
    service_slug: str
    event_type: str
    event_class: str
    title: str
    description: Optional[str]
    plan_name: Optional[str]
    model_name: Optional[str]
    region: Optional[str]
    old_value: Optional[Decimal]
    new_value: Optional[Decimal]
    currency: Optional[str]
    start_date: Optional[str]
    end_date: Optional[str]
    source_url: str
    gpt_confidence: Decimal
    source_confidence: Decimal
    final_confidence: Decimal
    evidence: list[str] = field(default_factory=list)
    detector_version: str = "v1"
    canonical_key: Optional[str] = None
    processing_status: str = "extracted"


@dataclass(frozen=True)
class RejectedEventRecord:
    raw_document_id: str
    service_slug: Optional[str]
    source_url: Optional[str]
    rejection_reason: str
    rejection_details: dict[str, Any]


@dataclass(frozen=True)
class FinalEventRecord:
    id: str
    canonical_key: str
    service_slug: str
    event_type: str
    event_class: str
    title: str
    description: Optional[str]
    old_value: Optional[Decimal]
    new_value: Optional[Decimal]
    currency: Optional[str]
    source_url: str
    confidence: Decimal
    event_status: str
    version: int
