"""Worker reiniciável: locks PostgreSQL evitam publicação/notificação duplicada."""
import logging
import time
from pathlib import Path
from datetime import timedelta
import sqlalchemy as sa
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app import models as m
from app.db import get_engine
from app.admin import now,audit
from app.cms import publish_entry
from app.contact_notifications import deliver
from app.config import get_settings

logger = logging.getLogger(__name__)
_smtp_missing = None

def notification_ready(settings):
    global _smtp_missing
    required = {'SMTP_HOST':settings.smtp_host, 'SMTP_FROM_EMAIL':settings.smtp_from,
                'SMTP_USERNAME':settings.smtp_user, 'SMTP_PASSWORD':settings.smtp_password}
    missing = tuple(key for key,value in required.items() if not value)
    if missing != _smtp_missing:
        if missing:
            logger.warning('Fila de contato pausada: faltam %s. Mensagens preservadas; configure e recrie backend e worker.', ', '.join(missing))
        else:
            logger.info('Configuracao SMTP carregada; fila de contato habilitada. Autenticacao ainda depende do provedor.')
        _smtp_missing = missing
    return not missing


def tick(db):
    rows=db.execute(sa.select(m.cms_entries).where(m.cms_entries.c.status=='scheduled',m.cms_entries.c.scheduled_at<=now(),m.cms_entries.c.deleted_at.is_(None)).with_for_update(skip_locked=True).limit(20)).mappings().all()
    for row in rows:
        try:
            with db.begin_nested(): publish_entry(db,row,row['editor_id'],row['scheduled_data'])
        except HTTPException:
            db.execute(m.cms_entries.update().where(m.cms_entries.c.id==row['id']).values(status='published' if row['published_data'] else 'draft',scheduled_at=None,scheduled_data=None))
            audit(db,'cms.schedule_failed',row['editor_id'],'cms_entries',row['id'])
    db.commit()
    config=db.scalar(sa.select(m.cms_entries.c.published_data).where(m.cms_entries.c.module=='configuracoes',m.cms_entries.c.published_data.is_not(None))) or {}
    settings=get_settings()
    if notification_ready(settings):
        jobs=list(db.scalars(sa.select(m.contact_notifications.c.message_id).where(m.contact_notifications.c.sent_at.is_(None),m.contact_notifications.c.attempts<5,m.contact_notifications.c.next_attempt_at<=now()).limit(5)))
        for message_id in jobs:
            result=deliver(db,message_id)
            logger.info('Notificacao de contato: %s', 'aceita pelo SMTP' if result=='sent' else 'pendente; consulte auditoria e tentativas no painel')
    cutoff=now()-timedelta(days=config.get('retentionDays',180))
    expired=sa.select(m.contact_messages.c.id).where(m.contact_messages.c.created_at<cutoff)
    db.execute(m.contact_notifications.delete().where(m.contact_notifications.c.message_id.in_(expired)))
    removed=db.execute(m.contact_messages.delete().where(m.contact_messages.c.created_at<cutoff)).rowcount
    if removed: audit(db,'contact.retention_cleanup',entity_type='contact_messages')
    db.execute(m.contact_tickets.delete().where(m.contact_tickets.c.expires_at<now()))
    db.execute(m.auth_rate_limits.delete().where(m.auth_rate_limits.c.expires_at<now()))
    db.commit()


if __name__=='__main__':
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
    while True:
        try:
            with Session(get_engine()) as db: tick(db)
            Path("/tmp/worker-heartbeat").touch()
        except Exception: logger.error('Falha no ciclo do worker; nova tentativa em 15 segundos. Detalhes internos omitidos.')
        time.sleep(15)
