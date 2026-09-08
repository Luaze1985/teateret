from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, Field

from .models import (
    AnalysisOutput,
    Brief,
    MarketObservation,
    PipelineResult,
    ReaderOutput,
    ReviewSummary,
    SalesObservation,
    SourceDocument,
    SourceReference,
    SourceSpec,
    VerificationOutput,
)
from .render import render_email, render_html, render_markdown
from .security import RepoPaths, safe_error_summary, scan_public_artifact


class PipelineSettings(BaseModel):
    live_mode_enabled: bool = False
    max_model_calls: int = Field(default=4, ge=3, le=10)
    max_retries: int = Field(default=1, ge=0, le=1)
    max_total_tokens: int = Field(default=50_000, ge=1_000, le=500_000)
    max_input_chars_per_call: int = Field(default=120_000, ge=1_000, le=1_000_000)
    model_name: str = "fixture"
    config_version: str = "v1"
    decision_questions: list[str] = Field(min_length=1, max_length=5)
    prompt_versions: dict[str, str] = Field(
        default_factory=lambda: {
            "reader": "v1",
            "analyst": "v1",
            "verifier": "v1",
        }
    )


class Fetcher(Protocol):
    def fetch(self, source: SourceSpec) -> SourceDocument: ...


class RoleRunner(Protocol):
    call_count: int

    def read_sources(self, documents: list[SourceDocument]) -> ReaderOutput: ...

    def analyze(
        self,
        signals: list,
        observations: list[SalesObservation],
        decision_questions: list[str],
        market_observations: list[MarketObservation] | None = None,
        review_summaries: list[ReviewSummary] | None = None,
    ) -> AnalysisOutput: ...

    def verify(
        self,
        signals: list,
        recommendations: list,
        documents: list[SourceDocument],
        decision_questions: list[str],
    ) -> VerificationOutput: ...


class BriefPipeline:
    def __init__(
        self,
        repo_root: Path,
        settings: PipelineSettings,
        fetcher: Fetcher,
        roles: RoleRunner,
    ):
        self.paths = RepoPaths(repo_root)
        self.settings = settings
        self.fetcher = fetcher
        self.roles = roles

    def _check_budget(self) -> None:
        if getattr(self.roles, "call_count", 0) >= self.settings.max_model_calls:
            raise RuntimeError("Maksimalt antall modellkall er nådd.")

    def _write_json(self, path: Path, payload) -> None:
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )

    def _hash_payload(self, payload) -> str:
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def run(
        self,
        sources: list[SourceSpec],
        observations: list[SalesObservation],
        run_id: str | None = None,
        market_observations: list[MarketObservation] | None = None,
        review_summaries: list[ReviewSummary] | None = None,
    ) -> PipelineResult:
        run_id = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?", run_id):
            raise ValueError("Ugyldig run-ID.")
        staging = self.paths.output_path(Path("runs") / ".staging" / run_id)
        final = self.paths.output_path(Path("runs") / run_id)
        if staging.exists() or final.exists():
            raise FileExistsError(f"Run finnes allerede: {run_id}")
        staging.mkdir(parents=True)
        started_at = datetime.now(timezone.utc)
        events: list[dict] = [{"event": "run_started", "at": started_at.isoformat()}]
        source_errors: list[dict] = []
        documents: list[SourceDocument] = []

        for source in [item for item in sources if item.enabled]:
            events.append({"event": "source_attempted", "source_id": source.id})
            try:
                document = self.fetcher.fetch(source)
                documents.append(document)
                events.append({"event": "source_succeeded", "source_id": source.id})
            except Exception as exc:  # source failures are isolated and reported
                source_errors.append(
                    {"source_id": source.id, "error": safe_error_summary(exc)}
                )
                events.append({"event": "source_failed", "source_id": source.id})

        input_hash = self._hash_payload(
            {
                "sources": [source.id for source in sources if source.enabled],
                "documents": [document.content_sha256 for document in documents],
                "observations": [item.model_dump(mode="json") for item in observations],
                "decision_questions": self.settings.decision_questions,
            }
        )
        if not documents:
            return self._finish_blocked(
                staging,
                final,
                run_id,
                started_at,
                "Ingen godkjente kilder kunne leses.",
                source_errors,
                events,
                input_hash,
                sources,
            )

        try:
            self._check_budget()
            events.append({"event": "role_started", "role": "reader"})
            reader = self.roles.read_sources(documents)
            events.append({"event": "role_completed", "role": "reader"})
            known_sources = {document.source_id for document in documents}
            for signal in reader.signals:
                if not set(signal.source_ids).issubset(known_sources):
                    raise ValueError("Kildeleser returnerte ukjent kilde-ID.")

            self._check_budget()
            events.append({"event": "role_started", "role": "analyst"})
            analysis = self.roles.analyze(
                reader.signals,
                observations,
                self.settings.decision_questions,
                market_observations=market_observations,
                review_summaries=review_summaries,
            )
            events.append({"event": "role_completed", "role": "analyst"})
            for recommendation in analysis.recommendations:
                if not set(recommendation.source_ids).issubset(known_sources):
                    raise ValueError("Analytiker returnerte ukjent kilde-ID.")

            self._check_budget()
            events.append({"event": "role_started", "role": "verifier"})
            verification = self.roles.verify(
                reader.signals,
                analysis.recommendations,
                documents,
                self.settings.decision_questions,
            )
            events.append({"event": "role_completed", "role": "verifier"})
            known_recommendations = {item.id for item in analysis.recommendations}
            if not set(verification.approved_recommendation_ids).issubset(known_recommendations):
                raise ValueError("Kontrollør returnerte ukjent anbefalings-ID.")
            if verification.status == "fail":
                raise ValueError("Kontrolløren avviste beslutningsgrunnlaget.")

            approved = [
                item
                for item in analysis.recommendations
                if item.id in verification.approved_recommendation_ids
            ]
            warnings = [
                *(f"Kilde {item['source_id']} feilet: {item['error']}" for item in source_errors),
                *verification.warnings,
            ]
            status = "warning" if warnings or verification.status == "warn" else "completed"
            brief = Brief(
                run_id=run_id,
                created_at=datetime.now(timezone.utc),
                status=status,
                signals=reader.signals,
                recommendations=approved,
                source_ids=sorted(known_sources),
                sources=[
                    SourceReference(
                        source_id=document.source_id,
                        title=document.title,
                        url=document.url,
                        published_at=document.published_at,
                        fetched_at=document.fetched_at,
                    )
                    for document in documents
                ],
                warnings=warnings,
                market_observations=market_observations or [],
                review_summaries=review_summaries or [],
            )
            rendered = {
                "brief.md": render_markdown(brief),
                "brief.html": render_html(brief),
                "email.txt": render_email(brief),
            }
            pii_findings = {
                name: scan_public_artifact(content) for name, content in rendered.items()
            }
            pii_findings = {name: items for name, items in pii_findings.items() if items}
            if pii_findings:
                raise ValueError("Genererte artefakter inneholder direkte kontaktopplysninger.")
            for name, content in rendered.items():
                (staging / name).write_text(content, encoding="utf-8")
                events.append({"event": "output_written", "file": name})
            if source_errors:
                self._write_json(staging / "errors.json", source_errors)
            outputs = [
                {
                    "file": name,
                    "sha256": hashlib.sha256((staging / name).read_bytes()).hexdigest(),
                }
                for name in rendered
            ]
            finished_at = datetime.now(timezone.utc)
            events.append({"event": "pii_scan_completed", "status": "pass"})
            events.append({"event": f"run_{status}", "at": finished_at.isoformat()})
            manifest = self._manifest(
                run_id=run_id,
                status=status,
                started_at=started_at,
                finished_at=finished_at,
                stop_reason=None,
                input_hash=input_hash,
                sources=sources,
                documents=documents,
                source_errors=source_errors,
                outputs=outputs,
                warnings=warnings,
            )
            self._write_json(staging / "manifest.json", manifest)
            self._write_json(staging / "events.json", events)
            final.parent.mkdir(parents=True, exist_ok=True)
            staging.replace(final)
            return PipelineResult(run_id=run_id, status=status, run_dir=final)
        except Exception as exc:
            safe_error = safe_error_summary(exc)
            events.append({"event": "role_failed", "error": safe_error})
            return self._finish_blocked(
                staging,
                final,
                run_id,
                started_at,
                safe_error,
                source_errors,
                events,
                input_hash,
                sources,
                documents=documents,
            )

    def _manifest(
        self,
        *,
        run_id,
        status,
        started_at,
        finished_at,
        stop_reason,
        input_hash,
        sources,
        documents,
        source_errors,
        outputs,
        warnings,
    ) -> dict:
        usage = getattr(self.roles, "usage", {})
        return {
            "run_id": run_id,
            "started_at": started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
            "status": status,
            "stop_reason": stop_reason,
            "config_version": self.settings.config_version,
            "prompt_versions": self.settings.prompt_versions,
            "decision_questions": self.settings.decision_questions,
            "decision_questions_sha256": self._hash_payload(
                self.settings.decision_questions
            ),
            "input_sha256": input_hash,
            "sources_attempted": [item.id for item in sources if item.enabled],
            "sources_succeeded": [item.source_id for item in documents],
            "source_records": [
                {
                    "source_id": item.source_id,
                    "url": item.url,
                    "published_at": item.published_at,
                    "fetched_at": item.fetched_at,
                    "content_sha256": item.content_sha256,
                    "extractor": item.extractor,
                }
                for item in documents
            ],
            "sources_failed": [item["source_id"] for item in source_errors],
            "model": getattr(self.roles, "model_name", self.settings.model_name),
            "call_count": getattr(self.roles, "call_count", 0),
            "retry_count": getattr(self.roles, "retry_count", 0),
            "token_usage": usage,
            "estimated_cost": getattr(self.roles, "estimated_cost", None),
            "outputs": outputs,
            "pii_scan_status": "pass" if status in ("completed", "warning") else "not_publishable",
            "warnings": warnings,
        }

    def _finish_blocked(
        self,
        staging: Path,
        final: Path,
        run_id: str,
        started_at: datetime,
        reason: str,
        errors: list[dict],
        events: list[dict],
        input_hash: str,
        sources: list[SourceSpec],
        documents: list[SourceDocument] | None = None,
    ) -> PipelineResult:
        documents = documents or []
        finished_at = datetime.now(timezone.utc)
        safe_reason = reason
        if staging.exists():
            shutil.rmtree(staging)
        staging.mkdir(parents=True)
        errors = [*errors, {"scope": "run", "error": safe_reason}]
        events.append({"event": "run_blocked", "at": finished_at.isoformat()})
        self._write_json(staging / "errors.json", errors)
        manifest = self._manifest(
            run_id=run_id,
            status="blocked",
            started_at=started_at,
            finished_at=finished_at,
            stop_reason=safe_reason,
            input_hash=input_hash,
            sources=sources,
            documents=documents,
            source_errors=[item for item in errors if "source_id" in item],
            outputs=[
                {
                    "file": "errors.json",
                    "sha256": hashlib.sha256((staging / "errors.json").read_bytes()).hexdigest(),
                }
            ],
            warnings=[],
        )
        self._write_json(staging / "manifest.json", manifest)
        self._write_json(staging / "events.json", events)
        final.parent.mkdir(parents=True, exist_ok=True)
        staging.replace(final)
        return PipelineResult(
            run_id=run_id,
            status="blocked",
            run_dir=final,
            stop_reason=safe_reason,
        )
