PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS "admin_users" (
  "id" TEXT PRIMARY KEY NOT NULL DEFAULT (lower(hex(randomblob(16)))),
  "created_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  "updated_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  "email" TEXT NOT NULL,
  "password_hash" TEXT NOT NULL,
  "active" INTEGER NOT NULL DEFAULT 1,
  UNIQUE ("email"),
  CHECK (email = lower(email))
);

CREATE TABLE IF NOT EXISTS "article_categories" (
  "id" TEXT PRIMARY KEY NOT NULL DEFAULT (lower(hex(randomblob(16)))),
  "created_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  "updated_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  "name" TEXT NOT NULL,
  "slug" TEXT NOT NULL,
  UNIQUE ("name"),
  UNIQUE ("slug")
);

CREATE TABLE IF NOT EXISTS "auth_rate_limits" (
  "key" TEXT PRIMARY KEY NOT NULL,
  "attempts" INTEGER NOT NULL,
  "expires_at" TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS "ix_auth_rate_limits_expires_at" ON "auth_rate_limits" ("expires_at");

CREATE TABLE IF NOT EXISTS "cases" (
  "id" TEXT PRIMARY KEY NOT NULL DEFAULT (lower(hex(randomblob(16)))),
  "created_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  "updated_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  "company" TEXT NOT NULL,
  "title" TEXT NOT NULL,
  "period" TEXT,
  "problem" TEXT,
  "solution" TEXT,
  "architecture" TEXT,
  "technologies" TEXT NOT NULL DEFAULT '[]',
  "results" TEXT,
  "links" TEXT NOT NULL DEFAULT '[]',
  "confidential" INTEGER NOT NULL DEFAULT 1,
  "slug" TEXT NOT NULL,
  "status" TEXT NOT NULL DEFAULT 'draft',
  "featured" INTEGER NOT NULL DEFAULT 0,
  "sort_order" INTEGER NOT NULL DEFAULT 0,
  "published_at" TEXT,
  "scheduled_at" TEXT,
  "archived_at" TEXT,
  UNIQUE ("slug"),
  CHECK (status <> 'published' OR confidential = false),
  CHECK (status IN ('draft','scheduled','published','archived'))
);

CREATE INDEX IF NOT EXISTS "ix_cases_status" ON "cases" ("status");

CREATE TABLE IF NOT EXISTS "contact_messages" (
  "id" TEXT PRIMARY KEY NOT NULL DEFAULT (lower(hex(randomblob(16)))),
  "created_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  "updated_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  "name" TEXT NOT NULL,
  "email" TEXT NOT NULL,
  "company" TEXT,
  "role" TEXT,
  "subject" TEXT NOT NULL,
  "message" TEXT NOT NULL,
  "consent" INTEGER NOT NULL,
  "privacy_version" TEXT NOT NULL,
  "status" TEXT NOT NULL DEFAULT 'new',
  "internal_notes" TEXT,
  "notified_at" TEXT,
  CHECK (consent = true),
  CHECK (status IN ('new','reviewing','replied','archived'))
);

CREATE INDEX IF NOT EXISTS "ix_contact_messages_created_at" ON "contact_messages" ("created_at");

CREATE INDEX IF NOT EXISTS "ix_contact_messages_status" ON "contact_messages" ("status");

CREATE TABLE IF NOT EXISTS "contact_tickets" (
  "token_hash" TEXT PRIMARY KEY NOT NULL,
  "created_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  "expires_at" TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS "ix_contact_tickets_expires_at" ON "contact_tickets" ("expires_at");

CREATE TABLE IF NOT EXISTS "pages" (
  "id" TEXT PRIMARY KEY NOT NULL DEFAULT (lower(hex(randomblob(16)))),
  "created_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  "updated_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  "title" TEXT NOT NULL,
  "locale" TEXT NOT NULL DEFAULT 'pt-BR',
  "body_html" TEXT,
  "seo_title" TEXT,
  "meta_description" TEXT,
  "slug" TEXT NOT NULL,
  "status" TEXT NOT NULL DEFAULT 'draft',
  "featured" INTEGER NOT NULL DEFAULT 0,
  "sort_order" INTEGER NOT NULL DEFAULT 0,
  "published_at" TEXT,
  "scheduled_at" TEXT,
  "archived_at" TEXT,
  UNIQUE ("slug"),
  CHECK (status IN ('draft','scheduled','published','archived'))
);

CREATE INDEX IF NOT EXISTS "ix_pages_status" ON "pages" ("status");

CREATE TABLE IF NOT EXISTS "site_settings" (
  "id" TEXT PRIMARY KEY NOT NULL DEFAULT (lower(hex(randomblob(16)))),
  "created_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  "updated_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  "key" TEXT NOT NULL,
  "value" TEXT NOT NULL DEFAULT '{}',
  UNIQUE ("key")
);

CREATE TABLE IF NOT EXISTS "skill_categories" (
  "id" TEXT PRIMARY KEY NOT NULL DEFAULT (lower(hex(randomblob(16)))),
  "created_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  "updated_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  "name" TEXT NOT NULL,
  "sort_order" INTEGER NOT NULL DEFAULT 0,
  UNIQUE ("name")
);

CREATE TABLE IF NOT EXISTS "admin_sessions" (
  "id" TEXT PRIMARY KEY NOT NULL DEFAULT (lower(hex(randomblob(16)))),
  "created_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  "updated_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  "admin_id" TEXT NOT NULL,
  "token_hash" TEXT NOT NULL,
  "csrf_hash" TEXT NOT NULL,
  "expires_at" TEXT NOT NULL,
  "revoked_at" TEXT,
  UNIQUE ("token_hash"),
  FOREIGN KEY ("admin_id") REFERENCES "admin_users" ("id") ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS "ix_admin_sessions_admin_id" ON "admin_sessions" ("admin_id");

CREATE INDEX IF NOT EXISTS "ix_admin_sessions_expires_at" ON "admin_sessions" ("expires_at");

CREATE TABLE IF NOT EXISTS "audit_logs" (
  "id" TEXT PRIMARY KEY NOT NULL DEFAULT (lower(hex(randomblob(16)))),
  "created_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  "updated_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  "actor_id" TEXT,
  "action" TEXT NOT NULL,
  "entity_type" TEXT,
  "entity_id" TEXT,
  "details" TEXT NOT NULL DEFAULT '{}',
  FOREIGN KEY ("actor_id") REFERENCES "admin_users" ("id") ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS "ix_audit_logs_created_at" ON "audit_logs" ("created_at");

CREATE INDEX IF NOT EXISTS "ix_audit_logs_actor_id" ON "audit_logs" ("actor_id");

CREATE TABLE IF NOT EXISTS "case_metrics" (
  "id" TEXT PRIMARY KEY NOT NULL DEFAULT (lower(hex(randomblob(16)))),
  "created_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  "updated_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  "case_id" TEXT NOT NULL,
  "label" TEXT NOT NULL,
  "value" TEXT NOT NULL,
  "evidence" TEXT NOT NULL,
  FOREIGN KEY ("case_id") REFERENCES "cases" ("id") ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS "ix_case_metrics_case_id" ON "case_metrics" ("case_id");

CREATE TABLE IF NOT EXISTS "cms_entries" (
  "id" TEXT PRIMARY KEY NOT NULL DEFAULT (lower(hex(randomblob(16)))),
  "created_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  "updated_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  "module" TEXT NOT NULL,
  "source_key" TEXT,
  "slug" TEXT NOT NULL,
  "title" TEXT NOT NULL,
  "data" TEXT NOT NULL DEFAULT '{}',
  "published_data" TEXT,
  "scheduled_data" TEXT,
  "status" TEXT NOT NULL DEFAULT 'draft',
  "version" INTEGER NOT NULL DEFAULT 1,
  "scheduled_at" TEXT,
  "published_at" TEXT,
  "deleted_at" TEXT,
  "editor_id" TEXT,
  CHECK (version > 0),
  UNIQUE ("module","slug"),
  CHECK (status IN ('draft','scheduled','published','archived')),
  UNIQUE ("source_key"),
  FOREIGN KEY ("editor_id") REFERENCES "admin_users" ("id") ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS "ix_cms_entries_scheduled_at" ON "cms_entries" ("scheduled_at");

CREATE INDEX IF NOT EXISTS "ix_cms_entries_editor_id" ON "cms_entries" ("editor_id");

CREATE INDEX IF NOT EXISTS "ix_cms_entries_module" ON "cms_entries" ("module");

CREATE INDEX IF NOT EXISTS "ix_cms_entries_status" ON "cms_entries" ("status");

CREATE TABLE IF NOT EXISTS "contact_notifications" (
  "id" TEXT PRIMARY KEY NOT NULL DEFAULT (lower(hex(randomblob(16)))),
  "created_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  "updated_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  "message_id" TEXT NOT NULL,
  "attempts" INTEGER NOT NULL DEFAULT 0,
  "next_attempt_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  "sent_at" TEXT,
  UNIQUE ("message_id"),
  FOREIGN KEY ("message_id") REFERENCES "contact_messages" ("id") ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS "ix_contact_notifications_message_id" ON "contact_notifications" ("message_id");

CREATE TABLE IF NOT EXISTS "media_assets" (
  "id" TEXT PRIMARY KEY NOT NULL DEFAULT (lower(hex(randomblob(16)))),
  "created_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  "updated_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  "storage_key" TEXT NOT NULL,
  "original_name" TEXT NOT NULL,
  "mime_type" TEXT NOT NULL,
  "size_bytes" INTEGER NOT NULL,
  "width" INTEGER,
  "height" INTEGER,
  "alt_text" TEXT,
  "sha256" TEXT NOT NULL,
  "uploaded_by" TEXT,
  "archived_at" TEXT,
  CHECK (size_bytes > 0),
  UNIQUE ("storage_key"),
  FOREIGN KEY ("uploaded_by") REFERENCES "admin_users" ("id") ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS "ix_media_assets_uploaded_by" ON "media_assets" ("uploaded_by");

CREATE TABLE IF NOT EXISTS "page_sections" (
  "id" TEXT PRIMARY KEY NOT NULL DEFAULT (lower(hex(randomblob(16)))),
  "created_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  "updated_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  "page_id" TEXT NOT NULL,
  "section_key" TEXT NOT NULL,
  "content" TEXT NOT NULL DEFAULT '{}',
  "sort_order" INTEGER NOT NULL DEFAULT 0,
  "visible" INTEGER NOT NULL DEFAULT 1,
  UNIQUE ("page_id","section_key"),
  FOREIGN KEY ("page_id") REFERENCES "pages" ("id") ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS "ix_page_sections_page_id" ON "page_sections" ("page_id");

CREATE TABLE IF NOT EXISTS "password_resets" (
  "id" TEXT PRIMARY KEY NOT NULL DEFAULT (lower(hex(randomblob(16)))),
  "created_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  "updated_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  "admin_id" TEXT NOT NULL,
  "token_hash" TEXT NOT NULL,
  "expires_at" TEXT NOT NULL,
  "used_at" TEXT,
  UNIQUE ("token_hash"),
  FOREIGN KEY ("admin_id") REFERENCES "admin_users" ("id") ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS "ix_password_resets_expires_at" ON "password_resets" ("expires_at");

CREATE INDEX IF NOT EXISTS "ix_password_resets_admin_id" ON "password_resets" ("admin_id");

CREATE TABLE IF NOT EXISTS "skills" (
  "id" TEXT PRIMARY KEY NOT NULL DEFAULT (lower(hex(randomblob(16)))),
  "created_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  "updated_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  "category_id" TEXT NOT NULL,
  "name" TEXT NOT NULL,
  "description" TEXT,
  "icon" TEXT,
  "sort_order" INTEGER NOT NULL DEFAULT 0,
  "featured" INTEGER NOT NULL DEFAULT 0,
  "visible" INTEGER NOT NULL DEFAULT 1,
  "archived_at" TEXT,
  UNIQUE ("category_id","name"),
  FOREIGN KEY ("category_id") REFERENCES "skill_categories" ("id") ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS "ix_skills_category_id" ON "skills" ("category_id");

CREATE TABLE IF NOT EXISTS "articles" (
  "id" TEXT PRIMARY KEY NOT NULL DEFAULT (lower(hex(randomblob(16)))),
  "created_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  "updated_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  "category_id" TEXT,
  "author_id" TEXT,
  "cover_id" TEXT,
  "slug" TEXT NOT NULL,
  "status" TEXT NOT NULL DEFAULT 'draft',
  "featured" INTEGER NOT NULL DEFAULT 0,
  "sort_order" INTEGER NOT NULL DEFAULT 0,
  "published_at" TEXT,
  "scheduled_at" TEXT,
  "archived_at" TEXT,
  CHECK (status IN ('draft','scheduled','published','archived')),
  UNIQUE ("slug"),
  FOREIGN KEY ("author_id") REFERENCES "admin_users" ("id") ON DELETE RESTRICT,
  FOREIGN KEY ("category_id") REFERENCES "article_categories" ("id") ON DELETE RESTRICT,
  FOREIGN KEY ("cover_id") REFERENCES "media_assets" ("id") ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS "ix_articles_status" ON "articles" ("status");

CREATE INDEX IF NOT EXISTS "ix_articles_author_id" ON "articles" ("author_id");

CREATE INDEX IF NOT EXISTS "ix_articles_cover_id" ON "articles" ("cover_id");

CREATE INDEX IF NOT EXISTS "ix_articles_category_id" ON "articles" ("category_id");

CREATE TABLE IF NOT EXISTS "case_images" (
  "id" TEXT PRIMARY KEY NOT NULL DEFAULT (lower(hex(randomblob(16)))),
  "created_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  "updated_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  "case_id" TEXT NOT NULL,
  "media_id" TEXT NOT NULL,
  "caption" TEXT,
  UNIQUE ("case_id","media_id"),
  FOREIGN KEY ("case_id") REFERENCES "cases" ("id") ON DELETE RESTRICT,
  FOREIGN KEY ("media_id") REFERENCES "media_assets" ("id") ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS "ix_case_images_case_id" ON "case_images" ("case_id");

CREATE INDEX IF NOT EXISTS "ix_case_images_media_id" ON "case_images" ("media_id");

CREATE TABLE IF NOT EXISTS "cms_links" (
  "id" TEXT PRIMARY KEY NOT NULL DEFAULT (lower(hex(randomblob(16)))),
  "created_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  "updated_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  "entry_id" TEXT NOT NULL,
  "target_id" TEXT NOT NULL,
  "scope" TEXT NOT NULL,
  UNIQUE ("entry_id","target_id","scope"),
  FOREIGN KEY ("target_id") REFERENCES "cms_entries" ("id") ON DELETE RESTRICT,
  FOREIGN KEY ("entry_id") REFERENCES "cms_entries" ("id") ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS "ix_cms_links_entry_id" ON "cms_links" ("entry_id");

CREATE INDEX IF NOT EXISTS "ix_cms_links_target_id" ON "cms_links" ("target_id");

CREATE TABLE IF NOT EXISTS "cms_media_refs" (
  "id" TEXT PRIMARY KEY NOT NULL DEFAULT (lower(hex(randomblob(16)))),
  "created_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  "updated_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  "entry_id" TEXT NOT NULL,
  "media_id" TEXT NOT NULL,
  "scope" TEXT NOT NULL,
  UNIQUE ("entry_id","media_id","scope"),
  FOREIGN KEY ("entry_id") REFERENCES "cms_entries" ("id") ON DELETE RESTRICT,
  FOREIGN KEY ("media_id") REFERENCES "media_assets" ("id") ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS "ix_cms_media_refs_media_id" ON "cms_media_refs" ("media_id");

CREATE INDEX IF NOT EXISTS "ix_cms_media_refs_entry_id" ON "cms_media_refs" ("entry_id");

CREATE TABLE IF NOT EXISTS "cms_revisions" (
  "id" TEXT PRIMARY KEY NOT NULL DEFAULT (lower(hex(randomblob(16)))),
  "created_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  "updated_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  "entry_id" TEXT NOT NULL,
  "editor_id" TEXT,
  "version" INTEGER NOT NULL,
  "action" TEXT NOT NULL,
  "snapshot" TEXT NOT NULL DEFAULT '{}',
  UNIQUE ("entry_id","version"),
  FOREIGN KEY ("entry_id") REFERENCES "cms_entries" ("id") ON DELETE RESTRICT,
  FOREIGN KEY ("editor_id") REFERENCES "admin_users" ("id") ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS "ix_cms_revisions_editor_id" ON "cms_revisions" ("editor_id");

CREATE INDEX IF NOT EXISTS "ix_cms_revisions_entry_id" ON "cms_revisions" ("entry_id");

CREATE TABLE IF NOT EXISTS "experiences" (
  "id" TEXT PRIMARY KEY NOT NULL DEFAULT (lower(hex(randomblob(16)))),
  "created_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  "updated_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  "company" TEXT NOT NULL,
  "role" TEXT,
  "relationship_type" TEXT,
  "start_date" TEXT,
  "end_date" TEXT,
  "date_precision" TEXT NOT NULL DEFAULT 'month',
  "responsibilities" TEXT,
  "technologies" TEXT NOT NULL DEFAULT '[]',
  "logo_id" TEXT,
  "featured" INTEGER NOT NULL DEFAULT 0,
  "visible" INTEGER NOT NULL DEFAULT 0,
  "sort_order" INTEGER NOT NULL DEFAULT 0,
  "archived_at" TEXT,
  CHECK (end_date IS NULL OR start_date IS NULL OR end_date >= start_date),
  CHECK (date_precision IN ('day','month','year')),
  FOREIGN KEY ("logo_id") REFERENCES "media_assets" ("id") ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS "ix_experiences_logo_id" ON "experiences" ("logo_id");

CREATE TABLE IF NOT EXISTS "projects" (
  "id" TEXT PRIMARY KEY NOT NULL DEFAULT (lower(hex(randomblob(16)))),
  "created_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  "updated_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  "name" TEXT NOT NULL,
  "description" TEXT NOT NULL,
  "category" TEXT,
  "cover_id" TEXT,
  "problem" TEXT,
  "architecture" TEXT,
  "technologies" TEXT NOT NULL DEFAULT '[]',
  "development_stage" TEXT,
  "results" TEXT,
  "links" TEXT NOT NULL DEFAULT '[]',
  "slug" TEXT NOT NULL,
  "status" TEXT NOT NULL DEFAULT 'draft',
  "featured" INTEGER NOT NULL DEFAULT 0,
  "sort_order" INTEGER NOT NULL DEFAULT 0,
  "published_at" TEXT,
  "scheduled_at" TEXT,
  "archived_at" TEXT,
  UNIQUE ("slug"),
  CHECK (status IN ('draft','scheduled','published','archived')),
  FOREIGN KEY ("cover_id") REFERENCES "media_assets" ("id") ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS "ix_projects_status" ON "projects" ("status");

CREATE INDEX IF NOT EXISTS "ix_projects_cover_id" ON "projects" ("cover_id");

CREATE TABLE IF NOT EXISTS "videos" (
  "id" TEXT PRIMARY KEY NOT NULL DEFAULT (lower(hex(randomblob(16)))),
  "created_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  "updated_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  "title" TEXT NOT NULL,
  "youtube_id" TEXT NOT NULL,
  "description" TEXT,
  "category" TEXT,
  "thumbnail_id" TEXT,
  "slug" TEXT NOT NULL,
  "status" TEXT NOT NULL DEFAULT 'draft',
  "featured" INTEGER NOT NULL DEFAULT 0,
  "sort_order" INTEGER NOT NULL DEFAULT 0,
  "published_at" TEXT,
  "scheduled_at" TEXT,
  "archived_at" TEXT,
  UNIQUE ("slug"),
  UNIQUE ("youtube_id"),
  CHECK (status IN ('draft','scheduled','published','archived')),
  FOREIGN KEY ("thumbnail_id") REFERENCES "media_assets" ("id") ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS "ix_videos_status" ON "videos" ("status");

CREATE INDEX IF NOT EXISTS "ix_videos_thumbnail_id" ON "videos" ("thumbnail_id");

CREATE TABLE IF NOT EXISTS "article_relations" (
  "id" TEXT PRIMARY KEY NOT NULL DEFAULT (lower(hex(randomblob(16)))),
  "created_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  "updated_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  "article_id" TEXT NOT NULL,
  "related_id" TEXT NOT NULL,
  UNIQUE ("article_id","related_id"),
  CHECK (article_id <> related_id),
  FOREIGN KEY ("article_id") REFERENCES "articles" ("id") ON DELETE RESTRICT,
  FOREIGN KEY ("related_id") REFERENCES "articles" ("id") ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS "ix_article_relations_article_id" ON "article_relations" ("article_id");

CREATE INDEX IF NOT EXISTS "ix_article_relations_related_id" ON "article_relations" ("related_id");

CREATE TABLE IF NOT EXISTS "article_tags" (
  "id" TEXT PRIMARY KEY NOT NULL DEFAULT (lower(hex(randomblob(16)))),
  "created_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  "updated_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  "article_id" TEXT NOT NULL,
  "name" TEXT NOT NULL,
  UNIQUE ("article_id","name"),
  FOREIGN KEY ("article_id") REFERENCES "articles" ("id") ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS "ix_article_tags_article_id" ON "article_tags" ("article_id");

CREATE TABLE IF NOT EXISTS "article_translations" (
  "id" TEXT PRIMARY KEY NOT NULL DEFAULT (lower(hex(randomblob(16)))),
  "created_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  "updated_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  "article_id" TEXT NOT NULL,
  "locale" TEXT NOT NULL,
  "slug" TEXT NOT NULL,
  "title" TEXT NOT NULL,
  "subtitle" TEXT,
  "body_html" TEXT NOT NULL,
  "seo_title" TEXT,
  "meta_description" TEXT,
  "reading_minutes" INTEGER,
  "status" TEXT NOT NULL DEFAULT 'draft',
  "published_at" TEXT,
  "scheduled_at" TEXT,
  CHECK (status IN ('draft','scheduled','published','archived')),
  CHECK (reading_minutes IS NULL OR reading_minutes > 0),
  UNIQUE ("locale","slug"),
  CHECK (locale IN ('pt-BR','en')),
  UNIQUE ("article_id","locale"),
  FOREIGN KEY ("article_id") REFERENCES "articles" ("id") ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS "ix_article_translations_article_id" ON "article_translations" ("article_id");

CREATE TABLE IF NOT EXISTS "experience_results" (
  "id" TEXT PRIMARY KEY NOT NULL DEFAULT (lower(hex(randomblob(16)))),
  "created_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  "updated_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  "experience_id" TEXT NOT NULL,
  "description" TEXT NOT NULL,
  "evidence" TEXT,
  "verified" INTEGER NOT NULL DEFAULT 0,
  FOREIGN KEY ("experience_id") REFERENCES "experiences" ("id") ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS "ix_experience_results_experience_id" ON "experience_results" ("experience_id");

CREATE TABLE IF NOT EXISTS "project_images" (
  "id" TEXT PRIMARY KEY NOT NULL DEFAULT (lower(hex(randomblob(16)))),
  "created_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  "updated_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  "project_id" TEXT NOT NULL,
  "media_id" TEXT NOT NULL,
  "caption" TEXT,
  "sort_order" INTEGER NOT NULL DEFAULT 0,
  UNIQUE ("project_id","media_id"),
  FOREIGN KEY ("media_id") REFERENCES "media_assets" ("id") ON DELETE RESTRICT,
  FOREIGN KEY ("project_id") REFERENCES "projects" ("id") ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS "ix_project_images_project_id" ON "project_images" ("project_id");

CREATE INDEX IF NOT EXISTS "ix_project_images_media_id" ON "project_images" ("media_id");

CREATE TABLE IF NOT EXISTS "video_articles" (
  "id" TEXT PRIMARY KEY NOT NULL DEFAULT (lower(hex(randomblob(16)))),
  "created_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  "updated_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  "video_id" TEXT NOT NULL,
  "article_id" TEXT NOT NULL,
  UNIQUE ("video_id","article_id"),
  FOREIGN KEY ("video_id") REFERENCES "videos" ("id") ON DELETE RESTRICT,
  FOREIGN KEY ("article_id") REFERENCES "articles" ("id") ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS "ix_video_articles_video_id" ON "video_articles" ("video_id");

CREATE INDEX IF NOT EXISTS "ix_video_articles_article_id" ON "video_articles" ("article_id");

CREATE TABLE IF NOT EXISTS "article_revisions" (
  "id" TEXT PRIMARY KEY NOT NULL DEFAULT (lower(hex(randomblob(16)))),
  "created_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  "updated_at" TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  "translation_id" TEXT NOT NULL,
  "editor_id" TEXT,
  "version" INTEGER NOT NULL,
  "snapshot" TEXT NOT NULL DEFAULT '{}',
  UNIQUE ("translation_id","version"),
  CHECK (version > 0),
  FOREIGN KEY ("translation_id") REFERENCES "article_translations" ("id") ON DELETE RESTRICT,
  FOREIGN KEY ("editor_id") REFERENCES "admin_users" ("id") ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS "ix_article_revisions_translation_id" ON "article_revisions" ("translation_id");

CREATE INDEX IF NOT EXISTS "ix_article_revisions_editor_id" ON "article_revisions" ("editor_id");

CREATE TABLE IF NOT EXISTS migration_receipts (snapshot_id TEXT PRIMARY KEY, imported_at TEXT NOT NULL, manifest TEXT NOT NULL);

ALTER TABLE contact_notifications ADD COLUMN lease_until TEXT;

ALTER TABLE contact_notifications ADD COLUMN provider_id TEXT;

ALTER TABLE contact_notifications ADD COLUMN last_error TEXT;

ALTER TABLE contact_tickets ADD COLUMN message_id TEXT;

CREATE INDEX IF NOT EXISTS ix_cms_refs_public ON cms_media_refs(media_id,scope);

CREATE INDEX IF NOT EXISTS ix_cms_public ON cms_entries(module,deleted_at,status);
