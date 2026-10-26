"""Single public article policy: eligibility, effective publication and pagination."""
import sqlalchemy as sa
from app import models as m


def first_publications():
    return (sa.select(m.cms_revisions.c.entry_id,sa.func.min(m.cms_revisions.c.created_at).label('first_published_at'))
            .where(m.cms_revisions.c.action=='publish')
            .group_by(m.cms_revisions.c.entry_id).subquery())


def eligibility():
    e=m.cms_entries
    return (e.c.module=='artigos',e.c.published_data.is_not(None),e.c.deleted_at.is_(None),e.c.status!='archived',
            e.c.published_data['visible'].as_boolean().is_not(False),e.c.published_data['planned'].as_boolean().is_not(True))


def article_query():
    e=m.cms_entries;first=first_publications()
    # CMS validates ISO dates. An editorial date is independent of record creation
    # and edits. Historical publish revisions repair the fallback without DB writes.
    editorial=sa.cast(sa.func.nullif(e.c.published_data['publishedDate'].astext,''),sa.Date)
    editorial=sa.cast(editorial,sa.DateTime()).op('AT TIME ZONE')('UTC')
    effective=sa.func.coalesce(editorial,sa.func.least(first.c.first_published_at,e.c.published_at))
    return (sa.select(e.c.id,e.c.source_key,e.c.published_data,effective.label('effective_published_at'))
            .outerjoin(first,e.c.id==first.c.entry_id).where(*eligibility())
            .order_by(effective.desc().nulls_last(),e.c.created_at.desc(),e.c.id.desc()))


def published_articles(db,limit=None,offset=0):
    query=article_query()
    if limit is not None:query=query.limit(limit)
    if offset:query=query.offset(offset)
    result=[]
    for row in db.execute(query).mappings():
        data=dict(row['published_data'])
        if not data.get('publishedDate') and row['effective_published_at']:
            data['publishedDate']=row['effective_published_at'].date().isoformat()
        result.append({**data,'id':str(row['id']),'sourceKey':row['source_key']})
    return result


def publication_instant(db,row,fallback):
    first=db.scalar(sa.select(sa.func.min(m.cms_revisions.c.created_at)).where(m.cms_revisions.c.entry_id==row['id'],m.cms_revisions.c.action=='publish'))
    known=[value for value in (first,row['published_at']) if value is not None]
    return min(known) if known else fallback
