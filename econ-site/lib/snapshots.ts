import { env } from "cloudflare:workers";
import type { CountryKey } from "@/app/data/catalog";
import { DATASET_KEYS, PERSONAL_INTERVIEW_PURPOSE, hostedBondCountriesForPurpose, validateSnapshot as validateSnapshotCore } from "@/lib/snapshot-logic";
import type { SnapshotObject } from "@/lib/snapshot-logic";

export { assertNoHistoryLoss, collectChanges } from "@/lib/snapshot-logic";

export const SNAPSHOT_DATASETS = DATASET_KEYS;

export type SnapshotDataset = (typeof SNAPSHOT_DATASETS)[number];
export type JsonObject = SnapshotObject;

const MAX_RAW_FILE_BYTES = 4 * 1024 * 1024;

type StoredVersion = {
  dataset_key: string;
  version: number;
  object_key: string;
  snapshot_sha256: string;
  manifest_json: string;
  previous_version: number | null;
  restored_from_version: number | null;
  created_at: string;
  created_by: string;
};

export type VersionManifest = {
  datasetKey: SnapshotDataset;
  version: number;
  previousVersion: number | null;
  restoredFromVersion: number | null;
  createdAt: string;
  createdBy: string;
  snapshotSha256: string;
  objectKey: string;
  diffObjectKey: string;
  changeCount: number;
  recentChangeCount: number;
  rawSnapshots: Array<{ name: string; sha256: string; objectKey: string }>;
  chartAssets?: Array<{ period: string; country: string; sha256: string; objectKey: string }>;
  sourceStatus: unknown;
  summary: Record<string, unknown>;
};

function db() {
  if (!env.DB) throw new Error("The Sites D1 binding `DB` is not configured.");
  return env.DB;
}

function bucket() {
  if (!env.BUCKET) throw new Error("The Sites R2 binding `BUCKET` is not configured.");
  return env.BUCKET;
}

export function isSnapshotDataset(value: string): value is SnapshotDataset {
  return (SNAPSHOT_DATASETS as readonly string[]).includes(value);
}

type BondPurposeEnv = { BOND_PRESENTATION_PURPOSE?: string };

/** The purpose setting records operator intent; it does not assert permission or clear provider terms. */
export function getBondPresentationPurpose() {
  return (env as typeof env & BondPurposeEnv).BOND_PRESENTATION_PURPOSE === PERSONAL_INTERVIEW_PURPOSE
    ? PERSONAL_INTERVIEW_PURPOSE
    : null;
}

export function getHostedBondCountries(): CountryKey[] {
  return [...hostedBondCountriesForPurpose(getBondPresentationPurpose())] as CountryKey[];
}

export function validateSnapshot(datasetKey: SnapshotDataset, value: unknown): asserts value is JsonObject {
  validateSnapshotCore(datasetKey, value, datasetKey === "bond-yields" ? getHostedBondCountries() : undefined);
}

export async function sha256(value: string | ArrayBuffer): Promise<string> {
  const bytes = typeof value === "string" ? new TextEncoder().encode(value) : value;
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

function currentVersionSql() {
  return `SELECT v.dataset_key, v.version, v.object_key, v.snapshot_sha256, v.manifest_json,
                 v.previous_version, v.restored_from_version, v.created_at, v.created_by
          FROM snapshot_heads h
          JOIN snapshot_versions v ON v.dataset_key = h.dataset_key AND v.version = h.version
          WHERE h.dataset_key = ?`;
}

export async function getCurrentVersion(datasetKey: SnapshotDataset): Promise<StoredVersion | null> {
  return db().prepare(currentVersionSql()).bind(datasetKey).first<StoredVersion>();
}

export async function getSnapshotBody(objectKey: string): Promise<unknown> {
  const object = await bucket().get(objectKey);
  if (!object) throw new Error("The snapshot body referenced by D1 is missing from R2.");
  return object.json();
}

export function toVersionManifest(row: StoredVersion): VersionManifest {
  const parsed = JSON.parse(row.manifest_json) as Omit<VersionManifest, "datasetKey" | "version" | "previousVersion" | "restoredFromVersion" | "createdAt" | "createdBy" | "snapshotSha256" | "objectKey">;
  return {
    ...parsed,
    datasetKey: row.dataset_key as SnapshotDataset,
    version: row.version,
    previousVersion: row.previous_version,
    restoredFromVersion: row.restored_from_version,
    createdAt: row.created_at,
    createdBy: row.created_by,
    snapshotSha256: row.snapshot_sha256,
    objectKey: row.object_key,
  };
}

export const getVersionManifest = toVersionManifest;

export async function listVersions(datasetKey: SnapshotDataset, limit = 100) {
  const boundedLimit = Math.max(1, Math.min(250, limit));
  const rows = await db().prepare(
    `SELECT dataset_key, version, object_key, snapshot_sha256, manifest_json,
            previous_version, restored_from_version, created_at, created_by
     FROM snapshot_versions WHERE dataset_key = ? ORDER BY version DESC LIMIT ?`,
  ).bind(datasetKey, boundedLimit).all<StoredVersion>();
  return (rows.results ?? []).map(toVersionManifest);
}

export async function getVersion(datasetKey: SnapshotDataset, version: number): Promise<StoredVersion | null> {
  return db().prepare(
    `SELECT dataset_key, version, object_key, snapshot_sha256, manifest_json,
            previous_version, restored_from_version, created_at, created_by
     FROM snapshot_versions WHERE dataset_key = ? AND version = ?`,
  ).bind(datasetKey, version).first<StoredVersion>();
}

export function getRawFileLimit() {
  return MAX_RAW_FILE_BYTES;
}

export function getBucket() {
  return bucket();
}

export function getDatabase() {
  return db();
}
