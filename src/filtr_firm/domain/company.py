from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class Source(StrEnum):
    CEIDG = "ceidg"
    KRS = "krs"


class LegalForm(StrEnum):
    JDG = "jdg"
    SP_ZOO = "sp_zoo"
    PSA = "psa"
    SA = "sa"
    SK = "sk"
    SKA = "ska"
    SJ = "sj"
    SP = "sp"
    SPOLDZIELNIA = "spoldzielnia"
    OTHER = "other"


@dataclass(frozen=True)
class CompanyFacts:
    """What the pre-filter knows about one company.

    `event_date` is the start of business for CEIDG and the registration date for KRS, the one date
    both registries publish for a new entity.
    """

    name: str
    source: Source
    legal_form: LegalForm
    voivodeship: str | None
    city: str | None
    pkd_main: str | None
    pkd_codes: tuple[str, ...]
    event_date: date | None
