"""Autenticação e consultas administrativas; nenhum cadastro público."""
import hashlib
import hmac
import logging
import re
import secrets
import smtplib
import ssl
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from urllib.parse import urlsplit

import sqlalchemy as sa
from argon2 import PasswordHasher, Type
from argon2.exceptions import VerificationError, InvalidHashError
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from app.config import get_settings
from app.db import get_db, get_engine
from app import models as m

router = APIRouter(prefix="/api/admin", tags=["Administração"])
hasher = PasswordHasher(type=Type.ID)
DUMMY_HASH = hasher.hash(secrets.token_urlsafe(32))
SESSION_COOKIE = "portfolio_session"
CSRF_COOKIE = "portfolio_csrf"


def now():
    return datetime.now(timezone.utc)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def audit(db, action, admin_id=None, entity_type="admin_users", entity_id=None):
    db.execute(m.audit_logs.insert().values(actor_id=admin_id, action=action,
        entity_type=entity_type, entity_id=entity_id))


def require_origin(request: Request):
    # Exact origin comparison, never trust Host/X-Forwarded-Host for CSRF.
    expected = urlsplit(get_settings().site_url)
    allowed = f"{expected.scheme}://{expected.netloc}"
    if request.headers.get("origin") != allowed:
        raise HTTPException(403, "Origem inválida. Recarregue o painel.")


def check_csrf(request: Request):
    require_origin(request)
    header = request.headers.get("x-csrf-token", "")
    cookie = request.cookies.get(CSRF_COOKIE, "")
    if not re.fullmatch(r"[A-Za-z0-9_-]{43}", header) or not re.fullmatch(r"[A-Za-z0-9_-]{43}", cookie) or not hmac.compare_digest(header, cookie):
        raise HTTPException(403, "Sessão de segurança inválida. Recarregue o painel.")
    return header


def rate_limit(db, key, maximum, minutes=15):
    """Contador atômico persistente, inclusive entre processos e reinícios."""
    current = now()
    stmt = insert(m.auth_rate_limits).values(key=digest(key), attempts=1,
        expires_at=current + timedelta(minutes=minutes))
    stmt = stmt.on_conflict_do_update(index_elements=[m.auth_rate_limits.c.key], set_={
        "attempts": sa.case((m.auth_rate_limits.c.expires_at <= current, 1), else_=m.auth_rate_limits.c.attempts + 1),
        "expires_at": sa.case((m.auth_rate_limits.c.expires_at <= current, stmt.excluded.expires_at), else_=m.auth_rate_limits.c.expires_at),
    }).returning(m.auth_rate_limits.c.attempts)
    attempts = db.scalar(stmt)
    db.commit()  # Falhas também precisam ser contabilizadas.
    if attempts > maximum:
        raise HTTPException(429, "Muitas tentativas. Aguarde 15 minutos.", headers={"Retry-After": "900"})


def throttle(request, db, email, scope):
    # O backend não confia em cabeçalhos de IP enviados pelo cliente. Atrás do
    # proxy, o limite por peer é conservador e compartilhado; o limite por conta é independente.
    peer = request.client.host if request.client else "unknown"
    rate_limit(db, f"{scope}:peer:{peer}", 30)
    rate_limit(db, f"{scope}:account:{email.lower()}", 5)


def authenticated(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get(SESSION_COOKIE, "")
    if not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
        raise HTTPException(401, "Entre no painel para continuar.")
    session = db.execute(sa.select(m.admin_sessions.c.id, m.admin_sessions.c.admin_id,
        m.admin_sessions.c.csrf_hash, m.admin_users.c.email).join(m.admin_users).where(
        m.admin_sessions.c.token_hash == digest(token), m.admin_sessions.c.revoked_at.is_(None),
        m.admin_sessions.c.expires_at > now(), m.admin_users.c.active.is_(True))).mappings().first()
    if not session:
        raise HTTPException(401, "Sua sessão expirou. Entre novamente.")
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        csrf = check_csrf(request)
        if not hmac.compare_digest(session["csrf_hash"], digest(csrf)):
            raise HTTPException(403, "Token de segurança inválido.")
    return session


class Login(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class Recovery(BaseModel):
    email: EmailStr


class Reset(BaseModel):
    token: str = Field(min_length=43, max_length=43)
    password: str = Field(min_length=14, max_length=256)


def set_cookie(response, name, value, httponly, seconds):
    response.set_cookie(name, value, max_age=seconds, httponly=httponly,
        secure=get_settings().cookie_secure, samesite="strict", path="/")


@router.get("/auth/csrf")
def csrf(request: Request, response: Response):
    # Keep the same token across tabs; authentication rotates both cookies.
    token = request.cookies.get(CSRF_COOKIE, "")
    if not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
        token = secrets.token_urlsafe(32)
        set_cookie(response, CSRF_COOKIE, token, False, 86400)
    return {"csrfToken": token, "passwordRecoveryAvailable": get_settings().smtp_configured}


@router.post("/auth/login")
def login(body: Login, request: Request, response: Response, db: Session = Depends(get_db)):
    check_csrf(request)
    email = str(body.email).lower()
    throttle(request, db, email, "login")
    user = db.execute(sa.select(m.admin_users).where(m.admin_users.c.email == email).with_for_update()).mappings().first()
    try:
        valid = hasher.verify(user["password_hash"] if user else DUMMY_HASH, body.password)
    except (VerificationError, InvalidHashError):
        valid = False
    if not valid or not user or not user["active"]:
        audit(db, "auth.login_failed")
        db.commit()
        raise HTTPException(401, "E-mail ou senha inválidos.")
    if hasher.check_needs_rehash(user["password_hash"]):
        db.execute(m.admin_users.update().where(m.admin_users.c.id == user["id"]).values(password_hash=hasher.hash(body.password)))
    old = request.cookies.get(SESSION_COOKIE, "")
    if old:
        db.execute(m.admin_sessions.update().where(m.admin_sessions.c.token_hash == digest(old)).values(revoked_at=now()))
    token, csrf_token = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    duration = get_settings().admin_session_hours * 3600
    db.execute(m.admin_sessions.insert().values(admin_id=user["id"], token_hash=digest(token),
        csrf_hash=digest(csrf_token), expires_at=now()+timedelta(seconds=duration)))
    audit(db, "auth.login", user["id"], entity_id=user["id"])
    db.commit()
    set_cookie(response, SESSION_COOKIE, token, True, duration)
    set_cookie(response, CSRF_COOKIE, csrf_token, False, duration)
    return {"email": email}


@router.get("/auth/me")
def me(user=Depends(authenticated)):
    return {"email": user["email"]}


@router.post("/auth/logout")
def logout(response: Response, user=Depends(authenticated), db: Session = Depends(get_db)):
    db.execute(m.admin_sessions.update().where(m.admin_sessions.c.id == user["id"]).values(revoked_at=now()))
    audit(db, "auth.logout", user["admin_id"], entity_id=user["admin_id"])
    db.commit()
    for name in (SESSION_COOKIE, CSRF_COOKIE):
        response.delete_cookie(name, path="/", secure=get_settings().cookie_secure, samesite="strict")
    return {"ok": True}


def send_reset(email, token, reset_id):
    settings = get_settings()
    message = EmailMessage()
    message["From"], message["To"] = settings.smtp_from, email
    message["Subject"] = "Redefinir acesso ao portfólio"
    # Fragment keeps the secret out of HTTP access logs and Referer headers.
    message.set_content(f"Redefina sua senha em até 30 minutos:\n{settings.site_url.rstrip('/')}/admin/redefinir-senha#token={token}\n\nSe não solicitou, ignore esta mensagem.")
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            if settings.smtp_starttls:
                smtp.starttls(context=ssl.create_default_context())
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(message)
    except Exception:
        # Do not log message bodies, addresses, SMTP credentials or reset URLs.
        logging.getLogger(__name__).warning("Falha no envio SMTP de recuperação")
        with get_engine().begin() as connection:
            connection.execute(m.password_resets.update().where(m.password_resets.c.id == reset_id).values(used_at=now()))
            audit(connection, "auth.recovery_delivery_failed")


@router.post("/auth/recovery", status_code=202)
def recovery(body: Recovery, request: Request, tasks: BackgroundTasks, db: Session = Depends(get_db)):
    check_csrf(request)
    settings = get_settings()
    if not settings.smtp_configured:
        raise HTTPException(503, "Recuperação por e-mail indisponível. Contate o administrador do ambiente.")
    email = str(body.email).lower()
    throttle(request, db, email, "recovery")
    user = db.execute(sa.select(m.admin_users).where(m.admin_users.c.email == email, m.admin_users.c.active.is_(True))).mappings().first()
    if user:
        token = secrets.token_urlsafe(32)
        reset_id = db.scalar(m.password_resets.insert().values(admin_id=user["id"], token_hash=digest(token),
            expires_at=now()+timedelta(minutes=30)).returning(m.password_resets.c.id))
        audit(db, "auth.recovery_requested", user["id"], entity_id=user["id"])
        db.commit()
        tasks.add_task(send_reset, email, token, reset_id)
    return {"message": "Se a conta estiver habilitada, você receberá as instruções por e-mail."}


@router.post("/auth/reset")
def reset(body: Reset, request: Request, db: Session = Depends(get_db)):
    check_csrf(request)
    rate_limit(db, f"reset:{request.client.host if request.client else 'unknown'}", 10)
    record = db.execute(sa.select(m.password_resets).where(m.password_resets.c.token_hash == digest(body.token),
        m.password_resets.c.used_at.is_(None), m.password_resets.c.expires_at > now())).mappings().first()
    if not record:
        raise HTTPException(400, "Link inválido ou expirado. Solicite outro link.")
    user = db.execute(sa.select(m.admin_users).where(m.admin_users.c.id == record["admin_id"]).with_for_update()).mappings().one()
    # Lock the account first so simultaneous resets cannot deadlock each other.
    valid = db.scalar(sa.select(m.password_resets.c.id).where(m.password_resets.c.id == record["id"],
        m.password_resets.c.used_at.is_(None), m.password_resets.c.expires_at > now()).with_for_update())
    if not valid:
        raise HTTPException(400, "Link inválido ou expirado. Solicite outro link.")
    if not user["active"]:
        raise HTTPException(400, "Link inválido ou expirado. Solicite outro link.")
    db.execute(m.admin_users.update().where(m.admin_users.c.id == user["id"]).values(password_hash=hasher.hash(body.password)))
    db.execute(m.password_resets.update().where(m.password_resets.c.admin_id == user["id"], m.password_resets.c.used_at.is_(None)).values(used_at=now()))
    db.execute(m.admin_sessions.update().where(m.admin_sessions.c.admin_id == user["id"]).values(revoked_at=now()))
    audit(db, "auth.password_reset", user["id"], entity_id=user["id"])
    db.commit()
    return {"message": "Senha atualizada. Entre novamente."}


@router.get("/dashboard")
def dashboard(user=Depends(authenticated), db: Session = Depends(get_db)):
    if db.scalar(sa.select(m.site_settings.c.id).where(m.site_settings.c.key=='cms_initialized')):
        from app.cms_dashboard import read_dashboard
        return read_dashboard(db)
    def count(table, *conditions):
        return db.scalar(sa.select(sa.func.count()).select_from(table).where(*conditions))
    counts = {"projects": count(m.projects, m.projects.c.archived_at.is_(None)),
        "publishedArticles": count(m.articles, m.articles.c.status == "published"),
        "draftArticles": count(m.articles, m.articles.c.status == "draft"),
        "videos": count(m.videos, m.videos.c.archived_at.is_(None)),
        "experiences": count(m.experiences, m.experiences.c.archived_at.is_(None)),
        "messages": count(m.contact_messages, m.contact_messages.c.status == "new")}
    recent, scheduled = [], []
    for table, label, title in [(m.projects,"Projeto",m.projects.c.name), (m.articles,"Artigo",m.articles.c.slug),
        (m.videos,"Vídeo",m.videos.c.title), (m.experiences,"Experiência",m.experiences.c.company), (m.cases,"Case",m.cases.c.title)]:
        rows = db.execute(sa.select(table.c.id, title.label("title"), table.c.updated_at).order_by(table.c.updated_at.desc()).limit(5)).mappings()
        recent.extend([{**dict(row), "type":label} for row in rows])
        if "scheduled_at" in table.c:
            rows = db.execute(sa.select(title.label("title"), table.c.scheduled_at).where(table.c.status=="scheduled").order_by(table.c.scheduled_at).limit(10)).mappings()
            scheduled.extend([{**dict(row), "type":label} for row in rows])
    recent.sort(key=lambda row: row["updated_at"], reverse=True)
    scheduled.sort(key=lambda row: row["scheduled_at"] or now())
    return {"counts":counts,"recent":recent[:8],"scheduled":scheduled[:10],"analyticsConnected":False,
        "smtpConfigured":get_settings().smtp_configured}


@router.get("/audit")
def audit_list(user=Depends(authenticated), db: Session = Depends(get_db)):
    return [dict(row) for row in db.execute(sa.select(m.audit_logs.c.id, m.audit_logs.c.action,
        m.audit_logs.c.entity_type, m.audit_logs.c.created_at).order_by(m.audit_logs.c.created_at.desc()).limit(50)).mappings()]
