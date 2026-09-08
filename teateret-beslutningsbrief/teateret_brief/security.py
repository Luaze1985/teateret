from __future__ import annotations

import ipaddress
import re
import socket
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


class PathPolicyError(ValueError):
    pass


class SourcePolicyError(ValueError):
    pass


class DataPolicyError(ValueError):
    pass


@dataclass(frozen=True)
class ApprovedUrl:
    url: str
    host: str


class RepoPaths:
    def __init__(self, root: Path):
        self.root = root.resolve(strict=True)

    def _resolve(self, relative: str | Path) -> Path:
        candidate = Path(relative)
        if candidate.is_absolute():
            raise PathPolicyError("Absolute stier er ikke tillatt.")
        resolved = (self.root / candidate).resolve(strict=False)
        if not resolved.is_relative_to(self.root):
            raise PathPolicyError("Stien forlater det bekreftede repoet.")
        current = self.root
        for part in candidate.parts:
            if part in ("", "."):
                continue
            current = current / part
            if current.exists() and current.is_symlink():
                if not current.resolve().is_relative_to(self.root):
                    raise PathPolicyError("Symlink forlater det bekreftede repoet.")
        return resolved

    def input_path(self, relative: str | Path) -> Path:
        path = self._resolve(relative)
        if not path.exists():
            raise PathPolicyError(f"Input finnes ikke: {relative}")
        return path

    def output_path(self, relative: str | Path) -> Path:
        return self._resolve(relative)


def _default_resolver(host: str) -> list[str]:
    return sorted({item[4][0] for item in socket.getaddrinfo(host, 443)})


class SourcePolicy:
    def __init__(
        self,
        allowed_hosts: set[str],
        resolver: Callable[[str], list[str]] | None = None,
    ):
        self.allowed_hosts = {host.casefold().rstrip(".") for host in allowed_hosts}
        self.resolver = resolver or _default_resolver

    def validate(self, url: str) -> ApprovedUrl:
        parsed = urlsplit(url)
        host = (parsed.hostname or "").casefold().rstrip(".")
        if parsed.scheme != "https":
            raise SourcePolicyError("Bare HTTPS-kilder er tillatt.")
        if parsed.username or parsed.password:
            raise SourcePolicyError("Brukernavn eller passord i URL er ikke tillatt.")
        try:
            port = parsed.port
        except ValueError as exc:
            raise SourcePolicyError("Ugyldig port i URL.") from exc
        if port not in (None, 443):
            raise SourcePolicyError("Bare standard HTTPS-port er tillatt.")
        if not host or host not in self.allowed_hosts:
            raise SourcePolicyError("Kilden er ikke på den godkjente listen.")
        addresses = self.resolver(host)
        if not addresses:
            raise SourcePolicyError("Kilden kunne ikke DNS-verifiseres.")
        for address in addresses:
            # NB: SourcePolicyError arver fra ValueError, så parsingen må skje i en
            # egen try/except. Ellers fanger `except ValueError` også den bevisste
            # "privat eller reservert"-feilen og maskerer den bak "ugyldig IP".
            try:
                parsed_ip = ipaddress.ip_address(address)
            except ValueError as exc:
                raise SourcePolicyError("Kilden ga en ugyldig IP-adresse.") from exc
            if not parsed_ip.is_global:
                raise SourcePolicyError("Kilden peker til en privat eller reservert adresse.")
        return ApprovedUrl(url=url, host=host)


_FORBIDDEN_COLUMN_EXACT = {
    # Names & Persons
    "navn",
    "name",
    "kundenavn",
    "kunde_navn",
    "customer_name",
    "customer",
    "kunde",
    "client",
    "client_name",
    "gjest",
    "gjester",
    "guest",
    "guests",
    "guest_name",
    "gjestenavn",
    "gjest_navn",
    "kontakt",
    "kontaktperson",
    "kontakt_navn",
    "contact",
    "contact_name",
    "fornavn",
    "first_name",
    "firstname",
    "etternavn",
    "last_name",
    "lastname",
    "fullt_navn",
    "full_name",
    "fullname",
    "personnavn",
    "bruker",
    "brukernavn",
    "user",
    "username",
    "user_name",
    "person",
    "passord",
    "password",
    "passwd",
    "pwd",
    # Contact
    "email",
    "e_post",
    "epost",
    "mail",
    "e_mail",
    "kundeepost",
    "kunde_epost",
    "customer_email",
    "phone",
    "telefon",
    "telefonnr",
    "telefonnummer",
    "kundetelefon",
    "tlf",
    "tlfnr",
    "mobil",
    "mobilnr",
    "mobilnummer",
    "cell",
    "cellphone",
    "mobile",
    "gjeste_telefon",
    "gjestetelefon",
    # National ID & Payments
    "fnr",
    "fodselsnummer",
    "fødselsnummer",
    "personnummer",
    "ssn",
    "national_id",
    "d_nummer",
    "dnummer",
    "kortnummer",
    "kredittkort",
    "credit_card",
    "card_number",
    "pan",
    "cvv",
    "cvc",
    "kontonummer",
    "bankkonto",
    "iban",
    # Address
    "adresse",
    "address",
    "gateadresse",
    "street_address",
    "postadresse",
    "postnr",
    "postnummer",
    "zipcode",
    "postal_code",
    "bosted",
    # Notes & Free Text
    "comment",
    "comments",
    "kommentar",
    "kommentarer",
    "notat",
    "notater",
    "note",
    "notes",
    "reservation_note",
    "reservasjonsnotat",
    "bestillingsnotat",
    "ordrenotat",
    "beskjed",
    "beskjeder",
    "melding",
    "meldinger",
    "message",
    "messages",
    "fritekst",
    "free_text",
    "fritekst_kommentar",
    "allergi",
    "allergier",
    "allergy",
    "allergies",
    "spesialonske",
    "spesialønske",
    "special_request",
    "preferanse",
    "preferanser",
    "dietary",
}

_DOMAIN_SAFE_EXACT = {
    "arrangement",
    "arrangementsnavn",
    "arrangement_navn",
    "forestilling",
    "forestillingsnavn",
    "forestilling_navn",
    "rom",
    "romnavn",
    "rom_navn",
    "lokale",
    "lokalnavn",
    "lokale_navn",
    "artist",
    "artistnavn",
    "artist_navn",
    "produksjon",
    "produksjonsnavn",
    "antall_gjester",
    "gjester_totalt",
    "total_guests",
    "antall_kunder",
    "kunder_totalt",
}

_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_PHONE_RE = re.compile(
    r"(?<![\d\w])(?:\+|00)\d{1,3}(?:[\s.-]|\(\d{1,3}\))?(?:[\s.-]?\d){8,12}(?!\d)|"
    r"(?<![\d\w])\(\+(?:47|\d{1,3})\)[\s-]?(?:[\s.-]?\d){8,10}(?!\d)|"
    r"(?<![\d\w])[2-9]\d{7}(?![\d\w])|"
    r"(?<![\d\w])[2-9]\d{2}[\s-]\d{2}[\s-]\d{3}(?![\d\w])|"
    r"(?<![\d\w])[2-9]\d[\s-]\d{2}[\s-]\d{2}[\s-]\d{2}(?![\d\w])"
)
_FNR_RE = re.compile(
    r"(?<!\d)(?:0[1-9]|[12]\d|3[01]|4[1-9]|[56]\d|7[01])(?:0[1-9]|1[0-2]|4[1-9]|5[0-2])\d{2}[\s-]?(?:\d{5}|\d{3}[\s-]?\d{2})(?!\d)"
)
_CREDIT_CARD_RE = re.compile(
    r"(?<!\d)(?:4\d{3}|5[1-5]\d{2}|6011|3[47]\d{2})[\s-]?(?:\d{4}[\s-]?){2}\d{1,4}(?!\d)|"
    r"(?<!\d)(?:4\d{12}(?:\d{3})?|5[1-5]\d{14}|3[47]\d{13}|6011\d{12})(?!\d)|"
    # Amex: 15 sifre gruppert 4-6-5 (f.eks. 3782 822463 10005)
    r"(?<!\d)3[47]\d{2}[\s-]?\d{6}[\s-]?\d{5}(?!\d)|"
    r"(?<!\d)\d{4}[\s-]\d{4}[\s-]\d{4}[\s-]\d{4}(?!\d)"
)


def is_valid_norwegian_fnr(value: str) -> bool:
    """Validerer 11-sifret norsk fødselsnummer / D-nummer med modulo 11 kontrollsiffer."""
    cleaned = re.sub(r"[\s-]", "", str(value))
    if len(cleaned) != 11 or not cleaned.isdigit():
        return False
    digits = [int(c) for c in cleaned]

    day = digits[0] * 10 + digits[1]
    month = digits[2] * 10 + digits[3]
    valid_day = (1 <= day <= 31) or (41 <= day <= 71) or (81 <= day <= 91)
    valid_month = (1 <= month <= 12) or (41 <= month <= 52) or (21 <= month <= 32)
    if not (valid_day and valid_month):
        return False

    w1 = [3, 7, 6, 1, 8, 9, 4, 5, 2]
    s1 = sum(w * d for w, d in zip(w1, digits[:9]))
    r1 = s1 % 11
    k1 = 0 if r1 == 0 else (11 - r1)
    if k1 == 10 or k1 != digits[9]:
        return False

    w2 = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    s2 = sum(w * d for w, d in zip(w2, digits[:10]))
    r2 = s2 % 11
    k2 = 0 if r2 == 0 else (11 - r2)
    if k2 == 10 or k2 != digits[10]:
        return False

    return True


def is_valid_luhn(card_number: str) -> bool:
    """Validerer kredittkortnummer med Luhn-algoritmen (Mod 10)."""
    cleaned = re.sub(r"[\s-]", "", str(card_number))
    if len(cleaned) < 13 or len(cleaned) > 19 or not cleaned.isdigit():
        return False
    digits = [int(c) for c in cleaned]
    checksum = 0
    reverse_digits = digits[::-1]
    for i, d in enumerate(reverse_digits):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0


def _normalise_header(header: str) -> str:
    return re.sub(r"[^a-z0-9æøå]+", "_", header.casefold()).strip("_")


def is_forbidden_column_header(header: str) -> bool:
    norm = _normalise_header(header)
    if norm in _DOMAIN_SAFE_EXACT:
        return False
    if norm in _FORBIDDEN_COLUMN_EXACT:
        return True
    tokens = set(norm.split("_"))
    if any(t in _FORBIDDEN_COLUMN_EXACT for t in tokens):
        return True
    stems = [
        "kunde",
        "kundenavn",
        "guest",
        "gjest",
        "epost",
        "email",
        "telefon",
        "mobil",
        "notat",
        "kommentar",
        "fodselsnummer",
        "fødselsnummer",
        "kredittkort",
        "creditcard",
        "credit_card",
        "personnummer",
        "fritekst",
        "passord",
        "password",
    ]
    for stem in stems:
        if stem in norm and norm not in _DOMAIN_SAFE_EXACT:
            return True
    return False


def assert_aggregated_csv(
    headers: Iterable[str],
    rows: Iterable[Iterable[str]],
    *,
    allowed_headers: Iterable[str] | None = None,
    strict: bool = False,
) -> None:
    headers_list = list(headers)
    violations = [h for h in headers_list if is_forbidden_column_header(h)]
    if violations:
        raise DataPolicyError(f"Person- eller fritekstfelt er ikke tillatt: {', '.join(violations)}")

    if strict and allowed_headers is not None:
        allowed_set = set(allowed_headers)
        unknown = [h for h in headers_list if h not in allowed_set]
        if unknown:
            raise DataPolicyError(f"Ukjente kolonner er ikke tillatt: {', '.join(sorted(unknown))}")

    for row in rows:
        for value in row:
            if value is None:
                continue
            text = str(value)
            findings = scan_public_artifact(text)
            if findings:
                raise DataPolicyError(
                    f"Direkte kontaktopplysninger er ikke tillatt i aggregert input ({', '.join(findings)})."
                )


def scan_public_artifact(text: str) -> list[str]:
    findings: list[str] = []
    if _EMAIL_RE.search(text):
        findings.append("email")
    if _PHONE_RE.search(text):
        findings.append("phone")
    if _FNR_RE.search(text):
        findings.append("fnr")
    if _CREDIT_CARD_RE.search(text):
        findings.append("credit_card")
    return findings


def redact_contact_details(text: str) -> tuple[str, list[str]]:
    findings = scan_public_artifact(text)
    redacted = _EMAIL_RE.sub("[MASKERT_EPOST]", text)
    redacted = _PHONE_RE.sub("[MASKERT_TELEFON]", redacted)
    redacted = _FNR_RE.sub("[MASKERT_FNR]", redacted)
    redacted = _CREDIT_CARD_RE.sub("[MASKERT_KORT]", redacted)
    return redacted, findings


def redact_reviewer_identity(text: str, author_name: str | None) -> str:
    """Fjern anmeldernavn fra sitat for å unngå PII-lekkasje med ordgrenser."""
    if not author_name or not author_name.strip():
        return text
    parts = author_name.strip().split()
    for part in parts:
        if len(part) >= 2:
            text = re.sub(rf"\b{re.escape(part)}\b", "[ANMELDER]", text, flags=re.IGNORECASE)
    return text


def assert_review_limit(count: int, max_reviews: int) -> None:
    """Blokkerer hvis for mange individuelle anmeldelser forsøkes lagret."""
    if count > max_reviews:
        raise DataPolicyError(
            f"Maks {max_reviews} anmeldelser per sted er tillatt, mottok {count}."
        )


def mask_sensitive_error(message: str) -> str:
    masked = _EMAIL_RE.sub("[MASKERT_EPOST]", message)
    masked = _PHONE_RE.sub("[MASKERT_TELEFON]", masked)
    masked = _FNR_RE.sub("[MASKERT_FNR]", masked)
    return _CREDIT_CARD_RE.sub("[MASKERT_KORT]", masked)


def safe_error_summary(exc: Exception) -> str:
    """Returner stabil feiltekst uten å persistere vilkårlig kilde- eller modellinnhold."""
    if isinstance(exc, DataPolicyError):
        return "Datapolicyen avviste input."
    if isinstance(exc, SourcePolicyError):
        return "Kildepolicyen avviste forespørselen eller innholdet."
    if isinstance(exc, PathPolicyError):
        return "Filpolicyen avviste stien."
    message = str(exc)
    stable_runtime_messages = {
        "Maksimalt antall modellkall er nådd.",
        "Maksimalt tokenbudsjett er nådd.",
        "Modellinput er større enn tillatt grense.",
        "Ingen godkjente kilder kunne leses.",
        "Kontrolløren avviste beslutningsgrunnlaget.",
        "Kildeleser returnerte ukjent kilde-ID.",
        "Analytiker returnerte ukjent kilde-ID.",
        "Kontrollør returnerte ukjent anbefalings-ID.",
    }
    if message in stable_runtime_messages:
        return message
    return f"Teknisk feil ({type(exc).__name__})."
