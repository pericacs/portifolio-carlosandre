"""Criação explícita do administrador; nenhuma credencial padrão."""
import getpass
import sys
from datetime import datetime, timezone
from argon2 import PasswordHasher, Type
from email_validator import validate_email, EmailNotValidError
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db import get_engine
from app.models import admin_users, audit_logs, admin_sessions, password_resets, auth_rate_limits


def create_admin():
    try:
        email = validate_email(input("E-mail do administrador: ").strip(), check_deliverability=False).normalized.lower()
    except EmailNotValidError:
        sys.exit("E-mail inválido.")
    password = getpass.getpass("Senha (mínimo 14 caracteres): ")
    if len(password) < 14 or password != getpass.getpass("Confirme a senha: "):
        sys.exit("Senha curta ou confirmação diferente. Nenhuma conta criada.")
    with Session(get_engine()) as session:
        if session.scalar(select(admin_users.c.id).where(admin_users.c.email == email)):
            sys.exit("Este administrador já existe. Nenhuma alteração realizada.")
        admin_id = session.execute(admin_users.insert().values(
            email=email, password_hash=PasswordHasher(type=Type.ID).hash(password)
        ).returning(admin_users.c.id)).scalar_one()
        session.execute(audit_logs.insert().values(actor_id=admin_id, action="admin.created", entity_type="admin_users", entity_id=admin_id))
        session.commit()
    print("Administrador criado. Acesse /admin/login no endereço do seu portfólio.")


def prune_auth():
    """Remover apenas tokens/contadores expirados; preservar auditoria e contas."""
    current = datetime.now(timezone.utc)
    with get_engine().begin() as connection:
        for table in (admin_sessions, password_resets, auth_rate_limits):
            connection.execute(table.delete().where(table.c.expires_at < current))
    print("Registros de autenticação expirados removidos. Auditoria preservada.")


if __name__ == "__main__":
    if sys.argv[1:] == ["create-admin"]:
        create_admin()
    elif sys.argv[1:] == ["prune-auth"]:
        prune_auth()
    else:
        sys.exit("Uso: python -m app.cli {create-admin|prune-auth}")
