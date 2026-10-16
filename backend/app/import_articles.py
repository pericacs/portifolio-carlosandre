"""Idempotent import of the author's approved LinkedIn content; does not overwrite drafts."""
import json,hashlib,shutil
from pathlib import Path
from uuid import uuid5,NAMESPACE_URL
import sqlalchemy as sa
from app import models as m
from app.cms import UPLOAD_ROOT,refs,revision,publish_entry
from app.cms_schema import validate

def install(db):
 root=Path(__file__).parent/'data/articles'
 mapping={}
 for a in json.loads((root/'manifest.json').read_text()):
  source=root/a['file'];raw=source.read_bytes();assert hashlib.sha256(raw).hexdigest()==a['sha256']
  mid=uuid5(NAMESPACE_URL,'portfolio-article:'+a['sha256']);key=str(mid)+source.suffix
  if not db.scalar(sa.select(m.media_assets.c.id).where(m.media_assets.c.id==mid)):
   UPLOAD_ROOT.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,UPLOAD_ROOT/key)
   db.execute(m.media_assets.insert().values(id=mid,storage_key=key,original_name=a['file'],mime_type=a['mime'],size_bytes=len(raw),width=a['width'],height=a['height'],sha256=a['sha256']))
  mapping['ASSET:'+a['file']]='/api/media/'+str(mid)
 text=(root/'content.json').read_text()
 for old,new in mapping.items():text=text.replace(old,new)
 count=0
 for supplied in json.loads(text):
  row=db.execute(sa.select(m.cms_entries).where(m.cms_entries.c.module=='artigos',sa.or_(m.cms_entries.c.slug==supplied['slug'],m.cms_entries.c.data['originalUrl'].astext==supplied['originalUrl']))).mappings().first()
  if row:continue # Preserve existing edits, publication state, and deleted records.
  data=validate('artigos',supplied)
  row=db.execute(m.cms_entries.insert().values(module='artigos',slug=data['slug'],title=data['title'],data=data).returning(m.cms_entries)).mappings().one()
  refs(db,row['id'],'artigos',data,'draft');revision(db,row,'linkedin_import',None);publish_entry(db,row,None);count+=1
 db.commit();print(f'{count} articles/insights imported; existing entries and drafts preserved.')
if __name__=='__main__':
 from sqlalchemy.orm import Session
 from app.db import get_engine
 with Session(get_engine()) as db:install(db)
