"""PKD 2025 codes and the one matching rule.

CEIDG always publishes the 5-character subclass, while KRS publishes whatever level was declared,
often a bare division such as `46`. Matching is therefore a prefix test in EITHER direction: a
company matches when the profile code is a prefix of a company code, or a company code is a prefix
of the profile code. The second direction is what catches a KRS row that declared only `46` for a
profile asking for `4611Z`.
"""

import re
from collections.abc import Iterable, Sequence

# division, group, class, subclass. A fifth character is always a capital letter, and the digits are
# ASCII because a normalised code becomes the prefix argument of the SQL starts_with.
_SHAPE = re.compile(r"^(?:[0-9]{2}|[0-9]{3}|[0-9]{4}|[0-9]{4}[A-Z])$")


def normalise_code(value: str) -> str:
    code = value.strip().upper()
    if not _SHAPE.match(code):
        raise ValueError(f"'{code}' is not a PKD code")
    return code


def code_matches(profile_code: str, company_code: str) -> bool:
    return company_code.startswith(profile_code) or profile_code.startswith(company_code)


def matches_any(profile_codes: Sequence[str], company_codes: Iterable[str | None]) -> bool:
    """An empty criterion means every industry; a company with no code satisfies no criterion."""
    if not profile_codes:
        return True
    stored = tuple(code for code in company_codes if code)
    return any(code_matches(profile, code) for profile in profile_codes for code in stored)
