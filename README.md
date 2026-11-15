# Filtr firm

## Nazwa kursu

Testowanie i Jakość Oprogramowania

## Autor

Piotr Mól

## Temat projektu

Filtr kwalifikacji nowo zarejestrowanych firm z rejestrów CEIDG i KRS

## Opis projektu

Projekt jest wydzielonym fragmentem pracy inżynierskiej „Projekt i implementacja agentowego systemu
weryfikacji klientów biznesowych z wykorzystaniem danych z rejestru CEIDG oraz dużych modeli
językowych”. Obejmuje deterministyczny filtr wstępny, który na podstawie profilu oferty użytkownika
wybiera z bazy firmy warte dalszej analizy.

Profil określa:

- kody PKD 2025 (dowolny poziom: dział `62`, grupa, klasa lub podklasa `6210B`),
- województwa,
- formy prawne,
- wiek firmy w dniach (od, do),
- czy uwzględniać firmy, które jeszcze nie rozpoczęły działalności.

Najważniejsze reguły:

- kody PKD są dopasowywane prefiksowo w obie strony, ponieważ CEIDG podaje zawsze podklasę, a KRS
  często tylko dział (firma z kodem `46` pasuje do profilu `4611Z` i odwrotnie),
- województwa są porównywane bez względu na wielkość liter (KRS zapisuje je wielkimi literami),
- firma z datą rozpoczęcia w przyszłości jest odrzucana, chyba że profil na to pozwala,
- filtr zwraca wszystkie powody odrzucenia, a nie tylko pierwszy.

Ta sama reguła istnieje w dwóch postaciach: jako funkcja w Pythonie oceniająca jedną firmę oraz jako
zapytanie SQL wybierające firmy z bazy. Obie muszą dawać ten sam wynik.

Baza zawiera 300 fikcyjnych firm generowanych deterministycznie. Prawdziwe dane z rejestrów nie są
używane, ponieważ nazwa jednoosobowej działalności w CEIDG to imię i nazwisko osoby.

## Interfejs użytkownika

Strona główna (`/`) ma trzy części:

- **Profil klienta**: kody PKD, województwa, formy prawne, wiek firmy w dniach, data odniesienia
  i zgoda na firmy przed rozpoczęciem działalności,
- **Pasujące firmy**: tabela firm z bazy spełniających profil, z liczbą wyników i stronicowaniem
  po 20 pozycji,
- **Ocena pojedynczej firmy**: formularz z danymi jednej firmy i werdykt wraz z listą powodów
  odrzucenia.

Niepoprawne kody PKD i zakres wieku są wykrywane jeszcze przed wysłaniem zapytania.

## Uruchomienie projektu

Wymagany Docker z Docker Compose.

```bash
docker compose up --build
```

Interfejs użytkownika działa pod adresem `http://localhost:8000`, a interaktywna dokumentacja API
pod `http://localhost:8000/docs`. Przy pierwszym uruchomieniu baza jest wypełniana przykładowymi danymi.

## Dokumentacja API

| Metoda | Ścieżka | Opis |
|---|---|---|
| GET | `/` | Interfejs użytkownika |
| GET | `/health` | Stan usługi |
| GET | `/companies` | Lista firm z bazy według filtrów: `source`, `pkd`, `voivodeship`, `legal_form`, `start_from`, `start_to`, `has_phone`, `has_email`, `limit` (1-500), `offset` |
| POST | `/qualification/evaluate` | Ocena jednej firmy względem profilu: wynik i lista powodów odrzucenia |
| POST | `/qualification/preview` | Firmy z bazy spełniające profil |

Przykład oceny firmy:

```json
POST /qualification/evaluate
{
  "company": {
    "name": "Handel Hurtowy 001 sp. z o.o.",
    "source": "krs",
    "legal_form": "sp_zoo",
    "voivodeship": "MAŁOPOLSKIE",
    "pkd_main": "46",
    "event_date": "2026-11-01"
  },
  "criteria": {
    "pkd": ["4611Z"],
    "voivodeship": ["małopolskie"],
    "age_to_days": 90
  },
  "reference_date": "2026-10-01"
}
```

Odpowiedź:

```json
{ "passed": false, "reasons": ["firma jeszcze nie rozpoczęła działalności"] }
```

## Technologie użyte w projekcie

- Python 3.12, FastAPI, Pydantic 2
- SQLAlchemy 2 (asyncio) z asyncpg
- PostgreSQL 18
- Docker Compose
- HTML, CSS i JavaScript bez frameworka (interfejs użytkownika)
- uv (zarządzanie zależnościami), ruff (lint i formatowanie)
