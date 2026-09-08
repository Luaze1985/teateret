"""Validate this generated workspace without mutating the canonical harness."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IGNORED_PARTS = {".git", ".pytest_cache", "runs"}


def collect_errors() -> list[str]:
    errors: list[str] = []
    manifest_path = ROOT / "workspace.yml"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"Ugyldig workspace.yml: {exc}"]

    for key in ("name", "profile", "created_at", "capabilities", "lifecycle", "required_paths"):
        if key not in manifest:
            errors.append(f"workspace.yml mangler felt: {key}")
    for relative_path in manifest.get("required_paths", []):
        if not (ROOT / relative_path).exists():
            errors.append(f"Mangler påkrevd sti: {relative_path}")

    for path in ROOT.rglob("*.md"):
        if any(part in IGNORED_PARTS for part in path.parts):
            continue
        try:
            first_line = path.read_text(encoding="utf-8").splitlines()[0]
        except (OSError, IndexError):
            first_line = ""
        if first_line.strip() != "---":
            errors.append(f"Markdown mangler frontmatter: {path.relative_to(ROOT)}")
    return errors


def main() -> int:
    errors = collect_errors()
    if errors:
        print("Workspace validation failed:")
        for error in errors:
            print(f" - {error}")
        return 1
    print("Workspace validation OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
