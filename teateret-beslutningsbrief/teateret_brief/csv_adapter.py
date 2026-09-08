from __future__ import annotations

import csv
import io
import math
import re
from datetime import date, datetime
from pathlib import Path

from pydantic import BaseModel, Field

from .models import SalesObservation
from .security import DataPolicyError, assert_aggregated_csv


class MetricMapping(BaseModel):
    column: str
    unit: str


class CsvMapping(BaseModel):
    delimiter: str = Field(default=";", min_length=0, max_length=10)
    date_column: str
    label_column: str
    room_column: str | None = None
    event_id_column: str | None = None
    metrics: dict[str, MetricMapping]
    source_system: str = "GastroPlanner"
    strict_columns: bool = True

    @property
    def declared_columns(self) -> set[str]:
        columns = {
            self.date_column,
            self.label_column,
            *(metric.column for metric in self.metrics.values()),
        }
        if self.room_column:
            columns.add(self.room_column)
        if self.event_id_column:
            columns.add(self.event_id_column)
        return columns


CANONICAL_ROOMS = {
    "hovedscenen": "Hovedscenen",
    "biscenen": "Biscenen",
    "intimscenen": "Intimscenen",
    "foajeen": "Foajeen",
    "restauranten": "Restauranten",
}

ROOM_ALIASES = {
    "hovedsalen": "Hovedscenen",
    "hovedsal": "Hovedscenen",
    "hovedscene": "Hovedscenen",
    "store sal": "Hovedscenen",
    "main stage": "Hovedscenen",
    "black box": "Biscenen",
    "blackbox": "Biscenen",
    "biscene": "Biscenen",
    "lille sal": "Biscenen",
    "klubbscenen": "Biscenen",
    "klubbscene": "Biscenen",
    "intimscene": "Intimscenen",
    "intimen": "Intimscenen",
    "prøvesalen": "Intimscenen",
    "provesalen": "Intimscenen",
    "foajé": "Foajeen",
    "foaje": "Foajeen",
    "foyer": "Foajeen",
    "teaterbaren": "Foajeen",
    "bar": "Foajeen",
    "foajescenen": "Foajeen",
    "restaurant": "Restauranten",
    "spiseriet": "Restauranten",
    "matbaren": "Restauranten",
}


def normalize_room(raw: str | None) -> str | None:
    """Normaliserer romnavn og scene-aliaser til kanoniske navn."""
    if raw is None:
        return None
    text = raw.strip()
    if not text:
        return None

    if "/" in text:
        parts = [normalize_room(p) for p in text.split("/")]
        return " / ".join(p for p in parts if p)

    cf = text.casefold()
    if cf in CANONICAL_ROOMS:
        return CANONICAL_ROOMS[cf]
    if cf in ROOM_ALIASES:
        return ROOM_ALIASES[cf]

    if "hovedsal" in cf or "hovedscene" in cf or "store sal" in cf:
        return "Hovedscenen"
    if "black box" in cf or "blackbox" in cf or "biscene" in cf or "lille sal" in cf:
        return "Biscenen"
    if "intim" in cf or "prøvesal" in cf or "provesal" in cf:
        return "Intimscenen"
    if "foaj" in cf or "foyer" in cf or "teaterbar" in cf:
        return "Foajeen"
    if "restaurant" in cf or "spiseri" in cf:
        return "Restauranten"

    return text


def _read_csv_content(path: Path) -> str:
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return path.read_text(encoding=enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return path.read_text(encoding="latin-1", errors="replace")


def _detect_delimiter(sample: str, configured: str = ";") -> str:
    if configured and configured.lower() != "auto" and len(configured) == 1:
        return configured
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=";,\t")
        return dialect.delimiter
    except Exception:
        first_line = sample.splitlines()[0] if sample else ""
        if ";" in first_line:
            return ";"
        if "\t" in first_line:
            return "\t"
        if "," in first_line:
            return ","
        return ";"


def _parse_date(value: str) -> date:
    text = value.strip()
    if "T" in text:
        try:
            return datetime.fromisoformat(text).date()
        except ValueError:
            pass
    formats = (
        "%Y-%m-%d",
        "%d.%m.%Y",
        "%d/%m/%Y",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%d.%m.%Y %H:%M:%S",
        "%d.%m.%Y %H:%M",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
    )
    for pattern in formats:
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            continue
    raise DataPolicyError(f"Ukjent datoformat: {text}")


def _parse_number(value: str | float | None) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        val = float(value)
        if not math.isfinite(val):
            raise DataPolicyError("Aggregert måleverdi må være et endelig tall.")
        if val < 0:
            raise DataPolicyError("Negative aggregerte måleverdier er ikke tillatt i piloten.")
        return val

    text = str(value).strip()
    for ws in ("\u00a0", "\u202f", "\t", "\r", "\n", " "):
        text = text.replace(ws, "")

    # Tomt felt eller kun mellomrom er ikke en gyldig aggregert måleverdi.
    if text == "":
        raise DataPolicyError("Aggregert måleverdi kan ikke være tom eller kun mellomrom.")
    # «N/A» skal avvises på linje med NaN — bruk 0 eksplisitt for ingen registrert verdi.
    if text.casefold() == "n/a":
        raise DataPolicyError("Aggregert måleverdi «N/A» er ikke tillatt; bruk 0 for ingen registrert verdi.")
    if text in ("-", "–", "—", "null", "None"):
        return 0.0

    # Strip currency tokens
    text = re.sub(r"(?i)\b(?:nok|kr\.?)\b", "", text)
    text = text.replace("NOK", "").replace("nok", "").replace("kr.", "").replace("kr", "").replace("Kr", "")
    if text.endswith(",-") or text.endswith(".-"):
        text = text[:-2] + ",00"
    text = text.strip()

    if text in ("", "-"):
        return 0.0

    if "." in text and "," in text:
        last_dot = text.rfind(".")
        last_comma = text.rfind(",")
        if last_comma > last_dot:
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        text = text.replace(",", ".")
    elif "." in text:
        if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", text):
            text = text.replace(".", "")

    try:
        val = float(text)
    except ValueError as exc:
        raise DataPolicyError("Aggregert måleverdi er ikke et tall.") from exc

    if not math.isfinite(val):
        raise DataPolicyError("Aggregert måleverdi må være et endelig tall.")
    if val < 0:
        raise DataPolicyError("Negative aggregerte måleverdier er ikke tillatt i piloten.")
    return val


def load_aggregated_csv(path: Path, mapping: CsvMapping) -> list[SalesObservation]:
    content = _read_csv_content(path)
    delimiter = _detect_delimiter(content, mapping.delimiter)

    reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)
    headers = reader.fieldnames or []
    rows = list(reader)

    missing = mapping.declared_columns.difference(headers)
    if missing:
        raise DataPolicyError(f"Påkrevde kolonner mangler: {', '.join(sorted(missing))}")

    unknown = set(headers).difference(mapping.declared_columns)
    if mapping.strict_columns and unknown:
        raise DataPolicyError(f"Ukjente kolonner er ikke tillatt: {', '.join(sorted(unknown))}")

    assert_aggregated_csv(
        headers,
        ([row.get(header, "") for header in headers] for row in rows),
        allowed_headers=mapping.declared_columns if mapping.strict_columns else None,
        strict=mapping.strict_columns,
    )

    observations: list[SalesObservation] = []
    for row in rows:
        period = _parse_date(row[mapping.date_column])
        label = row[mapping.label_column].strip()
        if not label:
            raise DataPolicyError("Arrangement/etikett kan ikke være tom.")

        raw_room = row.get(mapping.room_column) if mapping.room_column else None
        room = normalize_room(raw_room) if raw_room else None

        event_id = row[mapping.event_id_column].strip() if mapping.event_id_column and row.get(mapping.event_id_column) else None

        for metric_name, metric in mapping.metrics.items():
            observations.append(
                SalesObservation(
                    period=period,
                    label=label,
                    metric=metric_name,
                    value=_parse_number(row[metric.column]),
                    unit=metric.unit,
                    source_system=mapping.source_system,
                    room=room,
                    event_id=event_id,
                )
            )
    return observations

