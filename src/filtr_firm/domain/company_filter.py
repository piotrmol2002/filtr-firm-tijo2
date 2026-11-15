"""What a caller asks the company store for.

Every rule lives here, so the route validates once, the repository builds a WHERE clause and
nothing re-checks anything. There is deliberately no name search: a sole trader's company name is a
person's name, which has no business in a query string.
"""

from dataclasses import dataclass
from datetime import date

from filtr_firm.domain.company import LegalForm, Source
from filtr_firm.domain.pkd import normalise_code

DEFAULT_LIMIT = 50
MAX_LIMIT = 500


@dataclass(frozen=True)
class CompanyFilter:
    source: tuple[Source, ...] = ()
    pkd: tuple[str, ...] = ()
    voivodeship: tuple[str, ...] = ()
    legal_form: tuple[LegalForm, ...] = ()
    start_from: date | None = None
    start_to: date | None = None
    has_phone: bool | None = None
    has_email: bool | None = None
    # The SQL twin of the verdict rule that an unknown date passes when no age bound is set.
    include_undated: bool = False
    limit: int = DEFAULT_LIMIT
    offset: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "pkd", tuple(normalise_code(value) for value in self.pkd))
        # CEIDG stores mixed case and KRS upper case, so comparison is case insensitive.
        object.__setattr__(
            self, "voivodeship", tuple(value.strip().casefold() for value in self.voivodeship)
        )
        if self.start_from and self.start_to and self.start_from > self.start_to:
            raise ValueError("start_from is after start_to")
        if not 1 <= self.limit <= MAX_LIMIT:
            raise ValueError(f"limit must be between 1 and {MAX_LIMIT}")
        if self.offset < 0:
            raise ValueError("offset must not be negative")
