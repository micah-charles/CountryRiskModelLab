import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";

const siteRoot = fileURLToPath(new URL("../", import.meta.url));
const lock = JSON.parse(readFileSync(new URL("../package-lock.json", import.meta.url), "utf8"));
const packageVersion = lock.packages?.["node_modules/react-server-dom-webpack"]?.version;

if (!packageVersion) {
  console.error("react-server-dom-webpack is missing from the Site lockfile.");
  process.exit(1);
}

const versionParts = packageVersion.split(".").map(Number);
if (versionParts.some((part) => !Number.isInteger(part))) {
  console.error(`Unrecognized react-server-dom-webpack version: ${packageVersion}`);
  process.exit(1);
}

const [major, minor, patch] = versionParts;
if (major < 19 || (major === 19 && (minor < 2 || (minor === 2 && patch < 8)))) {
  console.error(`Bundled RSC runtime ${packageVersion} is older than the fixed 19.2.8 patch.`);
  process.exit(1);
}

const npm = process.platform === "win32" ? "npm.cmd" : "npm";
const audit = spawnSync(npm, ["audit", "--json", "--include=dev"], {
  cwd: siteRoot,
  encoding: "utf8",
  maxBuffer: 16 * 1024 * 1024,
});

if (audit.error) {
  console.error(`Could not run npm audit: ${audit.error.message}`);
  process.exit(1);
}

let report;
try {
  report = JSON.parse(audit.stdout);
} catch {
  console.error("npm audit did not return a parseable JSON report.");
  if (audit.stderr) console.error(audit.stderr.trim());
  process.exit(1);
}

if (!report.vulnerabilities || !report.metadata?.dependencies) {
  console.error("npm audit returned an incomplete report.");
  process.exit(1);
}

const rsc = report.vulnerabilities["react-server-dom-webpack"];
if (rsc) {
  const advisories = (rsc.via ?? [])
    .filter((item) => typeof item === "object" && item.url)
    .map((item) => `${item.title} (${item.url})`);
  console.error(`Bundled RSC runtime ${packageVersion} is reported vulnerable.`);
  for (const advisory of advisories) console.error(`- ${advisory}`);
  process.exit(1);
}

console.log(`Bundled RSC runtime ${packageVersion} has no npm audit finding.`);
