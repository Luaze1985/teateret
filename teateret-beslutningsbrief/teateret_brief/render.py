from __future__ import annotations

from html import escape

from .models import Brief


DISCLAIMER = "UTKAST – IKKE SENDT – MÅ KONTROLLERES AV ET MENNESKE"


def render_markdown(brief: Brief) -> str:
    lines = [
        f"# {brief.title}",
        "",
        f"> {DISCLAIMER}",
        "",
        f"Run-ID: `{brief.run_id}`  ",
        f"Status: `{brief.status}`",
        "",
    ]
    if brief.review_summaries:
        lines.extend(["## Gjestevurderinger og omdømme (Google)", ""])
        for rs in brief.review_summaries:
            lines.append(f"### {rs.place_name}")
            lines.append(f"- **Samlet score:** {rs.rating:.1f} / 5.0 ({rs.total_reviews} anmeldelser)")
            if rs.sentiment_topics:
                lines.append("- **Sentiment per tema:**")
                for topic in rs.sentiment_topics:
                    sent_nor = {"positive": "positiv", "mixed": "blandet", "negative": "negativ"}.get(
                        topic.sentiment, topic.sentiment
                    )
                    lines.append(f"  - *{topic.topic.capitalize()}* ({sent_nor}, {topic.mention_count} omtaler)")
                    for quote in topic.sample_quotes:
                        lines.append(f"    - «{quote}»")
            lines.append("")

    if brief.market_observations:
        lines.extend(["## Markedssignaler og trender", ""])
        for mo in brief.market_observations:
            direction = f" ({mo.detail.get('trend_direction')})" if mo.detail and mo.detail.get("trend_direction") else ""
            lines.append(
                f"- **{mo.label}** [{mo.source_system}]: {mo.metric} = {mo.value} {mo.unit}{direction}"
            )
        lines.append("")

    lines.extend(["## Signaler", ""])
    for signal in brief.signals:
        lines.append(
            f"- **{signal.id}** [{signal.confidence}]: {signal.claim} "
            f"(kilder: {', '.join(signal.source_ids)})"
        )
    lines.extend(["", "## Anbefalte handlinger", ""])
    for recommendation in brief.recommendations:
        lines.extend(
            [
                f"### {recommendation.id}: {recommendation.action}",
                "",
                recommendation.rationale,
                "",
                f"Forventet verdi: {recommendation.expected_value}  ",
                f"Innsats: {recommendation.effort}  ",
                f"Kilder: {', '.join(recommendation.source_ids)}",
                "",
            ]
        )
    if brief.warnings:
        lines.extend(["## Varsler", ""])
        lines.extend(f"- {warning}" for warning in brief.warnings)
        lines.append("")
    lines.extend(["## Kilder", ""])
    for source in brief.sources:
        published = f"; publisert {source.published_at}" if source.published_at else ""
        lines.append(
            f"- **{source.source_id}**: [{source.title}]({source.url}) "
            f"(hentet {source.fetched_at}{published})"
        )
    lines.append("")
    return "\n".join(lines)


def render_html(brief: Brief) -> str:
    reviews_html = ""
    if brief.review_summaries:
        reviews_parts = []
        for rs in brief.review_summaries:
            topic_items = "".join(
                f"<li><em>{escape(t.topic.capitalize())}</em>: {escape(t.sentiment)} ({t.mention_count} omtaler)</li>"
                for t in rs.sentiment_topics
            )
            reviews_parts.append(
                f"<div class='review-summary'><h3>{escape(rs.place_name)}</h3>"
                f"<p><strong>Score:</strong> {rs.rating:.1f} / 5.0 ({rs.total_reviews} anmeldelser)</p>"
                f"<ul>{topic_items}</ul></div>"
            )
        reviews_html = f"<h2>Gjestevurderinger (Google)</h2>{''.join(reviews_parts)}"

    market_html = ""
    if brief.market_observations:
        market_items = "".join(
            f"<li><strong>{escape(mo.label)}</strong>: {escape(mo.metric)} = {mo.value} {escape(mo.unit)}</li>"
            for mo in brief.market_observations
        )
        market_html = f"<h2>Markedssignaler og trender</h2><ul>{market_items}</ul>"

    signals = "".join(
        f"<li><strong>{escape(signal.id)}</strong> [{escape(signal.confidence)}]: "
        f"{escape(signal.claim)} (kilder: {escape(', '.join(signal.source_ids))})</li>"
        for signal in brief.signals
    )
    recommendations = "".join(
        f"<article><h3>{escape(item.id)}: {escape(item.action)}</h3>"
        f"<p>{escape(item.rationale)}</p>"
        f"<p>Forventet verdi: {escape(item.expected_value)} · Innsats: {escape(item.effort)}</p>"
        f"<p>Kilder: {escape(', '.join(item.source_ids))}</p></article>"
        for item in brief.recommendations
    )
    warnings = "".join(f"<li>{escape(item)}</li>" for item in brief.warnings)
    sources = "".join(
        f'<li><strong>{escape(item.source_id)}</strong>: '
        f'<a href="{escape(item.url)}">{escape(item.title)}</a> '
        f'(hentet {escape(item.fetched_at)})</li>'
        for item in brief.sources
    )
    return f"""<!doctype html>
<html lang="no"><head><meta charset="utf-8"><title>{escape(brief.title)}</title>
<style>body{{font-family:system-ui;max-width:800px;margin:2rem auto;padding:0 1rem;line-height:1.5}}.draft{{background:#fff3cd;padding:1rem;border:1px solid #e0b000}}code{{background:#eee;padding:.15rem .3rem}}.review-summary{{background:#f8f9fa;padding:1rem;margin:1rem 0;border-radius:4px}}</style>
</head><body><p class="draft"><strong>{escape(DISCLAIMER)}</strong></p>
<h1>{escape(brief.title)}</h1><p>Run-ID: <code>{escape(brief.run_id)}</code> · Status: {escape(brief.status)}</p>
{reviews_html}{market_html}
<h2>Signaler</h2><ul>{signals}</ul><h2>Anbefalte handlinger</h2>{recommendations}
<h2>Varsler</h2><ul>{warnings}</ul><h2>Kilder</h2><ul>{sources}</ul>
</body></html>"""


def render_email(brief: Brief) -> str:
    lines = [
        f"Emne: UTKAST – ukentlig beslutningsbrief – {brief.run_id}",
        "",
        DISCLAIMER,
        "",
        f"Run-ID: {brief.run_id}",
        f"Status: {brief.status}",
        "",
    ]
    if brief.review_summaries:
        lines.append("Google Omdømme:")
        for rs in brief.review_summaries:
            lines.append(f"- {rs.place_name}: {rs.rating:.1f}/5.0 ({rs.total_reviews} anmeldelser)")
        lines.append("")

    if brief.market_observations:
        lines.append("Google Trender / Markedssignaler:")
        for mo in brief.market_observations[:4]:
            lines.append(f"- {mo.label}: {mo.value} {mo.unit}")
        lines.append("")

    lines.append("Signaler:")
    for signal in brief.signals[:4]:
        lines.append(
            f"- {signal.claim} [{signal.confidence}; kilder: {', '.join(signal.source_ids)}]"
        )
    lines.extend(["", "Prioriterte handlinger:"])
    for item in brief.recommendations:
        lines.extend(
            [
                f"- {item.id}: {item.action}",
                f"  Hvorfor: {item.rationale}",
                f"  Verdi/innsats: {item.expected_value} / {item.effort}",
                f"  Kilder: {', '.join(item.source_ids)}",
            ]
        )
    if brief.warnings:
        lines.extend(["", "Må gjennomgås:"])
        lines.extend(f"- {warning}" for warning in brief.warnings)
    lines.extend(["", "Kilder:"])
    lines.extend(f"- {item.source_id}: {item.url}" for item in brief.sources)
    lines.append("")
    return "\n".join(lines)
