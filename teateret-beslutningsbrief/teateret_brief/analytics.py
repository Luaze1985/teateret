from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Literal

from .models import CrossSalesCorrelation, PublicEvent, SalesObservation


def calculate_cross_sales_correlations(
    observations: list[SalesObservation],
    matched_events: list[PublicEvent] | None = None,
    window_hours: int = 2,
) -> list[CrossSalesCorrelation]:
    """Beregner kryssalg og restaurantkorrelasjon for matchede arrangementer og salgsobservasjoner.

    Håndterer:
    1. Enkelt-rader med kombinert billett-, bord- og pakkesalg (Level 1 / Confirmed).
    2. Separate arrangements- og restaurantobservasjoner på samme dato (+/- 2t) (Level 3 / Indication).
    3. Null-divisjonsbeskyttelse for dager/arrangementer med 0 billetter eller 0 kapasitet.
    """
    if not observations:
        return []

    # Map matched_events for quick resolution
    events_by_id: dict[str, PublicEvent] = {}
    events_by_date: dict[date, list[PublicEvent]] = {}
    if matched_events:
        for ev in matched_events:
            if ev.event_id:
                events_by_id[ev.event_id] = ev
                events_by_id[ev.event_id.upper()] = ev
            events_by_date.setdefault(ev.date, []).append(ev)

    # Group observations by (period, event_id, label, room)
    raw_groups: dict[tuple[date, str | None, str, str | None], dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for obs in observations:
        key = (obs.period, obs.event_id, obs.label, obs.room)
        raw_groups[key][obs.metric] += obs.value

    # Parse groups into structured dicts
    show_groups: list[dict] = []
    dining_only_groups: list[dict] = []

    for (period, event_id, label, room), metrics in raw_groups.items():
        tickets_sold = sum(v for m, v in metrics.items() if m in ("tickets_sold", "tickets", "billetter"))
        capacity = sum(v for m, v in metrics.items() if m in ("capacity", "kapasitet"))
        table_res = sum(v for m, v in metrics.items() if m in ("table_reservations", "tables", "bord", "bordreservasjoner", "table_covers_2h", "table_reservations_2h"))
        preorder_pkgs = sum(v for m, v in metrics.items() if m in ("preorder_packages", "packages", "menyer", "pakkemenyer", "preorder_packages_2h"))
        revenue = sum(v for m, v in metrics.items() if m in ("revenue_nok", "dining_revenue_nok", "revenue", "omsetning", "preorder_revenue_2h", "inntekt"))

        group_data = {
            "period": period,
            "event_id": event_id,
            "label": label,
            "room": room,
            "tickets_sold": tickets_sold,
            "capacity": capacity,
            "table_reservations": table_res,
            "preorder_packages": preorder_pkgs,
            "revenue_nok": revenue,
            "confidence": "confirmed" if (event_id and len(event_id) > 0) else "indication",
        }

        if tickets_sold > 0:
            show_groups.append(group_data)
        else:
            dining_only_groups.append(group_data)

    # Correlate separate dining rows to show rows on the same date if applicable
    unmerged_dining: list[dict] = []
    for dining in dining_only_groups:
        matching_shows = [s for s in show_groups if s["period"] == dining["period"]]
        if len(matching_shows) == 1 and matching_shows[0]["table_reservations"] == 0 and matching_shows[0]["revenue_nok"] == 0:
            # Attach dining metrics to single show on date as indication
            show = matching_shows[0]
            show["table_reservations"] += dining["table_reservations"]
            show["preorder_packages"] += dining["preorder_packages"]
            show["revenue_nok"] += dining["revenue_nok"]
            show["confidence"] = "indication"
        else:
            unmerged_dining.append(dining)

    all_active_groups = show_groups + unmerged_dining
    correlations: list[CrossSalesCorrelation] = []

    for g in all_active_groups:
        period = g["period"]
        event_id = g["event_id"]
        label = g["label"]
        room = g["room"]
        tickets_sold = g["tickets_sold"]
        capacity = g["capacity"]
        table_reservations = g["table_reservations"]
        preorder_packages = g["preorder_packages"]
        revenue_nok = g["revenue_nok"]
        confidence = g["confidence"]

        # Look up matched event
        matched_ev = None
        if event_id and event_id.upper() in events_by_id:
            matched_ev = events_by_id[event_id.upper()]
        elif period in events_by_date and len(events_by_date[period]) == 1:
            matched_ev = events_by_date[period][0]

        event_title = matched_ev.title if matched_ev else label
        event_room = room or (matched_ev.room if matched_ev else None)
        if capacity == 0.0 and matched_ev and matched_ev.capacity:
            capacity = float(matched_ev.capacity)

        if capacity == 0.0 and event_room:
            norm_r = event_room.lower()
            for rk, cap_val in [
                ("hovedscenen", 400.0),
                ("biscenen", 148.0),
                ("intimscenen", 90.0),
                ("foaje", 50.0),
                ("restaurant", 80.0),
            ]:
                if rk in norm_r:
                    capacity = cap_val
                    break

        # Derived calculations with zero-division safety
        capacity_utilization_pct = round((tickets_sold / capacity) * 100, 1) if capacity > 0 else 0.0
        cross_sales_ratio = round(table_reservations / tickets_sold, 3) if tickets_sold > 0 else 0.0
        preorder_conversion_pct = round((preorder_packages / tickets_sold) * 100, 1) if tickets_sold > 0 else 0.0
        preorder_table_conversion_pct = round((preorder_packages / table_reservations) * 100, 1) if table_reservations > 0 else 0.0
        revenue_per_ticket_nok = round(revenue_nok / tickets_sold, 2) if tickets_sold > 0 else 0.0

        correlations.append(
            CrossSalesCorrelation(
                event_id=event_id,
                event_title=event_title,
                event_date=period,
                room=event_room,
                tickets_sold=tickets_sold,
                capacity=capacity,
                capacity_utilization_pct=capacity_utilization_pct,
                table_reservations_2h=table_reservations,
                preorder_packages_2h=preorder_packages,
                dining_revenue_nok=revenue_nok,
                cross_sales_ratio=cross_sales_ratio,
                preorder_conversion_pct=preorder_conversion_pct,
                preorder_table_conversion_pct=preorder_table_conversion_pct,
                revenue_per_ticket_nok=revenue_per_ticket_nok,
                correlation_confidence=confidence,
            )
        )

    correlations.sort(key=lambda c: (c.event_date, c.event_title))
    return correlations


def summarize_sales(observations: list[SalesObservation]) -> dict:
    """Returner totalsummer, arrangementsrangering og periodetrend uten personnivå."""
    try:
        import duckdb  # type: ignore
    except ImportError:
        return _python_summary(observations, backend="python_fallback")

    connection = duckdb.connect(":memory:")
    try:
        connection.execute(
            """CREATE TABLE observations(
                period DATE, label VARCHAR, metric VARCHAR, unit VARCHAR, value DOUBLE
            )"""
        )
        connection.executemany(
            "INSERT INTO observations VALUES (?, ?, ?, ?, ?)",
            [
                (item.period.isoformat(), item.label, item.metric, item.unit, item.value)
                for item in observations
            ],
        )
        totals = connection.execute(
            "SELECT metric, unit, SUM(value) FROM observations GROUP BY metric, unit ORDER BY metric, unit"
        ).fetchall()
        labels = connection.execute(
            """SELECT metric, unit, label, SUM(value) AS total
            FROM observations GROUP BY metric, unit, label
            ORDER BY metric, unit, total DESC, label"""
        ).fetchall()
        periods = connection.execute(
            """SELECT period, metric, unit, SUM(value) AS total
            FROM observations GROUP BY period, metric, unit
            ORDER BY metric, unit, period"""
        ).fetchall()
        return {
            "backend": "duckdb",
            "row_count": len(observations),
            "totals": [
                {"metric": metric, "unit": unit, "value": value}
                for metric, unit, value in totals
            ],
            "by_label": _rank_labels(labels),
            "by_period": _period_changes(periods),
        }
    finally:
        connection.close()


def _python_summary(observations: list[SalesObservation], *, backend: str) -> dict:
    totals: dict[tuple[str, str], float] = defaultdict(float)
    labels: dict[tuple[str, str, str], float] = defaultdict(float)
    periods: dict[tuple[object, str, str], float] = defaultdict(float)
    for item in observations:
        totals[(item.metric, item.unit)] += item.value
        labels[(item.metric, item.unit, item.label)] += item.value
        periods[(item.period, item.metric, item.unit)] += item.value
    label_rows = [
        (metric, unit, label, value)
        for (metric, unit, label), value in labels.items()
    ]
    label_rows.sort(key=lambda row: (row[0], row[1], -row[3], row[2]))
    period_rows = [
        (period, metric, unit, value)
        for (period, metric, unit), value in periods.items()
    ]
    period_rows.sort(key=lambda row: (row[1], row[2], row[0]))
    return {
        "backend": backend,
        "row_count": len(observations),
        "totals": [
            {"metric": metric, "unit": unit, "value": value}
            for (metric, unit), value in sorted(totals.items())
        ],
        "by_label": _rank_labels(label_rows),
        "by_period": _period_changes(period_rows),
    }


def _rank_labels(rows) -> list[dict]:
    ranks: dict[tuple[str, str], int] = defaultdict(int)
    output = []
    for metric, unit, label, value in rows:
        key = (metric, unit)
        ranks[key] += 1
        output.append(
            {
                "metric": metric,
                "unit": unit,
                "label": label,
                "value": value,
                "rank": ranks[key],
            }
        )
    return output


def _period_changes(rows) -> list[dict]:
    previous: dict[tuple[str, str], float] = {}
    output = []
    for period, metric, unit, value in rows:
        key = (metric, unit)
        previous_value = previous.get(key)
        change_percent = None
        if previous_value not in (None, 0):
            change_percent = round(((value - previous_value) / previous_value) * 100, 2)
        output.append(
            {
                "period": period.isoformat(),
                "metric": metric,
                "unit": unit,
                "value": value,
                "previous_value": previous_value,
                "change_percent": change_percent,
            }
        )
        previous[key] = value
    return output
