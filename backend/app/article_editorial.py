"""Transaction-scoped article ownership. Acquire before entry row locks."""
import sqlalchemy as sa
from app import models as m


def lock_editorial(db):
    db.execute(sa.text('SELECT pg_advisory_xact_lock(73194, 1)'))


def replace_editorial(db, row, payload, actor):
    from app.cms import revision
    lock_editorial(db)
    flags=[key for key in ('featured','spotlight') if payload.get(key)]
    if not flags or payload.get('planned') or payload.get('visible') is False:return
    previous=db.execute(sa.select(m.cms_entries).where(
        m.cms_entries.c.module=='artigos',m.cms_entries.c.id!=row['id'],
        m.cms_entries.c.deleted_at.is_(None),m.cms_entries.c.published_data.is_not(None)
    ).order_by(m.cms_entries.c.id).with_for_update()).mappings().all()
    for old in previous:
        cleared=[key for key in flags if old['published_data'].get(key)]
        if not cleared:continue
        # Only ownership flags change; content, publication instant and pending
        # draft edits survive. Existing revisions are never rewritten.
        data={**old['data'],**dict.fromkeys(cleared,False)}
        published={**old['published_data'],**dict.fromkeys(cleared,False)}
        updated=db.execute(m.cms_entries.update().where(m.cms_entries.c.id==old['id']).values(
            data=data,published_data=published,version=old['version']+1,editor_id=actor
        ).returning(m.cms_entries)).mappings().one()
        revision(db,updated,'editorial_replaced',actor)


def editorial_state(db):
    owners={'featured':[],'spotlight':[]}
    for row in db.execute(sa.select(m.cms_entries.c.id,m.cms_entries.c.published_data).where(
        m.cms_entries.c.module=='artigos',m.cms_entries.c.deleted_at.is_(None),
        m.cms_entries.c.published_data.is_not(None),m.cms_entries.c.status!='archived'
    )).mappings():
        data=row['published_data']
        if data.get('planned') or data.get('visible') is False:continue
        for key in owners:
            if data.get(key):owners[key].append({'id':str(row['id']),'title':data['title']})
    return owners
