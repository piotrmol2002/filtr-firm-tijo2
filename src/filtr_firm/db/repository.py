import string
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import Boolean, ColumnElement, and_, func, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from filtr_firm.db.models import CompanyRow
from filtr_firm.domain.company_filter import CompanyFilter


@dataclass(frozen=True)
class CompanyPage:
    items: list[CompanyRow]
    total: int
    limit: int
    offset: int


def pkd_code_match(profile: ColumnElement[str], stored: ColumnElement[str]) -> ColumnElement[bool]:
    """The SQL twin of domain.pkd.code_matches for one profile code and one stored code.

    starts_with instead of LIKE, so an underscore or a percent sign in a stored code is a character
    and never a wildcard. The blank guard is matches_any's `if code`: an empty string is a prefix of
    every profile code, so without it a blank stored code would match every profile.
    """
    return and_(
        stored != "",
        or_(
            func.starts_with(stored, profile, type_=Boolean),
            func.starts_with(profile, stored, type_=Boolean),
        ),
    )


def _pkd_match(codes: Sequence[str]) -> ColumnElement[bool]:
    """Bidirectional prefix match over pkd_main plus pkd_codes.

    EXISTS rather than a join, so a row with four matching codes is still one row.
    `array_prepend(NULL, codes)` yields a NULL element, which pkd_code_match never matches, so a row
    with no main code needs no extra branch.
    """
    code = func.unnest(func.array_prepend(CompanyRow.pkd_main, CompanyRow.pkd_codes)).column_valued(
        "pkd_code"
    )
    return select(code).where(or_(*(pkd_code_match(literal(c), code) for c in codes))).exists()


def value_present(column: ColumnElement[str | None]) -> ColumnElement[bool]:
    """Blank and whitespace-only registry values count as absent, as CEIDG really returns them.

    coalesce keeps the result a real boolean, so NOT of it never drops a NULL row.
    """
    return func.coalesce(func.btrim(column, string.whitespace), "") != ""


def company_predicates(criteria: CompanyFilter) -> list[ColumnElement[bool]]:
    where: list[ColumnElement[bool]] = []
    if criteria.source:
        where.append(CompanyRow.source.in_([source.value for source in criteria.source]))
    if criteria.pkd:
        where.append(_pkd_match(criteria.pkd))
    if criteria.voivodeship:
        where.append(func.lower(CompanyRow.voivodeship).in_(criteria.voivodeship))
    if criteria.legal_form:
        where.append(CompanyRow.legal_form.in_([form.value for form in criteria.legal_form]))
    dated: list[ColumnElement[bool]] = []
    if criteria.start_from is not None:
        dated.append(CompanyRow.event_date >= criteria.start_from)
    if criteria.start_to is not None:
        dated.append(CompanyRow.event_date <= criteria.start_to)
    if dated:
        where.append(
            or_(CompanyRow.event_date.is_(None), and_(*dated))
            if criteria.include_undated
            else and_(*dated)
        )
    for wanted, column in (
        (criteria.has_phone, CompanyRow.phone),
        (criteria.has_email, CompanyRow.email),
    ):
        if wanted is not None:
            present = value_present(column)
            where.append(present if wanted else ~present)
    return where


class CompanyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def search(self, criteria: CompanyFilter) -> CompanyPage:
        where = company_predicates(criteria)
        total = await self._session.scalar(
            select(func.count()).select_from(CompanyRow).where(*where)
        )
        rows = await self._session.scalars(
            select(CompanyRow)
            .where(*where)
            .order_by(CompanyRow.event_date.desc().nulls_last(), CompanyRow.id)
            .limit(criteria.limit)
            .offset(criteria.offset)
        )
        return CompanyPage(
            items=list(rows), total=total or 0, limit=criteria.limit, offset=criteria.offset
        )

    async def add_all(self, rows: Sequence[CompanyRow]) -> None:
        self._session.add_all(rows)
        await self._session.flush()

    async def count(self) -> int:
        return await self._session.scalar(select(func.count()).select_from(CompanyRow)) or 0
