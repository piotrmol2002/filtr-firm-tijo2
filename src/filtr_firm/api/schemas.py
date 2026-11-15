from datetime import date

from pydantic import BaseModel, Field

from filtr_firm.db.models import CompanyRow
from filtr_firm.db.repository import CompanyPage
from filtr_firm.domain.company import CompanyFacts, LegalForm, Source
from filtr_firm.domain.company_filter import DEFAULT_LIMIT, MAX_LIMIT
from filtr_firm.domain.criteria import ProfileCriteria
from filtr_firm.domain.prefilter import Verdict


class CompanyOut(BaseModel):
    """Contact values stay in the store: a list shows whether a contact exists, not what it is."""

    id: int
    source: Source
    name: str
    legal_form: LegalForm
    voivodeship: str | None
    city: str | None
    pkd_main: str | None
    pkd_codes: list[str]
    event_date: date | None
    has_phone: bool
    has_email: bool

    @classmethod
    def from_row(cls, row: CompanyRow) -> "CompanyOut":
        return cls(
            id=row.id,
            source=Source(row.source),
            name=row.name,
            legal_form=LegalForm(row.legal_form),
            voivodeship=row.voivodeship,
            city=row.city,
            pkd_main=row.pkd_main,
            pkd_codes=list(row.pkd_codes),
            event_date=row.event_date,
            has_phone=bool((row.phone or "").strip()),
            has_email=bool((row.email or "").strip()),
        )


class CompanyPageOut(BaseModel):
    items: list[CompanyOut]
    total: int
    limit: int
    offset: int

    @classmethod
    def from_page(cls, page: CompanyPage) -> "CompanyPageOut":
        return cls(
            items=[CompanyOut.from_row(row) for row in page.items],
            total=page.total,
            limit=page.limit,
            offset=page.offset,
        )


class CompanyIn(BaseModel):
    name: str = Field(min_length=1)
    source: Source
    legal_form: LegalForm
    voivodeship: str | None = None
    city: str | None = None
    pkd_main: str | None = None
    pkd_codes: list[str] = []
    event_date: date | None = None

    def to_facts(self) -> CompanyFacts:
        return CompanyFacts(
            name=self.name,
            source=self.source,
            legal_form=self.legal_form,
            voivodeship=self.voivodeship,
            city=self.city,
            pkd_main=self.pkd_main,
            pkd_codes=tuple(self.pkd_codes),
            event_date=self.event_date,
        )


class EvaluateIn(BaseModel):
    company: CompanyIn
    criteria: ProfileCriteria
    reference_date: date | None = None


class VerdictOut(BaseModel):
    passed: bool
    reasons: list[str]

    @classmethod
    def from_verdict(cls, verdict: Verdict) -> "VerdictOut":
        return cls(passed=verdict.passed, reasons=list(verdict.reasons))


class PreviewIn(BaseModel):
    criteria: ProfileCriteria
    reference_date: date | None = None
    limit: int = Field(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT)
    offset: int = Field(default=0, ge=0)
