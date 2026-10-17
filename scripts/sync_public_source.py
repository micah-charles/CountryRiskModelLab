#!/usr/bin/env python3
"""Copy reviewable source into an existing Git checkout; never copy research data.

The source workspace is intentionally not reset, cleaned, or made a Git worktree.
Remote-only files are preserved. Inspect the destination diff before committing.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

SOURCE_DIRS = ("frontend", "backend", "docs", "qa", "scripts", ".github", "government-bond-yields", "hk-china-demand-monitor", "econ-site")
ROOT_FILES = ("README.md", ".gitignore", ".dockerignore", ".env.example", "Dockerfile.frontend", "docker-compose.yml", "index.html", "package.json", "package-lock.json", "tsconfig.json", "vite.config.ts")
SKIP_PARTS = {"node_modules", ".venv", "venv", "__pycache__", ".pytest_cache", ".git", ".openai", ".wrangler", ".sites-runtime", ".next", ".vinext", "dist", "build", "outputs", "data", "data_registry", "research_cases", "state", "logs", "reports", "release_evidence", "screenshots", "playwright-report", "test-results", "work", "private-data", "private-seed", "source-snapshots"}
EXTENSIONS = {".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".mts", ".cts", ".css", ".html", ".md", ".json", ".yaml", ".yml", ".toml", ".sh", ".sql", ".txt", ".svg", ".LICENSE"}
NAMES = {"Dockerfile", ".gitignore", ".dockerignore", ".env.example"}


def eligible(relative: Path) -> bool:
    # The Sites starter's build/ contains maintained Worker/plugin SOURCE.
    if relative.as_posix() in {
        "econ-site/.openai/hosting.example.json",
        "econ-site/app/data/catalog.ts",
        "econ-site/build/connector-preview-plugin.mjs", "econ-site/build/connector-preview-worker.mjs",
        "econ-site/build/sites-vite-plugin.LICENSE", "econ-site/build/sites-vite-plugin.ts", "econ-site/build/sites-worker.ts",
    }:
        return True
    if any(part in SKIP_PARTS for part in relative.parts):
        return False
    if relative.name.startswith(".env") and relative.name != ".env.example":
        return False
    if any(part.startswith(".private") for part in relative.parts):
        return False
    if relative.as_posix() in {"docs/ECON_INTEGRATION_REVIEW.md", "qa/browser-use/button-qa-report.md", "qa/browser-use/button-qa-results.json"}:
        return False
    if relative.name in {"pnpm-lock.yaml", "package-lock.json"}:
        return True
    return relative.name in NAMES or relative.suffix in EXTENSIONS


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--apply", action="store_true", help="Default is a dry run")
    args = parser.parse_args()
    source, target = args.source.resolve(), args.checkout.resolve()
    if source == target or source in target.parents:
        raise SystemExit("Use a separate checkout outside the source workspace")
    subprocess.run(["git", "-C", str(target), "rev-parse", "--show-toplevel"], check=True, capture_output=True)
    remote = subprocess.check_output(["git", "-C", str(target), "remote", "get-url", "origin"], text=True).strip()
    if remote not in {"https://github.com/micah-charles/CountryRiskModelLab.git", "git@github.com:micah-charles/CountryRiskModelLab.git"}:
        raise SystemExit("Unexpected destination repository; no files copied")
    candidates = [source / name for name in ROOT_FILES]
    for name in SOURCE_DIRS:
        candidates.extend((source / name).rglob("*"))
    changed = []
    for path in sorted(set(candidates)):
        rel = path.relative_to(source)
        if path.is_symlink() or not path.is_file() or not eligible(rel):
            continue
        destination = target / rel
        content = path.read_bytes()
        if destination.exists() and destination.read_bytes() == content:
            continue
        changed.append(rel.as_posix())
        if args.apply:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination)
    print("Applied" if args.apply else "Dry run", len(changed), "source file changes; no data or remote-only files removed")
    for name in changed:
        print(name)


if __name__ == "__main__":
    main()
