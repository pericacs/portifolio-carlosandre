"""Importação idempotente: nunca sobrescreve registros já editados."""
import json
import uuid
from pathlib import Path
import sqlalchemy as sa
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from app import models as m
from app.db import get_engine
from app.cms_schema import validate
from app.cms import refs,revision
from app.admin import now


def import_content(db):
    source=json.loads(Path(__file__).with_name('data').joinpath('cms_initial.json').read_text(encoding='utf8'))
    # Stable UUIDs make relation mapping repeatable, even after partial deployments.
    ids={x['source_key']:uuid.uuid5(uuid.NAMESPACE_URL,'portfolio-cms:'+x['source_key']) for x in source}
    count=0
    for item in source:
        if db.scalar(sa.select(m.cms_entries.c.id).where(m.cms_entries.c.source_key==item['source_key'])):continue
        raw=item['data'].copy()
        for key,value in raw.items():
            if isinstance(value,str) and value.startswith('SOURCE:'):raw[key]=str(ids[value[7:]])
        data=validate(item['module'],raw)
        if '_legacy' in raw:data['_legacy']=raw['_legacy']
        # Import never publishes. Existing approved static pages remain the baseline
        # until their corresponding records are explicitly reviewed and published.
        row=db.execute(m.cms_entries.insert().values(id=ids[item['source_key']],source_key=item['source_key'],module=item['module'],slug=data.get('slug','main'),title=data['title'],data=data,status='draft').returning(m.cms_entries)).mappings().one()
        refs(db,row['id'],row['module'],data,'draft')
        revision(db,row,'import',None);count+=1
    db.execute(insert(m.site_settings).values(key='cms_initialized',value={'version':1,'mode':'approved-baseline-with-published-overrides'}).on_conflict_do_nothing(index_elements=['key']))
    db.commit();return count


if __name__=='__main__':
    with Session(get_engine()) as db:print('Conteúdos importados:',import_content(db))
