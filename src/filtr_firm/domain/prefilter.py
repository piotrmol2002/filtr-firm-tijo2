"""The deterministic pre-filter.

`evaluate` judges one company against one profile and collects every rejection reason rather than
stopping at the first, so a caller can report reasons by frequency. `filter_for` turns the same
profile into a database query, and the two must agree: a company passes `evaluate` exactly when the
query returns it.

There is deliberately no registry-status rule. CEIDG's own spelling is
OCZEKUJE_NA_ROZPOCZECIE_DZIALANOSCI (one L short, the registry's typo) and KRS rows carry no status,
so a status predicate would silently drop companies. Whether a company has started is a statement
about its event date instead.
"""

from dataclasses import dataclass
from datetime import date, timedelta

from filtr_firm.domain.company import CompanyFacts
from filtr_firm.domain.company_filter import DEFAULT_LIMIT, CompanyFilter
from filtr_firm.domain.criteria import ProfileCriteria
from filtr_firm.domain.pkd import matches_any

REASON_PKD = "inna branża niż w profilu"
REASON_VOIVODESHIP = "inne województwo niż w profilu"
REASON_NO_REGION = "brak regionu w rejestrze"
REASON_LEGAL_FORM = "inna forma prawna niż w profilu"
REASON_PRE_START = "firma jeszcze nie rozpoczęła działalności"
REASON_NO_EVENT_DATE = "brak daty rozpoczęcia w rejestrze"
REASON_TOO_YOUNG = "firma działa krócej, niż wymaga profil"
REASON_TOO_OLD = "firma działa dłużej, niż wymaga profil"


@dataclass(frozen=True)
class Verdict:
    passed: bool
    reasons: tuple[str, ...]


def _region_reasons(facts: CompanyFacts, criteria: ProfileCriteria) -> list[str]:
    if not criteria.voivodeship:
        return []
    if facts.voivodeship is None:
        return [REASON_NO_REGION]
    if facts.voivodeship.strip().casefold() not in criteria.voivodeship:
        return [REASON_VOIVODESHIP]
    return []


def _age_reasons(facts: CompanyFacts, criteria: ProfileCriteria, reference_date: date) -> list[str]:
    low, high = criteria.age_from_days, criteria.age_to_days
    if facts.event_date is None:
        return [REASON_NO_EVENT_DATE] if low is not None or high is not None else []
    # Negative for a company whose start date is still ahead, which a naive upper bound would pass.
    age = (reference_date - facts.event_date).days
    reasons: list[str] = []
    if low is not None and age < low:
        reasons.append(REASON_TOO_YOUNG)
    if high is not None and age > high:
        reasons.append(REASON_TOO_OLD)
    return reasons


def evaluate(facts: CompanyFacts, criteria: ProfileCriteria, reference_date: date) -> Verdict:
    reasons: list[str] = []
    if not matches_any(criteria.pkd, (facts.pkd_main, *facts.pkd_codes)):
        reasons.append(REASON_PKD)
    reasons.extend(_region_reasons(facts, criteria))
    if criteria.legal_form and facts.legal_form not in criteria.legal_form:
        reasons.append(REASON_LEGAL_FORM)
    pre_start = facts.event_date is not None and facts.event_date > reference_date
    if pre_start and not criteria.include_pre_start:
        reasons.append(REASON_PRE_START)
    reasons.extend(_age_reasons(facts, criteria, reference_date))
    return Verdict(passed=not reasons, reasons=tuple(reasons))


def filter_for(
    criteria: ProfileCriteria,
    *,
    reference_date: date,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
) -> CompanyFilter:
    """The query for one profile: its targeting and nothing else.

    Ages invert when they become dates: age_from_days is a MINIMUM age, so it bounds the event date
    from ABOVE, and age_to_days bounds it from below.
    """
    start_from = (
        None
        if criteria.age_to_days is None
        else reference_date - timedelta(days=criteria.age_to_days)
    )
    upper_bounds: list[date] = []
    if criteria.age_from_days is not None:
        upper_bounds.append(reference_date - timedelta(days=criteria.age_from_days))
    if not criteria.include_pre_start:
        upper_bounds.append(reference_date)
    return CompanyFilter(
        pkd=criteria.pkd,
        voivodeship=criteria.voivodeship,
        legal_form=criteria.legal_form,
        start_from=start_from,
        start_to=min(upper_bounds, default=None),
        include_undated=criteria.age_from_days is None and criteria.age_to_days is None,
        limit=limit,
        offset=offset,
    )
