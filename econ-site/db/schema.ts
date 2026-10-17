import { integer, primaryKey, sqliteTable, text } from "drizzle-orm/sqlite-core";

/** Immutable version metadata. Snapshot bodies and raw source files live in R2. */
export const snapshotVersions = sqliteTable(
  "snapshot_versions",
  {
    datasetKey: text("dataset_key").notNull(),
    version: integer("version").notNull(),
    objectKey: text("object_key").notNull(),
    snapshotSha256: text("snapshot_sha256").notNull(),
    manifestJson: text("manifest_json").notNull(),
    previousVersion: integer("previous_version"),
    restoredFromVersion: integer("restored_from_version"),
    createdAt: text("created_at").notNull(),
    createdBy: text("created_by").notNull(),
  },
  (table) => [primaryKey({ columns: [table.datasetKey, table.version] })],
);

/** One pointer per dataset. Updating this row makes a new version current. */
export const snapshotHeads = sqliteTable("snapshot_heads", {
  datasetKey: text("dataset_key").primaryKey(),
  version: integer("version").notNull(),
  updatedAt: text("updated_at").notNull(),
});

/** Append-only revision summaries; full diffs are immutable objects in R2. */
export const snapshotDiffs = sqliteTable(
  "snapshot_diffs",
  {
    datasetKey: text("dataset_key").notNull(),
    version: integer("version").notNull(),
    diffObjectKey: text("diff_object_key").notNull(),
    changeCount: integer("change_count").notNull(),
    recentChangeCount: integer("recent_change_count").notNull(),
    observedAt: text("observed_at").notNull(),
  },
  (table) => [
    primaryKey({ columns: [table.datasetKey, table.version] }),
  ],
);
