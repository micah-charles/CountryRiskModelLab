CREATE TABLE `snapshot_diffs` (
	`dataset_key` text NOT NULL,
	`version` integer NOT NULL,
	`diff_object_key` text NOT NULL,
	`change_count` integer NOT NULL,
	`recent_change_count` integer NOT NULL,
	`observed_at` text NOT NULL,
	PRIMARY KEY(`dataset_key`, `version`)
);
--> statement-breakpoint
CREATE TABLE `snapshot_heads` (
	`dataset_key` text PRIMARY KEY NOT NULL,
	`version` integer NOT NULL,
	`updated_at` text NOT NULL
);
--> statement-breakpoint
CREATE TABLE `snapshot_versions` (
	`dataset_key` text NOT NULL,
	`version` integer NOT NULL,
	`object_key` text NOT NULL,
	`snapshot_sha256` text NOT NULL,
	`manifest_json` text NOT NULL,
	`previous_version` integer,
	`restored_from_version` integer,
	`created_at` text NOT NULL,
	`created_by` text NOT NULL,
	PRIMARY KEY(`dataset_key`, `version`)
);
