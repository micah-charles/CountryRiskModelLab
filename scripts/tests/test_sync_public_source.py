"""Verify the public-code export boundary with disposable local Git fixtures."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "sync_public_source.py"
spec = importlib.util.spec_from_file_location("public_sync", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class PublicSourceBoundaryTests(unittest.TestCase):
    def test_private_content_never_enters_source_export(self):
        for path in ["docs/ECON_INTEGRATION_REVIEW.md", "backend/app/research_cases/example/case.json", "backend/app/data_registry/private.json", "econ-site/private-seed/input.json", "econ-site/.private-cache/copy.json", "econ-site/.sites-runtime/execution-profile.json", "econ-site/.vinext/dev/lock.json", "government-bond-yields/data/raw/a.csv", "hk-china-demand-monitor/web/public/data/metrics.json", "econ-site/.env.production", "econ-site/.openai/hosting.json"]:
            with self.subTest(path=path):
                self.assertFalse(module.eligible(Path(path)))

    def test_maintained_worker_sources_are_not_treated_as_build_output(self):
        for path in ["econ-site/.openai/hosting.example.json", "econ-site/app/data/catalog.ts", "econ-site/build/sites-worker.ts", "econ-site/build/sites-vite-plugin.ts", "econ-site/lib/connector-contract.mts", "econ-site/public/favicon.svg", "econ-site/drizzle/0000_schema.sql"]:
            with self.subTest(path=path):
                self.assertTrue(module.eligible(Path(path)))
        self.assertFalse(module.eligible(Path("econ-site/dist/server/app.js")))

    def test_dry_run_and_apply_preserve_private_source_and_remote_only_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, target = root / "source", root / "checkout"
            (source / "frontend").mkdir(parents=True)
            (source / "frontend" / "safe.ts").write_text("export const safe = true;")
            (source / "backend/app/research_cases/private").mkdir(parents=True)
            private = source / "backend/app/research_cases/private/case.json"
            private.write_text('{"private":"do not publish"}')
            target.mkdir()
            subprocess.run(["git", "init", "-q", str(target)], check=True)
            subprocess.run(["git", "-C", str(target), "remote", "add", "origin", "https://github.com/micah-charles/CountryRiskModelLab.git"], check=True)
            retained = target / "remote-only.md"
            retained.write_text("Preserve upstream work")
            command = [sys.executable, str(SCRIPT), "--source", str(source), "--checkout", str(target)]
            subprocess.run(command, check=True, capture_output=True)
            self.assertFalse((target / "frontend/safe.ts").exists())
            subprocess.run(command + ["--apply"], check=True, capture_output=True)
            self.assertTrue((target / "frontend/safe.ts").exists())
            self.assertFalse((target / "backend/app/research_cases/private/case.json").exists())
            self.assertTrue(private.exists())
            self.assertEqual(retained.read_text(), "Preserve upstream work")


if __name__ == "__main__":
    unittest.main()
