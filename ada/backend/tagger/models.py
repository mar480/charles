from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
import uuid


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


@dataclass
class ProjectRecord:
    id: str
    status: str = "draft"
    template_id: str | None = None
    filing_profile: str = "companies-house-microentity"
    taxonomy_year: str = "2024"
    taxonomy_entrypoint: str = "https://xbrl.frc.org.uk/FRS-102/2024-01-01/FRS-102-2024-01-01.xsd"
    company_snapshot: dict[str, Any] = field(default_factory=dict)
    defaults: dict[str, Any] = field(default_factory=dict)
    fields: dict[str, Any] = field(default_factory=dict)
    facts: dict[str, Any] = field(default_factory=dict)
    validation_runs: list[dict[str, Any]] = field(default_factory=list)
    exports: list[dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "status": self.status,
            "templateId": self.template_id,
            "filingProfile": self.filing_profile,
            "taxonomyYear": self.taxonomy_year,
            "taxonomyEntrypoint": self.taxonomy_entrypoint,
            "companySnapshot": self.company_snapshot,
            "defaults": self.defaults,
            "fields": self.fields,
            "facts": self.facts,
            "validationRuns": self.validation_runs,
            "exports": self.exports,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
        }

