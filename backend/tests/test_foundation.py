from datetime import date
import pytest
import sqlalchemy as sa
from argon2 import PasswordHasher
from fastapi.testclient import TestClient
from pydantic import ValidationError
from app import cli
from app.config import Settings
from app.main import app
from app.models import (metadata, admin_users, projects, project_images, media_assets,
    experiences, videos, cases, contact_messages, article_categories, articles, article_translations)
from app.seed import seed


def test_health_and_real_postgres():
    with TestClient(app) as client:
        assert client.get("/api/health/live").status_code == 200
        response = client.get("/api/health/ready")
        assert response.status_code == 200
        assert response.json()["database"] == "connected"


def test_all_entities_migrated(db):
    assert set(metadata.tables) <= set(sa.inspect(db).get_table_names())
    assert db.execute(sa.text("SHOW server_version")).scalar().startswith("16.")


def test_no_cascade_delete():
    for table in metadata.tables.values():
        for fk in table.foreign_keys:
            assert fk.ondelete == "RESTRICT"


def test_restrict_preserves_project_with_images(db):
    project_id = db.execute(projects.insert().values(name="Teste", slug="test-image", description="Test").returning(projects.c.id)).scalar_one()
    image_id = db.execute(media_assets.insert().values(storage_key="test.png", original_name="test.png",
        mime_type="image/png", size_bytes=42, sha256="a"*64).returning(media_assets.c.id)).scalar_one()
    db.execute(project_images.insert().values(project_id=project_id, media_id=image_id))
    with pytest.raises(sa.exc.IntegrityError), db.begin_nested():
        db.execute(projects.delete().where(projects.c.id == project_id))
    assert db.scalar(sa.select(projects.c.name).where(projects.c.id == project_id)) == "Teste"


def test_experiences_accept_overlapping_periods(db):
    for company in ["Empresa A", "Empresa B"]:
        db.execute(experiences.insert().values(company=company, start_date=date(2020, 1, 1), end_date=date(2022, 1, 1)))
    assert db.scalar(sa.select(sa.func.count()).select_from(experiences)) == 2


def test_invalid_dates_rejected(db):
    with pytest.raises(sa.exc.IntegrityError), db.begin_nested():
        db.execute(experiences.insert().values(company="Teste", start_date=date(2022, 1, 1), end_date=date(2020, 1, 1)))


def test_youtube_id_constraint(db):
    with pytest.raises(sa.exc.IntegrityError), db.begin_nested():
        db.execute(videos.insert().values(title="Teste", slug="test-video", youtube_id="invalid!"))


def test_confidential_case_cannot_be_published(db):
    with pytest.raises(sa.exc.IntegrityError), db.begin_nested():
        db.execute(cases.insert().values(company="Teste", title="Teste", slug="test-case", status="published", confidential=True))


def test_consent_required(db):
    with pytest.raises(sa.exc.IntegrityError), db.begin_nested():
        db.execute(contact_messages.insert().values(name="Teste", email="test@example.com", subject="Teste",
            message="Teste", consent=False, privacy_version="1"))


def test_independent_translations(db):
    article_id = db.execute(articles.insert().values(slug="test-article").returning(articles.c.id)).scalar_one()
    for locale, title, status in [("pt-BR", "Título", "published"), ("en", "Title", "draft")]:
        db.execute(article_translations.insert().values(article_id=article_id, locale=locale, slug="test", title=title, body_html="<p>Test</p>", status=status))
    assert db.scalar(sa.select(sa.func.count()).select_from(article_translations).where(article_translations.c.article_id == article_id)) == 2


def test_seed_is_idempotent_and_does_not_publish(db):
    seed(db)
    db.execute(projects.update().where(projects.c.slug == "smartfamily").values(description="Edição preservada"))
    seed(db)
    assert db.scalar(sa.select(sa.func.count()).select_from(projects)) == 4
    assert db.scalar(sa.select(projects.c.description).where(projects.c.slug == "smartfamily")) == "Edição preservada"
    assert set(db.scalars(sa.select(projects.c.status))) == {"draft"}


def test_admin_creation_uses_argon2id(db, monkeypatch):
    monkeypatch.setattr(cli, "get_engine", lambda: db)
    monkeypatch.setattr("builtins.input", lambda _: "admin@example.com")
    monkeypatch.setattr(cli.getpass, "getpass", lambda _: "only-for-this-test-strong-password")
    cli.create_admin()
    encoded = db.scalar(sa.select(admin_users.c.password_hash).where(admin_users.c.email == "admin@example.com"))
    assert encoded.startswith("$argon2id$")
    assert PasswordHasher().verify(encoded, "only-for-this-test-strong-password")
    with pytest.raises(SystemExit, match="já existe"):
        cli.create_admin()


def test_weak_admin_password_rejected(db, monkeypatch):
    monkeypatch.setattr(cli, "get_engine", lambda: db)
    monkeypatch.setattr("builtins.input", lambda _: "short@example.com")
    monkeypatch.setattr(cli.getpass, "getpass", lambda _: "short")
    with pytest.raises(SystemExit, match="Senha curta"):
        cli.create_admin()
    assert db.scalar(sa.select(admin_users.c.id).where(admin_users.c.email == "short@example.com")) is None


def test_production_requires_secure_configuration():
    with pytest.raises(ValidationError, match="HTTPS"):
        Settings(_env_file=None, postgres_password="test-database-password", app_env="production", cookie_secure=False)


def test_cors_rejects_unknown_origin():
    with TestClient(app) as client:
        response = client.options("/api/health/live", headers={"Origin": "https://untrusted.example", "Access-Control-Request-Method": "GET"})
        assert response.status_code == 400
        assert "access-control-allow-origin" not in response.headers
