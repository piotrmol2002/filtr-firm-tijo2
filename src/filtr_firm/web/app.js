const VOIVODESHIPS = [
  "dolnośląskie", "kujawsko-pomorskie", "lubelskie", "lubuskie",
  "łódzkie", "małopolskie", "mazowieckie", "opolskie",
  "podkarpackie", "podlaskie", "pomorskie", "śląskie",
  "świętokrzyskie", "warmińsko-mazurskie", "wielkopolskie", "zachodniopomorskie",
];

const LEGAL_FORMS = {
  jdg: "Jednoosobowa działalność gospodarcza",
  sp_zoo: "Spółka z o.o.",
  psa: "Prosta spółka akcyjna",
  sa: "Spółka akcyjna",
  sk: "Spółka komandytowa",
  ska: "Spółka komandytowo-akcyjna",
  sj: "Spółka jawna",
  sp: "Spółka partnerska",
  spoldzielnia: "Spółdzielnia",
  other: "Inna",
};

const SOURCES = { ceidg: "CEIDG", krs: "KRS" };
const PAGE_SIZE = 20;
const MAX_AGE_DAYS = 3650;
const PKD_SHAPE = /^(\d{2}|\d{3}|\d{4}|\d{4}[A-Z])$/;
const SERVER_ERROR = "Nie udało się połączyć z serwerem. Spróbuj ponownie.";
const INVALID_DATA = "Serwer odrzucił dane. Sprawdź wypełnione pola.";

const byId = (id) => document.getElementById(id);
let offset = 0;

function fillChecks(containerId, entries) {
  const container = byId(containerId);
  for (const [value, label] of entries) {
    const wrapper = document.createElement("label");
    wrapper.className = "check";
    const box = document.createElement("input");
    box.type = "checkbox";
    box.value = value;
    wrapper.append(box, label);
    container.append(wrapper);
  }
}

function fillSelect(selectId, entries) {
  const select = byId(selectId);
  for (const [value, label] of entries) {
    select.append(new Option(label, value));
  }
}

function checkedValues(containerId) {
  return [...byId(containerId).querySelectorAll("input:checked")].map((box) => box.value);
}

function splitCodes(text) {
  return text.split(",").map((code) => code.trim().toUpperCase()).filter(Boolean);
}

function invalidCodes(codes) {
  return codes.filter((code) => !PKD_SHAPE.test(code));
}

function optionalAge(inputId) {
  const raw = byId(inputId).value.trim();
  return raw === "" ? null : Number(raw);
}

function validAge(age) {
  return age === null || (Number.isInteger(age) && age >= 0 && age <= MAX_AGE_DAYS);
}

function showError(elementId, message) {
  const element = byId(elementId);
  element.textContent = message;
  element.hidden = !message;
}

function readProfile() {
  const pkd = splitCodes(byId("pkd").value);
  const wrongCodes = invalidCodes(pkd);
  if (wrongCodes.length) {
    return { error: `Nieprawidłowy kod PKD: ${wrongCodes.join(", ")}. Przykłady poprawnych: 62, 621, 6210, 6210B.` };
  }
  const ageFrom = optionalAge("age-from");
  const ageTo = optionalAge("age-to");
  if (!validAge(ageFrom) || !validAge(ageTo)) {
    return { error: `Wiek firmy musi być liczbą całkowitą od 0 do ${MAX_AGE_DAYS} dni.` };
  }
  if (ageFrom !== null && ageTo !== null && ageFrom > ageTo) {
    return { error: "Wiek „od” nie może być większy niż wiek „do”." };
  }
  return {
    criteria: {
      pkd,
      voivodeship: checkedValues("voivodeships"),
      legal_form: checkedValues("legal-forms"),
      age_from_days: ageFrom,
      age_to_days: ageTo,
      include_pre_start: byId("include-pre-start").checked,
    },
    referenceDate: byId("reference-date").value || null,
  };
}

async function postJson(path, body) {
  let response;
  try {
    response = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    return { error: SERVER_ERROR };
  }
  if (response.status === 422) {
    return { error: INVALID_DATA };
  }
  if (!response.ok) {
    return { error: SERVER_ERROR };
  }
  return { data: await response.json() };
}

function formatDate(isoDate) {
  if (!isoDate) {
    return "brak";
  }
  const [year, month, day] = isoDate.split("-").map(Number);
  return new Date(year, month - 1, day).toLocaleDateString("pl-PL");
}

function companyRow(company) {
  const cells = [
    company.name,
    SOURCES[company.source],
    LEGAL_FORMS[company.legal_form],
    company.voivodeship ? company.voivodeship.toLowerCase() : "brak",
    company.city || "brak",
    [company.pkd_main, ...company.pkd_codes].filter(Boolean).join(", ") || "brak",
    formatDate(company.event_date),
    company.has_phone ? "tak" : "nie",
    company.has_email ? "tak" : "nie",
  ];
  const row = document.createElement("tr");
  for (const value of cells) {
    const cell = document.createElement("td");
    cell.textContent = value;
    row.append(cell);
  }
  return row;
}

function companiesLabel(count) {
  const lastDigit = count % 10;
  const lastTwo = count % 100;
  if (count === 1) {
    return "firmę";
  }
  if (lastDigit >= 2 && lastDigit <= 4 && (lastTwo < 12 || lastTwo > 14)) {
    return "firmy";
  }
  return "firm";
}

function renderResults(page) {
  const table = byId("results");
  const body = table.querySelector("tbody");
  body.replaceChildren(...page.items.map(companyRow));
  table.hidden = page.items.length === 0;
  byId("results-summary").textContent = page.total === 0
    ? "Żadna firma w bazie nie spełnia profilu."
    : `Znaleziono ${page.total.toLocaleString("pl-PL")} ${companiesLabel(page.total)}.`;

  const pages = Math.max(1, Math.ceil(page.total / page.limit));
  const current = Math.floor(page.offset / page.limit) + 1;
  byId("pager").hidden = page.total <= page.limit;
  byId("page-info").textContent = `Strona ${current} z ${pages}`;
  byId("prev-page").disabled = page.offset === 0;
  byId("next-page").disabled = page.offset + page.limit >= page.total;
}

async function loadResults() {
  const profile = readProfile();
  showError("profile-error", profile.error || "");
  if (profile.error) {
    return;
  }
  const result = await postJson("/qualification/preview", {
    criteria: profile.criteria,
    reference_date: profile.referenceDate,
    limit: PAGE_SIZE,
    offset,
  });
  showError("profile-error", result.error || "");
  if (result.data) {
    renderResults(result.data);
  }
}

function readCompany() {
  const name = byId("company-name").value.trim();
  if (!name) {
    return { error: "Podaj nazwę firmy." };
  }
  const pkdMain = byId("company-pkd-main").value.trim().toUpperCase();
  const pkdCodes = splitCodes(byId("company-pkd-codes").value);
  const wrongCodes = invalidCodes([pkdMain, ...pkdCodes].filter(Boolean));
  if (wrongCodes.length) {
    return { error: `Nieprawidłowy kod PKD firmy: ${wrongCodes.join(", ")}.` };
  }
  return {
    company: {
      name,
      source: byId("company-source").value,
      legal_form: byId("company-legal-form").value,
      voivodeship: byId("company-voivodeship").value || null,
      city: byId("company-city").value.trim() || null,
      pkd_main: pkdMain || null,
      pkd_codes: pkdCodes,
      event_date: byId("company-event-date").value || null,
    },
  };
}

function renderVerdict(verdict) {
  const box = byId("verdict");
  box.className = `verdict ${verdict.passed ? "passed" : "rejected"}`;
  byId("verdict-title").textContent = verdict.passed
    ? "Firma spełnia profil klienta."
    : "Firma nie spełnia profilu klienta. Powody:";
  const reasons = verdict.reasons.map((reason) => {
    const item = document.createElement("li");
    item.textContent = reason;
    return item;
  });
  byId("verdict-reasons").replaceChildren(...reasons);
  box.hidden = false;
}

async function evaluateCompany(event) {
  event.preventDefault();
  byId("verdict").hidden = true;
  const profile = readProfile();
  const company = readCompany();
  const error = profile.error ? `Profil: ${profile.error}` : company.error;
  showError("company-error", error || "");
  if (error) {
    return;
  }
  const result = await postJson("/qualification/evaluate", {
    company: company.company,
    criteria: profile.criteria,
    reference_date: profile.referenceDate,
  });
  showError("company-error", result.error || "");
  if (result.data) {
    renderVerdict(result.data);
  }
}

function todayIso() {
  const now = new Date();
  const local = new Date(now.getTime() - now.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 10);
}

function init() {
  const voivodeshipEntries = VOIVODESHIPS.map((name) => [name, name]);
  const legalFormEntries = Object.entries(LEGAL_FORMS);
  fillChecks("voivodeships", voivodeshipEntries);
  fillChecks("legal-forms", legalFormEntries);
  fillSelect("company-legal-form", legalFormEntries);
  fillSelect("company-voivodeship", [["", "brak w rejestrze"], ...voivodeshipEntries]);
  byId("reference-date").value = todayIso();

  byId("profile-form").addEventListener("submit", (event) => {
    event.preventDefault();
    offset = 0;
    loadResults();
  });
  byId("prev-page").addEventListener("click", () => {
    offset = Math.max(0, offset - PAGE_SIZE);
    loadResults();
  });
  byId("next-page").addEventListener("click", () => {
    offset += PAGE_SIZE;
    loadResults();
  });
  byId("company-form").addEventListener("submit", evaluateCompany);
}

init();
