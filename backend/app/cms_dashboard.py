import sqlalchemy as sa
from app import models as m
from app.config import get_settings

def read_dashboard(db):
    def count(module,*conditions):
        return db.scalar(sa.select(sa.func.count()).select_from(m.cms_entries).where(m.cms_entries.c.module==module,m.cms_entries.c.deleted_at.is_(None),*conditions))
    published=m.cms_entries.c.published_data.is_not(None)
    counts={'projects':count('projetos'),'publishedArticles':count('artigos',published,m.cms_entries.c.published_data['planned'].as_boolean().is_not(True)),
        'draftArticles':count('artigos',m.cms_entries.c.status=='draft'),'videos':count('videos'),'experiences':count('experiencias'),
        'messages':db.scalar(sa.select(sa.func.count()).select_from(m.contact_messages).where(m.contact_messages.c.status=='new')),
        'scheduled':db.scalar(sa.select(sa.func.count()).select_from(m.cms_entries).where(m.cms_entries.c.status=='scheduled',m.cms_entries.c.deleted_at.is_(None)))}
    recent=[{'id':str(r.id),'title':r.title,'type':r.module,'updated_at':r.updated_at} for r in db.execute(sa.select(m.cms_entries).where(m.cms_entries.c.deleted_at.is_(None)).order_by(m.cms_entries.c.updated_at.desc()).limit(8))]
    scheduled=[{'title':r.title,'type':r.module,'scheduled_at':r.scheduled_at} for r in db.execute(sa.select(m.cms_entries).where(m.cms_entries.c.status=='scheduled',m.cms_entries.c.deleted_at.is_(None)).order_by(m.cms_entries.c.scheduled_at).limit(10))]
    activities=[dict(r) for r in db.execute(sa.select(m.audit_logs.c.id,m.audit_logs.c.action,m.audit_logs.c.created_at).order_by(m.audit_logs.c.created_at.desc()).limit(8)).mappings()]
    return {'counts':counts,'recent':recent,'scheduled':scheduled,'activities':activities,'analyticsConnected':False,'smtpConfigured':get_settings().smtp_configured}
