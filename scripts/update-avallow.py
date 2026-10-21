"""Targeted CMS draft update. Dry-run by default; retains OnStar ID/history.

Runs inside the explicitly selected local portfolio backend, never over SSH.
"""
import argparse,json,subprocess
from pathlib import Path

CODE=r'''
import json,sys,argparse
import sqlalchemy as sa
from sqlalchemy.orm import Session
from app import models as m,cms
from app.db import get_engine
p=argparse.ArgumentParser();p.add_argument('--expected-version',type=int,required=True);p.add_argument('--apply',action='store_true');args=p.parse_args()
patch=json.load(sys.stdin)
assert set(patch)=={'title','description','tags','developmentStage','cover'}
with Session(get_engine()) as db:
    row=db.execute(sa.select(m.cms_entries).where(m.cms_entries.c.module=='projetos',m.cms_entries.c.source_key=='initial:projetos:onstar-scd',m.cms_entries.c.deleted_at.is_(None)).with_for_update()).mappings().one()
    if all(row['data'].get(k)==v for k,v in patch.items()):
        print(json.dumps({'status':'already_updated','id':str(row['id']),'version':row['version']}));sys.exit()
    if row['version']!=args.expected_version:raise SystemExit('Version conflict; no changes applied')
    if row['scheduled_at'] is not None:raise SystemExit('Scheduled content; review before changing')
    data={**row['data'],**patch};data=cms.validate('projetos',data)
    if '_legacy' in row['data']:data['_legacy']=row['data']['_legacy']
    if not args.apply:
        print(json.dumps({'status':'plan_only','id':str(row['id']),'version':row['version'],'fields':patch},ensure_ascii=False));sys.exit()
    updated=db.execute(m.cms_entries.update().where(m.cms_entries.c.id==row['id'],m.cms_entries.c.version==row['version']).values(data=data,title=data['title'],version=row['version']+1,status='draft').returning(m.cms_entries)).mappings().one()
    cms.refs(db,row['id'],'projetos',data,'draft');cms.revision(db,updated,'update_avallow_card',None);db.commit()
    print(json.dumps({'status':'draft_updated','id':str(row['id']),'version':updated['version'],'published':False}))
'''

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--container',default='carlos-andre-portfolio-backend-1')
    p.add_argument('--expected-version',type=int,required=True)
    p.add_argument('--apply',action='store_true')
    args=p.parse_args()
    root=Path(__file__).resolve().parents[1]
    patch=json.loads((root/'frontend/src/data/avallow.json').read_text(encoding='utf8'))
    command=['docker','exec','-i',args.container,'python','-c',CODE,'--expected-version',str(args.expected_version)]
    if args.apply:command.append('--apply')
    subprocess.run(command,input=json.dumps(patch,ensure_ascii=False).encode('utf8'),check=True)
