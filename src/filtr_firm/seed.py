"""Loads fictional sample companies into an empty store.

The data is generated, not copied from the registries: a sole trader's company name in CEIDG is a
person's name, so real rows have no place in a public repository. The generator is seeded and every
date is counted from ANCHOR, so the same command always produces the same 300 companies.
"""

import asyncio
import random
from datetime import date, timedelta

from filtr_firm.db.models import CompanyRow
from filtr_firm.db.repository import CompanyRepository
from filtr_firm.db.session import create_schema, make_engine, make_sessionmaker
from filtr_firm.domain.company import LegalForm, Source

ANCHOR = date(2026, 10, 1)
COUNT = 300

SUBCLASSES = ("6210B", "7311Z", "8559B", "4332Z", "4100A", "4711Z", "4650Z", "7111Z", "4642Z")
# KRS keeps whatever level was declared, so some rows carry a bare division or class.
KRS_SHORT_CODES = ("46", "62", "73", "4711", "411")
VOIVODESHIPS = (
    "małopolskie",
    "mazowieckie",
    "śląskie",
    "podkarpackie",
    "wielkopolskie",
    "dolnośląskie",
    "pomorskie",
    "łódzkie",
)
CITIES = {
    "małopolskie": "Tarnów",
    "mazowieckie": "Warszawa",
    "śląskie": "Katowice",
    "podkarpackie": "Rzeszów",
    "wielkopolskie": "Poznań",
    "dolnośląskie": "Wrocław",
    "pomorskie": "Gdańsk",
    "łódzkie": "Łódź",
}
# Fictional names follow the main activity, so a list reads like real companies without being any.
NAMES = {
    "6210B": "Pracownia Programistyczna",
    "7311Z": "Agencja Reklamowa",
    "8559B": "Centrum Szkoleń",
    "4332Z": "Stolarka Budowlana",
    "4100A": "Budownictwo Mieszkaniowe",
    "4711Z": "Sklep Spożywczy",
    "4650Z": "Hurtownia Sprzętu IT",
    "7111Z": "Biuro Architektoniczne",
    "4642Z": "Hurtownia Odzieży",
    "46": "Handel Hurtowy",
    "62": "Usługi Informatyczne",
    "73": "Reklama i Badania Rynku",
    "4711": "Handel Detaliczny",
    "411": "Inwestycje Budowlane",
}
KRS_FORMS = (LegalForm.SP_ZOO, LegalForm.SP_ZOO, LegalForm.PSA, LegalForm.SA, LegalForm.SJ)
FORM_SUFFIX = {
    LegalForm.SP_ZOO: " sp. z o.o.",
    LegalForm.PSA: " P.S.A.",
    LegalForm.SA: " S.A.",
    LegalForm.SJ: " sp.j.",
}


def _voivodeship(rng: random.Random, source: Source) -> str | None:
    if rng.random() < 0.05:
        return None
    region = rng.choice(VOIVODESHIPS)
    # KRS publishes regions in upper case, which the filter must still match.
    return region.upper() if source is Source.KRS else region


def _event_date(rng: random.Random) -> date | None:
    if rng.random() < 0.05:
        return None
    # Mostly the last two years, plus a few companies that have not started yet.
    return ANCHOR + timedelta(days=rng.randint(-730, 30))


def _codes(rng: random.Random, source: Source) -> tuple[str, list[str]]:
    if source is Source.KRS and rng.random() < 0.4:
        return rng.choice(KRS_SHORT_CODES), []
    main = rng.choice(SUBCLASSES)
    extra = rng.sample([code for code in SUBCLASSES if code != main], k=rng.randint(0, 2))
    return main, extra


def generate(count: int = COUNT, seed: int = 2026) -> list[CompanyRow]:
    rng = random.Random(seed)
    rows: list[CompanyRow] = []
    for number in range(1, count + 1):
        source = Source.CEIDG if rng.random() < 0.7 else Source.KRS
        form = LegalForm.JDG if source is Source.CEIDG else rng.choice(KRS_FORMS)
        voivodeship = _voivodeship(rng, source)
        pkd_main, pkd_codes = _codes(rng, source)
        name = f"{NAMES[pkd_main]} {number:03d}"
        rows.append(
            CompanyRow(
                source=source.value,
                name=name + FORM_SUFFIX.get(form, ""),
                legal_form=form.value,
                voivodeship=voivodeship,
                city=CITIES[voivodeship.lower()] if voivodeship else None,
                pkd_main=pkd_main,
                pkd_codes=pkd_codes,
                event_date=_event_date(rng),
                phone=f"+48 500 000 {number:03d}" if rng.random() < 0.3 else None,
                email=f"kontakt@firma{number:03d}.example" if rng.random() < 0.3 else None,
            )
        )
    return rows


async def main() -> None:
    engine = make_engine()
    await create_schema(engine)
    async with make_sessionmaker(engine)() as session, session.begin():
        repository = CompanyRepository(session)
        if await repository.count() == 0:
            await repository.add_all(generate())
            print(f"Załadowano {COUNT} przykładowych firm.")
        else:
            print("Baza zawiera już dane, pomijam ładowanie.")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
