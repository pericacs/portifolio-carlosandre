"""Esquema PostgreSQL. Exclusão editorial por archived_at; FKs sempre RESTRICT.

SQLAlchemy Core mantém relações explícitas sem cascatas de ORM. Datas de
experiência são independentes; vínculos simultâneos são permitidos.
"""
import uuid
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

metadata = sa.MetaData(naming_convention={
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
})


def table(name, *columns):
    return sa.Table(name, metadata,
        sa.Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        *columns)


def ref(name, target, nullable=False):
    return sa.Column(name, UUID(as_uuid=True), sa.ForeignKey(target + ".id", ondelete="RESTRICT"), nullable=nullable, index=True)


def string(name, length=255, nullable=True, **kwargs):
    return sa.Column(name, sa.String(length), nullable=nullable, **kwargs)


def text(name, nullable=True):
    return sa.Column(name, sa.Text, nullable=nullable)


def json(name, array=False):
    return sa.Column(name, JSONB, nullable=False, server_default=sa.text("'[]'::jsonb" if array else "'{}'::jsonb"))


def editorial():
    return [
        string("slug", nullable=False, unique=True),
        string("status", 24, nullable=False, server_default="draft", index=True),
        sa.Column("featured", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("scheduled_at", sa.DateTime(timezone=True)),
        sa.Column("archived_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("status IN ('draft','scheduled','published','archived')", name="status"),
    ]


admin_users = table("admin_users", string("email", 320, nullable=False, unique=True),
    text("password_hash", False), sa.Column("active", sa.Boolean, nullable=False, server_default=sa.true()),
    sa.CheckConstraint("email = lower(email)", name="email_lowercase"))
admin_sessions = table("admin_sessions", ref("admin_id", "admin_users"),
    string("token_hash", 64, nullable=False, unique=True), string("csrf_hash", 64, nullable=False),
    sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False, index=True),
    sa.Column("revoked_at", sa.DateTime(timezone=True)))
media_assets = table("media_assets", string("storage_key", 512, nullable=False, unique=True),
    string("original_name", nullable=False), string("mime_type", 100, nullable=False),
    sa.Column("size_bytes", sa.BigInteger, nullable=False), sa.Column("width", sa.Integer),
    sa.Column("height", sa.Integer), string("alt_text", 1000),
    string("sha256", 64, nullable=False), ref("uploaded_by", "admin_users", True),
    sa.Column("archived_at", sa.DateTime(timezone=True)),
    sa.CheckConstraint("size_bytes > 0", name="positive_size"))
site_settings = table("site_settings", string("key", 100, nullable=False, unique=True), json("value"))
pages = table("pages", string("title", nullable=False), string("locale", 5, nullable=False, server_default="pt-BR"),
    text("body_html"), string("seo_title"), text("meta_description"), *editorial())
page_sections = table("page_sections", ref("page_id", "pages"), string("section_key", 100, nullable=False),
    json("content"), sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
    sa.Column("visible", sa.Boolean, nullable=False, server_default=sa.true()),
    sa.UniqueConstraint("page_id", "section_key"))
projects = table("projects", string("name", nullable=False), text("description", False), string("category"),
    ref("cover_id", "media_assets", True), text("problem"), text("architecture"), json("technologies", True),
    string("development_stage", 100), text("results"), json("links", True), *editorial())
project_images = table("project_images", ref("project_id", "projects"), ref("media_id", "media_assets"),
    string("caption", 1000), sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
    sa.UniqueConstraint("project_id", "media_id"))
experiences = table("experiences", string("company", nullable=False), string("role"), string("relationship_type", 100),
    sa.Column("start_date", sa.Date), sa.Column("end_date", sa.Date),
    string("date_precision", 10, nullable=False, server_default="month"),
    text("responsibilities"), json("technologies", True), ref("logo_id", "media_assets", True),
    sa.Column("featured", sa.Boolean, nullable=False, server_default=sa.false()),
    sa.Column("visible", sa.Boolean, nullable=False, server_default=sa.false()),
    sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
    sa.Column("archived_at", sa.DateTime(timezone=True)),
    sa.CheckConstraint("end_date IS NULL OR start_date IS NULL OR end_date >= start_date", name="date_order"),
    sa.CheckConstraint("date_precision IN ('day','month','year')", name="date_precision"))
experience_results = table("experience_results", ref("experience_id", "experiences"), text("description", False),
    text("evidence"), sa.Column("verified", sa.Boolean, nullable=False, server_default=sa.false()))
skill_categories = table("skill_categories", string("name", nullable=False, unique=True),
    sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"))
skills = table("skills", ref("category_id", "skill_categories"), string("name", nullable=False), text("description"),
    string("icon", 100), sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
    sa.Column("featured", sa.Boolean, nullable=False, server_default=sa.false()),
    sa.Column("visible", sa.Boolean, nullable=False, server_default=sa.true()),
    sa.Column("archived_at", sa.DateTime(timezone=True)), sa.UniqueConstraint("category_id", "name"))
article_categories = table("article_categories", string("name", nullable=False, unique=True), string("slug", nullable=False, unique=True))
articles = table("articles", ref("category_id", "article_categories", True), ref("author_id", "admin_users", True),
    ref("cover_id", "media_assets", True), *editorial())
article_translations = table("article_translations", ref("article_id", "articles"),
    string("locale", 5, nullable=False), string("slug", nullable=False), string("title", nullable=False),
    text("subtitle"), text("body_html", False), string("seo_title"), text("meta_description"),
    sa.Column("reading_minutes", sa.Integer),
    string("status", 24, nullable=False, server_default="draft"),
    sa.Column("published_at", sa.DateTime(timezone=True)), sa.Column("scheduled_at", sa.DateTime(timezone=True)),
    sa.CheckConstraint("locale IN ('pt-BR','en')", name="locale"),
    sa.CheckConstraint("status IN ('draft','scheduled','published','archived')", name="status"),
    sa.CheckConstraint("reading_minutes IS NULL OR reading_minutes > 0", name="reading_minutes"),
    sa.UniqueConstraint("article_id", "locale"), sa.UniqueConstraint("locale", "slug"))
article_tags = table("article_tags", ref("article_id", "articles"), string("name", 100, nullable=False),
    sa.UniqueConstraint("article_id", "name"))
article_revisions = table("article_revisions", ref("translation_id", "article_translations"),
    ref("editor_id", "admin_users", True), sa.Column("version", sa.Integer, nullable=False), json("snapshot"),
    sa.UniqueConstraint("translation_id", "version"), sa.CheckConstraint("version > 0", name="positive_version"))
article_relations = table("article_relations", ref("article_id", "articles"), ref("related_id", "articles"),
    sa.UniqueConstraint("article_id", "related_id"), sa.CheckConstraint("article_id <> related_id", name="not_self"))
videos = table("videos", string("title", nullable=False), string("youtube_id", 11, nullable=False, unique=True),
    text("description"), string("category"), ref("thumbnail_id", "media_assets", True), *editorial(),
    sa.CheckConstraint("youtube_id ~ '^[A-Za-z0-9_-]{11}$'", name="youtube_id"))
video_articles = table("video_articles", ref("video_id", "videos"), ref("article_id", "articles"),
    sa.UniqueConstraint("video_id", "article_id"))
cases = table("cases", string("company", nullable=False), string("title", nullable=False),
    string("period"), text("problem"), text("solution"), text("architecture"), json("technologies", True),
    text("results"), json("links", True),
    sa.Column("confidential", sa.Boolean, nullable=False, server_default=sa.true()), *editorial(),
    sa.CheckConstraint("status <> 'published' OR confidential = false", name="publication_clearance"))
case_metrics = table("case_metrics", ref("case_id", "cases"), string("label", nullable=False),
    string("value", nullable=False), text("evidence", False))
case_images = table("case_images", ref("case_id", "cases"), ref("media_id", "media_assets"),
    string("caption", 1000), sa.UniqueConstraint("case_id", "media_id"))
contact_messages = table("contact_messages", string("name", nullable=False), string("email", 320, nullable=False),
    string("company"), string("role"), string("subject", nullable=False), text("message", False),
    sa.Column("consent", sa.Boolean, nullable=False), string("privacy_version", 32, nullable=False),
    string("status", 24, nullable=False, server_default="new", index=True), text("internal_notes"),
    sa.Column("notified_at", sa.DateTime(timezone=True)),
    sa.CheckConstraint("consent = true", name="consent_required"),
    sa.CheckConstraint("status IN ('new','reviewing','replied','archived')", name="status"))
audit_logs = table("audit_logs", ref("actor_id", "admin_users", True), string("action", 100, nullable=False),
    string("entity_type", 100), sa.Column("entity_id", UUID(as_uuid=True)), json("details"))
sa.Index("ix_audit_logs_created_at", audit_logs.c.created_at)
sa.Index("ix_contact_messages_created_at", contact_messages.c.created_at)

# Base administrativa: adição sem alterar conteúdo editorial existente.
auth_rate_limits = sa.Table("auth_rate_limits", metadata,
    sa.Column("key", sa.String(64), primary_key=True),
    sa.Column("attempts", sa.Integer, nullable=False),
    sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False, index=True))
password_resets = table("password_resets", ref("admin_id", "admin_users"),
    string("token_hash", 64, nullable=False, unique=True),
    sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False, index=True),
    sa.Column("used_at", sa.DateTime(timezone=True)))

# Versioned editorial workspace: draft and public snapshots remain independent.
cms_entries = table("cms_entries", string("module",40,nullable=False,index=True),
    string("source_key",255,unique=True), string("slug",255,nullable=False),
    string("title",1000,nullable=False), json("data"),
    sa.Column("published_data",JSONB(none_as_null=True)),sa.Column("scheduled_data",JSONB(none_as_null=True)),
    string("status",24,nullable=False,server_default="draft",index=True),
    sa.Column("version",sa.Integer,nullable=False,server_default="1"),
    sa.Column("scheduled_at",sa.DateTime(timezone=True),index=True),
    sa.Column("published_at",sa.DateTime(timezone=True)),sa.Column("deleted_at",sa.DateTime(timezone=True)),
    ref("editor_id","admin_users",True),
    sa.UniqueConstraint("module","slug"),
    sa.CheckConstraint("status IN ('draft','scheduled','published','archived')",name="status"),
    sa.CheckConstraint("version > 0",name="version"))
cms_revisions = table("cms_revisions",ref("entry_id","cms_entries"),ref("editor_id","admin_users",True),
    sa.Column("version",sa.Integer,nullable=False),string("action",40,nullable=False),json("snapshot"),
    sa.UniqueConstraint("entry_id","version"))
cms_links = table("cms_links",ref("entry_id","cms_entries"),ref("target_id","cms_entries"),
    string("scope",16,nullable=False),sa.UniqueConstraint("entry_id","target_id","scope"))
cms_media_refs = table("cms_media_refs",ref("entry_id","cms_entries"),ref("media_id","media_assets"),
    string("scope",16,nullable=False),sa.UniqueConstraint("entry_id","media_id","scope"))
contact_tickets = sa.Table("contact_tickets",metadata,
    sa.Column("token_hash",sa.String(64),primary_key=True),
    sa.Column("created_at",sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),
    sa.Column("expires_at",sa.DateTime(timezone=True),nullable=False,index=True))
contact_notifications = table("contact_notifications",ref("message_id","contact_messages"),
    sa.Column("attempts",sa.Integer,nullable=False,server_default="0"),
    sa.Column("next_attempt_at",sa.DateTime(timezone=True),nullable=False,server_default=sa.func.now()),
    sa.Column("sent_at",sa.DateTime(timezone=True)),sa.UniqueConstraint("message_id"))
