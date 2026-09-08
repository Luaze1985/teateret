from __future__ import annotations

import argparse
import os
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from .agents import FixtureRoles, StructuredClaudeRoles
from .config import (
    load_csv_mapping,
    load_google_places_config,
    load_google_trends_config,
    load_runtime_settings,
    load_sources,
)
from .csv_adapter import load_aggregated_csv
from .fetcher import FixtureFetcher, SafeHttpFetcher
from .google_places import FixtureGooglePlacesAdapter, GooglePlacesAdapter
from .google_trends import FixtureGoogleTrendsAdapter, GoogleTrendsAdapter
from .models import MarketObservation, ReviewSummary, SourceSpec
from .pipeline import BriefPipeline
from .schema_events import FixtureSchemaEventExtractor, SchemaEventExtractor
from .security import RepoPaths, SourcePolicy


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Lag et kontrollert beslutningsbrief-utkast.")
    parser.add_argument("--mode", choices=("demo", "live"), default="demo")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--run-id")
    parser.add_argument("--sources")
    parser.add_argument("--sales")
    parser.add_argument("--mapping")
    parser.add_argument("--runtime", default="config/runtime.yml")
    parser.add_argument("--allow-live-network", action="store_true")
    parser.add_argument("--allow-live-model", action="store_true")
    parser.add_argument(
        "--google-places",
        action="store_true",
        help="Inkluder Google Business Profile (GBP) anmeldelser og rating.",
    )
    parser.add_argument(
        "--google-places-config",
        default="config/google_places_config.yml",
        help="Sti til Google Places-konfigurasjon.",
    )
    parser.add_argument(
        "--google-trends",
        action="store_true",
        help="Inkluder regional søkeinteresse fra Google Trends.",
    )
    parser.add_argument(
        "--google-trends-config",
        default="config/google_trends_config.yml",
        help="Sti til Google Trends-konfigurasjon.",
    )
    parser.add_argument(
        "--schema-events",
        action="store_true",
        help="Inkluder Schema.org strukturerte arrangementsdata (JSON-LD).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.repo_root).resolve(strict=True)
    paths = RepoPaths(root)
    settings = load_runtime_settings(paths.input_path(args.runtime))

    market_observations: list[MarketObservation] = []
    review_summaries: list[ReviewSummary] = []

    if args.mode == "demo":
        source_path = paths.input_path(args.sources or "sample_data/demo_sources.yml")
        sales_path = paths.input_path(args.sales or "sample_data/gastroplanner_sample_2026.csv")
        mapping_path = paths.input_path(
            args.mapping or "config/gastroplanner_mapping.example.yml"
        )
        sources, fixture_paths = load_sources(source_path)
        fetcher = FixtureFetcher(fixture_paths, paths)
        roles = FixtureRoles()

        if args.google_places:
            gp_config = load_google_places_config(paths.input_path(args.google_places_config))
            gp_fixture_path = paths.input_path("sample_data/google_places_fixture.json")
            gp_adapter = FixtureGooglePlacesAdapter(gp_fixture_path, gp_config)
            for res in gp_adapter.fetch_all():
                review_summaries.append(res.review_summary)
                market_observations.extend(res.observations)

        if args.google_trends:
            gt_config = load_google_trends_config(paths.input_path(args.google_trends_config))
            gt_fixture_path = paths.input_path("sample_data/google_trends_fixture.json")
            gt_adapter = FixtureGoogleTrendsAdapter(gt_fixture_path, gt_config)
            market_observations.extend(gt_adapter.fetch())

        if args.schema_events:
            schema_fixture_path = paths.input_path("sample_data/schema_events_fixture.json")
            schema_extractor = FixtureSchemaEventExtractor(schema_fixture_path)
            schema_source = SourceSpec(
                id="schema-events-teateret",
                name="Schema.org Teateret (JSON-LD)",
                url="https://www.teateret.no/program",
                region="local",
                topic="events",
                enabled=True,
            )
            sources.append(schema_source)
            fixture_paths[schema_source.id] = "sample_data/schema_events_fixture.json"
            # Schema extractor returns SourceDocument directly; we register it in fetcher
            fetcher = FixtureFetcher(fixture_paths, paths)
    else:
        if not settings.live_mode_enabled:
            raise SystemExit(
                "Live-modus er deaktivert i runtime-konfigurasjonen frem til sikkerhetsportene er godkjent."
            )
        if not (args.allow_live_network and args.allow_live_model):
            raise SystemExit(
                "Live-modus krever både --allow-live-network og --allow-live-model."
            )
        if not args.sales:
            raise SystemExit("Live-modus krever --sales med en relativ filsti i repoet.")
        source_path = paths.input_path(args.sources or "config/sources.yml")
        sales_path = paths.input_path(args.sales)
        mapping_path = paths.input_path(
            args.mapping or "config/gastroplanner_mapping.example.yml"
        )
        sources, _ = load_sources(source_path)
        allowed_hosts = {
            urlsplit(str(source.url)).hostname.casefold()
            for source in sources
            if source.enabled and urlsplit(str(source.url)).hostname
        }
        source_policy = SourcePolicy(allowed_hosts)
        fetcher = SafeHttpFetcher(source_policy)

        if args.google_places:
            gp_config = load_google_places_config(paths.input_path(args.google_places_config))
            gp_adapter = GooglePlacesAdapter(gp_config)
            for res in gp_adapter.fetch_all():
                review_summaries.append(res.review_summary)
                market_observations.extend(res.observations)

        if args.google_trends:
            gt_config = load_google_trends_config(paths.input_path(args.google_trends_config))
            gt_adapter = GoogleTrendsAdapter(gt_config)
            market_observations.extend(gt_adapter.fetch())

        if args.schema_events:
            schema_extractor = SchemaEventExtractor(source_policy)

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        model = os.environ.get("ANTHROPIC_MODEL")
        if not api_key or not model:
            raise SystemExit("ANTHROPIC_API_KEY og ANTHROPIC_MODEL må settes i miljøet.")
        import anthropic

        roles = StructuredClaudeRoles(
            anthropic.Anthropic(
                api_key=api_key,
                max_retries=0,
                timeout=httpx.Timeout(30.0, connect=5.0, write=10.0, pool=5.0),
            ),
            model,
            max_calls=settings.max_model_calls,
            max_retries=settings.max_retries,
            max_total_tokens=settings.max_total_tokens,
            max_input_chars_per_call=settings.max_input_chars_per_call,
        )

    mapping = load_csv_mapping(mapping_path)
    observations = load_aggregated_csv(sales_path, mapping)
    result = BriefPipeline(root, settings, fetcher, roles).run(
        sources,
        observations,
        run_id=args.run_id,
        market_observations=market_observations or None,
        review_summaries=review_summaries or None,
    )
    print(f"STATUS: {result.status.upper()}")
    print(f"RUN: {result.run_id}")
    print(f"OUTPUT: {result.run_dir}")
    if result.stop_reason:
        print(f"STOPPGRUNN: {result.stop_reason}")
    return 0 if result.status in {"completed", "warning"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
