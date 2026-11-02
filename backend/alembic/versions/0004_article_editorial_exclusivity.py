"""Exclusive article flags; reconcile legacy duplicates without removing articles."""
from alembic import op
import sqlalchemy as sa
from uuid import uuid4

revision='0004'
down_revision='0003'
branch_labels=None
depends_on=None


def upgrade():
    db=op.get_bind()
    db.execute(sa.text('SELECT pg_advisory_xact_lock(73194, 1)'))
    meta=sa.MetaData()
    entries=sa.Table('cms_entries',meta,autoload_with=db)
    revisions=sa.Table('cms_revisions',meta,autoload_with=db)
    date=sa.func.coalesce(sa.func.nullif(entries.c.published_data['publishedDate'].astext,''),sa.cast(entries.c.published_at,sa.String))
    rows=db.execute(sa.select(entries).where(entries.c.module=='artigos',entries.c.published_data.is_not(None),entries.c.deleted_at.is_(None)).order_by(date.desc().nulls_last(),entries.c.id.desc()).with_for_update()).mappings().all()
    owned=set()
    for row in rows:
        published=dict(row['published_data']);data=dict(row['data']);cleared=[]
        for flag in ('featured','spotlight'):
            if not published.get(flag):continue
            if flag in owned or published.get('planned') or published.get('visible') is False or row['status']=='archived':
                published[flag]=False;data[flag]=False;cleared.append(flag)
            else:owned.add(flag)
        if cleared:
            version=row['version']+1
            db.execute(entries.update().where(entries.c.id==row['id']).values(published_data=published,data=data,version=version))
            # Preserve both old snapshots in the journal before reconciliation.
            db.execute(revisions.insert().values(id=uuid4(),entry_id=row['id'],version=version,action='editorial_reconciled',snapshot={**row['data'],'_previousPublishedData':row['published_data']}))
    for flag in ('featured','spotlight'):
        op.execute(sa.text(f"CREATE UNIQUE INDEX uq_article_{flag}_published ON cms_entries ((1)) WHERE module='artigos' AND deleted_at IS NULL AND published_data IS NOT NULL AND published_data->>'{flag}'='true'"))


def downgrade():
    for flag in ('featured','spotlight'):op.drop_index(f'uq_article_{flag}_published',table_name='cms_entries')
    # Reconciliation history remains available; do not reintroduce duplicate flags.
