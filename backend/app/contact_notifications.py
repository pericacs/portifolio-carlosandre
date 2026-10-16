"""Persisted contact notifications, serialized across API and worker retries."""
from datetime import timedelta
from types import SimpleNamespace
import sqlalchemy as sa
from fastapi import HTTPException
from app import models as m
from app.admin import now,audit
from app.contact_mail import send_contact

def deliver(db,message_id):
 job=db.execute(sa.select(m.contact_notifications).where(m.contact_notifications.c.message_id==message_id).with_for_update(skip_locked=True)).mappings().first()
 if not job:db.commit();return 'pending'
 if job['sent_at']:db.commit();return 'sent'
 row=db.execute(sa.select(m.contact_messages).where(m.contact_messages.c.id==message_id)).mappings().one()
 try:send_contact(SimpleNamespace(**row))
 except HTTPException as error:
  db.execute(m.contact_notifications.update().where(m.contact_notifications.c.id==job['id']).values(attempts=job['attempts']+1,next_attempt_at=now()+timedelta(minutes=min(60,2**min(job['attempts']+1,6)))))
  audit(db,'contact.smtp_unconfigured' if error.status_code==503 else 'contact.notification_failed',entity_type='contact_messages',entity_id=message_id)
  db.commit();return 'pending'
 db.execute(m.contact_notifications.update().where(m.contact_notifications.c.id==job['id']).values(attempts=job['attempts']+1,sent_at=now()))
 db.execute(m.contact_messages.update().where(m.contact_messages.c.id==message_id).values(notified_at=now()))
 audit(db,'contact.notification_sent',entity_type='contact_messages',entity_id=message_id)
 db.commit();return 'sent'
