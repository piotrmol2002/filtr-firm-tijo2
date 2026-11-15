from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import date
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from filtr_firm.api.schemas import CompanyPageOut, EvaluateIn, PreviewIn, VerdictOut
from filtr_firm.db.repository import CompanyRepository
from filtr_firm.db.session import create_schema, make_engine, make_sessionmaker
from filtr_firm.domain.company import LegalForm, Source
from filtr_firm.domain.company_filter import DEFAULT_LIMIT, MAX_LIMIT, CompanyFilter
from filtr_firm.domain.prefilter import evaluate, filter_for

INVALID_FILTER = "Nieprawidłowe parametry filtra."


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    engine = make_engine()
    await create_schema(engine)
    app.state.sessionmaker = make_sessionmaker(engine)
    yield
    await engine.dispose()


app = FastAPI(
    title="Filtr firm",
    description="Wstępna kwalifikacja nowo zarejestrowanych firm z rejestrów CEIDG i KRS.",
    version="0.1.0",
    lifespan=lifespan,
)


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.sessionmaker() as session:
        yield session


def get_repository(session: Annotated[AsyncSession, Depends(get_session)]) -> CompanyRepository:
    return CompanyRepository(session)


def get_today() -> date:
    return date.today()


Repository = Annotated[CompanyRepository, Depends(get_repository)]
Today = Annotated[date, Depends(get_today)]


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/companies", tags=["companies"])
async def search_companies(
    repository: Repository,
    source: Annotated[list[Source] | None, Query()] = None,
    pkd: Annotated[list[str] | None, Query()] = None,
    voivodeship: Annotated[list[str] | None, Query()] = None,
    legal_form: Annotated[list[LegalForm] | None, Query()] = None,
    start_from: date | None = None,
    start_to: date | None = None,
    has_phone: bool | None = None,
    has_email: bool | None = None,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> CompanyPageOut:
    try:
        criteria = CompanyFilter(
            source=tuple(source or ()),
            pkd=tuple(pkd or ()),
            voivodeship=tuple(voivodeship or ()),
            legal_form=tuple(legal_form or ()),
            start_from=start_from,
            start_to=start_to,
            has_phone=has_phone,
            has_email=has_email,
            limit=limit,
            offset=offset,
        )
    except ValueError:
        raise HTTPException(status_code=422, detail=INVALID_FILTER) from None
    return CompanyPageOut.from_page(await repository.search(criteria))


@app.post("/qualification/evaluate", tags=["qualification"])
async def evaluate_company(body: EvaluateIn, today: Today) -> VerdictOut:
    verdict = evaluate(body.company.to_facts(), body.criteria, body.reference_date or today)
    return VerdictOut.from_verdict(verdict)


@app.post("/qualification/preview", tags=["qualification"])
async def preview(body: PreviewIn, repository: Repository, today: Today) -> CompanyPageOut:
    query = filter_for(
        body.criteria,
        reference_date=body.reference_date or today,
        limit=body.limit,
        offset=body.offset,
    )
    return CompanyPageOut.from_page(await repository.search(query))
