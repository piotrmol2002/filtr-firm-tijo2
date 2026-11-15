from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from filtr_firm.domain.company import LegalForm
from filtr_firm.domain.pkd import normalise_code

MAX_AGE_DAYS = 3650
VOIVODESHIPS: frozenset[str] = frozenset(
    {
        "dolnośląskie",
        "kujawsko-pomorskie",
        "lubelskie",
        "lubuskie",
        "łódzkie",
        "małopolskie",
        "mazowieckie",
        "opolskie",
        "podkarpackie",
        "podlaskie",
        "pomorskie",
        "śląskie",
        "świętokrzyskie",
        "warmińsko-mazurskie",
        "wielkopolskie",
        "zachodniopomorskie",
    }
)


class ProfileCriteria(BaseModel):
    """The targeting part of a user's offer profile: which new companies are worth a look."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    pkd: tuple[str, ...] = ()
    voivodeship: tuple[str, ...] = ()
    legal_form: tuple[LegalForm, ...] = ()
    age_from_days: int | None = Field(default=None, ge=0, le=MAX_AGE_DAYS)
    age_to_days: int | None = Field(default=None, ge=0, le=MAX_AGE_DAYS)
    include_pre_start: bool = False

    # Sorted rather than kept in input order, so the same ticked boxes give equal criteria.
    @field_validator("pkd")
    @classmethod
    def _codes(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(sorted(normalise_code(code) for code in value))

    @field_validator("voivodeship")
    @classmethod
    def _regions(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        regions = tuple(sorted(region.strip().casefold() for region in value))
        unknown = [region for region in regions if region not in VOIVODESHIPS]
        if unknown:
            raise ValueError(f"not a voivodeship: {', '.join(unknown)}")
        return regions

    @field_validator("legal_form")
    @classmethod
    def _forms(cls, value: tuple[LegalForm, ...]) -> tuple[LegalForm, ...]:
        return tuple(sorted(value))

    @model_validator(mode="after")
    def _age_range(self) -> Self:
        low, high = self.age_from_days, self.age_to_days
        if low is not None and high is not None and low > high:
            raise ValueError(f"age_from_days {low} is greater than age_to_days {high}")
        return self
