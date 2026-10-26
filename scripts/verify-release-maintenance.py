"""Discardable PostgreSQL proof of targeted publication/rollback and draft safety."""
import subprocess,uuid,time
from pathlib import Path
root=Path(__file__).resolve().parents[1];name='portfolio-maintenance-'+uuid.uuid4().hex[:10]
env=['-e','POSTGRES_USER=stage','-e','POSTGRES_DB=stage','-e','POSTGRES_PASSWORD=synthetic-maintenance-test-password','-e','DB_HOST=db']
def run(*args,**kwargs):return subprocess.run(['docker',*args],capture_output=True,text=True,check=True,**kwargs).stdout
code=r'''
import importlib.util,io,json,contextlib,sys
import sqlalchemy as sa
from sqlalchemy.orm import Session
from app import models as m,cms
from app.db import get_engine
from app.import_cms import import_content
spec=importlib.util.spec_from_file_location('maintenance','/release.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
with Session(get_engine()) as db:
    import_content(db)
    from app.admin import hasher
    db.execute(m.admin_users.insert().values(email='maintenance@example.com',password_hash=hasher.hash('Synthetic-unused-password-32')))
    row=h.target(db);data={**row['data'],'body':'<p>DRAFT_SENTINEL_MUST_NOT_PUBLISH</p>'}
    row=db.execute(m.cms_entries.update().where(m.cms_entries.c.id==row['id']).values(data=data,version=row['version']+1).returning(m.cms_entries)).mappings().one();cms.revision(db,row,'fixture',None);db.commit()
def call(mode,release,payload=None):
    out=io.StringIO();old=sys.stdin;sys.stdin=io.StringIO(json.dumps(payload))
    try:
        with contextlib.redirect_stdout(out):h.execute(mode,release)
    finally:sys.stdin=old
    return out.getvalue()
def snap():return json.loads(call('snapshot','proof'))
before=snap();call('apply','first',before);after=snap()
assert 'DRAFT_SENTINEL' in after['target']['data']['body'] and 'DRAFT_SENTINEL' not in after['target']['published_data']['body']
call('verify','first',before)
assert json.loads(call('apply','retry',after))['changed'] is False
call('rollback','first',before);restored=snap()
assert restored['target']['data']==before['target']['data'] and restored['target']['published_data'] is None and restored['others_hash']==before['others_hash']
call('rollback','first',before)
with Session(get_engine()) as db:
    row=h.target(db,True);public={**row['data'],'title':'Previous public title','body':'<p>Previous public content only.</p>'};cms.publish_entry(db,row,None,public);db.commit()
before=snap();call('apply','published',before);after=snap()
assert after['target']['published_data']['body']=='<p>Previous public content only.</p>'
call('rollback','published',before);assert snap()['target']['published_data']==before['target']['published_data']
before=snap();call('apply','concurrent',before)
with Session(get_engine()) as db:
    row=h.target(db,True);data={**row['data'],'description':'Later operator edit'}
    db.execute(m.cms_entries.update().where(m.cms_entries.c.id==row['id']).values(data=data,version=row['version']+1));db.commit()
try:call('rollback','concurrent',before)
except AssertionError:pass
else:raise AssertionError('Concurrent edit was overwritten')
assert snap()['target']['data']['description']=='Later operator edit'
print('PASS: pending drafts never published; previous publication retained; idempotency; exact targeted rollback; concurrent edits protected; other CMS unchanged')
'''
try:
    run('network','create','--internal',name);run('volume','create',name)
    run('run','-d','--name',name,'--network',name,'--network-alias','db',*env,'-v',name+':/var/lib/postgresql/data','postgres:16-alpine')
    for _ in range(60):
        if subprocess.run(['docker','exec',name,'pg_isready','-U','stage'],capture_output=True).returncode==0:break
        time.sleep(1)
    args=['run','--rm','--network',name,*env,'-v',str(root/'scripts/production/portfolio-release.py')+':/release.py:ro','carlosandre-production-check-backend']
    run(*args,'alembic','upgrade','head');print(run(*args,'python','-c',code))
except subprocess.CalledProcessError as error:
    print(error.stdout);print(error.stderr);raise
finally:
    subprocess.run(['docker','rm','-f',name],capture_output=True)
    subprocess.run(['docker','volume','rm',name],capture_output=True)
    subprocess.run(['docker','network','rm',name],capture_output=True)
